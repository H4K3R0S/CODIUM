# ========== SERVIS AUTOMATIZACIJE ==========
# Spaja dogadjaje koje podsistemi vec objavljuju sa akcijama koje vec umeju da
# se izvrse. Ne donosi nove sposobnosti — spaja postojece.
#
# Akter je `automation:<id>`, pa opasne akcije prolaze kroz ScopeGate iz E1 i
# ostavljaju trag u dnevniku bez ijednog novog reda ovde. Automatizacija po
# konstrukciji nema vise prava od agenta.
from __future__ import annotations

import json

from core.domains.codium.audit import AuditEntry, AuditRepository
from core.domains.codium.automations import actions as akcije_modul
from core.domains.codium.automations import conditions
from core.domains.codium.automations.actions import ActionContext
from core.domains.codium.automations.bus import EventBus, event_bus
from core.domains.codium.automations.models import (
    MAKS_DUBINA,
    POLJA_DOGADJAJA,
    Action,
    AutomationRun,
    Event,
    EventName,
    Rule,
    RunStatus,
    TestResult,
)
from core.domains.codium.automations.repository import (
    AutomationRunRepository,
    RuleRepository,
)
from core.security.scope_gate import ALLOW

AKCIJA_UPIS = "automation.write"
AKCIJA_OKIDANJE = "automation.fire"

# Prefiks aktera. Po njemu se prepoznaje i sopstvena posledica: dogadjaj sa
# ovakvim poreklom je proizvela automatizacija, ne svet.
PREFIKS_AKTERA = "automation:"


class AutomationError(RuntimeError):
    """Zajednicki koren gresaka ovog servisa."""


class RuleNotFound(AutomationError):
    """Trazeno pravilo ne postoji."""


class InvalidRule(AutomationError):
    """Pravilo nije ispravno: nepoznat dogadjaj, los uslov ili losa akcija."""


