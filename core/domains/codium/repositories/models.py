# ========== MODELI REPOZITORIJUMA ==========
# Commit-i se ne kopiraju u bazu — git im je vec baza. Ovde su samo oblici
# kroz koje podaci putuju od provider-a do ekrana.
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Repository:
    """Red iz `codium_repositories`."""

    name: str
    local_path: str
    project_id: int | None = None
    remote_url: str | None = None
    default_branch: str = "main"
    provider: str = "local_git"
    last_synced_at: str | None = None
    created_at: str = ""
    updated_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class RepoInfo:
    """Sta je provider nasao na putanji pri registraciji."""

    root: str
    branch: str
    remote_url: str | None = None


@dataclass(frozen=True)
class RepoStatus:
    """Stanje radnog stabla u jednom trenutku.

    `missing` znaci da putanja vise ne postoji na disku. To nije greska
    liste — registar sme da nadzivi folder.
    """

    branch: str = ""
    dirty: bool = False
    changed_files: int = 0
    ahead: int = 0
    behind: int = 0
    missing: bool = False


@dataclass(frozen=True)
class BranchInfo:
    """Jedna grana."""

    name: str
    is_current: bool = False
    target: str = ""


@dataclass(frozen=True)
class CommitInfo:
    """Jedan commit, sa zbirom izmena."""

    sha: str
    short_sha: str
    author: str
    date: str
    subject: str
    body: str = ""
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
