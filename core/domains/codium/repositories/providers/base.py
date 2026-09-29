# ========== PROTOKOL GIT PROVIDER-A ==========
# `local_git` je jedini provider u ovoj fazi. Protokol postoji da bi
# `github` kasnije usao bez prepravke servisa i ekrana.
from __future__ import annotations

from typing import Protocol

from core.domains.codium.repositories.models import (
    BranchInfo,
    CommitInfo,
    RepoInfo,
    RepoStatus,
)


class GitUnavailable(RuntimeError):
    """Alat `git` ne postoji na masini."""


class GitError(RuntimeError):
    """Git je pokrenut ali je vratio gresku."""


class InvalidGitRef(GitError):
    """Ref, grana ili putanja koju je pozivalac poslao pocinje sa `-`.

    Git bi tako nesto procitao kao opciju, ne kao pokazivac na commit ili
    fajl — cist unos, ne kvar git-a, pa router ovo mapira na 400.
    """


class GitProvider(Protocol):
    """Sta provider mora da ume."""

    def detect(self, path: str) -> RepoInfo | None:
        """Vraca opis repozitorijuma, ili None ako putanja nije repo."""

    def status(self, root: str) -> RepoStatus: ...

    def branches(self, root: str) -> list[BranchInfo]: ...

    def log(self, root: str, branch: str, limit: int,
            offset: int) -> list[CommitInfo]: ...

    def diff(self, root: str, ref_a: str, ref_b: str,
             path: str | None) -> str: ...

    def file_at(self, root: str, ref: str, path: str) -> str: ...

    def fetch(self, root: str) -> None: ...
