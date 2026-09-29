# ========== REPOZITORIJUMI: pravila dozvola i dnevnik ==========
# Pravila stoje u poslovnoj `codium.db`, dnevnik u operativnoj
# `codium_ops.db` — dve baze, jer im se rast i bekap razlikuju.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.audit.models import AuditEntry
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)
from core.security.scope_gate import ScopeRule

# ==========          PRAVILA DOZVOLA          ==========

class ScopeRuleRepository:
    """Citanje i upis pravila koja hrane `ScopeGate`."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def list(self) -> list[ScopeRule]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                "SELECT id, actor, action, target, verdict, note "
                "FROM codium_scope_rules ORDER BY id"
            ).fetchall()
        return [
            ScopeRule(id=row[0], actor=row[1], action=row[2], target=row[3],
                      verdict=row[4], note=row[5])
            for row in rows
        ]

    def add(self, rule: ScopeRule) -> ScopeRule:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO codium_scope_rules (actor, action, target, "
                "verdict, note) VALUES (?, ?, ?, ?, ?)",
                (rule.actor, rule.action, rule.target, rule.verdict, rule.note),
            )
            novi_id = cursor.lastrowid
        # Frozen dataclass: novi primerak, ne izmena postojeceg.
        return ScopeRule(id=novi_id, actor=rule.actor, action=rule.action,
                         target=rule.target, verdict=rule.verdict,
                         note=rule.note)

    def delete(self, rule_id: int) -> None:
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                "DELETE FROM codium_scope_rules WHERE id = ?", (rule_id,)
            )


# ==========          DNEVNIK          ==========

class AuditRepository:
    """Upis i citanje dnevnika akcija.

    Namerno nema `update` ni `delete`: dnevnik koji se moze prepraviti nije
    dnevnik. Zadrzavanje starih unosa je posao odrzavanja, ne aplikacije.
    """

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_ops_database_path()

    def record(self, entry: AuditEntry) -> None:
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO codium_audit_log (
                    actor, action, target, verdict, outcome, detail, project_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (entry.actor, entry.action, entry.target, entry.verdict,
                 entry.outcome, entry.detail, entry.project_id),
            )

    def query(self, *, actor: str | None = None, action: str | None = None,
              limit: int = 100, offset: int = 0) -> list[AuditEntry]:
        uslovi: list[str] = []
        parametri: list[object] = []
        if actor is not None:
            uslovi.append("actor = ?")
            parametri.append(actor)
        if action is not None:
            uslovi.append("action = ?")
            parametri.append(action)

        where = f" WHERE {' AND '.join(uslovi)}" if uslovi else ""
        parametri.extend([limit, offset])

        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                "SELECT id, at, actor, action, target, verdict, outcome, "
                f"detail, project_id FROM codium_audit_log{where} "
                "ORDER BY id DESC LIMIT ? OFFSET ?",
                tuple(parametri),
            ).fetchall()

        return [
            AuditEntry(id=row[0], at=row[1], actor=row[2], action=row[3],
                       target=row[4], verdict=row[5], outcome=row[6],
                       detail=row[7], project_id=row[8])
            for row in rows
        ]
