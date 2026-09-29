---
id: codium-2fed3447-2026-08-29-codium-e2-repositories-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: E2 Repositories — plan izvođenja
summary: '> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
  (recommended) or superpowers:executing-plans to implement this plan t'
keywords:
- repositories
- izvođenja
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-29-codium-e2-repositories.md
edges:
- type: references
  target: core-32ee86c0-2026-08-29-codium-e2-repositories-design-md
  weight: 0.3
---

# E2 Repositories — plan izvođenja

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Git postaje entitet CODIUM-a — registar repozitorijuma, stanje, istorija i razlika kroz servis, API, ekran i dva alata agenta.

**Architecture:** Novi paket `core/domains/codium/repositories/` po obrascu enterprise trake: `models.py` (dataclass-i), `providers/base.py` (Protocol) i `providers/local_git.py` (omotač oko podprocesa `git`), `repository.py` (SQL, bez logike), `service.py` (jedini zove kapiju i dnevnik). Iznad njega runtime, Pydantic šeme i router; ispod njega migracija `v10`. GUI stoji na dva mesta nad istim jezgrom komponenti: strana `/codium/repositories` i „Git" panel u docking rasporedu workspace-a.

**Tech Stack:** Python 3.14, FastAPI, SQLite (`codium.db` poslovna, `codium_ops.db` operativna), pytest; React 19 + TypeScript, Monaco `DiffEditor`, dockview, vitest.

**Spec:** [docs/superpowers/specs/2026-08-29-codium-e2-repositories-design.md](../specs/2026-08-29-codium-e2-repositories-design.md)

## Global Constraints

- **Jezik.** Kod i identifikatori na engleskom; komentari, docstring-ovi, UI stringovi i dokumentacija na srpskom.
- **Veličina fajla.** 150–300 linija je cilj; preko 500 razmotriti podelu.
- **Putanje** isključivo preko `CodiumPaths`. Nijedan modul ne sklapa putanju sam.
- **Audit.** Svaka mutacija u servisu zove `AuditRepository.record(...)`. Nema mutacije bez traga.
- **ScopeGate.** Spoljna akcija (`fetch`) prolazi `ScopeGate.check(...)` pre izvršenja.
- **Nema nove Python biblioteke.** Samo ugrađeni `subprocess`. Jedina nova stavka je spoljni alat `git`, upisan po sva četiri koraka iz `docs/DEPENDENCIES.md`.
- **Komanda se ne sastavlja spajanjem stringova.** Argumenti idu kao lista.
- **Bez WebSocket-a.** Osvežavanje je polling iz GUI-ja.
- **Testovi backend-a:** `./.venv/Scripts/python.exe -m pytest` iz korena repozitorijuma — ne sistemski `python`.
- **Testovi GUI-ja:** `npm run test -- <putanja>` iz `apps/gui`.
- **`_DEFAULTS` u `core/security/scope_gate.py` se ne dira.** Novi glagoli dobijaju pravila u migraciji.
- **Van dometa:** `checkout`, `pull`, `commit`, `push`, `stage`, `providers/github.py`, kopiranje commit-a u bazu, Git panel u fiksnom rasporedu.

---

### Task 1: `git` u katalogu zavisnosti

