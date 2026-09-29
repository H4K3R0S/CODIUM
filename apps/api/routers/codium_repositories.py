# ========== ROUTER: REPOZITORIJUMI (CODIUM) ==========
# Rute nose `actor="human"` — covek ne prolazi kroz kapiju. Agent ide istim
# servisom sa `actor=f"agent:{slug}"` i pada na pravilo iz migracije v10.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas.codium_repositories import (
    BranchesResponse,
    BranchResponse,
    CommitResponse,
    CommitsResponse,
    DiffResponse,
    FileAtResponse,
    RepositoriesResponse,
    RepositoryCreateRequest,
    RepositoryDeletedResponse,
    RepositoryResponse,
    RepositoryWithStatus,
    RepoStatusResponse,
    SuggestionResponse,
    SuggestionsResponse,
    SyncResponse,
)
from core.domains.codium.repositories.providers.base import (
    GitError,
    GitUnavailable,
    InvalidGitRef,
)
from core.domains.codium.repositories.service import (
    NotAGitRepo,
    RegistrationDenied,
    RepositoryExists,
    RepositoryNotFound,
    RepositoryService,
)

router = APIRouter(
    prefix="/api/v1/codium/repositories",
    tags=["CODIUM Repozitorijumi"],
)

COVEK = "human"


def get_service() -> RepositoryService:
    from apps.api import codium_repositories_runtime
    return codium_repositories_runtime.get_service()


def _prevedi(greska: Exception) -> HTTPException:
    """Domenska greska u HTTP odgovor.

    `stderr` git-a ume da nosi apsolutne putanje, pa ide samo prva linija
    koju je provider vec skratio.
    """

    if isinstance(greska, RepositoryNotFound):
        return HTTPException(status_code=404, detail=str(greska))
    if isinstance(greska, RegistrationDenied):
        return HTTPException(status_code=403, detail=str(greska))
    if isinstance(greska, InvalidGitRef):
        # Losa vrednost, ne kvar git-a — 400, ne 502.
        return HTTPException(status_code=400, detail=str(greska))
    if isinstance(greska, (NotAGitRepo, RepositoryExists)):
        return HTTPException(status_code=400, detail=str(greska))
    if isinstance(greska, GitUnavailable):
        return HTTPException(status_code=503, detail=str(greska))
    return HTTPException(status_code=502, detail=str(greska))


def _repo_u_odgovor(repo) -> dict:
    return {
        "id": repo.id, "project_id": repo.project_id, "name": repo.name,
        "local_path": repo.local_path, "remote_url": repo.remote_url,
        "default_branch": repo.default_branch, "provider": repo.provider,
        "last_synced_at": repo.last_synced_at,
    }


@router.get("/", response_model=RepositoriesResponse)
def lista(project_id: int | None = Query(default=None),
          servis: RepositoryService = Depends(get_service)) -> RepositoriesResponse:
    try:
        parovi = servis.list(project_id)
    except (GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska
    return RepositoriesResponse(repositories=[
        RepositoryWithStatus(**_repo_u_odgovor(repo),
                             status=RepoStatusResponse(**vars(stanje)))
        for repo, stanje in parovi
    ])


@router.get("/suggestions", response_model=SuggestionsResponse)
def ponude(servis: RepositoryService = Depends(get_service)) -> SuggestionsResponse:
    try:
        stavke = servis.suggestions()
    except (GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska
    return SuggestionsResponse(suggestions=[
        SuggestionResponse(project_id=s.project_id, project_name=s.project_name,
                           local_path=s.local_path)
        for s in stavke
    ])


@router.post("/", response_model=RepositoryResponse)
def registruj(zahtev: RepositoryCreateRequest,
              servis: RepositoryService = Depends(get_service)) -> RepositoryResponse:
    try:
        upisan = servis.register(zahtev.local_path, zahtev.project_id,
                                 zahtev.name, actor=COVEK)
    except (RepositoryExists, NotAGitRepo, RegistrationDenied,
            GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska
    return RepositoryResponse(**_repo_u_odgovor(upisan))


@router.delete("/{repo_id}", response_model=RepositoryDeletedResponse)
def ukloni(repo_id: int,
           servis: RepositoryService = Depends(get_service)) -> RepositoryDeletedResponse:
    try:
        servis.remove(repo_id, actor=COVEK)
    except RepositoryNotFound as greska:
        raise _prevedi(greska) from greska
    return RepositoryDeletedResponse(deleted=repo_id)


@router.get("/{repo_id}/status", response_model=RepoStatusResponse)
def stanje(repo_id: int,
           servis: RepositoryService = Depends(get_service)) -> RepoStatusResponse:
    try:
        return RepoStatusResponse(**vars(servis.status(repo_id)))
    except (RepositoryNotFound, GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska


@router.get("/{repo_id}/branches", response_model=BranchesResponse)
def grane(repo_id: int,
          servis: RepositoryService = Depends(get_service)) -> BranchesResponse:
    try:
        stavke = servis.branches(repo_id)
    except (RepositoryNotFound, GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska
    return BranchesResponse(branches=[BranchResponse(**vars(g)) for g in stavke])


@router.get("/{repo_id}/commits", response_model=CommitsResponse)
def istorija(repo_id: int, branch: str = Query(default=""),
             limit: int = Query(default=50, ge=1, le=500),
             offset: int = Query(default=0, ge=0),
             servis: RepositoryService = Depends(get_service)) -> CommitsResponse:
    try:
        stavke = servis.history(repo_id, branch, limit, offset)
    except (RepositoryNotFound, GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska
    return CommitsResponse(commits=[CommitResponse(**vars(c)) for c in stavke])


@router.get("/{repo_id}/diff", response_model=DiffResponse)
def razlika(repo_id: int, a: str = Query(...), b: str = Query(...),
            path: str | None = Query(default=None),
            servis: RepositoryService = Depends(get_service)) -> DiffResponse:
    try:
        return DiffResponse(diff=servis.diff(repo_id, a, b, path))
    except (RepositoryNotFound, GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska


@router.get("/{repo_id}/file", response_model=FileAtResponse)
def fajl_na_refu(repo_id: int, ref: str = Query(...), path: str = Query(...),
                 servis: RepositoryService = Depends(get_service)) -> FileAtResponse:
    try:
        return FileAtResponse(content=servis.file_at(repo_id, ref, path))
    except (RepositoryNotFound, GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska


@router.post("/{repo_id}/sync", response_model=SyncResponse)
def sinhronizuj(repo_id: int,
                servis: RepositoryService = Depends(get_service)) -> SyncResponse:
    try:
        izvrseno = servis.sync(repo_id, actor=COVEK)
    except (RepositoryNotFound, GitUnavailable, GitError) as greska:
        raise _prevedi(greska) from greska
    return SyncResponse(executed=izvrseno,
                        detail="" if izvrseno else "kapija nije dozvolila fetch")
