# ========== SERVIS REPOZITORIJUMA ==========
# Jedino mesto u fazi koje zove kapiju i dnevnik. Provider ne zna za dozvole,
# SQL sloj ne zna za pravila — obe odluke zive ovde.
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from core.domains.codium.audit import AuditEntry, AuditRepository
from core.domains.codium.repositories.models import (
    BranchInfo,
    CommitInfo,
    Repository,
    RepoStatus,
)
from core.domains.codium.repositories.providers.base import GitError, GitProvider
from core.domains.codium.repositories.repository import RepositoryRepository
from core.security.scope_gate import ALLOW, ScopeGate

# Koliko dugo stanje jednog repozitorijuma vazi bez ponovnog pitanja git-a.
# Bez ovoga bi svaki render liste pokrenuo po jedan proces po repozitorijumu.
KES_SEKUNDI = 10


class RepositoryError(RuntimeError):
    """Zajednicki koren gresaka ovog servisa."""


class RepositoryNotFound(RepositoryError):
    """Trazen repozitorijum ne postoji u registru."""


class NotAGitRepo(RepositoryError):
    """Putanja postoji ali nije git repozitorijum."""


class RepositoryExists(RepositoryError):
    """Putanja je vec upisana u registar."""


class RegistrationDenied(RepositoryError):
    """Kapija nije dozvolila registraciju ovom akteru."""


@dataclass(frozen=True)
class RepoSuggestion:
    """Projekat ciji je `local_path` git repo a nije registrovan."""

    project_id: int
    project_name: str
    local_path: str