class AutomationService:
    """Pravila, njihovo okidanje i zastita od petlje."""

    def __init__(self, *, rules: RuleRepository,
                 runs: AutomationRunRepository,
                 audit: AuditRepository,
                 context: ActionContext | None = None,
                 bus: EventBus | None = None,
                 now: str | None = None) -> None:
        self._rules = rules
        self._runs = runs
        self._audit = audit
        self._context = context or ActionContext()
        self._bus = bus if bus is not None else event_bus
        self._now = now

    # ----------          PRETPLATA          ----------

    def subscribe(self) -> None:
        """Vezuje servis na razglas. Poziva se jednom, iz runtime-a."""

        self._bus.subscribe(self.handle)

    def unsubscribe(self) -> None:
        self._bus.unsubscribe(self.handle)

    # ----------          OKIDANJE          ----------

    def handle(self, event: Event) -> list[AutomationRun]:
        """Prolazi kroz pravila koja slusaju ovaj dogadjaj.

        Zastita od petlje je ovde, na tri mesta, jer je pravilo koje pali samo
        sebe najlaksi nacin da se sistem zaglavi.
        """

        # (3) Dubina lanca: dogadjaj -> akcija -> dogadjaj -> ... Dalje ne ide.
        if event.depth >= MAKS_DUBINA:
            return []

        ishodi: list[AutomationRun] = []
        for pravilo in self._rules.list(event.name, only_enabled=True):
            # (1) Sopstvena posledica: pravilo se ne pali na dogadjaj koji je
            # samo proizvelo. Bez ovoga jedno pravilo sa akcijom koja objavi
            # isti dogadjaj vrti se u krug.
            if event.origin == f"{PREFIKS_AKTERA}{pravilo.id}":
                continue

            ishod = self._oceni_i_izvrsi(pravilo, event)
            if ishod is not None:
                ishodi.append(ishod)
        return ishodi

    def _oceni_i_izvrsi(self, rule: Rule, event: Event) -> AutomationRun | None:
        try:
            pogadja = conditions.matches(rule.condition_expr, event.payload)
        except conditions.ConditionError as greska:
            # Pokvaren uslov ne sme tiho da preskoci pravilo: covek mora da
            # vidi da mu pravilo ne radi, i zasto.
            return self._zapisi(rule, event, RunStatus.FAILED,
                                f"uslov nije ispravan: {greska}", matched=False)

        if not pogadja:
            return self._zapisi(rule, event, RunStatus.SKIPPED,
                                "uslov nije ispunjen", matched=False)

        # (2) Ucestalost: prekoracenje GASI pravilo i javlja coveku.
        koliko = self._runs.count_recent(rule.id, rule.rate_limit_seconds,
                                         now=self._now)
        if koliko >= rule.rate_limit_n:
            self._rules.set_enabled(rule.id, False)
            poruka = (f"pravilo „{rule.name}“ se upalilo {koliko} puta u "
                      f"{rule.rate_limit_seconds} s i zato je ugaseno")
            self._javi(poruka)
            return self._zapisi(rule, event, RunStatus.RATE_LIMITED, poruka)

        return self._izvrsi(rule, event)

    def _izvrsi(self, rule: Rule, event: Event) -> AutomationRun:
        """Izvrsava akcije pravila redom. Jedna koja stane ne rusi ostale."""

        ctx = ActionContext(
            actor=f"{PREFIKS_AKTERA}{rule.id}",
            notifier=self._context.notifier,
            codium=self._context.codium,
            pipelines=self._context.pipelines,
            deployments=self._context.deployments,
            infrastructure=self._context.infrastructure,
            agents=self._context.agents,
            dev_log_dir=self._context.dev_log_dir,
        )

        opisi: list[str] = []
        status = RunStatus.DONE
        for akcija in rule.actions:
            try:
                opisi.append(f"{akcija.name}: "
                             f"{akcije_modul.execute(akcija.name, akcija.params, event, ctx)}")
            except Exception as greska:  # noqa: BLE001 - ishod se belezi, ne dize
                ime = type(greska).__name__
                # Cekanje na odobrenje NIJE kvar: molba je upisana, potez nije
                # izvrsen, i to je tacno ono sto kapija treba da uradi.
                if ime == "ApprovalPending":
                    opisi.append(f"{akcija.name}: ceka odobrenje")
                    status = RunStatus.WAITING_APPROVAL
                    continue
                opisi.append(f"{akcija.name}: greska — {greska}")
                if status != RunStatus.WAITING_APPROVAL:
                    status = RunStatus.FAILED

        self._trag(ctx.actor, AKCIJA_OKIDANJE, f"rule:{rule.id}",
                   "ok" if status == RunStatus.DONE else "error",
                   f"{event.name}: {'; '.join(opisi)}"[:400])
        return self._zapisi(rule, event, status, "; ".join(opisi))

    # ----------          PROBA          ----------

    def test(self, rule_id: int, payload: dict | None = None) -> TestResult:
        """Proba pravila nad izmisljenim dogadjajem. NE IZVRSAVA akcije.

        Postoji da se pravilo proveri bez posledica — pravilo koje isporucuje
        ne sme da se proverava isporukom.
        """

        pravilo = self._nadji(rule_id)
        dogadjaj = Event(name=pravilo.event, payload=payload or {})

        try:
            pogadja = conditions.matches(pravilo.condition_expr,
                                         dogadjaj.payload)
        except conditions.ConditionError as greska:
            return TestResult(matched=False, reason=f"uslov nije ispravan: {greska}")

        if not pogadja:
            return TestResult(matched=False, reason="uslov nije ispunjen")

        opisi = []
        for akcija in pravilo.actions:
            try:
                spec = akcije_modul.spec(akcija.name)
            except akcije_modul.UnknownAction as greska:
                opisi.append(str(greska))
                continue
            dodatak = " (traži odobrenje)" if spec.scope_action else ""
            opisi.append(f"{spec.label}{dodatak}")

        return TestResult(matched=True, reason="uslov je ispunjen",
                          would_run=opisi)

    # ----------          PRAVILA          ----------

    def rules(self, event: str | None = None) -> list[Rule]:
        return self._rules.list(event)

    def create_rule(self, rule: Rule, actor: str = "human") -> Rule:
        self._proveri(rule)
        upisano = self._rules.add(rule)
        self._trag(actor, AKCIJA_UPIS, f"rule:{upisano.id}", "ok",
                   f"{rule.event} -> {len(rule.actions)} akcija")
        return upisano

    def update_rule(self, rule_id: int, *, name: str, condition_expr: str,
                    actions: list[Action], enabled: bool, rate_limit_n: int,
                    rate_limit_seconds: int, actor: str = "human") -> Rule:
        postojece = self._nadji(rule_id)
        # Provera ide nad BUDUCIM stanjem: inace bi los uslov prosao samo zato
        # sto je stari bio dobar.
        self._proveri(Rule(
            name=name, event=postojece.event, condition_expr=condition_expr,
            actions=actions, project_id=postojece.project_id, enabled=enabled,
            rate_limit_n=rate_limit_n, rate_limit_seconds=rate_limit_seconds,
        ))
        izmenjeno = self._rules.update(
            rule_id, name=name, condition_expr=condition_expr, actions=actions,
            enabled=enabled, rate_limit_n=rate_limit_n,
            rate_limit_seconds=rate_limit_seconds)
        self._trag(actor, AKCIJA_UPIS, f"rule:{rule_id}", "ok", "izmenjeno")
        return izmenjeno

    def delete_rule(self, rule_id: int, actor: str = "human") -> None:
        self._nadji(rule_id)
        self._rules.delete(rule_id)
        self._trag(actor, AKCIJA_UPIS, f"rule:{rule_id}", "ok", "obrisano")

    def runs(self, rule_id: int | None = None,
             limit: int = 50) -> list[AutomationRun]:
        return self._runs.list(rule_id, limit)

    def last_run_at(self, rule_id: int) -> str | None:
        return self._runs.last_run_at(rule_id)

    # ----------          PROVERE          ----------

    def _proveri(self, rule: Rule) -> None:
        """Pravilo se proverava PRI UPISU, ne tek kad se upali.

        Pravilo koje puca tek na pravi dogadjaj puca u najgorem trenutku — a
        do tada covek misli da ga cuva.
        """

        if not rule.name.strip():
            raise InvalidRule("Pravilo trazi ime.")

        if rule.event not in POLJA_DOGADJAJA:
            raise InvalidRule(
                f"Nepoznat dogadjaj: {rule.event}. "
                f"Dozvoljeno: {', '.join(POLJA_DOGADJAJA)}.")

        try:
            stablo = conditions.parse(rule.condition_expr)
        except conditions.ConditionError as greska:
            raise InvalidRule(str(greska)) from greska

        # Uslov koji cita polje koje ovaj dogadjaj NE nosi nikad ne bi bio
        # tacan — to je greska u kucanju, ne pravilo koje se retko pali.
        poznata = set(POLJA_DOGADJAJA[rule.event])
        nepoznata = conditions.polja_u_izrazu(stablo) - poznata
        if nepoznata:
            raise InvalidRule(
                f"Dogadjaj `{rule.event}` ne nosi polja: "
                f"{', '.join(sorted(nepoznata))}. "
                f"Nosi: {', '.join(sorted(poznata))}.")

        if not rule.actions:
            raise InvalidRule("Pravilo bez ijedne akcije nista ne radi.")
        for akcija in rule.actions:
            akcije_modul.spec(akcija.name)   # nepoznata akcija pada ovde

        if rule.rate_limit_n < 1 or rule.rate_limit_seconds < 1:
            raise InvalidRule("Ogranicenje ucestalosti mora biti bar 1 na 1 s.")

    def _nadji(self, rule_id: int) -> Rule:
        pravilo = self._rules.get(rule_id)
        if pravilo is None:
            raise RuleNotFound(f"Pravilo {rule_id} ne postoji.")
        return pravilo

    # ----------          POMOCNO          ----------

    def _zapisi(self, rule: Rule, event: Event, status: str, detail: str,
                matched: bool = True) -> AutomationRun:
        return self._runs.record(AutomationRun(
            rule_id=rule.id,
            event_json=json.dumps({"name": event.name, "payload": event.payload,
                                   "origin": event.origin, "depth": event.depth},
                                  ensure_ascii=False),
            matched=matched, status=status, detail=detail[:500],
        ))

    def _javi(self, poruka: str) -> None:
        if self._context.notifier is not None:
            self._context.notifier.notify("CORE: automatizacija", poruka)

    def _trag(self, actor: str, action: str, target: str, outcome: str,
              detail: str) -> None:
        self._audit.record(AuditEntry(
            actor=actor, action=action, target=target, verdict=ALLOW,
            outcome=outcome, detail=detail,
        ))


def dostupni_dogadjaji() -> list[dict]:
    """Dogadjaji i polja koja nose. `/events` cita ovo."""

    return [{"name": str(ime), "fields": list(polja)}
            for ime, polja in POLJA_DOGADJAJA.items()]


def dostupne_akcije() -> list[dict]:
    """Akcije i dozvole koje traze. `/actions` cita ovo."""

    return [
        {
            "name": str(spec.name),
            "label": spec.label,
            "description": spec.description,
            "requires_approval": bool(spec.scope_action),
            "scope_action": spec.scope_action,
            "params": list(spec.params),
        }
        for spec in akcije_modul.SPECIFIKACIJE
    ]


# Namerno izvezeno: `EventName` treba i ekranu i testovima, a uvoziti modele
# zbog jednog nabrajanja je vise kucanja nego koristi.
__all__ = [
    "AKCIJA_OKIDANJE", "AKCIJA_UPIS", "AutomationError", "AutomationService",
    "EventName", "InvalidRule", "RuleNotFound", "dostupne_akcije",
    "dostupni_dogadjaji",
]
