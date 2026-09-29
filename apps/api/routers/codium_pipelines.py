# ========== ROUTER: PIPELINE-I (CODIUM) ==========
# Rute nose `actor="human"`. Live log je polling `logs?after_seq=`, bez
# WebSocket-a — pravilo CORE-a.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas.codium_pipelines import (
    CancelResponse,
    LogLineResponse,
    PipelineCreateRequest,
    PipelineDeletedResponse,
    PipelineResponse,
    PipelinesResponse,
    PipelineUpdateRequest,
    RunDetailResponse,
    RunLogsResponse,
    RunResponse,
    RunsResponse,
    StepResponse,
)
from core.domains.codium.pipelines.definition import DefinitionError
from core.domains.codium.pipelines.service import (
    PipelineNotFound,
    PipelineService,
    RepositoryMissing,
    RunDenied,
    RunNotFound,
)

router = APIRouter(
    prefix="/api/v1/codium/pipelines",
    tags=["CODIUM Pipeline-i"],
)

COVEK = "human"


def get_service() -> PipelineService:
    from apps.api import codium_pipelines_runtime
    return codium_pipelines_runtime.get_service()


def _prevedi(greska: Exception) -> HTTPException:
    if isinstance(greska, (PipelineNotFound, RunNotFound)):
        return HTTPException(status_code=404, detail=str(greska))
    if isinstance(greska, DefinitionError):
        return HTTPException(status_code=400, detail=str(greska))
    if isinstance(greska, RunDenied):
        return HTTPException(status_code=403, detail=str(greska))
    # Nestao koren nije kvar sistema nego stanje sveta.
    if isinstance(greska, RepositoryMissing):
        return HTTPException(status_code=409, detail=str(greska))
    return HTTPException(status_code=500, detail=str(greska))


def _pipeline_u_odgovor(pipeline) -> PipelineResponse:
    return PipelineResponse(
        id=pipeline.id, repository_id=pipeline.repository_id,
        name=pipeline.name, definition=pipeline.definition,
        enabled=pipeline.enabled, created_at=pipeline.created_at,
        updated_at=pipeline.updated_at,
    )


def _run_u_odgovor(run) -> RunResponse:
    return RunResponse(
        id=run.id, pipeline_id=run.pipeline_id, status=str(run.status),
        trigger=run.trigger, commit_sha=run.commit_sha, branch=run.branch,
        exit_code=run.exit_code, detail=run.detail,
        started_at=run.started_at, finished_at=run.finished_at,
        created_at=run.created_at,
    )


@router.get("/", response_model=PipelinesResponse)
def lista(repository_id: int | None = Query(default=None),
          servis: PipelineService = Depends(get_service)) -> PipelinesResponse:
    return PipelinesResponse(pipelines=[
        _pipeline_u_odgovor(p) for p in servis.list(repository_id)
    ])


@router.post("/", response_model=PipelineResponse)
def napravi(zahtev: PipelineCreateRequest,
            servis: PipelineService = Depends(get_service)) -> PipelineResponse:
    try:
        upisan = servis.create(zahtev.repository_id, zahtev.definition,
                               actor=COVEK)
    except (DefinitionError, RepositoryMissing) as greska:
        raise _prevedi(greska) from greska
    return _pipeline_u_odgovor(upisan)


@router.put("/{pipeline_id}", response_model=PipelineResponse)
def izmeni(pipeline_id: int, zahtev: PipelineUpdateRequest,
           servis: PipelineService = Depends(get_service)) -> PipelineResponse:
    try:
        izmenjen = servis.update(pipeline_id, zahtev.definition, actor=COVEK)
    except (PipelineNotFound, DefinitionError, RepositoryMissing) as greska:
        raise _prevedi(greska) from greska
    return _pipeline_u_odgovor(izmenjen)


@router.delete("/{pipeline_id}", response_model=PipelineDeletedResponse)
def obrisi(pipeline_id: int,
           servis: PipelineService = Depends(get_service)) -> PipelineDeletedResponse:
    try:
        servis.delete(pipeline_id, actor=COVEK)
    except PipelineNotFound as greska:
        raise _prevedi(greska) from greska
    return PipelineDeletedResponse(deleted=pipeline_id)


@router.post("/{pipeline_id}/run", response_model=RunResponse)
async def pokreni(pipeline_id: int,
                  servis: PipelineService = Depends(get_service)) -> RunResponse:
    # `async def` nije stilski izbor, nego jedini razlog zasto ova ruta
    # ovde uopste ima petlju koja radi: `servis.run()` na kraju zove
    # `PipelineRunner.start()`, kome je potrebna RADNA petlja u niti poziva
    # (prvo pokusava `asyncio.create_task()`). FastAPI sinhrone rute
    # (`def`) izvrsava u threadpool niti BEZ ikakve petlje — tamo `start()`
    # pada na povezanu petlju (`bind_loop`, vidi `core_lifespan`) ako je
    # ima, a bez nje na go `RuntimeError`. Ne menjaj ovo u `def`: to je
    # tacno ista greska koja je run_pipeline alat agenta drzala trajno
    # pokvarenim dok je nije popravio bind_loop (vidi
    # `tests/test_pipeline_runner.py`).
    try:
        pokretanje = servis.run(pipeline_id, actor=COVEK)
    except (PipelineNotFound, DefinitionError, RepositoryMissing,
            RunDenied) as greska:
        raise _prevedi(greska) from greska
    return _run_u_odgovor(pokretanje)


@router.get("/runs", response_model=RunsResponse)
def istorija(pipeline_id: int | None = Query(default=None),
             status: str | None = Query(default=None),
             limit: int = Query(default=50, ge=1, le=200),
             servis: PipelineService = Depends(get_service)) -> RunsResponse:
    return RunsResponse(runs=[
        _run_u_odgovor(r) for r in servis.run_history(pipeline_id, status, limit)
    ])


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def detalj(run_id: int,
           servis: PipelineService = Depends(get_service)) -> RunDetailResponse:
    try:
        pokretanje, koraci = servis.run_detail(run_id)
    except RunNotFound as greska:
        raise _prevedi(greska) from greska
    return RunDetailResponse(
        run=_run_u_odgovor(pokretanje),
        steps=[StepResponse(idx=k.idx, name=k.name, status=str(k.status),
                            exit_code=k.exit_code, started_at=k.started_at,
                            finished_at=k.finished_at)
               for k in koraci],
    )


@router.get("/runs/{run_id}/logs", response_model=RunLogsResponse)
def log(run_id: int, after_seq: int = Query(default=0, ge=0),
        servis: PipelineService = Depends(get_service)) -> RunLogsResponse:
    try:
        redovi = servis.logs(run_id, after_seq)
    except RunNotFound as greska:
        raise _prevedi(greska) from greska
    return RunLogsResponse(lines=[
        LogLineResponse(seq=r.seq, step_idx=r.step_idx, stream=r.stream,
                        line=r.line, at=r.at)
        for r in redovi
    ])


@router.post("/runs/{run_id}/cancel", response_model=CancelResponse)
def otkazi(run_id: int,
           servis: PipelineService = Depends(get_service)) -> CancelResponse:
    try:
        return CancelResponse(cancelled=servis.cancel(run_id, actor=COVEK))
    except RunNotFound as greska:
        raise _prevedi(greska) from greska