**Files:**
- Modify: `core/foundation/dependencies.py` (dodavanje u `CORE_DEPENDENCIES`)
- Create: `scripts/install/git.ps1`
- Modify: `core/foundation/installer.py` (`INSTALL_SCRIPTS`)
- Modify: `docs/DEPENDENCIES.md` (tabela „Katalog alata")
- Test: `tests/test_dependencies.py`

**Interfaces:**
- Consumes: ništa (prvi task).
- Produces: ključ zavisnosti `"git"` u `CORE_DEPENDENCIES`; kasniji task-ovi na njega ne referišu u kodu, ali indikator zdravlja pored „CORE Online" od sada zna za git.

- [ ] **Step 1: Napiši test koji pada**

Dopuni `tests/test_dependencies.py` (ako fajl ne postoji, napravi ga sa ovim sadržajem):

```python
# ========== TESTOVI: katalog zavisnosti ==========
from __future__ import annotations

from core.foundation.dependencies import (
    CORE_DEPENDENCIES,
    DependencyInstaller,
    DependencyKind,
    DependencySeverity,
)
from core.foundation.installer import INSTALL_SCRIPTS


def test_git_je_u_katalogu_zavisnosti():
    git = next((d for d in CORE_DEPENDENCIES if d.key == "git"), None)
    assert git is not None
    assert git.kind is DependencyKind.SYSTEM
    # Bez git-a CORE i dalje radi — pada samo CODIUM Repositories.
    assert git.severity is DependencySeverity.IMPORTANT
    assert git.probe == "git"
    assert git.installer is DependencyInstaller.WINGET


def test_git_ima_install_skriptu():
    assert INSTALL_SCRIPTS["git"] == "git.ps1"
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_dependencies.py -v
```

Očekivano: FAIL — `assert git is not None` puca, i `KeyError: 'git'`.

- [ ] **Step 3: Upiši zavisnost**

U `core/foundation/dependencies.py`, u `CORE_DEPENDENCIES`, odmah iza unosa za `ffprobe`:

```python
    Dependency(
        key="git",
        label="Git",
        kind=DependencyKind.SYSTEM,
        severity=DependencySeverity.IMPORTANT,
        probe="git",
        purpose="Čitanje istorije i razlike u CODIUM Repositories.",
        install_hint="winget install Git.Git",
        installer=DependencyInstaller.WINGET,
    ),
```

`probe_fn` se ne zadaje: `check_dependency` za `SYSTEM` traži izvršni fajl na PATH-u preko `shutil.which("git")`, što je tačno ono što nam treba.

- [ ] **Step 4: Napravi install skriptu**

`scripts/install/git.ps1`:

```powershell
# CORE install skripta: Git (čitanje istorije i razlike u CODIUM-u) preko winget-a.
$ErrorActionPreference = "Stop"
Write-Host "== CORE INSTALL: Git =="
winget install --exact --id Git.Git `
  --accept-source-agreements --accept-package-agreements
Write-Host "== GOTOVO: Git =="
```

U `core/foundation/installer.py`, u `INSTALL_SCRIPTS`, dodaj red:

```python
    "git": "git.ps1",
```

- [ ] **Step 5: Dopuni `docs/DEPENDENCIES.md`**

U tabelu „Katalog alata" dodaj red (uskladi kolone sa postojećim redovima u tom fajlu):

```markdown
| `git` | Git | system | important | winget | Čitanje istorije i razlike u CODIUM Repositories. |
```

- [ ] **Step 6: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_dependencies.py -v
```

Očekivano: PASS.

- [ ] **Step 7: Commit**

```bash
git add core/foundation/dependencies.py core/foundation/installer.py scripts/install/git.ps1 docs/DEPENDENCIES.md tests/test_dependencies.py
git commit -m "feat(core): git ulazi u katalog zavisnosti"
```

---

### Task 2: Modeli i `local_git` provider

**Files:**
- Create: `core/domains/codium/repositories/__init__.py`
- Create: `core/domains/codium/repositories/models.py`
- Create: `core/domains/codium/repositories/providers/__init__.py`
- Create: `core/domains/codium/repositories/providers/base.py`
- Create: `core/domains/codium/repositories/providers/local_git.py`
- Test: `tests/test_local_git_provider.py`

**Interfaces:**
- Consumes: ništa iz ranijih task-ova.
- Produces:
  - `Repository(id, project_id, name, local_path, remote_url, default_branch, provider, last_synced_at, created_at, updated_at)` — frozen dataclass.
  - `RepoInfo(root: str, remote_url: str | None, branch: str)`
  - `RepoStatus(branch: str, dirty: bool, changed_files: int, ahead: int, behind: int, missing: bool = False)`
  - `BranchInfo(name: str, is_current: bool, target: str)`
  - `CommitInfo(sha, short_sha, author, date, subject, body, files_changed, insertions, deletions)`
  - `GitProvider` Protocol sa metodama `detect/status/branches/log/diff/file_at/fetch`
  - `LocalGitProvider()` — implementacija; izuzeci `GitUnavailable`, `GitError`

- [ ] **Step 1: Napiši test koji pada**

`tests/test_local_git_provider.py`:

```python
# ========== TESTOVI: local_git provider ==========
# Jedini test u fazi koji pokrece pravi proces. Provider je omotac oko
# podprocesa, pa lazni provider ovde ne bi dokazao nista.
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from core.domains.codium.repositories.providers.local_git import LocalGitProvider


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True,
                   capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path) -> Path:
    """Repozitorijum sa dva commit-a i jednom nesacuvanom izmenom."""

    if shutil.which("git") is None:
        pytest.skip("git nije na PATH-u — provider se ne moze proveriti")

    koren = tmp_path / "projekat"
    koren.mkdir()
    _git(koren, "init", "--initial-branch=main")
    _git(koren, "config", "user.email", "test@core.local")
    _git(koren, "config", "user.name", "CORE Test")

    (koren / "prvi.txt").write_text("prva linija\n", encoding="utf-8")
    _git(koren, "add", "prvi.txt")
    _git(koren, "commit", "-m", "prvi commit")

    (koren / "prvi.txt").write_text("prva linija\ndruga linija\n", encoding="utf-8")
    _git(koren, "add", "prvi.txt")
    _git(koren, "commit", "-m", "drugi commit")

    # Nesacuvana izmena — `status` mora da je prijavi.
    (koren / "prvi.txt").write_text("prva linija\ndruga linija\ntreca\n",
                                    encoding="utf-8")
    return koren


def test_detect_prepoznaje_repozitorijum(repo):
    info = LocalGitProvider().detect(str(repo))
    assert info is not None
    assert Path(info.root).resolve() == repo.resolve()
    assert info.branch == "main"
    # Repozitorijum bez remote-a: polje je prazno, ne greska.
    assert info.remote_url is None


def test_detect_vraca_none_za_obican_folder(tmp_path):
    obican = tmp_path / "nije-repo"
    obican.mkdir()
    assert LocalGitProvider().detect(str(obican)) is None


def test_status_prijavljuje_dirty_i_granu(repo):
    stanje = LocalGitProvider().status(str(repo))
    assert stanje.branch == "main"
    assert stanje.dirty is True
    assert stanje.changed_files == 1
    # Bez remote-a nema ni ahead ni behind.
    assert stanje.ahead == 0
    assert stanje.behind == 0


def test_log_vraca_oba_commita_u_tacnom_redosledu(repo):
    commiti = LocalGitProvider().log(str(repo), branch="main", limit=10, offset=0)
    assert [c.subject for c in commiti] == ["drugi commit", "prvi commit"]
    assert commiti[0].files_changed == 1
    assert commiti[0].insertions == 1
    assert len(commiti[0].short_sha) >= 7


def test_diff_izmedju_dva_commita_nije_prazan(repo):
    provider = LocalGitProvider()
    commiti = provider.log(str(repo), branch="main", limit=10, offset=0)
    razlika = provider.diff(str(repo), commiti[1].sha, commiti[0].sha, None)
    assert "druga linija" in razlika


def test_file_at_vraca_stari_sadrzaj(repo):
    provider = LocalGitProvider()
    commiti = provider.log(str(repo), branch="main", limit=10, offset=0)
    stari = provider.file_at(str(repo), commiti[1].sha, "prvi.txt")
    assert stari == "prva linija\n"


def test_branches_ima_tekucu_granu(repo):
    grane = LocalGitProvider().branches(str(repo))
    assert [g.name for g in grane] == ["main"]
    assert grane[0].is_current is True
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_local_git_provider.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: No module named 'core.domains.codium.repositories'`.

- [ ] **Step 3: Napiši modele**

`core/domains/codium/repositories/models.py`:

```python
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
```

- [ ] **Step 4: Napiši protokol provider-a**

`core/domains/codium/repositories/providers/base.py`:

```python
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
```

`core/domains/codium/repositories/providers/__init__.py`:

```python
from core.domains.codium.repositories.providers.base import (
    GitError,
    GitProvider,
    GitUnavailable,
)
from core.domains.codium.repositories.providers.local_git import LocalGitProvider

__all__ = ["GitError", "GitProvider", "GitUnavailable", "LocalGitProvider"]
```

- [ ] **Step 5: Napiši `local_git` provider**

`core/domains/codium/repositories/providers/local_git.py`:

```python
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
from core.domains.codium.repositories.providers.base import GitError, GitUnavailable

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
        argumenti = ["log", _LOG_FORMAT, "--numstat",
                     f"--max-count={int(limit)}", f"--skip={int(offset)}"]
        if branch:
            argumenti.append(branch)
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
        argumenti = ["diff", ref_a, ref_b]
        if path:
            # `--` odvaja putanju od ref-a: fajl koji se zove kao grana
            # inace pravi dvosmislenost.
            argumenti.extend(["--", path])
        return _git(root, *argumenti)

    def file_at(self, root: str, ref: str, path: str) -> str:
        return _git(root, "show", f"{ref}:{path}")

    def fetch(self, root: str) -> None:
        _git(root, "fetch", "--prune", timeout=_ROK_FETCH)
```

`core/domains/codium/repositories/__init__.py` (za sada samo modeli i provider; dopunjuje se u Task-u 3 i 4):

```python
from core.domains.codium.repositories.models import (
    BranchInfo,
    CommitInfo,
    RepoInfo,
    RepoStatus,
    Repository,
)
from core.domains.codium.repositories.providers import (
    GitError,
    GitProvider,
    GitUnavailable,
    LocalGitProvider,
)

__all__ = [
    "BranchInfo", "CommitInfo", "GitError", "GitProvider", "GitUnavailable",
    "LocalGitProvider", "RepoInfo", "RepoStatus", "Repository",
]
```

- [ ] **Step 6: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_local_git_provider.py -v
```

Očekivano: PASS (ili SKIPPED ako git nije na PATH-u — tada ga instaliraj pa ponovi).

- [ ] **Step 7: Commit**

```bash
git add core/domains/codium/repositories tests/test_local_git_provider.py
git commit -m "feat(codium): local_git provider cita stanje, grane, istoriju i razliku"
```

---

### Task 3: Migracija `v10` i SQL sloj

**Files:**
- Modify: `core/domains/codium/migrations.py` (dodavanje `CODIUM_MIGRATION_V10` i unos u `CODIUM_MIGRATIONS`)
- Create: `core/domains/codium/repositories/repository.py`
- Modify: `core/domains/codium/repositories/__init__.py`
- Test: `tests/test_codium_repositories_repository.py`

**Interfaces:**
- Consumes: `Repository` iz Task-a 2.
- Produces: `RepositoryRepository(database_path: Path | None)` sa metodama
  `add(repo: Repository) -> Repository`, `list(project_id: int | None = None) -> list[Repository]`,
  `get(repo_id: int) -> Repository | None`, `get_by_path(local_path: str) -> Repository | None`,
  `delete(repo_id: int) -> None`, `mark_synced(repo_id: int) -> None`.

- [ ] **Step 1: Napiši test koji pada**

`tests/test_codium_repositories_repository.py`:

```python
# ========== TESTOVI: SQL sloj repozitorijuma ==========
from __future__ import annotations

import sqlite3

import pytest

from core.domains.codium.repositories import Repository
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.runtime import initialize_codium_database
from core.database import core_database_connection


@pytest.fixture
def registar(tmp_path) -> RepositoryRepository:
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    return RepositoryRepository(baza)


def test_upisan_repozitorijum_se_cita_nazad(registar):
    upisan = registar.add(Repository(name="core", local_path="C:/kod/core",
                                     remote_url="https://example.invalid/core.git",
                                     default_branch="main"))
    assert upisan.id is not None
    svi = registar.list()
    assert len(svi) == 1
    assert svi[0].name == "core"
    assert svi[0].local_path == "C:/kod/core"


def test_ista_putanja_dvaput_pada_na_jedinstvenom_indeksu(registar):
    registar.add(Repository(name="core", local_path="C:/kod/core"))
    with pytest.raises(sqlite3.IntegrityError):
        registar.add(Repository(name="isti", local_path="C:/kod/core"))


def test_lista_po_projektu_filtrira(registar):
    registar.add(Repository(name="a", local_path="C:/kod/a", project_id=1))
    registar.add(Repository(name="b", local_path="C:/kod/b", project_id=2))
    assert [r.name for r in registar.list(project_id=2)] == ["b"]


def test_get_by_path_nalazi_upisan(registar):
    registar.add(Repository(name="a", local_path="C:/kod/a"))
    assert registar.get_by_path("C:/kod/a") is not None
    assert registar.get_by_path("C:/kod/nema") is None


def test_brisanje_uklanja_red(registar):
    upisan = registar.add(Repository(name="a", local_path="C:/kod/a"))
    registar.delete(upisan.id)
    assert registar.list() == []


def test_migracija_v10_upisuje_pravila_kapije(tmp_path):
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    with core_database_connection(baza) as veza:
        redovi = veza.execute(
            "SELECT action, verdict FROM codium_scope_rules "
            "WHERE action LIKE 'repo.%' ORDER BY action"
        ).fetchall()
    assert [(r[0], r[1]) for r in redovi] == [
        ("repo.fetch", "needs_approval"),
        ("repo.register", "deny"),
    ]
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_repositories_repository.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: ... repositories.repository`.

- [ ] **Step 3: Napiši migraciju**

U `core/domains/codium/migrations.py`, iza `CODIUM_MIGRATION_V9`:

```python
# ---------- v10: registar repozitorijuma ----------

CODIUM_MIGRATION_V10 = DatabaseMigration(
    scope="codium",
    version=10,
    name="repositories",
    statements=(
        # Repozitorijum nije projekat: jedan projekat sme dva repozitorijuma,
        # a repozitorijum sme da stoji bez projekta.
        """
        CREATE TABLE codium_repositories (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id     INTEGER REFERENCES codium_projects (id)
                           ON DELETE SET NULL,
            name           TEXT NOT NULL,
            local_path     TEXT NOT NULL,
            remote_url     TEXT,
            default_branch TEXT NOT NULL DEFAULT 'main',
            provider       TEXT NOT NULL DEFAULT 'local_git',
            last_synced_at TEXT,
            created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE UNIQUE INDEX idx_codium_repos_path "
        "ON codium_repositories (local_path)",
        # `ScopeGate` nepoznat glagol odbija, a `fetch` i `register` su
        # nepoznati. Pravila stoje ovde, a ne u `_DEFAULTS` CORE kapije:
        # `fetch` je git pojam, ne CORE glagol.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'repo.fetch', '*', 'needs_approval',
                'fetch ide na mrezu — covek odobrava')
        """,
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'repo.register', '*', 'deny',
                'registar repozitorijuma je covekova odluka')
        """,
    ),
)
```

I dopuni torku na dnu fajla:

```python
CODIUM_MIGRATIONS = (
    CODIUM_MIGRATION_V1,
    CODIUM_MIGRATION_V2,
    CODIUM_MIGRATION_V3,
    CODIUM_MIGRATION_V4,
    CODIUM_MIGRATION_V5,
    CODIUM_MIGRATION_V6,
    CODIUM_MIGRATION_V7,
    CODIUM_MIGRATION_V8,
    CODIUM_MIGRATION_V9,
    CODIUM_MIGRATION_V10,
)
```

- [ ] **Step 4: Napiši SQL sloj**

`core/domains/codium/repositories/repository.py`:

```python
# ========== SQL SLOJ REPOZITORIJUMA ==========
# Samo citanje i pisanje redova. Poslovna logika, kapija i dnevnik su u
# servisu — ovde ih namerno nema.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.repositories.models import Repository
from core.domains.codium.runtime import codium_database_path

_KOLONE = ("id, project_id, name, local_path, remote_url, default_branch, "
           "provider, last_synced_at, created_at, updated_at")


def _od_reda(row) -> Repository:
    return Repository(
        id=row[0], project_id=row[1], name=row[2], local_path=row[3],
        remote_url=row[4], default_branch=row[5], provider=row[6],
        last_synced_at=row[7], created_at=row[8], updated_at=row[9],
    )


class RepositoryRepository:
    """Perzistencija registra repozitorijuma."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, repo: Repository) -> Repository:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_repositories (project_id, name, "
                "local_path, remote_url, default_branch, provider) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (repo.project_id, repo.name, repo.local_path, repo.remote_url,
                 repo.default_branch, repo.provider),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self, project_id: int | None = None) -> list[Repository]:
        uslov = " WHERE project_id = ?" if project_id is not None else ""
        parametri = (project_id,) if project_id is not None else ()
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE} FROM codium_repositories{uslov} ORDER BY id",
                parametri,
            ).fetchall()
        return [_od_reda(red) for red in redovi]

    def get(self, repo_id: int) -> Repository | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE} FROM codium_repositories WHERE id = ?",
                (repo_id,),
            ).fetchone()
        return _od_reda(red) if red else None

    def get_by_path(self, local_path: str) -> Repository | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE} FROM codium_repositories WHERE local_path = ?",
                (local_path,),
            ).fetchone()
        return _od_reda(red) if red else None

    def delete(self, repo_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute("DELETE FROM codium_repositories WHERE id = ?",
                         (repo_id,))

    def mark_synced(self, repo_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_repositories SET last_synced_at = "
                "CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (repo_id,),
            )
```

Dopuni `core/domains/codium/repositories/__init__.py`:

```python
from core.domains.codium.repositories.repository import RepositoryRepository
```

i dodaj `"RepositoryRepository"` u `__all__`.

- [ ] **Step 5: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_repositories_repository.py -v
```

Očekivano: PASS.

- [ ] **Step 6: Pokreni ceo CODIUM skup da migracija ne obori postojeće testove**

```bash
./.venv/Scripts/python.exe -m pytest tests -k codium -q
```

Očekivano: PASS.

- [ ] **Step 7: Commit**

```bash
git add core/domains/codium/migrations.py core/domains/codium/repositories tests/test_codium_repositories_repository.py
git commit -m "feat(codium): migracija v10 — tabela repozitorijuma i pravila kapije"
```

---

### Task 4: `RepositoryService`

**Files:**
- Create: `core/domains/codium/repositories/service.py`
- Modify: `core/domains/codium/repositories/__init__.py`
- Test: `tests/test_codium_repositories.py`

**Interfaces:**
- Consumes: `RepositoryRepository` (Task 3), `GitProvider`, `Repository`, `RepoStatus`, `RepoInfo`, `CommitInfo`, `BranchInfo` (Task 2), `ScopeGate` iz `core.security.scope_gate`, `AuditRepository`/`AuditEntry` iz `core.domains.codium.audit`, `CodiumRepository.list_projects()` za ponudu.
- Produces: `RepositoryService(repos, provider, gate, audit, projects, clock=time.monotonic)` sa metodama:
  - `register(path: str, project_id: int | None = None, name: str | None = None, actor: str = "human") -> Repository`
  - `suggestions() -> list[RepoSuggestion]` (`RepoSuggestion(project_id, project_name, local_path)`)
  - `list(project_id: int | None = None) -> list[tuple[Repository, RepoStatus]]`
  - `status(repo_id: int) -> RepoStatus`
  - `branches(repo_id: int) -> list[BranchInfo]`
  - `history(repo_id: int, branch: str = "", limit: int = 50, offset: int = 0) -> list[CommitInfo]`
  - `diff(repo_id: int, ref_a: str, ref_b: str, path: str | None = None) -> str`
  - `file_at(repo_id: int, ref: str, path: str) -> str`
  - `sync(repo_id: int, actor: str = "human") -> bool`
  - `remove(repo_id: int, actor: str = "human") -> None`
  - izuzeci `RepositoryNotFound`, `NotAGitRepo`, `RepositoryExists`

- [ ] **Step 1: Napiši test koji pada**

`tests/test_codium_repositories.py`:

```python
# ========== TESTOVI: servis repozitorijuma ==========
# Provider je lazan: nijedan test ovde ne pokrece `git` niti ide na mrezu.
from __future__ import annotations

import pytest

from core.domains.codium.audit import AuditRepository
from core.domains.codium.models import ProjectCreate
from core.domains.codium.repository import CodiumRepository
from core.domains.codium.repositories import (
    BranchInfo,
    CommitInfo,
    RepoInfo,
    RepoStatus,
)
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.repositories.service import (
    NotAGitRepo,
    RepositoryExists,
    RepositoryNotFound,
    RepositoryService,
)
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)
from core.security.scope_gate import ALLOW, DENY, Decision, ScopeGate, ScopeRule


class _LazniGit:
    """Provider koji broji pozive i vraca unapred spremne odgovore."""

    def __init__(self, repo_putanje: set[str]) -> None:
        self._repoi = repo_putanje
        self.status_poziva = 0
        self.fetch_poziva = 0

    def detect(self, path: str) -> RepoInfo | None:
        if path not in self._repoi:
            return None
        return RepoInfo(root=path, branch="main",
                        remote_url="https://example.invalid/x.git")

    def status(self, root: str) -> RepoStatus:
        self.status_poziva += 1
        return RepoStatus(branch="main", dirty=True, changed_files=2,
                          ahead=1, behind=0)

    def branches(self, root: str) -> list[BranchInfo]:
        return [BranchInfo(name="main", is_current=True, target="abc1234")]

    def log(self, root, branch, limit, offset) -> list[CommitInfo]:
        svi = [CommitInfo(sha=f"sha{i}", short_sha=f"s{i}", author="CORE",
                          date="2026-08-29T10:00:00+02:00", subject=f"c{i}")
               for i in range(5)]
        return svi[offset:offset + limit]

    def diff(self, root, ref_a, ref_b, path) -> str:
        return "diff --git a/x b/x"

    def file_at(self, root, ref, path) -> str:
        return "sadrzaj"

    def fetch(self, root) -> None:
        self.fetch_poziva += 1


@pytest.fixture
def okruzenje(tmp_path):
    poslovna = tmp_path / "codium.db"
    operativna = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(operativna)

    projekti = CodiumRepository(poslovna)
    git = _LazniGit({"C:/kod/core", "C:/kod/drugi"})
    dnevnik = AuditRepository(operativna)
    # Sat pod kontrolom testa — kes se proverava bez cekanja.
    sat = {"t": 1000.0}
    servis = RepositoryService(
        repos=RepositoryRepository(poslovna),
        provider=git,
        gate=ScopeGate(lambda: []),
        audit=dnevnik,
        projects=projekti,
        clock=lambda: sat["t"],
    )
    return servis, git, dnevnik, projekti, sat


def test_registracija_ne_git_putanje_daje_urednu_gresku(okruzenje):
    servis, _, _, _, _ = okruzenje
    with pytest.raises(NotAGitRepo):
        servis.register("C:/kod/nije-repo")


def test_duplikat_putanje_daje_urednu_gresku(okruzenje):
    servis, _, _, _, _ = okruzenje
    servis.register("C:/kod/core")
    with pytest.raises(RepositoryExists):
        servis.register("C:/kod/core")


def test_registracija_uzima_remote_i_granu_od_providera(okruzenje):
    servis, _, _, _, _ = okruzenje
    upisan = servis.register("C:/kod/core")
    assert upisan.remote_url == "https://example.invalid/x.git"
    assert upisan.default_branch == "main"
    assert upisan.name == "core"


def test_kes_stanja_ne_zove_provider_dvaput_unutar_prozora(okruzenje):
    servis, git, _, _, sat = okruzenje
    upisan = servis.register("C:/kod/core")
    servis.status(upisan.id)
    servis.status(upisan.id)
    assert git.status_poziva == 1

    # Prozor je 10 s; posle njega provider se ponovo pita.
    sat["t"] += 11
    servis.status(upisan.id)
    assert git.status_poziva == 2


def test_sync_bez_dozvole_ne_izvrsava_fetch_ali_ostavlja_trag(tmp_path):
    poslovna = tmp_path / "codium.db"
    operativna = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(operativna)
    git = _LazniGit({"C:/kod/core"})
    dnevnik = AuditRepository(operativna)
    zabrana = ScopeGate(lambda: [ScopeRule(id=1, actor="agent:x",
                                           action="repo.fetch", target="*",
                                           verdict=DENY, note="bez mreze")])
    servis = RepositoryService(
        repos=RepositoryRepository(poslovna), provider=git, gate=zabrana,
        audit=dnevnik, projects=CodiumRepository(poslovna),
    )
    upisan = servis.register("C:/kod/core")

    izvrseno = servis.sync(upisan.id, actor="agent:x")

    assert izvrseno is False
    assert git.fetch_poziva == 0
    tragovi = [u for u in dnevnik.query(limit=10) if u.action == "repo.fetch"]
    assert len(tragovi) == 1
    assert tragovi[0].verdict == DENY
    assert tragovi[0].outcome == "blocked"


def test_sync_sa_dozvolom_izvrsava_fetch(okruzenje):
    servis, git, dnevnik, _, _ = okruzenje
    upisan = servis.register("C:/kod/core")
    assert servis.sync(upisan.id, actor="human") is True
    assert git.fetch_poziva == 1
    tragovi = [u for u in dnevnik.query(limit=10) if u.action == "repo.fetch"]
    assert tragovi[0].outcome == "ok"


def test_suggestions_izostavlja_vec_upisane(okruzenje):
    servis, _, _, projekti, _ = okruzenje
    # `create_project` trazi i slug — repozitorijum ga ne izvodi sam.
    projekti.create_project(
        ProjectCreate(name="Core", local_path="C:/kod/core"), slug="core")
    projekti.create_project(
        ProjectCreate(name="Drugi", local_path="C:/kod/drugi"), slug="drugi")
    projekti.create_project(
        ProjectCreate(name="Bez", local_path="C:/kod/nije-repo"), slug="bez")

    pre = {p.local_path for p in servis.suggestions()}
    assert pre == {"C:/kod/core", "C:/kod/drugi"}

    servis.register("C:/kod/core")
    posle = {p.local_path for p in servis.suggestions()}
    assert posle == {"C:/kod/drugi"}


def test_history_postuje_limit_i_offset(okruzenje):
    servis, _, _, _, _ = okruzenje
    upisan = servis.register("C:/kod/core")
    strana = servis.history(upisan.id, limit=2, offset=2)
    assert [c.subject for c in strana] == ["c2", "c3"]


def test_nepostojeci_repozitorijum_daje_not_found(okruzenje):
    servis, _, _, _, _ = okruzenje
    with pytest.raises(RepositoryNotFound):
        servis.status(999)


def test_uklanjanje_ne_dira_disk_ali_pise_u_dnevnik(okruzenje, tmp_path):
    servis, _, dnevnik, _, _ = okruzenje
    upisan = servis.register("C:/kod/core")
    servis.remove(upisan.id, actor="human")
    assert servis.list() == []
    tragovi = [u for u in dnevnik.query(limit=10) if u.action == "repo.remove"]
    assert len(tragovi) == 1
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_repositories.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: ... repositories.service`.

- [ ] **Step 3: Napiši servis**

`core/domains/codium/repositories/service.py`:

```python
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
    RepoStatus,
    Repository,
)
from core.domains.codium.repositories.providers.base import GitProvider
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
        self._trag(actor, "repo.register", f"repo:{upisan.id}", ALLOW, "ok",
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
        return [(repo, self.status(repo.id))
                for repo in self._repos.list(project_id)]

    def status(self, repo_id: int) -> RepoStatus:
        repo = self._nadji(repo_id)
        sada = self._clock()
        kesirano = self._kes.get(repo_id)
        if kesirano is not None and sada - kesirano[0] < KES_SEKUNDI:
            return kesirano[1]

        stanje = self._provider.status(repo.local_path)
        self._kes[repo_id] = (sada, stanje)
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
```

Dopuni `core/domains/codium/repositories/__init__.py`:

```python
from core.domains.codium.repositories.service import (
    NotAGitRepo,
    RepositoryError,
    RepositoryExists,
    RepositoryNotFound,
    RepositoryService,
    RepoSuggestion,
)
```

i dodaj ta imena u `__all__`.

- [ ] **Step 4: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_repositories.py -v
```

Očekivano: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/domains/codium/repositories tests/test_codium_repositories.py
git commit -m "feat(codium): servis repozitorijuma sa kesom stanja, kapijom i dnevnikom"
```

---

### Task 5: Šeme, runtime i router

**Files:**
- Create: `apps/api/schemas/codium_repositories.py`
- Create: `apps/api/codium_repositories_runtime.py`
- Create: `apps/api/routers/codium_repositories.py`
- Modify: `apps/api/main.py` (import i `include_router`)
- Test: `tests/test_api_codium_repositories.py`

**Interfaces:**
- Consumes: `RepositoryService` i njegove izuzetke (Task 4), `GitUnavailable`/`GitError` (Task 2), `codium_security_runtime.get_scope_gate()` i `get_audit()`.
- Produces: `apps/api/codium_repositories_runtime.get_service()` (koristi ga Task 6), router pod `/api/v1/codium/repositories` i zavisnost `get_service` koju testovi menjaju kroz `app.dependency_overrides`.

- [ ] **Step 1: Napiši test koji pada**

`tests/test_api_codium_repositories.py`:

```python
# ========== TESTOVI: API repozitorijuma ==========
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers.codium_repositories import get_service
from core.domains.codium.audit import AuditRepository
from core.domains.codium.repositories import RepoInfo, RepoStatus
from core.domains.codium.repositories.models import BranchInfo, CommitInfo
from core.domains.codium.repositories.providers.base import GitUnavailable
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.repositories.service import RepositoryService
from core.domains.codium.repository import CodiumRepository
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)
from core.security.scope_gate import ScopeGate


class _LazniGit:
    def __init__(self, *, git_postoji: bool = True) -> None:
        self._postoji = git_postoji

    def detect(self, path: str) -> RepoInfo | None:
        if not self._postoji:
            raise GitUnavailable("git nije instaliran na ovoj masini")
        if path != "C:/kod/core":
            return None
        return RepoInfo(root=path, branch="main", remote_url=None)

    def status(self, root: str) -> RepoStatus:
        if not self._postoji:
            raise GitUnavailable("git nije instaliran na ovoj masini")
        return RepoStatus(branch="main", dirty=False, changed_files=0)

    def branches(self, root: str) -> list[BranchInfo]:
        return [BranchInfo(name="main", is_current=True, target="abc1234")]

    def log(self, root, branch, limit, offset) -> list[CommitInfo]:
        svi = [CommitInfo(sha=f"sha{i}", short_sha=f"s{i}", author="CORE",
                          date="2026-08-29T10:00:00+02:00", subject=f"c{i}")
               for i in range(5)]
        return svi[offset:offset + limit]

    def diff(self, root, ref_a, ref_b, path) -> str:
        return "diff --git a/x b/x"

    def file_at(self, root, ref, path) -> str:
        return "sadrzaj"

    def fetch(self, root) -> None:
        return None


def _servis(tmp_path, *, git_postoji: bool = True) -> RepositoryService:
    poslovna = tmp_path / "codium.db"
    operativna = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(operativna)
    return RepositoryService(
        repos=RepositoryRepository(poslovna),
        provider=_LazniGit(git_postoji=git_postoji),
        gate=ScopeGate(lambda: []),
        audit=AuditRepository(operativna),
        projects=CodiumRepository(poslovna),
    )


@pytest.fixture
def klijent(tmp_path) -> Iterator[TestClient]:
    servis = _servis(tmp_path)
    app.dependency_overrides[get_service] = lambda: servis
    with TestClient(app) as klijent:
        yield klijent
    app.dependency_overrides.clear()


def test_registracija_pa_lista(klijent):
    odgovor = klijent.post("/api/v1/codium/repositories/",
                           json={"local_path": "C:/kod/core"})
    assert odgovor.status_code == 200
    assert odgovor.json()["name"] == "core"

    lista = klijent.get("/api/v1/codium/repositories/").json()
    assert len(lista["repositories"]) == 1
    assert lista["repositories"][0]["status"]["branch"] == "main"


def test_registracija_ne_git_putanje_daje_400(klijent):
    odgovor = klijent.post("/api/v1/codium/repositories/",
                           json={"local_path": "C:/kod/nije-repo"})
    assert odgovor.status_code == 400


def test_stranicenje_istorije(klijent):
    upisan = klijent.post("/api/v1/codium/repositories/",
                          json={"local_path": "C:/kod/core"}).json()
    strana = klijent.get(
        f"/api/v1/codium/repositories/{upisan['id']}/commits?limit=2&offset=2"
    ).json()
    assert [c["subject"] for c in strana["commits"]] == ["c2", "c3"]


def test_delete_ne_dira_disk(klijent, tmp_path):
    # Folder koji stvarno postoji na disku ostaje posle brisanja iz registra.
    upisan = klijent.post("/api/v1/codium/repositories/",
                          json={"local_path": "C:/kod/core"}).json()
    odgovor = klijent.delete(f"/api/v1/codium/repositories/{upisan['id']}")
    assert odgovor.status_code == 200
    assert klijent.get("/api/v1/codium/repositories/").json()["repositories"] == []


def test_nepostojeci_repozitorijum_daje_404(klijent):
    assert klijent.get("/api/v1/codium/repositories/999/status").status_code == 404


def test_git_koji_ne_postoji_daje_503(tmp_path):
    servis = _servis(tmp_path, git_postoji=False)
    app.dependency_overrides[get_service] = lambda: servis
    with TestClient(app) as klijent:
        odgovor = klijent.post("/api/v1/codium/repositories/",
                               json={"local_path": "C:/kod/core"})
    app.dependency_overrides.clear()
    assert odgovor.status_code == 503
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api_codium_repositories.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: ... routers.codium_repositories`.

- [ ] **Step 3: Napiši Pydantic šeme**

`apps/api/schemas/codium_repositories.py`:

```python
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
```

- [ ] **Step 4: Napiši runtime**

`apps/api/codium_repositories_runtime.py`:

```python
# ========== RUNTIME REPOZITORIJUMA ==========
# Rute traze servis kroz `Depends`, pa im ovde stoji jedan primerak.
# Testovi ga menjaju kroz `app.dependency_overrides`, ne kroz ovaj modul.
from __future__ import annotations

from pathlib import Path

from apps.api import codium_security_runtime
from core.domains.codium.repositories.providers.local_git import LocalGitProvider
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.repositories.service import RepositoryService
from core.domains.codium.repository import CodiumRepository
from core.domains.codium.runtime import codium_database_path

_service: RepositoryService | None = None


def _database_path() -> Path:
    """Poslovna baza. Izdvojeno da test moze da je zameni."""
    return codium_database_path()


def get_service() -> RepositoryService:
    global _service
    if _service is None:
        baza = _database_path()
        _service = RepositoryService(
            repos=RepositoryRepository(baza),
            provider=LocalGitProvider(),
            gate=codium_security_runtime.get_scope_gate(),
            audit=codium_security_runtime.get_audit(),
            projects=CodiumRepository(baza),
        )
    return _service


def reset() -> None:
    """Zaboravi napravljen primerak (koristi se u testovima)."""
    global _service
    _service = None
```

- [ ] **Step 5: Napiši router**

`apps/api/routers/codium_repositories.py`:

```python
# ========== ROUTER: REPOZITORIJUMI (CODIUM) ==========
# Rute nose `actor="human"` — covek ne prolazi kroz kapiju. Agent ide istim
# servisom sa `actor=f"agent:{slug}"` i pada na pravilo iz migracije v10.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api import codium_repositories_runtime
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
from core.domains.codium.repositories.providers.base import GitError, GitUnavailable
from core.domains.codium.repositories.service import (
    NotAGitRepo,
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
    return codium_repositories_runtime.get_service()


def _prevedi(greska: Exception) -> HTTPException:
    """Domenska greska u HTTP odgovor.

    `stderr` git-a ume da nosi apsolutne putanje, pa ide samo prva linija
    koju je provider vec skratio.
    """

    if isinstance(greska, RepositoryNotFound):
        return HTTPException(status_code=404, detail=str(greska))
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
    except (RepositoryExists, NotAGitRepo, GitUnavailable, GitError) as greska:
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
```

- [ ] **Step 6: Registruj router**

U `apps/api/main.py`, uz ostale CODIUM import-e:

```python
from apps.api.routers.codium_repositories import (
    router as codium_repositories_router,
)
```

i uz ostale `include_router` pozive:

```python
app.include_router(codium_repositories_router)
```

- [ ] **Step 7: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api_codium_repositories.py -v
```

Očekivano: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/api/schemas/codium_repositories.py apps/api/codium_repositories_runtime.py apps/api/routers/codium_repositories.py apps/api/main.py tests/test_api_codium_repositories.py
git commit -m "feat(api): rute za CODIUM repozitorijume"
```

---

### Task 6: Alati agenta `git_log` i `git_diff`

**Files:**
- Modify: `core/domains/codium/agents/tools/builtin.py`
- Modify: `apps/api/codium_agents_runtime.py` (`tools_for`, `tool_catalog`)
- Test: `tests/test_codium_agent_tools.py`

**Interfaces:**
- Consumes: `RepositoryService` (Task 4), `codium_repositories_runtime.get_service()` (Task 5).
- Produces: `build_tools(explorer, service, project_id, repos=None)` — četvrti parametar je opcion, sa podrazumevanim `None`, da postojeći pozivi ne puknu. Registar dobija alate `git_log` i `git_diff`, oba sa `action="repo.read"`.

- [ ] **Step 1: Napiši test koji pada**

Dopuni `tests/test_codium_agent_tools.py` ovim testovima (postojeće testove ne diraj):

```python
# ---------- git alati ----------

class _LazniRepoServis:
    """Servis repozitorijuma sveden na ono sto alati koriste."""

    def __init__(self, repoi: list) -> None:
        self._repoi = repoi

    def list(self, project_id=None):
        return [(repo, None) for repo in self._repoi]

    def history(self, repo_id, branch="", limit=50, offset=0):
        from core.domains.codium.repositories import CommitInfo
        return [CommitInfo(sha="sha1", short_sha="s1", author="CORE",
                           date="2026-08-29T10:00:00+02:00",
                           subject="prvi commit")]

    def diff(self, repo_id, ref_a, ref_b, path=None):
        return "diff --git a/x b/x"


def test_git_log_bez_registrovanog_repozitorijuma_vraca_recenicu(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer

    alati = build_tools(CodiumExplorer(tmp_path), None, 1,
                        repos=_LazniRepoServis([]))
    odgovor = alati.get("git_log").run()
    assert "nema registrovan repozitorijum" in odgovor.lower()


def test_git_log_bez_servisa_ne_puca(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer

    alati = build_tools(CodiumExplorer(tmp_path), None, 1)
    odgovor = alati.get("git_log").run()
    assert "nema registrovan repozitorijum" in odgovor.lower()


def test_git_log_vraca_commit_e_prvog_repozitorijuma(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer
    from core.domains.codium.repositories import Repository

    repo = Repository(id=3, name="core", local_path="C:/kod/core")
    alati = build_tools(CodiumExplorer(tmp_path), None, 1,
                        repos=_LazniRepoServis([repo]))
    odgovor = alati.get("git_log").run()
    assert "prvi commit" in odgovor
    assert "s1" in odgovor


def test_git_alati_nose_akciju_repo_read(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer

    alati = build_tools(CodiumExplorer(tmp_path), None, None)
    assert alati.get("git_log").action == "repo.read"
    assert alati.get("git_diff").action == "repo.read"
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_tools.py -v
```

Očekivano: FAIL — `build_tools() got an unexpected keyword argument 'repos'`.

- [ ] **Step 3: Dopuni alate**

U `core/domains/codium/agents/tools/builtin.py`, izmeni potpis i dodaj dva alata. Import na vrhu fajla:

```python
from core.domains.codium.repositories.service import RepositoryService
```

Nov potpis i telo (dodaci unutar `build_tools`, pre `return ToolRegistry([...])`):

```python
def build_tools(explorer: CodiumExplorer, service: CodiumService | None,
                project_id: int | None,
                repos: RepositoryService | None = None) -> ToolRegistry:
    """Sklapa alate vezane za jedan projekat.

    `repos` je opcion: bez njega git alati stoje u registru ali kazu da
    repozitorijuma nema. Tako model dobija recenicu, a ne izuzetak.
    """

    def _prvi_repo():
        """Repozitorijum projekta nad kojim git alati rade.

        Kad ih projekat ima vise, uzima se najstariji upis — `list` vraca
        redove sortirane po `id`. Alat to kaze u odgovoru, da model ne bi
        mislio da je video sve.
        """

        if repos is None:
            return None
        parovi = repos.list(project_id)
        return parovi[0][0] if parovi else None

    def alat_git_log(limit: int = 20) -> str:
        repo = _prvi_repo()
        if repo is None:
            return "Projekat nema registrovan repozitorijum."
        commiti = repos.history(repo.id, limit=int(limit))
        if not commiti:
            return f"Repozitorijum `{repo.name}` nema commit-a."
        redovi = [f"{c.short_sha} {c.date[:10]} {c.author}: {c.subject}"
                  for c in commiti]
        return f"Repozitorijum `{repo.name}`:\n" + "\n".join(redovi)

    def alat_git_diff(a: str = "", b: str = "", path: str = "") -> str:
        repo = _prvi_repo()
        if repo is None:
            return "Projekat nema registrovan repozitorijum."
        if not a or not b:
            return "Nedostaje `a` ili `b` — razlika trazi dva ref-a."
        razlika = repos.diff(repo.id, a, b, path or None)
        return razlika or "Nema razlike izmedju ta dva ref-a."
```

I dva nova `ToolSpec`-a u listi koja se vraća:

```python
        ToolSpec(
            name="git_log",
            description="Istorija commit-a repozitorijuma projekta.",
            args={"limit": "najvise commit-a (podrazumevano 20)"},
            action="repo.read",
            run=alat_git_log,
        ),
        ToolSpec(
            name="git_diff",
            description="Razlika izmedju dva ref-a u repozitorijumu projekta.",
            args={"a": "prvi ref", "b": "drugi ref",
                  "path": "opciona putanja, prazno za ceo repozitorijum"},
            action="repo.read",
            run=alat_git_diff,
        ),
```

- [ ] **Step 4: Ožiči servis u runtime agenata**

U `apps/api/codium_agents_runtime.py` dodaj import:

```python
from apps.api import codium_repositories_runtime
```

i izmeni `tools_for`:

```python
def tools_for(project_id: int | None) -> ToolRegistry:
    return build_tools(CodiumExplorer(project_root(project_id)),
                       get_service(), project_id,
                       repos=codium_repositories_runtime.get_service())
```

`tool_catalog()` ostaje kakav jeste — zove `tools_for(None)`, pa i on sada opisuje osam alata.

- [ ] **Step 5: Pokreni testove da prođu**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_tools.py tests/test_codium_agent_loop.py -v
```

Očekivano: PASS.

- [ ] **Step 6: Pokreni ceo backend skup**

```bash
./.venv/Scripts/python.exe -m pytest tests -q
```

Očekivano: PASS.

- [ ] **Step 7: Commit**

```bash
git add core/domains/codium/agents/tools/builtin.py apps/api/codium_agents_runtime.py tests/test_codium_agent_tools.py
git commit -m "feat(codium): agent dobija git_log i git_diff"
```

---

### Task 7: GUI tipovi, API klijent i značke

**Files:**
- Modify: `apps/gui/src/types/codium.ts`
- Modify: `apps/gui/src/services/codiumApi.ts`
- Create: `apps/gui/src/features/codium/repositories/repoBadges.ts`
- Test: `apps/gui/src/features/codium/repositories/repoBadges.test.ts`

**Interfaces:**
- Consumes: rute iz Task-a 5.
- Produces:
  - tipovi `Repository`, `RepoStatus`, `RepositoryWithStatus`, `BranchInfo`, `CommitInfo`, `RepoSuggestion` i omotači odgovora `RepositoriesResponse`, `BranchesResponse`, `CommitsResponse`, `DiffResponse`, `FileAtResponse`, `SuggestionsResponse`, `SyncResponse`
  - funkcije `fetchRepositories`, `fetchRepoSuggestions`, `registerRepository`, `deleteRepository`, `fetchRepoStatus`, `fetchRepoBranches`, `fetchRepoCommits`, `fetchRepoDiff`, `fetchRepoFileAt`, `syncRepository`
  - `repoBadges(status: RepoStatus): string[]` — tekst značaka za jedan repozitorijum

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/repositories/repoBadges.test.ts`:

```typescript
import { describe, expect, it } from "vitest";

import { repoBadges } from "./repoBadges";

describe("repoBadges", () => {
  it("čist repozitorijum na grani daje samo granu", () => {
    expect(
      repoBadges({
        branch: "main",
        dirty: false,
        changed_files: 0,
        ahead: 0,
        behind: 0,
        missing: false,
      }),
    ).toEqual(["main"]);
  });

  it("neispraćene izmene daju značku sa brojem", () => {
    expect(
      repoBadges({
        branch: "main",
        dirty: true,
        changed_files: 3,
        ahead: 0,
        behind: 0,
        missing: false,
      }),
    ).toEqual(["main", "3 izmene"]);
  });

  it("jedna izmena je u jednini", () => {
    const znacke = repoBadges({
      branch: "main",
      dirty: true,
      changed_files: 1,
      ahead: 0,
      behind: 0,
      missing: false,
    });
    expect(znacke).toContain("1 izmena");
  });

  it("ahead i behind idu kao zasebne značke", () => {
    expect(
      repoBadges({
        branch: "main",
        dirty: false,
        changed_files: 0,
        ahead: 2,
        behind: 1,
        missing: false,
      }),
    ).toEqual(["main", "↑2", "↓1"]);
  });

  it("nestao folder daje samo jednu značku", () => {
    expect(
      repoBadges({
        branch: "",
        dirty: false,
        changed_files: 0,
        ahead: 0,
        behind: 0,
        missing: true,
      }),
    ).toEqual(["nema na disku"]);
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/repositories/repoBadges.test.ts
```

(iz `apps/gui`.) Očekivano: FAIL — modul `./repoBadges` ne postoji.

- [ ] **Step 3: Napiši tipove**

U `apps/gui/src/types/codium.ts` dodaj:

```typescript
// ==========          REPOZITORIJUMI (E2)          ==========

export interface RepoStatus {
  branch: string;
  dirty: boolean;
  changed_files: number;
  ahead: number;
  behind: number;
  missing: boolean;
}

export interface Repository {
  id: number;
  project_id: number | null;
  name: string;
  local_path: string;
  remote_url: string | null;
  default_branch: string;
  provider: string;
  last_synced_at: string | null;
}

export interface RepositoryWithStatus extends Repository {
  status: RepoStatus;
}

export interface BranchInfo {
  name: string;
  is_current: boolean;
  target: string;
}

export interface CommitInfo {
  sha: string;
  short_sha: string;
  author: string;
  date: string;
  subject: string;
  body: string;
  files_changed: number;
  insertions: number;
  deletions: number;
}

export interface RepoSuggestion {
  project_id: number;
  project_name: string;
  local_path: string;
}

export interface RepositoriesResponse {
  repositories: RepositoryWithStatus[];
}

export interface BranchesResponse {
  branches: BranchInfo[];
}

export interface CommitsResponse {
  commits: CommitInfo[];
}

export interface DiffResponse {
  diff: string;
}

export interface FileAtResponse {
  content: string;
}

export interface SuggestionsResponse {
  suggestions: RepoSuggestion[];
}

export interface SyncResponse {
  executed: boolean;
  detail: string;
}

export interface RepositoryCreateRequest {
  local_path: string;
  project_id?: number | null;
  name?: string | null;
}
```

- [ ] **Step 4: Dopuni API klijent**

U `apps/gui/src/services/codiumApi.ts` dodaj tipove u postojeći `import type { ... }` blok (`BranchesResponse`, `CommitsResponse`, `DiffResponse`, `FileAtResponse`, `RepositoriesResponse`, `Repository`, `RepositoryCreateRequest`, `RepoStatus`, `SuggestionsResponse`, `SyncResponse`) i na dno fajla:

```typescript
// ==========          REPOZITORIJUMI (E2)          ==========

export function fetchRepositories(
  projectId?: number,
): Promise<RepositoriesResponse> {
  const upit = projectId === undefined ? "" : `?project_id=${projectId}`;
  return getJson(`/api/v1/codium/repositories/${upit}`);
}

export function fetchRepoSuggestions(): Promise<SuggestionsResponse> {
  return getJson("/api/v1/codium/repositories/suggestions");
}

export function registerRepository(
  zahtev: RepositoryCreateRequest,
): Promise<Repository> {
  return postJson("/api/v1/codium/repositories/", zahtev);
}

export function deleteRepository(repoId: number): Promise<{ deleted: number }> {
  return deleteRequest(`/api/v1/codium/repositories/${repoId}`);
}

export function fetchRepoStatus(repoId: number): Promise<RepoStatus> {
  return getJson(`/api/v1/codium/repositories/${repoId}/status`);
}

export function fetchRepoBranches(repoId: number): Promise<BranchesResponse> {
  return getJson(`/api/v1/codium/repositories/${repoId}/branches`);
}

export function fetchRepoCommits(
  repoId: number,
  branch = "",
  limit = 50,
  offset = 0,
): Promise<CommitsResponse> {
  const grana = branch ? `&branch=${encodeURIComponent(branch)}` : "";
  return getJson(
    `/api/v1/codium/repositories/${repoId}/commits?limit=${limit}&offset=${offset}${grana}`,
  );
}

export function fetchRepoDiff(
  repoId: number,
  a: string,
  b: string,
  path?: string,
): Promise<DiffResponse> {
  const putanja = path ? `&path=${encodeURIComponent(path)}` : "";
  return getJson(
    `/api/v1/codium/repositories/${repoId}/diff?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}${putanja}`,
  );
}

export function fetchRepoFileAt(
  repoId: number,
  ref: string,
  path: string,
): Promise<FileAtResponse> {
  return getJson(
    `/api/v1/codium/repositories/${repoId}/file?ref=${encodeURIComponent(ref)}&path=${encodeURIComponent(path)}`,
  );
}

export function syncRepository(repoId: number): Promise<SyncResponse> {
  return postJson(`/api/v1/codium/repositories/${repoId}/sync`, {});
}
```

