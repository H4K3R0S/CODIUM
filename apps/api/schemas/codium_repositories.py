# ========== SEME: REPOZITORIJUMI (CODIUM) ==========
from __future__ import annotations

from pydantic import BaseModel


class RepositoryCreateRequest(BaseModel):
    """Registracija postojece putanje kao repozitorijuma."""

    local_path: str
    project_id: int | None = None
    name: str | None = None


class RepoStatusResponse(BaseModel):
    branch: str = ""
    dirty: bool = False
    changed_files: int = 0
    ahead: int = 0
    behind: int = 0
    missing: bool = False


class RepositoryResponse(BaseModel):
    id: int
    project_id: int | None = None
    name: str
    local_path: str
    remote_url: str | None = None
    default_branch: str = "main"
    provider: str = "local_git"
    last_synced_at: str | None = None


class RepositoryWithStatus(RepositoryResponse):
    status: RepoStatusResponse


class RepositoriesResponse(BaseModel):
    repositories: list[RepositoryWithStatus]


class BranchResponse(BaseModel):
    name: str
    is_current: bool = False
    target: str = ""


class BranchesResponse(BaseModel):
    branches: list[BranchResponse]


class CommitResponse(BaseModel):
    sha: str
    short_sha: str
    author: str
    date: str
    subject: str
    body: str = ""
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


class CommitsResponse(BaseModel):
    commits: list[CommitResponse]


class DiffResponse(BaseModel):
    diff: str


class FileAtResponse(BaseModel):
    content: str


class SuggestionResponse(BaseModel):
    project_id: int
    project_name: str
    local_path: str


class SuggestionsResponse(BaseModel):
    suggestions: list[SuggestionResponse]


class SyncResponse(BaseModel):
    """`executed=False` znaci da je kapija trazila odobrenje ili odbila."""

    executed: bool
    detail: str = ""


class RepositoryDeletedResponse(BaseModel):
    deleted: int