class RepositoryService:
    """Registar repozitorijuma i citanje git podataka kroz provider."""

    def __init__(self, *, repos: RepositoryRepository, provider: GitProvider,
                 gate: ScopeGate, audit: AuditRepository, projects,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._repos = repos
        self._provider = provider
        self._gate = gate
        self._audit = audit
        self._projects = projects
        self._clock = clock
        self._kes: dict[int, tuple[float, RepoStatus]] = {}

    # ----------          REGISTAR          ----------

    def register(self, path: str, project_id: int | None = None,
                 name: str | None = None, actor: str = "human") -> Repository:
        cilj = f"path:{path}"
        odluka = self._gate.check(actor=actor, action="repo.register", target=cilj)
        if odluka.verdict != ALLOW:
            self._trag(actor, "repo.register", cilj, odluka.verdict, "blocked",
                       odluka.reason, project_id)
            raise RegistrationDenied(
                f"Kapija ne dozvoljava registraciju akteru `{actor}`: {odluka.reason}")

        info = self._provider.detect(path)
        if info is None:
            raise NotAGitRepo(f"Putanja `{path}` nije git repozitorijum.")
        if self._repos.get_by_path(info.root) is not None:
            raise RepositoryExists(f"Putanja `{info.root}` je vec upisana.")

        upisan = self._repos.add(Repository(
            name=name or Path(info.root).name,
            local_path=info.root,
            project_id=project_id,
            remote_url=info.remote_url,
            default_branch=info.branch or "main",
        ))
        self._trag(actor, "repo.register", f"repo:{upisan.id}", odluka.verdict, "ok",
                   info.root, project_id)
        return upisan

    def suggestions(self) -> list[RepoSuggestion]:
        """Projekti cija je putanja git repo a jos nisu u registru."""

        upisane = {r.local_path for r in self._repos.list()}
        ponude: list[RepoSuggestion] = []
        for projekat in self._projects.list_projects():
            putanja = (projekat.local_path or "").strip()
            if not putanja:
                continue
            info = self._provider.detect(putanja)
            if info is None or info.root in upisane:
                continue
            ponude.append(RepoSuggestion(project_id=projekat.id,
                                         project_name=projekat.name,
                                         local_path=info.root))
        return ponude

    def remove(self, repo_id: int, actor: str = "human") -> None:
        repo = self._nadji(repo_id)
        self._repos.delete(repo_id)
        self._kes.pop(repo_id, None)
        # Disk se ne dira — brise se samo red u registru.
        self._trag(actor, "repo.remove", f"repo:{repo_id}", ALLOW, "ok",
                   repo.local_path, repo.project_id)

    # ----------          CITANJE          ----------

    def list(self, project_id: int | None = None
             ) -> list[tuple[Repository, RepoStatus]]:
        """Red po red — jedan pokvaren repozitorijum ne obara ostatak liste.

        `.git` obrisan iz foldera koji jos postoji je greska tog reda, ne
        greska liste: red se vraca sa `missing=True`, kao i kad je ceo
        folder nestao. `GitUnavailable` (git uopste nije instaliran) ostaje
        da puca — to je sistemska greska koja pogadja svaki red isto, pa
        maskiranje u `missing=True` bi samo sakrilo pravi uzrok.
        """

        parovi: list[tuple[Repository, RepoStatus]] = []
        for repo in self._repos.list(project_id):
            try:
                # Vec imamo red iz `list()` — status racunamo nad njim, bez
                # dodatnog `get(repo.id)` po redu (izbegnut DB N+1).
                stanje = self._status_za(repo)
            except GitError:
                stanje = RepoStatus(missing=True)
            parovi.append((repo, stanje))
        return parovi

    def status(self, repo_id: int) -> RepoStatus:
        return self._status_za(self._nadji(repo_id))

    def _status_za(self, repo: Repository) -> RepoStatus:
        sada = self._clock()
        kesirano = self._kes.get(repo.id)
        if kesirano is not None and sada - kesirano[0] < KES_SEKUNDI:
            return kesirano[1]

        stanje = self._provider.status(repo.local_path)
        self._kes[repo.id] = (sada, stanje)
        return stanje

    def branches(self, repo_id: int) -> list[BranchInfo]:
        return self._provider.branches(self._nadji(repo_id).local_path)

    def history(self, repo_id: int, branch: str = "", limit: int = 50,
                offset: int = 0) -> list[CommitInfo]:
        repo = self._nadji(repo_id)
        return self._provider.log(repo.local_path, branch or repo.default_branch,
                                  limit, offset)

    def diff(self, repo_id: int, ref_a: str, ref_b: str,
             path: str | None = None) -> str:
        return self._provider.diff(self._nadji(repo_id).local_path,
                                   ref_a, ref_b, path)

    def file_at(self, repo_id: int, ref: str, path: str) -> str:
        return self._provider.file_at(self._nadji(repo_id).local_path, ref, path)

    # ----------          MREZA          ----------

    def sync(self, repo_id: int, actor: str = "human") -> bool:
        """`fetch` kroz kapiju. Vraca da li je stvarno izvrsen."""

        repo = self._nadji(repo_id)
        cilj = f"repo:{repo_id}"
        odluka = self._gate.check(actor=actor, action="repo.fetch", target=cilj)
        if odluka.verdict != ALLOW:
            self._trag(actor, "repo.fetch", cilj, odluka.verdict, "blocked",
                       odluka.reason, repo.project_id)
            return False

        self._provider.fetch(repo.local_path)
        self._repos.mark_synced(repo_id)
        # Stanje posle fetch-a je drugacije — stari kes bi lagao o `behind`.
        self._kes.pop(repo_id, None)
        self._trag(actor, "repo.fetch", cilj, odluka.verdict, "ok",
                   repo.local_path, repo.project_id)
        return True

    # ----------          POMOCNO          ----------

    def _nadji(self, repo_id: int) -> Repository:
        repo = self._repos.get(repo_id)
        if repo is None:
            raise RepositoryNotFound(f"Repozitorijum {repo_id} ne postoji.")
        return repo

    def _trag(self, actor: str, action: str, target: str, verdict: str,
              outcome: str, detail: str, project_id: int | None) -> None:
        self._audit.record(AuditEntry(
            actor=actor, action=action, target=target, verdict=verdict,
            outcome=outcome, detail=detail, project_id=project_id,
        ))