- [ ] **Step 5: Napiši `repoBadges`**

`apps/gui/src/features/codium/repositories/repoBadges.ts`:

```typescript
import type { RepoStatus } from "../../../types/codium";

/**
 * Stanje repozitorijuma u tekst značaka koje lista prikazuje.
 *
 * Čist modul bez React-a i bez mreže — zato ga test pokriva direktno.
 */
export function repoBadges(status: RepoStatus): string[] {
  // Folder koji više ne postoji nema šta drugo da kaže; grana i brojevi
  // iz keša bi bili laž.
  if (status.missing) {
    return ["nema na disku"];
  }

  const znacke: string[] = [];
  if (status.branch) {
    znacke.push(status.branch);
  }
  if (status.changed_files > 0) {
    const rec = status.changed_files === 1 ? "izmena" : "izmene";
    znacke.push(`${status.changed_files} ${rec}`);
  }
  if (status.ahead > 0) {
    znacke.push(`↑${status.ahead}`);
  }
  if (status.behind > 0) {
    znacke.push(`↓${status.behind}`);
  }
  return znacke;
}
```

- [ ] **Step 6: Pokreni test da prođe**

```bash
npm run test -- src/features/codium/repositories/repoBadges.test.ts
```

Očekivano: PASS.

- [ ] **Step 7: Proveri tipove**

