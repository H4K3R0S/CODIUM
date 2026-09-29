# ========== SQL SLOJ MERENJA ==========
# Dve baze, namerno: uzorci su najbrze rastuca tabela u sistemu i zive u
# `codium_ops.db`, a pravila i alarmi su poslovni podaci i zive u `codium.db`.
# Zato su i dva repozitorijuma, svaki sa svojom putanjom.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.monitoring.models import (
    Alert,
    AlertRule,
    AlertState,
    MetricSample,
    SeriesPoint,
)
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)

_KOLONE_UZORAK = "id, service_id, node_id, metric, value, at"
_KOLONE_PRAVILO = ("id, service_id, metric, comparison, threshold, "
                   "for_samples, enabled, created_at")
_KOLONE_ALARM = "id, rule_id, state, value, started_at, resolved_at"

# Koliko dugo se uzorci cuvaju u punoj rezoluciji, pa u petominutnim i dnevnim
# prosecima. Brojevi su iz faznog fajla; zadrzavanje NIJE opciono.
SATI_PUNA_REZOLUCIJA = 48
DANA_PETOMINUTNI = 30
DANA_MAKSIMUM = 365


def _uzorak_od_reda(row) -> MetricSample:
    return MetricSample(id=row[0], service_id=row[1], node_id=row[2],
                        metric=row[3], value=row[4], at=row[5])


def _pravilo_od_reda(row) -> AlertRule:
    return AlertRule(id=row[0], service_id=row[1], metric=row[2],
                     comparison=row[3], threshold=row[4], for_samples=row[5],
                     enabled=bool(row[6]), created_at=row[7])


def _alarm_od_reda(row) -> Alert:
    return Alert(id=row[0], rule_id=row[1], state=row[2], value=row[3],
                 started_at=row[4], resolved_at=row[5])


# Kako se vreme uzorka pretvara u oznaku kante — SQL izraz nad kolonom `at`,
# ne `strftime` oblik: petominutna kanta trazi da se minuti odseku na umnozak
# od pet, a to `strftime` sam ne ume.
_IZRAZ_KANTE = {
    "minute": "strftime('%Y-%m-%d %H:%M', at)",
    "5min": (
        "strftime('%Y-%m-%d %H:', at) || "
        "substr('0' || (CAST(strftime('%M', at) AS INTEGER) / 5 * 5), -2, 2)"
    ),
    "hour": "strftime('%Y-%m-%d %H:00', at)",
    "day": "strftime('%Y-%m-%d', at)",
}


