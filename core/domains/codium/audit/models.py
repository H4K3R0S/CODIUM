# ========== MODELI DNEVNIKA ==========
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuditEntry:
    """Jedan upis u dnevnik: ko je sta trazio i sta je gate odgovorio.

    `outcome` je ishod same akcije (`ok` / `blocked` / `error`), dok je
    `verdict` odgovor gate-a. Nisu isto: dozvoljena akcija moze da pukne.
    """

    actor: str
    action: str
    verdict: str
    target: str = ""
    outcome: str = "ok"
    detail: str = ""
    project_id: int | None = None
    at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class Approval:
    """Molba koja ceka ljudsku odluku.

    Namerno ne zna ko je trazi: nosi aktera i pun poziv u `payload`, a vezu
    prema tekucem poslu drzi taj posao. Tako ista tabela sluzi agentima i
    kasnijim automatizacijama.
    """

    actor: str
    action: str
    target: str = ""
    payload: str = ""
    status: str = "pending"
    note: str = ""
    requested_at: str = ""
    decided_at: str | None = None
    id: int | None = None