```bash
npm run build
```

Očekivano: `tsc` bez greške.

- [ ] **Step 8: Commit**

```bash
git add apps/gui/src/types/codium.ts apps/gui/src/services/codiumApi.ts apps/gui/src/features/codium/repositories
git commit -m "feat(gui): tipovi, API klijent i znacke za repozitorijume"
```

---

### Task 8: Strana `/codium/repositories`

**Files:**
- Create: `apps/gui/src/features/codium/repositories/useRepositories.ts`
- Create: `apps/gui/src/features/codium/repositories/RepoList.tsx`
- Create: `apps/gui/src/features/codium/repositories/RegisterRepo.tsx`
- Create: `apps/gui/src/features/codium/repositories/CommitHistory.tsx`
- Create: `apps/gui/src/features/codium/repositories/CommitDiff.tsx`
- Create: `apps/gui/src/pages/CodiumRepositories.tsx`
- Create: `apps/gui/src/styles/codium-repositories.css`
- Modify: `apps/gui/src/App.tsx` (ruta)
- Modify: `apps/gui/src/components/layout/Sidebar.tsx` (stavka prelazi u rutu)
- Test: `apps/gui/src/pages/CodiumRepositories.test.tsx`

**Interfaces:**
- Consumes: sve iz Task-a 7.
- Produces: `useRepositories()` koji vraća `{ repositories, suggestions, isLoading, error, refresh, register, remove, sync }`; komponente `RepoList`, `RegisterRepo`, `CommitHistory`, `CommitDiff` (koristi ih i Task 9).

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/pages/CodiumRepositories.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CodiumRepositories from "./CodiumRepositories";
import * as api from "../services/codiumApi";

