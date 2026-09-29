# ========== SQL SLOJ AUTOMATIZACIJE ==========
# Samo citanje i pisanje redova. Ocena uslova, kapija i zastita od petlje su u
# servisu — ovde ih namerno nema.
from __future__ import annotations

import json
from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.automations.models import (
    Action,
    AutomationRun,
    Rule,
    RunStatus,
)
from core.domains.codium.runtime import codium_database_path

_KOLONE_PRAVILO = ("id, name, event, condition_expr, actions_json, project_id, "
                   "enabled, rate_limit_n, rate_limit_seconds, created_at, "
                   "updated_at")
_KOLONE_OKIDANJE = "id, rule_id, event_json, matched, status, detail, at"


def _akcije(sirovo: str) -> list[Action]:
    """Cita `actions_json`. Krnj JSON u bazi ne sme da obori citanje liste."""

    try:
        vrednost = json.loads(sirovo or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(vrednost, list):
        return []

    akcije: list[Action] = []
    for stavka in vrednost:
        if isinstance(stavka, dict) and isinstance(stavka.get("name"), str):
            params = stavka.get("params")
            akcije.append(Action(name=stavka["name"],
                                 params=params if isinstance(params, dict) else {}))
    return akcije


def _u_json(akcije: list[Action]) -> str:
    return json.dumps([{"name": str(a.name), "params": a.params}
                       for a in akcije], ensure_ascii=False)


def _pravilo_od_reda(row) -> Rule:
    return Rule(
        id=row[0], name=row[1], event=row[2], condition_expr=row[3],
        actions=_akcije(row[4]), project_id=row[5], enabled=bool(row[6]),
        rate_limit_n=row[7], rate_limit_seconds=row[8],
        created_at=row[9], updated_at=row[10],
    )


def _okidanje_od_reda(row) -> AutomationRun:
    return AutomationRun(id=row[0], rule_id=row[1], event_json=row[2],
                         matched=bool(row[3]), status=row[4], detail=row[5],
                         at=row[6])


class RuleRepository:
    """Perzistencija pravila."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, rule: Rule) -> Rule:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_automation_rules (name, event, "
                "condition_expr, actions_json, project_id, enabled, "
                "rate_limit_n, rate_limit_seconds) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (rule.name, str(rule.event), rule.condition_expr,
                 _u_json(rule.actions), rule.project_id, int(rule.enabled),
                 rule.rate_limit_n, rule.rate_limit_seconds),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self, event: str | None = None,
             only_enabled: bool = False) -> list[Rule]:
        uslovi: list[str] = []
        parametri: list[object] = []
        if event is not None:
            uslovi.append("event = ?")
            parametri.append(event)
        if only_enabled:
            uslovi.append("enabled = 1")
        gde = (" WHERE " + " AND ".join(uslovi)) if uslovi else ""

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_PRAVILO} FROM codium_automation_rules{gde} "
                "ORDER BY id",
                tuple(parametri),
            ).fetchall()
        return [_pravilo_od_reda(red) for red in redovi]

    def get(self, rule_id: int) -> Rule | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_PRAVILO} FROM codium_automation_rules "
                "WHERE id = ?",
                (rule_id,),
            ).fetchone()
        return _pravilo_od_reda(red) if red else None

    def update(self, rule_id: int, *, name: str, condition_expr: str,
               actions: list[Action], enabled: bool, rate_limit_n: int,
               rate_limit_seconds: int) -> Rule | None:
        """Menja ono sto sme da se menja.

        `event` nije u listi namerno: pravilo koje promeni dogadjaj vise nije
        isto pravilo, a njegova istorija okidanja opisivala bi nesto drugo.
        """

        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_automation_rules SET name = ?, "
                "condition_expr = ?, actions_json = ?, enabled = ?, "
                "rate_limit_n = ?, rate_limit_seconds = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, condition_expr, _u_json(actions), int(enabled),
                 rate_limit_n, rate_limit_seconds, rule_id),
            )
        return self.get(rule_id)

    def set_enabled(self, rule_id: int, enabled: bool) -> None:
        """Pali i gasi pravilo. Odvojeno jer to radi i zastita od petlje."""

        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_automation_rules SET enabled = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (int(enabled), rule_id),
            )

    def delete(self, rule_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute("DELETE FROM codium_automation_rules WHERE id = ?",
                         (rule_id,))


class AutomationRunRepository:
    """Perzistencija okidanja — trag zasto se pravilo (ni)je upalilo."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def record(self, run: AutomationRun) -> AutomationRun:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_automation_runs (rule_id, event_json, "
                "matched, status, detail) VALUES (?, ?, ?, ?, ?)",
                (run.rule_id, run.event_json, int(run.matched),
                 str(run.status), run.detail),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def get(self, run_id: int) -> AutomationRun | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_OKIDANJE} FROM codium_automation_runs "
                "WHERE id = ?",
                (run_id,),
            ).fetchone()
        return _okidanje_od_reda(red) if red else None

    def list(self, rule_id: int | None = None,
             limit: int = 50) -> list[AutomationRun]:
        uslov = " WHERE rule_id = ?" if rule_id is not None else ""
        parametri = (rule_id, limit) if rule_id is not None else (limit,)
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_OKIDANJE} FROM codium_automation_runs{uslov} "
                "ORDER BY id DESC LIMIT ?",
                parametri,
            ).fetchall()
        return [_okidanje_od_reda(red) for red in redovi]

    def count_recent(self, rule_id: int, seconds: int,
                     now: str | None = None) -> int:
        """Koliko je puta pravilo IZVRSENO u poslednjih `seconds`.

        Broje se samo stvarna izvrsenja (`done`, `waiting_approval`, `failed`),
        ne i preskoceni dogadjaji: pravilo koje sto puta odluci da NE uradi
        nista nije se otelo, pa ne sme da bude ugaseno zbog toga.
        """

        osnova = f"'{now}'" if now else "'now'"
        with core_database_connection(self._database_path) as veza:
            return veza.execute(
                "SELECT COUNT(*) FROM codium_automation_runs "
                "WHERE rule_id = ? AND status IN (?, ?, ?) "
                f"AND at >= datetime({osnova}, '-' || ? || ' seconds')",
                (rule_id, str(RunStatus.DONE), str(RunStatus.WAITING_APPROVAL),
                 str(RunStatus.FAILED), seconds),
            ).fetchone()[0]

    def last_run_at(self, rule_id: int) -> str | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                "SELECT at FROM codium_automation_runs WHERE rule_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (rule_id,),
            ).fetchone()
        return red[0] if red else None
