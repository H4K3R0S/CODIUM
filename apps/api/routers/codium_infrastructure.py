# ========== ROUTER: INFRASTRUKTURA (CODIUM) ==========
# Rute nose `actor="human"`. Lista servisa nosi i zivo stanje, jer ekran bez
# njega ne bi imao sta da pokaze — a stanje je kesirano u servisu, pa jedan
# otvoren ekran ne cacka Docker na svakih par sekundi.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas.codium_infrastructure import (
    DiscoveredResponse,
    DiscoverResponse,
    LogsResponse,
    NodeCreateRequest,
    NodeResponse,
    NodesResponse,
    ServiceCreateRequest,
    ServiceDeletedResponse,
    ServiceResponse,
    ServicesResponse,
    ServiceStateResponse,
    ServiceUpdateRequest,
)
from core.domains.codium.infrastructure.models import Node, Service
from core.domains.codium.infrastructure.providers.base import (
    ActionUnsupported,
    ServiceConfigError,
)
from core.domains.codium.infrastructure.service import (
    ActionDenied,
    ApprovalPending,
    InfrastructureError,
    InfrastructureService,
    NodeNotFound,
    ServiceNotFound,
    UnknownProvider,
)

router = APIRouter(
    prefix="/api/v1/codium/infrastructure",
    tags=["CODIUM Infrastruktura"],
)

COVEK = "human"


def get_service() -> InfrastructureService:
    from apps.api import codium_infrastructure_runtime
    return codium_infrastructure_runtime.get_service()


def _prevedi(greska: Exception) -> HTTPException:
    if isinstance(greska, (NodeNotFound, ServiceNotFound)):
        return HTTPException(status_code=404, detail=str(greska))
    # Molba je upisana i ceka coveka — 202 je jedini kod koji to opisuje bez
    # laganja: zahtev je prihvacen, a nista jos nije izvedeno.
    if isinstance(greska, ApprovalPending):
        return HTTPException(status_code=202, detail={
            "detail": str(greska), "approval_id": greska.approval_id,
        })
    if isinstance(greska, ActionDenied):
        return HTTPException(status_code=403, detail=str(greska))
    if isinstance(greska, (ServiceConfigError, UnknownProvider)):
        return HTTPException(status_code=400, detail=str(greska))
    # Potez koji ovaj provajder ne ume nije los zahtev nego stanje sveta:
    # `port_probe` se samo posmatra.
    if isinstance(greska, ActionUnsupported):
        return HTTPException(status_code=409, detail=str(greska))
    if isinstance(greska, InfrastructureError):
        return HTTPException(status_code=409, detail=str(greska))
    return HTTPException(status_code=500, detail=str(greska))


def _node_u_odgovor(node) -> NodeResponse:
    return NodeResponse(id=node.id, name=node.name, kind=str(node.kind),
                        connector_id=node.connector_id,
                        created_at=node.created_at)


def _stanje_u_odgovor(stanje) -> ServiceStateResponse:
    return ServiceStateResponse(state=str(stanje.state), pid=stanje.pid,
                                detail=stanje.detail)


def _servis_u_odgovor(servis, stanje) -> ServiceResponse:
    return ServiceResponse(
        id=servis.id, node_id=servis.node_id, name=servis.name,
        kind=str(servis.kind), config=servis.config,
        project_id=servis.project_id, auto_start=servis.auto_start,
        created_at=servis.created_at, updated_at=servis.updated_at,
        status=_stanje_u_odgovor(stanje),
    )


# ----------          NODE-OVI          ----------

@router.get("/nodes", response_model=NodesResponse)
def node_ovi(servis: InfrastructureService = Depends(get_service)) -> NodesResponse:
    return NodesResponse(nodes=[_node_u_odgovor(n) for n in servis.nodes()])


