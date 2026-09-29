# ========== RED ODOBRENJA ==========
# Kapija samo kaze `needs_approval`. Upis molbe je posao pozivaoca, pa je
# ovde — `ScopeGate` i dalje ne dodiruje bazu.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.audit.models import Approval
from core.domains.codium.runtime import codium_database_path

_KOLONE = ("id, actor, action, target, payload, status, note, "
           "requested_at, decided_at")


def _to_approval(row) -> Approval:
    return Approval(id=row[0], actor=row[1], action=row[2], target=row[3],
                    payload=row[4], status=row[5], note=row[6],
                    requested_at=row[7], decided_at=row[8])


class ApprovalRepository:
    """Citanje i odlucivanje o molbama za odobrenje."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def request(self, approval: Approval) -> Approval:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO codium_approvals (actor, action, target, payload) "
                "VALUES (?, ?, ?, ?)",
                (approval.actor, approval.action, approval.target,
                 approval.payload),
            )
            novi_id = cursor.lastrowid
        return self.get(novi_id)

    def pending(self) -> list[Approval]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                f"SELECT {_KOLONE} FROM codium_approvals "
                "WHERE status = 'pending' ORDER BY id DESC"
            ).fetchall()
        return [_to_approval(row) for row in rows]

    def get(self, approval_id: int) -> Approval | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_KOLONE} FROM codium_approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
        return _to_approval(row) if row else None

    def decide(self, approval_id: int, status: str,
               note: str = "") -> Approval | None:
        """Odlucuje o molbi koja jos ceka.

        Uslov `status = 'pending'` je u upitu namerno: vec odlucena molba se ne
        odlucuje ponovo, inace bi odbijen potez mogao naknadno da postane
        odobren. Vraca `None` kada nista nije promenjeno.
        """

        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "UPDATE codium_approvals "
                "SET status = ?, note = ?, decided_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND status = 'pending'",
                (status, note, approval_id),
            )
            promenjeno = cursor.rowcount
        return self.get(approval_id) if promenjeno else None
