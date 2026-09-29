# ========== SERVIS MERENJA ==========
# Spaja tri stvari koje same po sebi ne znaju jedna za drugu: probe (mere),
# uzorke (cuvaju se) i pravila (ocenjuju). Jedino mesto koje zove dnevnik i
# notifikacije.
#
# Sam sakupljac (pozadinski zadatak) je u `collector.py` — ovde je jedan krug
# merenja, sinhron i pozivljiv, da moze i rucno („izmeri odmah") i iz petlje.
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass

from core.domains.codium.audit import AuditEntry, AuditRepository
from core.domains.codium.automations import bus
from core.domains.codium.infrastructure.models import (
    Service,
    ServiceKind,
    ServiceState,
)
from core.domains.codium.infrastructure.service import InfrastructureService
from core.domains.codium.monitoring import alerts as ocena
from core.domains.codium.monitoring.models import (
    Alert,
    AlertRule,
    AlertState,
    Metric,
    MetricSample,
    SeriesPoint,
)
from core.domains.codium.monitoring.probes import (
    probe_docker,
    probe_http,
    probe_process,
    probe_tcp,
)
from core.domains.codium.monitoring.repository import (
    AlertRepository,
    AlertRuleRepository,
    SampleRepository,
)
from core.security.scope_gate import ALLOW

AKCIJA_UPIS = "monitor.write"
AKCIJA_ALARM = "monitor.alert"

# Koliko proba sme da radi istovremeno. Probe su cekanje na mrezu, ne racun,
# pa niti kostaju malo — a bez njih jedan servis koji ne odgovara drzi ceo
# krug: na Windows-u veza ka zatvorenom portu ne biva odbijena nego se cuti
# do isteka roka, pa deset mrtvih servisa znaci dvadeset sekundi po krugu.
UPOREDO = 8


class MonitoringError(RuntimeError):
    """Zajednicki koren gresaka ovog servisa."""


class RuleNotFound(MonitoringError):
    """Trazeno pravilo ne postoji."""


class Notifier:
    """Ono cime servis javlja coveku. Podrazumevano cuti."""

    def notify(self, title: str, message: str) -> None:
        return None


@dataclass(frozen=True)
class ServiceOverview:
    """Poslednje poznato stanje jednog servisa, u jednom redu.

    Ekran zid plocica crta bas ovo, pa se racuna na serveru: racunati
    dostupnost u pregledacu znacilo bi poslati mu sve uzorke iz 24 sata.
    """

    service_id: int
    name: str
    kind: str
    state: str
    up: float | None
    latency_ms: float | None
    cpu_percent: float | None
    memory_mb: float | None
    # Udeo uzoraka u kojima je servis bio ziv, u poslednja 24 sata (0..1).
    uptime_24h: float | None
    firing_alerts: int


