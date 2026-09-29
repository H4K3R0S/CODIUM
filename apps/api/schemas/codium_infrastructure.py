# ========== SEME: INFRASTRUKTURA (CODIUM) ==========
from __future__ import annotations

from pydantic import BaseModel


class NodeCreateRequest(BaseModel):
    name: str
    kind: str = "local"
    connector_id: int | None = None


class NodeResponse(BaseModel):
    id: int
    name: str
    kind: str
    connector_id: int | None = None
    created_at: str = ""


class NodesResponse(BaseModel):
    nodes: list[NodeResponse]


class ServiceCreateRequest(BaseModel):
    """Nov servis. `kind` bira provajdera i vise se ne menja."""

    node_id: int
    name: str
    kind: str
    config: dict[str, str] = {}
    project_id: int | None = None
    auto_start: bool = False


class ServiceUpdateRequest(BaseModel):
    name: str
    config: dict[str, str] = {}
    project_id: int | None = None
    auto_start: bool = False


class ServiceStateResponse(BaseModel):
    """Zivo stanje. Ne cuva se u bazi — cita se od provajdera po zahtevu."""

    state: str
    pid: int | None = None
    detail: str = ""


class ServiceResponse(BaseModel):
    id: int
    node_id: int
    name: str
    kind: str
    config: dict[str, str] = {}
    project_id: int | None = None
    auto_start: bool = False
    created_at: str = ""
    updated_at: str = ""
    status: ServiceStateResponse


class ServicesResponse(BaseModel):
    services: list[ServiceResponse]


class ServiceDeletedResponse(BaseModel):
    deleted: bool = True


class DiscoveredResponse(BaseModel):
    """Predlog, ne zapis: registar ostaje prazan dok covek ne potvrdi."""

    name: str
    kind: str
    config: dict[str, str] = {}
    state: str
    detail: str = ""
    already_registered: bool = False


class DiscoverResponse(BaseModel):
    found: list[DiscoveredResponse]


class LogsResponse(BaseModel):
    lines: list[str]
