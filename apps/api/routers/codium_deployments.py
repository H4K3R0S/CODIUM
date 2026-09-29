# ========== ROUTER: ISPORUKA (CODIUM) ==========
# Rute nose `actor="human"`. Isporuka je sinhrona: za razliku od pipeline-a,
# potez je kratak (raspakivanje ili `docker` poziv), pa nema sta da se prati
# uzivo — ishod se zna kad ruta odgovori.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas.codium_deployments import (
    DeployableRunsResponse,
    DeploymentResponse,
    DeploymentsResponse,
    DeployRequest,
    HealthResponse,
    TargetCreateRequest,
    TargetDeletedResponse,
    TargetResponse,
    TargetsResponse,
    TargetUpdateRequest,
)
from core.domains.codium.deployments.models import DeployTarget
from core.domains.codium.deployments.providers.base import (
    RollbackUnsupported,
    TargetConfigError,
)
from core.domains.codium.deployments.service import (
    ApprovalPending,
    DeployDenied,
    DeploymentNotFound,
    DeploymentService,
    DeploymentServiceError,
    RunNotDeployable,
    TargetNotFound,
    UnknownProvider,
)

router = APIRouter(
    prefix="/api/v1/codium/deployments",
    tags=["CODIUM Isporuka"],
)

COVEK = "human"


def get_service() -> DeploymentService:
    from apps.api import codium_deployments_runtime
    return codium_deployments_runtime.get_service()


def _prevedi(greska: Exception) -> HTTPException:
    if isinstance(greska, (TargetNotFound, DeploymentNotFound)):
        return HTTPException(status_code=404, detail=str(greska))
    # Molba je upisana i ceka coveka — 202 je jedini kod koji to opisuje
    # bez laganja: zahtev je prihvacen, a nista jos nije izvedeno.
    if isinstance(greska, ApprovalPending):
        return HTTPException(status_code=202, detail={
            "detail": str(greska), "deployment_id": greska.deployment_id,
            "approval_id": greska.approval_id,
        })
    if isinstance(greska, DeployDenied):
        return HTTPException(status_code=403, detail=str(greska))
    if isinstance(greska, (TargetConfigError, UnknownProvider)):
        return HTTPException(status_code=400, detail=str(greska))
    # Pokretanje koje se ne moze isporuciti nije los zahtev nego stanje sveta:
    # covek je trazio isporuku necega sto (jos) nema paket.
    if isinstance(greska, (RunNotDeployable, RollbackUnsupported)):
        return HTTPException(status_code=409, detail=str(greska))
    if isinstance(greska, DeploymentServiceError):
        return HTTPException(status_code=409, detail=str(greska))
    return HTTPException(status_code=500, detail=str(greska))


def _cilj_u_odgovor(cilj) -> TargetResponse:
    return TargetResponse(
        id=cilj.id, name=cilj.name, kind=str(cilj.kind), config=cilj.config,
        project_id=cilj.project_id, connector_id=cilj.connector_id,
        enabled=cilj.enabled, created_at=cilj.created_at,
        updated_at=cilj.updated_at,
    )


def _isporuka_u_odgovor(isporuka) -> DeploymentResponse:
    return DeploymentResponse(
        id=isporuka.id, target_id=isporuka.target_id, run_id=isporuka.run_id,
        commit_sha=isporuka.commit_sha, status=str(isporuka.status),
        release_ref=isporuka.release_ref, detail=isporuka.detail,
        started_at=isporuka.started_at, finished_at=isporuka.finished_at,
        created_at=isporuka.created_at,
    )


# ----------          CILJEVI          ----------

@router.get("/targets", response_model=TargetsResponse)
def ciljevi(project_id: int | None = Query(default=None),
            servis: DeploymentService = Depends(get_service)) -> TargetsResponse:
    return TargetsResponse(targets=[
        _cilj_u_odgovor(c) for c in servis.list_targets(project_id)
    ])


@router.post("/targets", response_model=TargetResponse)
def nov_cilj(zahtev: TargetCreateRequest,
             servis: DeploymentService = Depends(get_service)) -> TargetResponse:
    try:
        return _cilj_u_odgovor(servis.create_target(
            DeployTarget(name=zahtev.name, kind=zahtev.kind,
                         config=zahtev.config, project_id=zahtev.project_id,
                         connector_id=zahtev.connector_id),
            actor=COVEK,
        ))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.patch("/targets/{target_id}", response_model=TargetResponse)
def izmeni_cilj(target_id: int, zahtev: TargetUpdateRequest,
                servis: DeploymentService = Depends(get_service)) -> TargetResponse:
    try:
        return _cilj_u_odgovor(servis.update_target(
            target_id, name=zahtev.name, config=zahtev.config,
            enabled=zahtev.enabled, actor=COVEK,
        ))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.delete("/targets/{target_id}", response_model=TargetDeletedResponse)
def obrisi_cilj(target_id: int,
                servis: DeploymentService = Depends(get_service),
                ) -> TargetDeletedResponse:
    try:
        servis.delete_target(target_id, actor=COVEK)
    except Exception as greska:
        raise _prevedi(greska) from greska
    return TargetDeletedResponse()


@router.get("/targets/{target_id}/health", response_model=HealthResponse)
def zdravlje(target_id: int,
             servis: DeploymentService = Depends(get_service)) -> HealthResponse:
    try:
        ishod = servis.health(target_id)
    except Exception as greska:
        raise _prevedi(greska) from greska
    return HealthResponse(healthy=ishod.healthy, detail=ishod.detail)


# ----------          ISPORUKA          ----------

@router.get("/runs", response_model=DeployableRunsResponse)
def pokretanja_za_isporuku(
    limit: int = Query(default=30, ge=1, le=200),
    servis: DeploymentService = Depends(get_service),
) -> DeployableRunsResponse:
    return DeployableRunsResponse(run_ids=servis.deployable_runs(limit))


@router.post("/", response_model=DeploymentResponse)
def isporuci(zahtev: DeployRequest,
             servis: DeploymentService = Depends(get_service),
             ) -> DeploymentResponse:
    try:
        return _isporuka_u_odgovor(
            servis.deploy(zahtev.target_id, zahtev.run_id, actor=COVEK))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.get("/", response_model=DeploymentsResponse)
def istorija(target_id: int | None = Query(default=None),
             limit: int = Query(default=50, ge=1, le=200),
             servis: DeploymentService = Depends(get_service),
             ) -> DeploymentsResponse:
    return DeploymentsResponse(deployments=[
        _isporuka_u_odgovor(i) for i in servis.history(target_id, limit)
    ])


@router.post("/{deployment_id}/rollback", response_model=DeploymentResponse)
def vrati(deployment_id: int,
          servis: DeploymentService = Depends(get_service),
          ) -> DeploymentResponse:
    try:
        return _isporuka_u_odgovor(servis.rollback(deployment_id, actor=COVEK))
    except Exception as greska:
        raise _prevedi(greska) from greska
