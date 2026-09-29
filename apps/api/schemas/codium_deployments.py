# ========== SEME: ISPORUKA (CODIUM) ==========
from __future__ import annotations

from pydantic import BaseModel


class TargetCreateRequest(BaseModel):
    """Nov cilj isporuke. `kind` bira provajdera i vise se ne menja."""

    name: str
    kind: str
    config: dict[str, str] = {}
    project_id: int | None = None
    connector_id: int | None = None


class TargetUpdateRequest(BaseModel):
    """Menja se ime, konfiguracija i ukljucenost — ne i tip cilja."""

    name: str
    config: dict[str, str] = {}
    enabled: bool = True


class TargetResponse(BaseModel):
    id: int
    name: str
    kind: str
    config: dict[str, str] = {}
    project_id: int | None = None
    connector_id: int | None = None
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""


class TargetsResponse(BaseModel):
    targets: list[TargetResponse]


class TargetDeletedResponse(BaseModel):
    deleted: bool = True


class HealthResponse(BaseModel):
    healthy: bool
    detail: str = ""


class DeploymentResponse(BaseModel):
    id: int
    target_id: int
    run_id: int | None = None
    commit_sha: str | None = None
    status: str
    release_ref: str | None = None
    detail: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str = ""


class DeploymentsResponse(BaseModel):
    deployments: list[DeploymentResponse]


class DeployRequest(BaseModel):
    target_id: int
    run_id: int


class DeployableRunsResponse(BaseModel):
    """Pokretanja koja stvarno imaju paket na disku.

    Ekran nudi bas njih pod „Isporuci"; nuditi pokretanje bez paketa znacilo
    bi dugme koje uvek pada.
    """

    run_ids: list[int]


class ApprovalPendingResponse(BaseModel):
    """Odgovor kad kapija trazi ljudsku odluku.

    Nije greska nego stanje: molba je upisana, cilj nije dodirnut. Ekran po
    ovome vodi coveka na red odobrenja (E1).
    """

    detail: str
    deployment_id: int
    approval_id: int