@router.post("/nodes", response_model=NodeResponse)
def nov_node(zahtev: NodeCreateRequest,
             servis: InfrastructureService = Depends(get_service)) -> NodeResponse:
    try:
        return _node_u_odgovor(servis.create_node(
            Node(name=zahtev.name, kind=zahtev.kind,
                 connector_id=zahtev.connector_id),
            actor=COVEK,
        ))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.post("/nodes/{node_id}/discover", response_model=DiscoverResponse)
def pronadji(node_id: int,
             servis: InfrastructureService = Depends(get_service),
             ) -> DiscoverResponse:
    try:
        nadjeni = servis.discover(node_id)
    except Exception as greska:
        raise _prevedi(greska) from greska
    return DiscoverResponse(found=[
        DiscoveredResponse(name=n.name, kind=str(n.kind), config=n.config,
                           state=str(n.state), detail=n.detail,
                           already_registered=n.already_registered)
        for n in nadjeni
    ])


# ----------          SERVISI          ----------

@router.get("/services", response_model=ServicesResponse)
def servisi(node_id: int | None = Query(default=None),
            project_id: int | None = Query(default=None),
            servis: InfrastructureService = Depends(get_service),
            ) -> ServicesResponse:
    return ServicesResponse(services=[
        _servis_u_odgovor(s, servis.status(s))
        for s in servis.services(node_id, project_id)
    ])


@router.post("/services", response_model=ServiceResponse)
def nov_servis(zahtev: ServiceCreateRequest,
               servis: InfrastructureService = Depends(get_service),
               ) -> ServiceResponse:
    try:
        upisan = servis.create_service(
            Service(node_id=zahtev.node_id, name=zahtev.name, kind=zahtev.kind,
                    config=zahtev.config, project_id=zahtev.project_id,
                    auto_start=zahtev.auto_start),
            actor=COVEK,
        )
        return _servis_u_odgovor(upisan, servis.status(upisan))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.patch("/services/{service_id}", response_model=ServiceResponse)
def izmeni(service_id: int, zahtev: ServiceUpdateRequest,
           servis: InfrastructureService = Depends(get_service),
           ) -> ServiceResponse:
    try:
        izmenjen = servis.update_service(
            service_id, name=zahtev.name, config=zahtev.config,
            project_id=zahtev.project_id, auto_start=zahtev.auto_start,
            actor=COVEK,
        )
        return _servis_u_odgovor(izmenjen, servis.status(izmenjen))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.delete("/services/{service_id}", response_model=ServiceDeletedResponse)
def ukloni(service_id: int,
           servis: InfrastructureService = Depends(get_service),
           ) -> ServiceDeletedResponse:
    try:
        servis.delete_service(service_id, actor=COVEK)
    except Exception as greska:
        raise _prevedi(greska) from greska
    return ServiceDeletedResponse()


@router.get("/services/{service_id}/logs", response_model=LogsResponse)
def log(service_id: int, lines: int = Query(default=200, ge=1, le=2000),
        servis: InfrastructureService = Depends(get_service)) -> LogsResponse:
    try:
        return LogsResponse(lines=servis.logs(service_id, lines))
    except Exception as greska:
        raise _prevedi(greska) from greska


# ----------          POTEZI          ----------

@router.post("/services/{service_id}/start", response_model=ServiceStateResponse)
def pokreni(service_id: int,
            servis: InfrastructureService = Depends(get_service),
            ) -> ServiceStateResponse:
    try:
        return _stanje_u_odgovor(servis.start(service_id, actor=COVEK))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.post("/services/{service_id}/stop", response_model=ServiceStateResponse)
def zaustavi(service_id: int,
             servis: InfrastructureService = Depends(get_service),
             ) -> ServiceStateResponse:
    try:
        return _stanje_u_odgovor(servis.stop(service_id, actor=COVEK))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.post("/services/{service_id}/restart", response_model=ServiceStateResponse)
def restartuj(service_id: int,
              servis: InfrastructureService = Depends(get_service),
              ) -> ServiceStateResponse:
    try:
        return _stanje_u_odgovor(servis.restart(service_id, actor=COVEK))
    except Exception as greska:
        raise _prevedi(greska) from greska