vi.mock("../services/codiumApi");

const REPO = {
  id: 1,
  project_id: null,
  name: "core",
  local_path: "C:/kod/core",
  remote_url: null,
  default_branch: "main",
  provider: "local_git",
  last_synced_at: null,
  status: {
    branch: "main",
    dirty: true,
    changed_files: 2,
    ahead: 1,
    behind: 0,
    missing: false,
  },
};

const COMMIT = {
  sha: "sha1",
  short_sha: "s1",
  author: "CORE",
  date: "2026-08-29T10:00:00+02:00",
  subject: "prvi commit",
  body: "",
  files_changed: 1,
  insertions: 2,
  deletions: 0,
};

beforeEach(() => {
  vi.mocked(api.fetchRepositories).mockResolvedValue({ repositories: [REPO] });
  vi.mocked(api.fetchRepoSuggestions).mockResolvedValue({ suggestions: [] });
  vi.mocked(api.fetchRepoCommits).mockResolvedValue({ commits: [COMMIT] });
});

function nacrtaj() {
  return render(
    <MemoryRouter>
      <CodiumRepositories />
    </MemoryRouter>,
  );
}

describe("CodiumRepositories", () => {
  it("crta listu repozitorijuma sa značkama", async () => {
    nacrtaj();
    expect(await screen.findByText("core")).toBeInTheDocument();
    expect(screen.getByText("main")).toBeInTheDocument();
    expect(screen.getByText("2 izmene")).toBeInTheDocument();
  });

  it("prazan registar nudi upis", async () => {
    vi.mocked(api.fetchRepositories).mockResolvedValue({ repositories: [] });
    nacrtaj();
    expect(
      await screen.findByText(/nijedan repozitorijum nije registrovan/i),
    ).toBeInTheDocument();
  });

  it("izbor repozitorijuma dohvata istoriju", async () => {
    nacrtaj();
    const stavka = await screen.findByText("core");
    await userEvent.click(stavka);
    await waitFor(() => {
      expect(api.fetchRepoCommits).toHaveBeenCalledWith(1, "", 50, 0);
    });
    expect(await screen.findByText("prvi commit")).toBeInTheDocument();
  });

  it("ponuda iz projekata se prikazuje kad postoji", async () => {
    vi.mocked(api.fetchRepoSuggestions).mockResolvedValue({
      suggestions: [
        { project_id: 4, project_name: "Filmium", local_path: "C:/kod/filmium" },
      ],
    });
    nacrtaj();
    expect(await screen.findByText(/Filmium/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/pages/CodiumRepositories.test.tsx
```

Očekivano: FAIL — modul `./CodiumRepositories` ne postoji.

- [ ] **Step 3: Napiši hook**

`apps/gui/src/features/codium/repositories/useRepositories.ts`:

```typescript
import { useCallback, useEffect, useState } from "react";

import {
  deleteRepository,
  fetchRepoSuggestions,
  fetchRepositories,
  registerRepository,
  syncRepository,
} from "../../../services/codiumApi";
import type {
  RepositoryWithStatus,
  RepoSuggestion,
} from "../../../types/codium";

/**
 * Registar repozitorijuma i ponuda iz projekata, sa osvežavanjem.
 *
 * Bez polling-a: lista se osvežava na akciju korisnika. Stanje ionako ima
 * keš od 10 s u servisu, pa bi tajmer samo trošio procese.
 */
export function useRepositories(projectId?: number) {
  const [repositories, setRepositories] = useState<RepositoryWithStatus[]>([]);
  const [suggestions, setSuggestions] = useState<RepoSuggestion[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [lista, ponude] = await Promise.all([
        fetchRepositories(projectId),
        fetchRepoSuggestions(),
      ]);
      setRepositories(lista.repositories);
      setSuggestions(ponude.suggestions);
      setError("");
    } catch (greska) {
      setError(greska instanceof Error ? greska.message : String(greska));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const register = useCallback(
    async (localPath: string, forProject?: number | null) => {
      await registerRepository({ local_path: localPath, project_id: forProject });
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (repoId: number) => {
      await deleteRepository(repoId);
      await refresh();
    },
    [refresh],
  );

  const sync = useCallback(
    async (repoId: number) => {
      await syncRepository(repoId);
      await refresh();
    },
    [refresh],
  );

  return { repositories, suggestions, isLoading, error, refresh, register, remove, sync };
}
```

- [ ] **Step 4: Napiši komponente**

`apps/gui/src/features/codium/repositories/RepoList.tsx`:

```tsx
import type { RepositoryWithStatus } from "../../../types/codium";
import { repoBadges } from "./repoBadges";

type Props = {
  repositories: RepositoryWithStatus[];
  selectedId: number | null;
  onSelect: (repoId: number) => void;
  onSync: (repoId: number) => void;
  onRemove: (repoId: number) => void;
};

export default function RepoList({
  repositories,
  selectedId,
  onSelect,
  onSync,
  onRemove,
}: Props) {
  if (repositories.length === 0) {
    return (
      <p className="crepo-prazno">
        Nijedan repozitorijum nije registrovan. Dodaj putanju iznad.
      </p>
    );
  }

  return (
    <ul className="crepo-lista">
      {repositories.map((repo) => (
        <li
          key={repo.id}
          className={`crepo-stavka ${repo.id === selectedId ? "izabrana" : ""}`}
        >
          <button type="button" className="crepo-ime" onClick={() => onSelect(repo.id)}>
            {repo.name}
          </button>
          <div className="crepo-znacke">
            {repoBadges(repo.status).map((znacka) => (
              <span key={znacka} className="crepo-znacka">
                {znacka}
              </span>
            ))}
          </div>
          <div className="crepo-akcije">
            <button type="button" onClick={() => onSync(repo.id)}>
              Sinhronizuj
            </button>
            <button type="button" onClick={() => onRemove(repo.id)}>
              Ukloni
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
```

`apps/gui/src/features/codium/repositories/RegisterRepo.tsx`:

```tsx
import { useState } from "react";

import type { RepoSuggestion } from "../../../types/codium";

type Props = {
  suggestions: RepoSuggestion[];
  onRegister: (localPath: string, projectId?: number | null) => Promise<void>;
};

/**
 * Ručan upis putanje, uz ponudu projekata čiji je `local_path` git repo.
 *
 * Registar ostaje čovekova odluka — ponuda samo skraćuje kucanje putanje
 * koju sistem ionako zna.
 */
export default function RegisterRepo({ suggestions, onRegister }: Props) {
  const [putanja, setPutanja] = useState("");
  const [greska, setGreska] = useState("");

  async function upisi(localPath: string, projectId?: number | null) {
    try {
      await onRegister(localPath, projectId);
      setPutanja("");
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <div className="crepo-upis">
      <form
        onSubmit={(dogadjaj) => {
          dogadjaj.preventDefault();
          void upisi(putanja.trim());
        }}
      >
        <input
          type="text"
          value={putanja}
          placeholder="Putanja do repozitorijuma"
          aria-label="Putanja do repozitorijuma"
          onChange={(dogadjaj) => setPutanja(dogadjaj.target.value)}
        />
        <button type="submit" disabled={!putanja.trim()}>
          Registruj
        </button>
      </form>

      {greska && <p className="crepo-greska">{greska}</p>}

      {suggestions.length > 0 && (
        <div className="crepo-ponuda">
          <p className="crepo-hint">Projekti čija je putanja git repozitorijum:</p>
          <ul>
            {suggestions.map((ponuda) => (
              <li key={ponuda.project_id}>
                <button
                  type="button"
                  onClick={() => void upisi(ponuda.local_path, ponuda.project_id)}
                >
                  {ponuda.project_name} — {ponuda.local_path}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

`apps/gui/src/features/codium/repositories/CommitHistory.tsx`:

```tsx
import { useEffect, useState } from "react";

import { fetchRepoCommits } from "../../../services/codiumApi";
import type { CommitInfo } from "../../../types/codium";

type Props = {
  repoId: number | null;
  branch?: string;
  onSelect: (commit: CommitInfo) => void;
  selectedSha: string | null;
};

export default function CommitHistory({
  repoId,
  branch = "",
  onSelect,
  selectedSha,
}: Props) {
  const [commits, setCommits] = useState<CommitInfo[]>([]);
  const [greska, setGreska] = useState("");

  useEffect(() => {
    if (repoId === null) {
      setCommits([]);
      return;
    }
    let otkazano = false;
    fetchRepoCommits(repoId, branch, 50, 0)
      .then((odgovor) => {
        if (!otkazano) {
          setCommits(odgovor.commits);
          setGreska("");
        }
      })
      .catch((problem: unknown) => {
        if (!otkazano) {
          setGreska(problem instanceof Error ? problem.message : String(problem));
        }
      });
    return () => {
      otkazano = true;
    };
  }, [repoId, branch]);

  if (repoId === null) {
    return <p className="crepo-hint">Izaberi repozitorijum.</p>;
  }
  if (greska) {
    return <p className="crepo-greska">{greska}</p>;
  }

  return (
    <ul className="crepo-istorija">
      {commits.map((commit) => (
        <li key={commit.sha}>
          <button
            type="button"
            className={commit.sha === selectedSha ? "izabran" : ""}
            onClick={() => onSelect(commit)}
          >
            <span className="crepo-sha">{commit.short_sha}</span>
            <span className="crepo-naslov">{commit.subject}</span>
            <span className="crepo-autor">{commit.author}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
```

`apps/gui/src/features/codium/repositories/CommitDiff.tsx`:

```tsx
import { DiffEditor } from "@monaco-editor/react";
import { useEffect, useState } from "react";

import { fetchRepoDiff } from "../../../services/codiumApi";
import type { CommitInfo } from "../../../types/codium";

type Props = {
  repoId: number | null;
  commit: CommitInfo | null;
};

/**
 * Razlika izabranog commit-a prema njegovom roditelju.
 *
 * Monaco `DiffEditor` traži dva teksta, a ne unified patch. Dok se ne
 * izabere pojedinačan fajl, prikazuje se sam patch kao tekst — to je i
 * dalje tačna slika izmene, bez lažne strukture.
 */
export default function CommitDiff({ repoId, commit }: Props) {
  const [patch, setPatch] = useState("");
  const [greska, setGreska] = useState("");

  useEffect(() => {
    if (repoId === null || commit === null) {
      setPatch("");
      return;
    }
    let otkazano = false;
    fetchRepoDiff(repoId, `${commit.sha}~1`, commit.sha)
      .then((odgovor) => {
        if (!otkazano) {
          setPatch(odgovor.diff);
          setGreska("");
        }
      })
      .catch((problem: unknown) => {
        if (!otkazano) {
          setGreska(problem instanceof Error ? problem.message : String(problem));
        }
      });
    return () => {
      otkazano = true;
    };
  }, [repoId, commit]);

  if (commit === null) {
    return <p className="crepo-hint">Izaberi commit da vidiš razliku.</p>;
  }
  if (greska) {
    return <p className="crepo-greska">{greska}</p>;
  }

  return (
    <div className="crepo-razlika">
      <DiffEditor
        height="100%"
        language="diff"
        original=""
        modified={patch}
        options={{ readOnly: true, renderSideBySide: false }}
      />
    </div>
  );
}
```

- [ ] **Step 5: Napiši stranu i stil**

`apps/gui/src/pages/CodiumRepositories.tsx`:

```tsx
import { useState } from "react";

import CommitDiff from "../features/codium/repositories/CommitDiff";
import CommitHistory from "../features/codium/repositories/CommitHistory";
import RegisterRepo from "../features/codium/repositories/RegisterRepo";
import RepoList from "../features/codium/repositories/RepoList";
import { useRepositories } from "../features/codium/repositories/useRepositories";
import type { CommitInfo } from "../types/codium";
import "../styles/codium-repositories.css";

export default function CodiumRepositories() {
  const { repositories, suggestions, isLoading, error, register, remove, sync } =
    useRepositories();
  const [izabranRepo, setIzabranRepo] = useState<number | null>(null);
  const [izabranCommit, setIzabranCommit] = useState<CommitInfo | null>(null);

  return (
    <div className="crepo-strana">
      <header className="crepo-zaglavlje">
        <h1>Repositories</h1>
        {isLoading && <span className="crepo-hint">Učitavanje…</span>}
        {error && <span className="crepo-greska">{error}</span>}
      </header>

      <section className="crepo-levo">
        <RegisterRepo suggestions={suggestions} onRegister={register} />
        <RepoList
          repositories={repositories}
          selectedId={izabranRepo}
          onSelect={(repoId) => {
            setIzabranRepo(repoId);
            setIzabranCommit(null);
          }}
          onSync={(repoId) => void sync(repoId)}
          onRemove={(repoId) => void remove(repoId)}
        />
      </section>

      <section className="crepo-desno">
        <CommitHistory
          repoId={izabranRepo}
          onSelect={setIzabranCommit}
          selectedSha={izabranCommit?.sha ?? null}
        />
        <CommitDiff repoId={izabranRepo} commit={izabranCommit} />
      </section>
    </div>
  );
}
```

`apps/gui/src/styles/codium-repositories.css` (uskladi promenljive sa postojećim `codium-*.css` fajlovima u projektu):

```css
/* ==========          CODIUM REPOSITORIES          ========== */

.crepo-strana {
  display: grid;
  grid-template-columns: minmax(280px, 360px) 1fr;
  grid-template-rows: auto 1fr;
  gap: 12px;
  height: 100%;
  padding: 16px;
}

.crepo-zaglavlje {
  grid-column: 1 / -1;
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.crepo-levo,
.crepo-desno {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow: auto;
}

.crepo-lista,
.crepo-istorija {
  list-style: none;
  margin: 0;
  padding: 0;
}

.crepo-stavka {
  display: grid;
  gap: 4px;
  padding: 8px;
  border-radius: 8px;
}

.crepo-stavka.izabrana {
  outline: 1px solid currentColor;
}

.crepo-znacke {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.crepo-znacka {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 999px;
  border: 1px solid currentColor;
}

.crepo-razlika {
  flex: 1;
  min-height: 240px;
}

.crepo-greska {
  color: #d66;
}
```

- [ ] **Step 6: Uveži rutu i sidebar**

U `apps/gui/src/App.tsx`, uz ostale CODIUM rute:

```tsx
        <Route
          path="/codium/repositories"
          element={<CodiumRepositories />}
        />
```

(import `CodiumRepositories` napiši istim stilom kao susedne CODIUM strane u tom fajlu — lazy ili direktan, kako već stoji.)

U `apps/gui/src/components/layout/Sidebar.tsx` zameni red:

```tsx
        { id: "repositories", label: "Repositories", icon: GitBranch, kind: "soon", phase: "F13" },
```

sa:

```tsx
        { id: "repositories", label: "Repositories", icon: GitBranch, kind: "route", path: "/codium/repositories" },
```

- [ ] **Step 7: Oživi pločicu na Overview-u**

U `apps/gui/src/pages/CodiumOverview.tsx` zameni izračunavanje `repoCount` (danas broji projekte sa `repository_url`) stvarnim brojem iz API-ja:

```tsx
  const [repoStats, setRepoStats] = useState({ ukupno: 0, prljavih: 0 });

  useEffect(() => {
    fetchRepositories()
      .then((odgovor) => {
        setRepoStats({
          ukupno: odgovor.repositories.length,
          prljavih: odgovor.repositories.filter((r) => r.status.dirty).length,
        });
      })
      // Overview ne sme da padne zbog jedne pločice.
      .catch(() => setRepoStats({ ukupno: 0, prljavih: 0 }));
  }, []);
```

i u `stats` listi zameni pločicu `stat-repos`:

```tsx
    {
      id: "stat-repos",
      icon: <GitBranch size={20} />,
      label: "Repositories",
      value: isLoading ? "—" : String(repoStats.ukupno),
      hint: `${repoStats.prljavih} sa neispraćenim izmenama`,
    },
```

Dodaj `fetchRepositories` u postojeći import iz `../services/codiumApi`.

- [ ] **Step 8: Pokreni testove da prođu**

```bash
npm run test -- src/pages/CodiumRepositories.test.tsx
```

Očekivano: PASS.

- [ ] **Step 9: Pokreni ceo GUI skup i tipove**

```bash
npm run test
```

```bash
npm run build
```

Očekivano: oba prolaze.

- [ ] **Step 10: Commit**

```bash
git add apps/gui/src
git commit -m "feat(gui): strana Repositories, ruta i ozivljena plocica na Overview-u"
```

---

### Task 9: „Git" panel u docking rasporedu

**Files:**
- Create: `apps/gui/src/features/codium/repositories/GitPanel.tsx`
- Modify: `apps/gui/src/features/codium/CodiumDockLayout.tsx` (`PANEL_COMPONENTS`, `PANEL_META`)
- Test: `apps/gui/src/features/codium/repositories/GitPanel.test.tsx`

**Interfaces:**
- Consumes: `useRepositories(projectId)`, `CommitHistory`, `CommitDiff`, `repoBadges` (Task 7 i 8).
- Produces: `GitPanel({ projectId })` — uži rez iste funkcionalnosti za aktivan projekat; ključ panela `git` u docking rasporedu.

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/repositories/GitPanel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GitPanel from "./GitPanel";
import * as api from "../../../services/codiumApi";

vi.mock("../../../services/codiumApi");

const REPO = {
  id: 7,
  project_id: 3,
  name: "core",
  local_path: "C:/kod/core",
  remote_url: null,
  default_branch: "main",
  provider: "local_git",
  last_synced_at: null,
  status: {
    branch: "main",
    dirty: false,
    changed_files: 0,
    ahead: 0,
    behind: 0,
    missing: false,
  },
};

beforeEach(() => {
  vi.mocked(api.fetchRepoSuggestions).mockResolvedValue({ suggestions: [] });
  vi.mocked(api.fetchRepoCommits).mockResolvedValue({ commits: [] });
});

describe("GitPanel", () => {
  it("traži repozitorijume samo za aktivan projekat", async () => {
    vi.mocked(api.fetchRepositories).mockResolvedValue({ repositories: [REPO] });
    render(<GitPanel projectId={3} />);
    expect(await screen.findByText("core")).toBeInTheDocument();
    expect(api.fetchRepositories).toHaveBeenCalledWith(3);
  });

  it("projekat bez repozitorijuma dobija uputstvo, ne prazan panel", async () => {
    vi.mocked(api.fetchRepositories).mockResolvedValue({ repositories: [] });
    render(<GitPanel projectId={3} />);
    expect(
      await screen.findByText(/nema registrovan repozitorijum/i),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/repositories/GitPanel.test.tsx
```

Očekivano: FAIL — modul `./GitPanel` ne postoji.

- [ ] **Step 3: Napiši panel**

`apps/gui/src/features/codium/repositories/GitPanel.tsx`:

```tsx
import { useState } from "react";

import type { CommitInfo } from "../../../types/codium";
import CommitDiff from "./CommitDiff";
import CommitHistory from "./CommitHistory";
import { repoBadges } from "./repoBadges";
import { useRepositories } from "./useRepositories";

type Props = {
  projectId: number;
};

/**
 * Git uz editor: repozitorijum aktivnog projekta, stanje, istorija i razlika.
 *
 * Uži rez strane `/codium/repositories` — registracija ovde namerno ne stoji,
 * jer je registar odluka koja se donosi nad celim domenom, ne usput.
 */
export default function GitPanel({ projectId }: Props) {
  const { repositories, isLoading, error, sync } = useRepositories(projectId);
  const [izabranCommit, setIzabranCommit] = useState<CommitInfo | null>(null);

  const repo = repositories[0] ?? null;

  if (isLoading) {
    return <p className="crepo-hint">Učitavanje…</p>;
  }
  if (error) {
    return <p className="crepo-greska">{error}</p>;
  }
  if (repo === null) {
    return (
      <p className="crepo-hint">
        Projekat nema registrovan repozitorijum. Dodaj ga na strani Repositories.
      </p>
    );
  }

  return (
    <div className="crepo-panel">
      <header className="crepo-panel-glava">
        <strong>{repo.name}</strong>
        <div className="crepo-znacke">
          {repoBadges(repo.status).map((znacka) => (
            <span key={znacka} className="crepo-znacka">
              {znacka}
            </span>
          ))}
        </div>
        <button type="button" onClick={() => void sync(repo.id)}>
          Sinhronizuj
        </button>
      </header>

      <CommitHistory
        repoId={repo.id}
        onSelect={setIzabranCommit}
        selectedSha={izabranCommit?.sha ?? null}
      />
      <CommitDiff repoId={repo.id} commit={izabranCommit} />
    </div>
  );
}
```

Kad projekat ima više repozitorijuma, panel pokazuje prvi — isto pravilo koje važi za alate agenta. Puna lista je na strani.

- [ ] **Step 4: Uveži panel u docking raspored**

U `apps/gui/src/features/codium/CodiumDockLayout.tsx`:

```tsx
import GitPanel from "./repositories/GitPanel";
```

Panel-komponenta (uz ostale, npr. odmah iza `BrainPanel`):

```tsx
function GitDockPanel(_props: IDockviewPanelProps) {
  const { project } = useDock();
  return (
    <div className="cdk-panel-scroll">
      <GitPanel projectId={project.id} />
    </div>
  );
}
```

`useDock()` je hook koji ostali paneli u tom fajlu već koriste za aktivan projekat.

U `PANEL_COMPONENTS`:

```tsx
  git: GitDockPanel,
```

U `PANEL_META`:

```tsx
  git: { title: "Git", icon: <GitBranch size={13} /> },
```

Dodaj `GitBranch` u import iz `lucide-react`. U `buildDefaultLayout` se **ne** dodaje ništa — panel se otvara ručno, kao Preview i Tasks.

- [ ] **Step 5: Pokreni testove da prođu**

```bash
npm run test -- src/features/codium/repositories/GitPanel.test.tsx
```

Očekivano: PASS.

- [ ] **Step 6: Pokreni ceo GUI skup i tipove**

```bash
npm run test
```

```bash
npm run build
```

Očekivano: oba prolaze.

- [ ] **Step 7: Commit**

```bash
git add apps/gui/src/features/codium
git commit -m "feat(gui): Git panel u docking rasporedu workspace-a"
```

---

### Task 10: Provera uživo, dev-log i indeks

**Files:**
- Create: `.ai/dev-log/2026-08-29-e2-repositories.md`
- Modify: `.ai/izgradnja/codium/00-INDEX.md` (status faze i redosled)
- Modify: `.ai/izgradnja/codium/12-E2-repositories.md` (upisan broj migracije i odstupanja)

**Interfaces:**
- Consumes: sve prethodne task-ove.
- Produces: ništa u kodu; zatvara fazu.

- [ ] **Step 1: Pokreni ceo backend skup**

```bash
./.venv/Scripts/python.exe -m pytest tests -q
```

Očekivano: sve prolazi. Ako `test_local_git_provider` javi SKIPPED, instaliraj git pa ponovi — faza se ne zatvara sa preskočenim proverama provider-a.

- [ ] **Step 2: Pokreni ceo GUI skup i tipove**

```bash
npm run test
```

```bash
npm run build
```

Očekivano: oba prolaze.

- [ ] **Step 3: Proveri uživo**

Pokreni CORE, otvori `/codium/repositories`, pa uradi redom:

1. Registruj repozitorijum ovog projekta ručno (`C:/Users/Game Centar/Documents/AI HOME/CORE - Cloude`) — lista mora da pokaže granu i broj neispraćenih izmena.
2. Proveri da ponuda iz projekata više ne nudi tu putanju.
3. Klikni repozitorijum, pa commit — razlika mora da se prikaže.
4. Klikni „Sinhronizuj" — lista se osveži, a u Audit Logs stoji red `repo.fetch` sa ishodom `ok`.
5. Otvori workspace projekta, dodaj panel „Git" iz trake panela — mora da pokaže isti repozitorijum.
6. Otvori Overview — pločica „Repositories" pokazuje stvaran broj.

- [ ] **Step 4: Napiši dev-log**

`.ai/dev-log/2026-08-29-e2-repositories.md` — kratka beleška: šta je stvarno urađeno, šta je odstupilo od faznog fajla (`/suggestions` i `/{id}/file` su nove rute; GUI je urađen zajedno sa backend-om; migracija je dobila broj v10), i šta je ostalo van dometa. Uskladi oblik sa postojećim fajlovima u `.ai/dev-log/`.

- [ ] **Step 5: Upiši status u indeks**

U `.ai/izgradnja/codium/00-INDEX.md`:

- U tabeli enterprise trake red `E2` dobija `codium v10` u koloni „Baza", status `**zavrseno**` i datum.
- Pasus „**Sledeci posao je E2 Repositories**" zameni novim: sledeći je `E3 Pipelines` (zavisi od E1 i E2, oba završena), a `E0-pun` i dalje čeka svog potrošača.
- U odeljku „Dugovi" ne dodaje se ništa novo osim ako se pri radu ne pojavi parkiran dug — tada red u tabelu, sa izvorom „E2".

U `.ai/izgradnja/codium/12-E2-repositories.md` upiši dodeljen broj migracije (v10) umesto napomene „broj se dodeljuje pri izradi" i dopiši dve rute koje fazni fajl nije imao.

- [ ] **Step 6: Commit**

```bash
git add .ai/dev-log/2026-08-29-e2-repositories.md .ai/izgradnja/codium/00-INDEX.md .ai/izgradnja/codium/12-E2-repositories.md
git commit -m "docs(codium): E2 Repositories zavrsen, indeks i dev-log"
```