class SampleRepository:
    """Uzorci merenja. Zivi u operativnoj bazi."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_ops_database_path()

    def append(self, samples: list[MetricSample]) -> None:
        """Upisuje seriju uzoraka u jednoj transakciji.

        Sakupljac uvek ima vise uzoraka odjednom (nekoliko servisa puta
        nekoliko metrika); red po red bi znacilo desetine transakcija na
        svakih 30 sekundi.
        """

        if not samples:
            return
        with core_database_connection(self._database_path) as veza:
            veza.executemany(
                "INSERT INTO codium_metric_samples (service_id, node_id, "
                "metric, value) VALUES (?, ?, ?, ?)",
                [(u.service_id, u.node_id, u.metric, float(u.value))
                 for u in samples],
            )

    def latest(self, service_id: int, metric: str,
               limit: int = 10) -> list[MetricSample]:
        """Poslednjih `limit` uzoraka, najnoviji prvi."""

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_UZORAK} FROM codium_metric_samples "
                "WHERE service_id = ? AND metric = ? ORDER BY id DESC LIMIT ?",
                (service_id, metric, limit),
            ).fetchall()
        return [_uzorak_od_reda(red) for red in redovi]

    def latest_value(self, service_id: int, metric: str) -> float | None:
        """Poslednja izmerena vrednost, ili None ako nikad nije merena."""

        poslednji = self.latest(service_id, metric, limit=1)
        return poslednji[0].value if poslednji else None

    def series(self, *, service_id: int, metric: str, bucket: str = "hour",
               since: str | None = None, until: str | None = None,
               limit: int = 500) -> list[SeriesPoint]:
        """Vremenski red, vec sazet u kante.

        Sazimanje ide u SQL-u, ne u Python-u: grafikon od 400 piksela ne treba
        hiljadu tacaka, a prenositi ih pa ih baciti znaci citati ceo period u
        memoriju bez razloga.
        """

        izraz = _IZRAZ_KANTE.get(bucket)
        if izraz is None:
            raise ValueError(
                f"Nepoznata velicina kante: {bucket}. "
                f"Dozvoljeno: {', '.join(_IZRAZ_KANTE)}.")

        uslovi = ["service_id = ?", "metric = ?"]
        parametri: list[object] = [service_id, metric]
        if since is not None:
            uslovi.append("at >= ?")
            parametri.append(since)
        if until is not None:
            uslovi.append("at <= ?")
            parametri.append(until)
        parametri.append(limit)

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {izraz} AS kanta, "
                "AVG(value), COUNT(*) FROM codium_metric_samples "
                f"WHERE {' AND '.join(uslovi)} "
                "GROUP BY kanta ORDER BY kanta DESC LIMIT ?",
                tuple(parametri),
            ).fetchall()

        # Upit ide unazad (da `LIMIT` uzme NAJNOVIJE kante), a grafikon se
        # crta unapred — zato se okrece ovde, a ne u pozivaocu.
        return [SeriesPoint(bucket=red[0], value=round(red[1], 2),
                            samples=red[2])
                for red in reversed(redovi)]

    def delete_for_service(self, service_id: int) -> int:
        """Brise uzorke obrisanog servisa. Kaskade nema — druga je baza."""

        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "DELETE FROM codium_metric_samples WHERE service_id = ?",
                (service_id,),
            )
            return kursor.rowcount

    def count(self) -> int:
        with core_database_connection(self._database_path) as veza:
            return veza.execute(
                "SELECT COUNT(*) FROM codium_metric_samples").fetchone()[0]

    # ----------          ZADRZAVANJE          ----------

    def compact(self, *, older_than_hours: int = SATI_PUNA_REZOLUCIJA,
                bucket: str = "5min", now: str | None = None) -> int:
        """Sazima uzorke starije od `older_than_hours` u prosek po kanti.

        Vraca koliko je redova nestalo. Radi u jednoj transakciji: pola
        sazetog i pola sirovog perioda bilo bi gore od oba.
        """

        izraz = _IZRAZ_KANTE.get(bucket)
        if izraz is None:
            raise ValueError(f"Nepoznata velicina kante: {bucket}.")

        granica = (f"datetime('{now}', '-{older_than_hours} hours')"
                   if now else f"datetime('now', '-{older_than_hours} hours')")

        with core_database_connection(self._database_path) as veza:
            pre = veza.execute(
                "SELECT COUNT(*) FROM codium_metric_samples "
                f"WHERE at < {granica}").fetchone()[0]
            if pre == 0:
                return 0

            # Prosek po kanti se prvo izracuna, pa se sirovi redovi obrisu, pa
            # se proseci vrate — tako se ne meša staro i novo u istom upitu.
            veza.execute(
                "CREATE TEMP TABLE IF NOT EXISTS _sazeto "
                "(service_id INTEGER, node_id INTEGER, metric TEXT, "
                " value REAL, at TEXT)")
            veza.execute("DELETE FROM _sazeto")
            veza.execute(
                "INSERT INTO _sazeto (service_id, node_id, metric, value, at) "
                "SELECT service_id, node_id, metric, AVG(value), "
                f"       MIN(at) FROM codium_metric_samples "
                f"WHERE at < {granica} "
                f"GROUP BY service_id, node_id, metric, {izraz}"
            )
            veza.execute(
                f"DELETE FROM codium_metric_samples WHERE at < {granica}")
            veza.execute(
                "INSERT INTO codium_metric_samples "
                "(service_id, node_id, metric, value, at) "
                "SELECT service_id, node_id, metric, value, at FROM _sazeto")
            posle = veza.execute("SELECT COUNT(*) FROM _sazeto").fetchone()[0]
            veza.execute("DELETE FROM _sazeto")

        return pre - posle

    def purge(self, *, older_than_days: int = DANA_MAKSIMUM,
              now: str | None = None) -> int:
        """Brise uzorke starije od `older_than_days`."""

        granica = (f"datetime('{now}', '-{older_than_days} days')"
                   if now else f"datetime('now', '-{older_than_days} days')")
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                f"DELETE FROM codium_metric_samples WHERE at < {granica}")
            return kursor.rowcount




class AlertRuleRepository:
    """Pravila alarma. Zive u poslovnoj bazi."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, rule: AlertRule) -> AlertRule:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_alert_rules (service_id, metric, "
                "comparison, threshold, for_samples, enabled) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (rule.service_id, rule.metric, str(rule.comparison),
                 float(rule.threshold), rule.for_samples, int(rule.enabled)),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self, service_id: int | None = None,
             only_enabled: bool = False) -> list[AlertRule]:
        uslovi: list[str] = []
        parametri: list[object] = []
        if service_id is not None:
            uslovi.append("service_id = ?")
            parametri.append(service_id)
        if only_enabled:
            uslovi.append("enabled = 1")
        gde = (" WHERE " + " AND ".join(uslovi)) if uslovi else ""

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_PRAVILO} FROM codium_alert_rules{gde} "
                "ORDER BY id",
                tuple(parametri),
            ).fetchall()
        return [_pravilo_od_reda(red) for red in redovi]

    def get(self, rule_id: int) -> AlertRule | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_PRAVILO} FROM codium_alert_rules WHERE id = ?",
                (rule_id,),
            ).fetchone()
        return _pravilo_od_reda(red) if red else None

    def update(self, rule_id: int, *, comparison: str, threshold: float,
               for_samples: int, enabled: bool) -> AlertRule | None:
        """Menja prag i uslov.

        `metric` i `service_id` nisu u listi namerno: pravilo koje promeni
        metriku vise nije isto pravilo, a alarmi vezani za njega bi opisivali
        merenje koje se vise ne radi.
        """

        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_alert_rules SET comparison = ?, threshold = ?, "
                "for_samples = ?, enabled = ? WHERE id = ?",
                (comparison, float(threshold), for_samples, int(enabled),
                 rule_id),
            )
        return self.get(rule_id)

    def delete(self, rule_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute("DELETE FROM codium_alert_rules WHERE id = ?",
                         (rule_id,))


class AlertRepository:
    """Alarmi. Zive u poslovnoj bazi, uz pravila."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def open_for_rule(self, rule_id: int) -> Alert | None:
        """Alarm koji jos gori za ovo pravilo, ako ga ima.

        Postoji da se isti alarm ne bi ponavljao dok traje — jedan kvar je
        jedan alarm, ma koliko uzoraka ga potvrdilo.
        """

        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_ALARM} FROM codium_alerts "
                "WHERE rule_id = ? AND state = ? ORDER BY id DESC LIMIT 1",
                (rule_id, str(AlertState.FIRING)),
            ).fetchone()
        return _alarm_od_reda(red) if red else None

    def fire(self, rule_id: int, value: float | None) -> Alert:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_alerts (rule_id, state, value) "
                "VALUES (?, ?, ?)",
                (rule_id, str(AlertState.FIRING), value),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def resolve(self, alert_id: int) -> Alert | None:
        """Gasi alarm koji jos gori. Vec razresen se ne razresava ponovo."""

        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_alerts SET state = ?, "
                "resolved_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND state = ?",
                (str(AlertState.RESOLVED), alert_id, str(AlertState.FIRING)),
            )
        return self.get(alert_id)

    def get(self, alert_id: int) -> Alert | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_ALARM} FROM codium_alerts WHERE id = ?",
                (alert_id,),
            ).fetchone()
        return _alarm_od_reda(red) if red else None

    def list(self, state: str | None = None, limit: int = 50) -> list[Alert]:
        uslov = " WHERE state = ?" if state else ""
        parametri = (state, limit) if state else (limit,)
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_ALARM} FROM codium_alerts{uslov} "
                "ORDER BY id DESC LIMIT ?",
                parametri,
            ).fetchall()
        return [_alarm_od_reda(red) for red in redovi]