class MonitoringService:
    """Merenje servisa, cuvanje uzoraka i alarmi."""

    def __init__(self, *, samples: SampleRepository,
                 rules: AlertRuleRepository, alerts: AlertRepository,
                 infrastructure: InfrastructureService,
                 audit: AuditRepository,
                 notifier: Notifier | None = None,
                 probe_timeout: float = 5.0,
                 max_parallel: int = UPOREDO) -> None:
        self._samples = samples
        self._rules = rules
        self._alerts = alerts
        self._infra = infrastructure
        self._audit = audit
        self._notifier = notifier or Notifier()
        self._probe_timeout = probe_timeout
        self._max_parallel = max(1, max_parallel)

    # ----------          MERENJE          ----------

    def collect_once(self) -> int:
        """Jedan krug merenja svih servisa. Vraca broj upisanih uzoraka.

        Neuspela proba jednog servisa NE prekida krug — servis koji ne
        odgovara je bas ono sto merenje treba da zabelezi, a ne razlog da
        ostali ostanu neizmereni.
        """

        servisi = self._infra.services()
        if not servisi:
            return 0

        uzorci: list[MetricSample] = []
        radnika = min(self._max_parallel, len(servisi))
        with concurrent.futures.ThreadPoolExecutor(max_workers=radnika) as bazen:
            poslovi = {bazen.submit(self._izmeri, s): s for s in servisi}
            for posao in concurrent.futures.as_completed(poslovi):
                servis = poslovi[posao]
                try:
                    uzorci.extend(posao.result())
                except Exception as greska:  # noqa: BLE001 - krug mora da prezivi
                    uzorci.append(MetricSample(
                        metric=Metric.UP, value=0.0, service_id=servis.id))
                    self._trag("system", AKCIJA_ALARM, f"service:{servis.id}",
                               "error", str(greska))

        self._samples.append(uzorci)
        self.evaluate_rules()
        return len(uzorci)

    def _izmeri(self, service: Service) -> list[MetricSample]:
        """Bira probu po tipu servisa i po tome sta je u konfiguraciji.

        Docker i proces se mere svojom probom; sve ostalo sto ima port meri se
        preko porta. Servis koji ima i URL dobija HTTP probu, jer „port slusa"
        i „aplikacija odgovara" nisu isto.
        """

        config = service.config

        if service.kind == ServiceKind.LOCAL_DOCKER and config.get("container"):
            return probe_docker(config["container"], service_id=service.id).samples

        url = config.get("url", "").strip()
        if url:
            return probe_http(url, service_id=service.id,
                              timeout=self._probe_timeout).samples

        if service.kind == ServiceKind.LOCAL_PROCESS:
            stanje = self._infra.status(service)
            if stanje.pid is not None:
                return probe_process(stanje.pid, service_id=service.id).samples
            # Nema naseg procesa — port je jedino sto jos moze da se pita.

        port = config.get("port", "").strip()
        if port.isdigit():
            host = config.get("host", "127.0.0.1").strip() or "127.0.0.1"
            return probe_tcp(host, int(port), service_id=service.id,
                             timeout=self._probe_timeout).samples

        # Nista merljivo osim onoga sto infrastruktura vec zna.
        stanje = self._infra.status(service)
        ziv = 1.0 if stanje.state == ServiceState.RUNNING else 0.0
        return [MetricSample(metric=Metric.UP, value=ziv, service_id=service.id)]

    # ----------          ALARMI          ----------

    def evaluate_rules(self) -> list[Alert]:
        """Ocenjuje sva ukljucena pravila nad poslednjim uzorcima.

        Vraca alarme koji su se u ovom krugu PROMENILI (upalili ili ugasili) —
        ne sve koji gore, jer je promena ono na sta se reaguje.
        """

        promene: list[Alert] = []
        for pravilo in self._rules.list(only_enabled=True):
            if pravilo.service_id is None:
                continue
            promena = self._oceni_pravilo(pravilo)
            if promena is not None:
                promene.append(promena)
        return promene

    def _oceni_pravilo(self, rule: AlertRule) -> Alert | None:
        gori = self._alerts.open_for_rule(rule.id)
        poslednji = self._samples.latest(rule.service_id, rule.metric,
                                         limit=max(1, rule.for_samples))
        odluka = ocena.oceni(rule, poslednji, alarm_gori=gori is not None)

        if odluka == AlertState.FIRING:
            vrednost = poslednji[0].value if poslednji else None
            alarm = self._alerts.fire(rule.id, vrednost)
            poruka = ocena.opis(rule, vrednost)
            self._notifier.notify("CORE: alarm", poruka)
            self._trag("system", AKCIJA_ALARM, f"rule:{rule.id}", "error",
                       poruka)
            bus.publish("alert.fired", {
                "alert_id": alarm.id, "rule_id": rule.id,
                "service_id": rule.service_id, "metric": str(rule.metric),
                "value": vrednost,
            })
            return alarm

        if odluka == AlertState.RESOLVED and gori is not None:
            razresen = self._alerts.resolve(gori.id)
            self._trag("system", AKCIJA_ALARM, f"rule:{rule.id}", "ok",
                       f"razreseno: {ocena.opis(rule, poslednji[0].value)}")
            bus.publish("alert.resolved", {
                "alert_id": gori.id, "rule_id": rule.id,
                "service_id": rule.service_id, "metric": str(rule.metric),
            })
            return razresen

        return None

    # ----------          PRAVILA          ----------

    def rules(self, service_id: int | None = None) -> list[AlertRule]:
        return self._rules.list(service_id)

    def create_rule(self, rule: AlertRule, actor: str = "human") -> AlertRule:
        # Uslov se proverava odmah, ne tek pri prvoj oceni: pravilo sa
        # nepoznatim uslovom nikad ne bi upalilo alarm, a covek bi mislio da
        # ga cuva.
        ocena.krsi(0.0, rule.comparison, rule.threshold)
        if rule.for_samples < 1:
            raise MonitoringError("Polje `for_samples` mora biti bar 1.")

        upisano = self._rules.add(rule)
        self._trag(actor, AKCIJA_UPIS, f"rule:{upisano.id}", "ok",
                   f"{rule.metric} {rule.comparison} {rule.threshold:g}")
        return upisano

    def update_rule(self, rule_id: int, *, comparison: str, threshold: float,
                    for_samples: int, enabled: bool,
                    actor: str = "human") -> AlertRule:
        self._nadji_pravilo(rule_id)
        ocena.krsi(0.0, comparison, threshold)
        if for_samples < 1:
            raise MonitoringError("Polje `for_samples` mora biti bar 1.")

        izmenjeno = self._rules.update(rule_id, comparison=comparison,
                                       threshold=threshold,
                                       for_samples=for_samples, enabled=enabled)
        self._trag(actor, AKCIJA_UPIS, f"rule:{rule_id}", "ok", "izmenjeno")
        return izmenjeno

    def delete_rule(self, rule_id: int, actor: str = "human") -> None:
        self._nadji_pravilo(rule_id)
        self._rules.delete(rule_id)
        self._trag(actor, AKCIJA_UPIS, f"rule:{rule_id}", "ok", "obrisano")

    def alerts(self, state: str | None = None, limit: int = 50) -> list[Alert]:
        return self._alerts.list(state, limit)

    # ----------          CITANJE          ----------

    def series(self, *, service_id: int, metric: str, bucket: str = "hour",
               since: str | None = None, until: str | None = None,
               limit: int = 500) -> list[SeriesPoint]:
        try:
            return self._samples.series(service_id=service_id, metric=metric,
                                        bucket=bucket, since=since,
                                        until=until, limit=limit)
        except ValueError as greska:
            raise MonitoringError(str(greska)) from greska

    def overview(self) -> list[ServiceOverview]:
        """Poslednje stanje svih servisa, u jednom pozivu."""

        gore_po_pravilu = {a.rule_id for a in
                           self._alerts.list(str(AlertState.FIRING), limit=200)}
        pravila_po_servisu: dict[int, int] = {}
        for pravilo in self._rules.list():
            if pravilo.id in gore_po_pravilu and pravilo.service_id is not None:
                pravila_po_servisu[pravilo.service_id] = (
                    pravila_po_servisu.get(pravilo.service_id, 0) + 1)

        pregled: list[ServiceOverview] = []
        for servis in self._infra.services():
            stanje = self._infra.status(servis)
            pregled.append(ServiceOverview(
                service_id=servis.id,
                name=servis.name,
                kind=str(servis.kind),
                state=str(stanje.state),
                up=self._samples.latest_value(servis.id, Metric.UP),
                latency_ms=self._samples.latest_value(servis.id,
                                                      Metric.LATENCY_MS),
                cpu_percent=self._samples.latest_value(servis.id,
                                                       Metric.CPU_PERCENT),
                memory_mb=self._samples.latest_value(servis.id,
                                                     Metric.MEMORY_MB),
                uptime_24h=self._dostupnost(servis.id),
                firing_alerts=pravila_po_servisu.get(servis.id, 0),
            ))
        return pregled

    def _dostupnost(self, service_id: int) -> float | None:
        """Udeo vremena u kojem je servis bio ziv, u poslednja 24 sata.

        Racuna se iz dnevnih kanti `up` metrike — prosek nula i jedinica JESTE
        dostupnost, pa nema sta da se sabira posebno.
        """

        kante = self._samples.series(
            service_id=service_id, metric=Metric.UP, bucket="day", limit=2)
        if not kante:
            return None
        return round(kante[-1].value, 3)

    # ----------          ODRZAVANJE          ----------

    def maintain(self) -> dict[str, int]:
        """Zadrzavanje uzoraka. Poziva se jednom dnevno.

        Uzorak na 30 s za deset servisa je oko 29.000 redova dnevno — bez
        ovoga baza raste bez granice.
        """

        sazeto = self._samples.compact(older_than_hours=48, bucket="5min")
        dnevno = self._samples.compact(older_than_hours=24 * 30, bucket="day")
        obrisano = self._samples.purge(older_than_days=365)
        return {"compacted": sazeto, "daily": dnevno, "purged": obrisano}

    # ----------          POMOCNO          ----------

    def _nadji_pravilo(self, rule_id: int) -> AlertRule:
        pravilo = self._rules.get(rule_id)
        if pravilo is None:
            raise RuleNotFound(f"Pravilo {rule_id} ne postoji.")
        return pravilo

    def _trag(self, actor: str, action: str, target: str, outcome: str,
              detail: str) -> None:
        self._audit.record(AuditEntry(
            actor=actor, action=action, target=target, verdict=ALLOW,
            outcome=outcome, detail=detail,
        ))
