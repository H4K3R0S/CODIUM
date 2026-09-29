# ========== PROVIDER: LOKALNI GIT ==========
# Svaki poziv je jedan podproces. Bez stanja i bez nove zavisnosti; cenu
# pokretanja procesa pokriva kes stanja u servisu.
from __future__ import annotations

import subprocess
from pathlib import Path

from core.domains.codium.repositories.models import (
    BranchInfo,
    CommitInfo,
    RepoInfo,
    RepoStatus,
)
from core.domains.codium.repositories.providers.base import (
    GitError,
    GitUnavailable,
    InvalidGitRef,
)

# Razdvajaci koje commit poruka ne sme da sadrzi. Sve ostalo sme.
_POLJE = "\x1f"
_ZAPIS = "\x1e"

_LOG_FORMAT = (
    f"--format={_ZAPIS}%H{_POLJE}%h{_POLJE}%an{_POLJE}%aI{_POLJE}"
    f"%s{_POLJE}%b{_POLJE}"
)

# Citanje je brzo; `fetch` ide na mrezu pa dobija duzi rok.
_ROK_CITANJE = 10
_ROK_FETCH = 60


def _proveri_ref(vrednost: str, naziv: str) -> None:
    """Odbija vrednost koju bi git procitao kao opciju, ne kao ref/putanju.

    Lista argumenata vec sprecava SHELL injekciju — git ipak sam parsira
    svaki argument koji pocinje sa `-` kao svoju opciju, bez obzira odakle
    dolazi. `--output=<put>` ili `--no-index` na mestu ref-a bi git poslusno
    izvrsio. Ovo je poslednja brana pre podprocesa.
    """

    if vrednost.startswith("-"):
        raise InvalidGitRef(
            f"`{naziv}` ne sme da pocinje znakom `-`: `{vrednost}`")


def _git(root: str, *args: str, timeout: int = _ROK_CITANJE) -> str:
    """Pokrece jedan `git` poziv i vraca `stdout`.

    Argumenti idu kao lista — komanda se nikada ne sastavlja spajanjem
    stringova sa korisnickim unosom.
    """

    try:
        ishod = subprocess.run(
            ["git", "--no-pager", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as greska:
        raise GitUnavailable("git nije instaliran na ovoj masini") from greska
    except subprocess.TimeoutExpired as greska:
        raise GitError(f"git nije odgovorio u {timeout} s") from greska

    if ishod.returncode != 0:
        prva = (ishod.stderr or "").strip().splitlines()
        raise GitError(prva[0] if prva else f"git je vratio {ishod.returncode}")
    return ishod.stdout


class LocalGitProvider:
    """Git na ovoj masini, kroz podproces."""

    def detect(self, path: str) -> RepoInfo | None:
        if not Path(path).is_dir():
            return None
        try:
            koren = _git(path, "rev-parse", "--show-toplevel").strip()
        except GitError:
            # Folder koji nije repo nije greska pozivaoca — samo nije repo.
            return None
        if not koren:
            return None

        grana = _git(koren, "rev-parse", "--abbrev-ref", "HEAD").strip()
        try:
            remote = _git(koren, "remote", "get-url", "origin").strip() or None
        except GitError:
            # Repozitorijum bez remote-a je i dalje ispravan repozitorijum.
            remote = None
        return RepoInfo(root=koren, branch=grana, remote_url=remote)

    def status(self, root: str) -> RepoStatus:
        if not Path(root).is_dir():
            return RepoStatus(missing=True)

        izlaz = _git(root, "status", "--porcelain=v2", "--branch")
        grana = ""
        ahead = 0
        behind = 0
        izmenjeni = 0

        for linija in izlaz.splitlines():
            if linija.startswith("# branch.head "):
                grana = linija.split(" ", 2)[2].strip()
            elif linija.startswith("# branch.ab "):
                # Oblik: `# branch.ab +2 -1`
                delovi = linija.split()
                ahead = int(delovi[2])
                behind = abs(int(delovi[3]))
            elif linija[:2] in ("1 ", "2 ", "u ", "? "):
                izmenjeni += 1

        return RepoStatus(branch=grana, dirty=izmenjeni > 0,
                          changed_files=izmenjeni, ahead=ahead, behind=behind)

    def branches(self, root: str) -> list[BranchInfo]:
        izlaz = _git(root, "for-each-ref", "refs/heads",
                     f"--format=%(refname:short){_POLJE}%(HEAD){_POLJE}%(objectname:short)")
        grane: list[BranchInfo] = []
        for linija in izlaz.splitlines():
            if not linija.strip():
                continue
            ime, glava, cilj = linija.split(_POLJE)
            grane.append(BranchInfo(name=ime, is_current=glava == "*", target=cilj))
        return grane

    def log(self, root: str, branch: str, limit: int,
            offset: int) -> list[CommitInfo]:
        if branch:
            _proveri_ref(branch, "branch")
        argumenti = ["log", _LOG_FORMAT, "--numstat",
                     f"--max-count={int(limit)}", f"--skip={int(offset)}"]
        if branch:
            argumenti.extend(["--end-of-options", branch])
        izlaz = _git(root, *argumenti)

        commiti: list[CommitInfo] = []
        for zapis in izlaz.split(_ZAPIS):
            if not zapis.strip():
                continue
            polja = zapis.split(_POLJE)
            if len(polja) < 7:
                continue
            sha, kratki, autor, datum, naslov, telo, numstat = polja[:7]
            fajlova = dodato = obrisano = 0
            for red in numstat.strip().splitlines():
                delovi = red.split("\t")
                if len(delovi) != 3:
                    continue
                fajlova += 1
                # Binarni fajl daje `-` umesto broja.
                dodato += int(delovi[0]) if delovi[0].isdigit() else 0
                obrisano += int(delovi[1]) if delovi[1].isdigit() else 0
            commiti.append(CommitInfo(
                sha=sha, short_sha=kratki, author=autor, date=datum,
                subject=naslov, body=telo.strip(), files_changed=fajlova,
                insertions=dodato, deletions=obrisano,
            ))
        return commiti

    def diff(self, root: str, ref_a: str, ref_b: str,
             path: str | None) -> str:
        _proveri_ref(ref_a, "a")
        _proveri_ref(ref_b, "b")
        argumenti = ["diff", "--end-of-options", ref_a, ref_b]
        if path:
            _proveri_ref(path, "path")
            # `--` odvaja putanju od ref-a: fajl koji se zove kao grana
            # inace pravi dvosmislenost.
            argumenti.extend(["--", path])
        return _git(root, *argumenti)

    def file_at(self, root: str, ref: str, path: str) -> str:
        _proveri_ref(ref, "ref")
        _proveri_ref(path, "path")
        return _git(root, "show", f"{ref}:{path}")

    def fetch(self, root: str) -> None:
        _git(root, "fetch", "--prune", timeout=_ROK_FETCH)
