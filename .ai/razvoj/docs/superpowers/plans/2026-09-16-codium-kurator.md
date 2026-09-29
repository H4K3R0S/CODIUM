# CODIUM Kurator (C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Preneti Kurator obrazac na CODIUM: 12 persona-identiteta + deljene dev-komande (repo/pipeline) preko kanonskog frameworka (K), uz malo unazad-kompatibilno proširenje kernela.

**Architecture:** Prvo mali K amandman u CORE (`CuratorActionError` + `AtomLoader.shared_root`). Zatim se osnaženi kanon kopira u CODIUM ćeliju, gde domen dodaje `INTENTS`, `CodiumExecutors` (nad `RepositoryService`/`PipelineService`, sa razrešavanjem imena→id iznutra i `CuratorActionError` na „nije nađeno"), seed atome (12 persona + deljeni katalog), runtime, `codium_curator` router i minimalan GUI (Kurator chat + persona picker + Settings paneli).

**Tech Stack:** Python 3.14, FastAPI, pydantic v2, stdlib; GUI React + TS. Dva repoa.

**Spec:** `docs/superpowers/specs/2026-09-16-codium-kurator-design.md`

## Global Constraints

- **Dva repoa:** Task 1 je u **CORE** (`C:\Users\Game Centar\Documents\AI HOME\CORE - Cloude`, grana `feat/codium-kurator`). Taskovi 2–6 su u **CODIUM ćeliji** (`C:\Users\Game Centar\Desktop\CODIUM`, nova grana `feat/kurator`).
- **Test runneri:** CORE `./.venv/Scripts/python.exe -m pytest`; CODIUM (iz `C:\Users\Game Centar\Desktop\CODIUM`) `./.venv/Scripts/python.exe -m pytest`.
- **Jezik:** srpski stringovi/komentari, engleski identifikatori (interni srpski identifikatori su stil repoa — dozvoljeno).
- **Bez novih zavisnosti** (stdlib + fastapi/pydantic). `httpx` za TestClient je test-only; instalirati u ciljni `.venv` ako fali, ne commitovati.
- **Izvor kanona za kopiranje (Task 2):** CORE `core/cell/curator/`, `core/cell/ai_config.py`, `apps/api/routers/cell.py` (ai-config/atoms endpointi), `apps/api/schemas/cell.py`, `apps/gui/src/cell/{cellApi.ts,CuratorSettingsPanels.tsx}` — POSLE Task 1 (osnaženi kanon).
- **12 persona tekstova:** iz `C:\Users\Game Centar\Documents\AI HOME\CORE - Cloude\NADOGRADNJE\KALIMA\Codium Persone.md` (svih 12 blokova).
- NE diraj FILMIUM ćeliju. NE diraj master ni jedne grane.

## File Structure

CORE (Task 1): `core/cell/curator/protocols.py`, `core/cell/curator/agent.py`, `core/cell/curator/atoms.py` (+ testovi).

CODIUM ćelija (Task 2–6):
- `core/cell/curator/*`, `core/cell/ai_config.py` (kopije kanona).
- `apps/api/routers/cell.py`, `apps/api/schemas/cell.py` (dopune iz kanona).
- `core/domains/codium/curator/{__init__.py,intents.py,executors.py,resolver.py}`.
- `.ai/atomi/personas/<12 id>/persona.md` + `.ai/atomi/personas/_shared/{commands/katalog.md,tools/repo.md,tools/pipeline.md}`.
- `apps/api/codium_curator_runtime.py`, `apps/api/routers/codium_curator.py`, `apps/api/schemas/codium_curator.py`, dopuna `cell_app.py` (`API_ROUTERS`).
- `gui/src/cell/cellApi.ts`, `gui/src/features/codium/CodiumKuratorChat.tsx`, dopuna Settings.

---

## Task 1: K amandman (CuratorActionError + AtomLoader.shared_root) — CORE

**Files:**
- Modify: `core/cell/curator/protocols.py`, `core/cell/curator/agent.py`, `core/cell/curator/atoms.py`
- Test: `tests/test_cck_action_error.py`, dopuna `tests/test_cck_atoms.py`

**Interfaces:**
- Produces: `CuratorActionError(Exception)` u protocols; agent hvata je u handle/confirm → graciozan answer; `AtomLoader(root, shared_root=None)` gde `tool/commands/command_catalog` čitaju iz `shared_root` ako je dat.

- [ ] **Step 1: Napiši failing testove**

```python
# tests/test_cck_action_error.py
from __future__ import annotations

import json
from pathlib import Path

from core.cell.curator.agent import CuratorAgent
from core.cell.curator.atoms import AtomLoader
from core.cell.curator.confirm import ConfirmStore
from core.cell.curator.intents import IntentSpec
from core.cell.curator.interaction_log import InteractionLog
from core.cell.curator.protocols import CuratorActionError


def _seed(root: Path) -> None:
    (root / "tools").mkdir(parents=True)
    (root / "commands").mkdir(parents=True)
    (root / "persona.md").write_text("---\ntype: persona\n---\nX.\n", encoding="utf-8")
    (root / "commands" / "katalog.md").write_text("act|edit\n", encoding="utf-8")


INTENTS = {
    "act": IntentSpec("act", is_write=False, is_navigate=False, needs_entity=False, tool=None, required_params=()),
    "edit": IntentSpec("edit", is_write=True, is_navigate=False, needs_entity=False, tool=None, required_params=()),
}


class _Puca:
    def run(self, intent_name, params):
        raise CuratorActionError("nema toga")

    def preview(self, intent_name, params):
        raise CuratorActionError("nema toga za upis")

    def apply(self, intent_name, params):
        raise CuratorActionError("ne moze")


def _agent(tmp_path, model_json):
    root = tmp_path / "p"
    _seed(root)
    return CuratorAgent(
        intents=INTENTS, executors=_Puca(), resolver=None,
        atoms=AtomLoader(root), confirm=ConfirmStore(),
        log=InteractionLog(tmp_path / "log"),
        generate=lambda m, p, *, system=None, fmt=None: json.dumps(model_json),
        model="x",
    )


def test_run_action_error_je_graciozan(tmp_path):
    a = _agent(tmp_path, {"intent": "act", "params": {}, "reply": "?"})
    r = a.handle("uradi")
    assert r.kind == "answer"
    assert "nema toga" in r.reply


def test_preview_action_error_ne_daje_token(tmp_path):
    a = _agent(tmp_path, {"intent": "edit", "params": {}, "reply": "?"})
    r = a.handle("izmeni")
    assert r.kind == "answer"
    assert r.confirm_token is None
    assert "nema toga za upis" in r.reply
```

Dopuna `tests/test_cck_atoms.py` (dodaj na kraj):

```python
def test_shared_root_odvaja_personu_od_komandi(tmp_path):
    from core.cell.curator.atoms import AtomLoader
    persona = tmp_path / "p"
    shared = tmp_path / "shared"
    (persona).mkdir()
    (persona / "persona.md").write_text("---\ntype: persona\n---\nJa.\n", encoding="utf-8")
    (shared / "commands").mkdir(parents=True)
    (shared / "tools").mkdir(parents=True)
    (shared / "commands" / "katalog.md").write_text("deljeno\n", encoding="utf-8")
    (shared / "tools" / "alat.md").write_text("Alat.\n", encoding="utf-8")
    loader = AtomLoader(persona, shared_root=shared)
    assert "Ja" in loader.persona().body
    assert "deljeno" in loader.command_catalog()
    assert "Alat" in loader.tool("alat").body
```

- [ ] **Step 2: Pokreni — mora da padne**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_cck_action_error.py tests/test_cck_atoms.py -v`
Expected: FAIL (`CuratorActionError` ne postoji; `shared_root` param ne postoji).

- [ ] **Step 3: Implementacija**

U `core/cell/curator/protocols.py` dodaj na vrh (posle importa):

```python
class CuratorActionError(Exception):
    """Domenski izvršilac je diže kad namera ne može gracioznо da se izvrši
    (npr. „nema entiteta tog imena"). Agent je hvata i vraća uredan odgovor."""
```

U `core/cell/curator/agent.py`:
- import: `from core.cell.curator.protocols import Executors, Resolver, CuratorActionError`.
- U `handle`, obmotaj write granu i run granu. Zameni postojeći `if spec.is_write:` blok i `out = self._executors.run(...)` blok ovim:

```python
        if spec.is_write:
            try:
                preview = self._executors.preview(intent_name, params)
            except CuratorActionError as error:
                log_id = self._log.record(message, intent_name, params, spec.tool, reply)
                return AgentResult(kind="answer", intent="unknown",
                                   reply=str(error), log_id=log_id)
            token = self._confirm.issue(intent_name, params)
            log_id = self._log.record(message, intent_name, params, spec.tool, reply)
            return AgentResult(kind="proposal", intent=intent_name, params=params,
                               reply=reply, preview=preview, confirm_token=token,
                               log_id=log_id)

        try:
            out = self._executors.run(intent_name, params)
        except CuratorActionError as error:
            log_id = self._log.record(message, intent_name, params, spec.tool, reply)
            return AgentResult(kind="answer", intent="unknown",
                               reply=str(error), log_id=log_id)
        kind = out.get("kind", "answer")
        sources = out.get("sources", [])
        log_id = self._log.record(message, intent_name, params, spec.tool, reply)
        return AgentResult(kind=kind, intent=intent_name, params=params, reply=reply,
                           preview=out, sources=sources, log_id=log_id)
```

U `core/cell/curator/atoms.py` `AtomLoader`:
- Konstruktor: `def __init__(self, root: Path, shared_root: Path | None = None) -> None:` čuvaj `self._shared = shared_root or root`.
- `persona()` čita iz `self._root` (nepromenjeno).
- `_read` za `tool/commands`: koristi `self._shared` umesto `self._root`. Konkretno neka `tool(name)` čita `self._shared / f"tools/{name}.md"`, a `commands()` `self._shared / "commands/katalog.md"`. `persona()` ostaje na `self._root / "persona.md"`. (Ako `_read(relative)` prima relativnu putanju, dodaj parametar baze ili napravi `_read_from(base, relative)`.)

- [ ] **Step 4: Pokreni — mora da prođe**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_cck_action_error.py tests/test_cck_atoms.py tests/test_cck_agent.py -v`
Expected: PASS (novi + postojeći agent/atoms testovi; `shared_root=None` čuva staro ponašanje).

- [ ] **Step 5: Commit**

```bash
git add core/cell/curator/protocols.py core/cell/curator/agent.py core/cell/curator/atoms.py tests/test_cck_action_error.py tests/test_cck_atoms.py
git commit -m "feat(curator-kernel): CuratorActionError + AtomLoader.shared_root (za multi-persona/multi-entitet)"
```

---

## Task 2: Kopiraj osnaženi kanon u CODIUM ćeliju — CODIUM

**Files (u `C:\Users\Game Centar\Desktop\CODIUM`):**
- Create: `core/cell/curator/*` (8 fajlova), `core/cell/ai_config.py`
- Modify: `apps/api/routers/cell.py`, `apps/api/schemas/cell.py`
- Create: `gui/src/cell/CuratorSettingsPanels.tsx`; Modify `gui/src/cell/cellApi.ts`

**Interfaces:**
- Produces: identičan kanonski framework u CODIUM ćeliji kao u CORE (posle Task 1).

- [ ] **Step 1: Napravi granu**

Iz `C:\Users\Game Centar\Desktop\CODIUM`: `git checkout -b feat/kurator`.

- [ ] **Step 2: Kopiraj Python kanon**

Kopiraj iz CORE (`C:\Users\Game Centar\Documents\AI HOME\CORE - Cloude`) u CODIUM VERBATIM (isti relativni put):
- `core/cell/curator/__init__.py, atoms.py, confirm.py, interaction_log.py, scaffold.py, atom_files.py, intents.py, protocols.py, agent.py`
- `core/cell/ai_config.py`
(Ovo je stanje POSLE Task 1 — sa `CuratorActionError` i `shared_root`.) Bez izmene uvoza (`core.cell.curator.*` isto važi u ćeliji).

- [ ] **Step 3: Dopuni CODIUM cell.py/schemas endpointima**

U CODIUM `apps/api/routers/cell.py` i `apps/api/schemas/cell.py` dodaj generičke
`/cell/ai-config` i `/cell/atoms` endpointe + scheme, TAČNO kao u CORE kanonu
(`apps/api/routers/cell.py`, `apps/api/schemas/cell.py`). APPEND-only; ne diraj
postojeće CODIUM cell endpointe. `_PERSONA_ID` default „opsti" (CODIUM podrazumevana persona).

- [ ] **Step 4: Kopiraj GUI kanon**

Kopiraj CORE `apps/gui/src/cell/CuratorSettingsPanels.tsx` → CODIUM `gui/src/cell/CuratorSettingsPanels.tsx` VERBATIM. Dodaj u CODIUM `gui/src/cell/cellApi.ts` iste tipove/funkcije (`CellAiConfig`, `CellAtom`, `getCellAiConfig`, `saveCellAiConfig`, `listCellAtoms`, `saveCellAtom`) kao u CORE kanonu (rute `/cell/ai-config`, `/cell/atoms`).

- [ ] **Step 5: Provera importa (bez novih testova ovde)**

Run (iz CODIUM): `./.venv/Scripts/python.exe -c "import core.cell.curator.agent, core.cell.ai_config; from core.cell.curator.protocols import CuratorActionError; print('ok')"`
Expected: `ok`. Zatim GUI tsc: `cd gui && npx tsc -p tsconfig.app.json --noEmit` (0 novih grešaka).

- [ ] **Step 6: Commit**

```bash
git add core/cell/curator core/cell/ai_config.py apps/api/routers/cell.py apps/api/schemas/cell.py gui/src/cell/CuratorSettingsPanels.tsx gui/src/cell/cellApi.ts
git commit -m "feat(kurator): kopiraj kanonski curator framework + cell endpointi + GUI paneli"
```

---

## Task 3: CODIUM intenti + izvršioci + razrešavanje imena — CODIUM

**Files:**
- Create: `core/domains/codium/curator/__init__.py`, `core/domains/codium/curator/intents.py`, `core/domains/codium/curator/executors.py`
- Test: `tests/test_codium_curator_executors.py`, `tests/test_codium_curator_intents.py`

**Interfaces:**
- Consumes: kanon `IntentSpec`/`Executors`/`CuratorActionError`; `RepositoryService`, `PipelineService`.
- Produces: `CODIUM_INTENTS`, `CodiumExecutors(repositories, pipelines)`.

- [ ] **Step 1: Napiši failing testove**

```python
# tests/test_codium_curator_intents.py
from core.domains.codium.curator.intents import CODIUM_INTENTS


def test_komande_prisutne():
    assert set(CODIUM_INTENTS) == {
        "list_repos", "list_pipelines", "repo_status", "sync_repo", "run_pipeline", "open"}
    assert CODIUM_INTENTS["sync_repo"].is_write is True
    assert CODIUM_INTENTS["run_pipeline"].is_write is True
    assert CODIUM_INTENTS["open"].is_navigate is True
    assert CODIUM_INTENTS["list_repos"].is_write is False
```

```python
# tests/test_codium_curator_executors.py
from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.cell.curator.protocols import CuratorActionError
from core.domains.codium.curator.executors import CodiumExecutors


@dataclass
class _Repo:
    id: int
    name: str


@dataclass
class _Pipe:
    id: int
    name: str


class _RepoSvc:
    def __init__(self):
        self.synced = None

    def list(self, project_id=None):
        return [(_Repo(1, "alfa"), object()), (_Repo(2, "beta"), object())]

    def status(self, repo_id):
        return {"branch": "main", "id": repo_id}

    def sync(self, repo_id, actor="human"):
        self.synced = (repo_id, actor)
        return True


class _PipeSvc:
    def __init__(self):
        self.ran = None

    def list(self, repository_id=None):
        return [_Pipe(10, "build"), _Pipe(11, "test")]

    def run(self, pipeline_id, actor="human", trigger="manual"):
        self.ran = (pipeline_id, actor)
        return object()


def _ex():
    return CodiumExecutors(_RepoSvc(), _PipeSvc())


def test_list_repos_vraca_imena():
    out = _ex().run("list_repos", {})
    assert out["sources"] == ["alfa", "beta"]


def test_list_pipelines_vraca_imena():
    out = _ex().run("list_pipelines", {})
    assert out["sources"] == ["build", "test"]


def test_open_repo_navigate():
    out = _ex().run("open", {"name": "beta"})
    assert out["kind"] == "navigate"
    assert "/codium/repos/2" in out["route"]


def test_repo_status_razresi_ime():
    out = _ex().run("repo_status", {"name": "alfa"})
    assert out["kind"] == "answer"
    assert "main" in out["reply"]


def test_nepoznato_ime_je_action_error():
    with pytest.raises(CuratorActionError):
        _ex().run("repo_status", {"name": "nema"})


def test_sync_preview_pa_apply():
    ex = _ex()
    prev = ex.preview("sync_repo", {"name": "alfa"})
    assert prev["repo"] == "alfa"
    ex.apply("sync_repo", {"name": "alfa"})
    assert ex._repositories.synced[0] == 1


def test_run_pipeline_apply():
    ex = _ex()
    ex.preview("run_pipeline", {"name": "build"})
    ex.apply("run_pipeline", {"name": "build"})
    assert ex._pipelines.ran[0] == 10
```

- [ ] **Step 2: Pokreni — mora da padne**

Run (CODIUM): `./.venv/Scripts/python.exe -m pytest tests/test_codium_curator_executors.py tests/test_codium_curator_intents.py -v`
Expected: FAIL — moduli ne postoje.

- [ ] **Step 3: Implementacija**

```python
# core/domains/codium/curator/__init__.py
# ========== CODIUM KURATOR (domenski deo) ==========
```

```python
# core/domains/codium/curator/intents.py
# ========== CODIUM INTENTI (allowlist) ==========
from __future__ import annotations

from core.cell.curator.intents import IntentSpec

# `needs_entity=False` svuda: CODIUM ima dva tipa entiteta (repo, pipeline) koje
# izvršilac razrešava IZNUTRA po imenu (`params["name"]`), pa se K `entity_key`
# (jedan tip) ne koristi; „nije nađeno" ide kroz CuratorActionError.
CODIUM_INTENTS: dict[str, IntentSpec] = {
    "list_repos": IntentSpec("list_repos", is_write=False, is_navigate=False,
                             needs_entity=False, tool="repo", required_params=()),
    "list_pipelines": IntentSpec("list_pipelines", is_write=False, is_navigate=False,
                                 needs_entity=False, tool="pipeline", required_params=()),
    "repo_status": IntentSpec("repo_status", is_write=False, is_navigate=False,
                              needs_entity=False, tool="repo", required_params=("name",)),
    "sync_repo": IntentSpec("sync_repo", is_write=True, is_navigate=False,
                            needs_entity=False, tool="repo", required_params=("name",)),
    "run_pipeline": IntentSpec("run_pipeline", is_write=True, is_navigate=False,
                               needs_entity=False, tool="pipeline", required_params=("name",)),
    "open": IntentSpec("open", is_write=False, is_navigate=True,
                       needs_entity=False, tool="repo", required_params=("name",)),
}
```

```python
# core/domains/codium/curator/executors.py
# ========== CODIUM IZVRŠIOCI ==========
# Mapira namere na RepositoryService/PipelineService. Ime entiteta se razrešava
# u id iznutra; nenađeno/višesmisleno → CuratorActionError (agent ga hvata).
from __future__ import annotations

from typing import Any

from core.cell.curator.protocols import CuratorActionError

REPO_ROUTE = "/codium/repos/{id}"


class CodiumExecutors:
    """Izvršioci CODIUM Kuratora (repo + pipeline komande)."""

    def __init__(self, repositories: Any, pipelines: Any) -> None:
        self._repositories = repositories
        self._pipelines = pipelines

    # ---------- razrešavanje imena ----------

    def _repo_id(self, name: str) -> int:
        ime = (name or "").strip().lower()
        pogodci = [r for r, _ in self._repositories.list() if r.name.lower() == ime]
        if len(pogodci) != 1:
            raise CuratorActionError(f"Nema tačno jednog repozitorijuma „{name}".")
        return pogodci[0].id

    def _pipeline_id(self, name: str) -> int:
        ime = (name or "").strip().lower()
        pogodci = [p for p in self._pipelines.list() if p.name.lower() == ime]
        if len(pogodci) != 1:
            raise CuratorActionError(f"Nema tačno jednog pipeline-a „{name}".")
        return pogodci[0].id

    # ---------- run (čitanje / navigacija) ----------

    def run(self, intent_name: str, params: dict) -> dict:
        if intent_name == "list_repos":
            return {"kind": "answer", "sources": [r.name for r, _ in self._repositories.list()]}
        if intent_name == "list_pipelines":
            return {"kind": "answer", "sources": [p.name for p in self._pipelines.list()]}
        if intent_name == "repo_status":
            repo_id = self._repo_id(params["name"])
            stanje = self._repositories.status(repo_id)
            return {"kind": "answer", "reply": f"Status repoa: {stanje}"}
        if intent_name == "open":
            repo_id = self._repo_id(params["name"])
            return {"kind": "navigate", "repo_id": repo_id,
                    "route": REPO_ROUTE.format(id=repo_id)}
        raise CuratorActionError(f"Nepoznata namera: {intent_name}")

    # ---------- preview / apply (upisi) ----------

    def preview(self, intent_name: str, params: dict) -> dict:
        if intent_name == "sync_repo":
            self._repo_id(params["name"])  # razreši ili digni
            return {"repo": params["name"], "akcija": "sync"}
        if intent_name == "run_pipeline":
            self._pipeline_id(params["name"])
            return {"pipeline": params["name"], "akcija": "run"}
        raise CuratorActionError(f"Nepoznat upis: {intent_name}")

    def apply(self, intent_name: str, params: dict) -> dict:
        if intent_name == "sync_repo":
            repo_id = self._repo_id(params["name"])
            self._repositories.sync(repo_id, actor="kurator")
            return {"synced": True, "repo": params["name"]}
        if intent_name == "run_pipeline":
            pipeline_id = self._pipeline_id(params["name"])
            self._pipelines.run(pipeline_id, actor="kurator")
            return {"started": True, "pipeline": params["name"]}
        raise CuratorActionError(f"Nepoznat upis: {intent_name}")
```

Napomena: `repo_status` reply koristi ceo `status(...)` objekat radi jednostavnosti;
ako želiš čitljiviji tekst, formatiraj iz `RepoStatus` polja (proveri model
`core/domains/codium/repositories/models.py`). Nije blokada za testove.

- [ ] **Step 4: Pokreni — mora da prođe**

Run (CODIUM): `./.venv/Scripts/python.exe -m pytest tests/test_codium_curator_executors.py tests/test_codium_curator_intents.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/domains/codium/curator/__init__.py core/domains/codium/curator/intents.py core/domains/codium/curator/executors.py tests/test_codium_curator_executors.py tests/test_codium_curator_intents.py
git commit -m "feat(kurator): CODIUM intenti + izvrsioci (repo/pipeline) sa razresavanjem imena"
```

---

## Task 4: Seed atomi (12 persona + deljeni katalog) — CODIUM

**Files:**
- Create: `.ai/atomi/personas/<12 id>/persona.md`
- Create: `.ai/atomi/personas/_shared/commands/katalog.md`, `.ai/atomi/personas/_shared/tools/repo.md`, `.ai/atomi/personas/_shared/tools/pipeline.md`
- Test: `tests/test_codium_curator_atoms.py`

**Interfaces:**
- Consumes: `AtomLoader(root, shared_root)` (Task 1).

- [ ] **Step 1: Napiši failing test**

```python
# tests/test_codium_curator_atoms.py
from __future__ import annotations

from pathlib import Path

from core.cell.curator.atoms import AtomLoader

_BASE = Path(__file__).resolve().parents[1] / ".ai" / "atomi" / "personas"
_IDS = ["opsti", "arhitekta", "graditelj", "recenzent", "dizajner", "menadzer",
        "debager", "pisac", "bezbednjak", "devops", "tester", "data-engineer"]


def test_svih_12_persona_postoji():
    for pid in _IDS:
        assert (_BASE / pid / "persona.md").is_file(), pid


def test_deljeni_katalog_ima_komande():
    loader = AtomLoader(_BASE / "opsti", shared_root=_BASE / "_shared")
    catalog = loader.command_catalog()
    for intent in ("list_repos", "sync_repo", "run_pipeline", "open"):
        assert intent in catalog
    assert "repo" in loader.tool("repo").body.lower()
    assert "pipeline" in loader.tool("pipeline").body.lower()


def test_persona_telo_iz_root():
    loader = AtomLoader(_BASE / "graditelj", shared_root=_BASE / "_shared")
    assert loader.persona().body.strip()
```

- [ ] **Step 2: Pokreni — mora da padne**

Run (CODIUM): `./.venv/Scripts/python.exe -m pytest tests/test_codium_curator_atoms.py -v`
Expected: FAIL — atomi ne postoje.

- [ ] **Step 3: Napravi atome**

Za svih 12 persona kreiraj `.ai/atomi/personas/<id>/persona.md` sa frontmatter-om
i telom. Tekst svake persone PREUZMI iz
`C:\Users\Game Centar\Documents\AI HOME\CORE - Cloude\NADOGRADNJE\KALIMA\Codium Persone.md`
(svaki `## # <Ime>` blok = jedna persona). Mapiranje naslov→id:
Opšti pomoćnik→`opsti`, Arhitekta→`arhitekta`, Graditelj→`graditelj`,
Recenzent→`recenzent`, Dizajner→`dizajner`, Menadžer→`menadzer`, Debager→`debager`,
Pisac→`pisac`, Bezbednjak→`bezbednjak`, DevOps & Cloud Inženjer→`devops`,
Tester→`tester`, Data Engineer→`data-engineer`. Format svakog:

```markdown
---
id: <id>
type: persona
title: <Ime persone>
---
<telo: ceo tekst uloge iz Codium Persone.md za tu personu>
```

Deljeni katalog `_shared/commands/katalog.md`:

```markdown
---
id: codium-command-katalog
type: command
title: Katalog komandi
---
Daj `name` (ime repozitorijuma ili pipeline-a) za komande koje ga traže.

- list_repos — izlistaj repozitorijume. params: {}
- list_pipelines — izlistaj pipeline-e. params: {}
- repo_status — stanje repozitorijuma. params: {name}
- sync_repo — sync/pull repozitorijuma (traži potvrdu). params: {name}
- run_pipeline — pokreni pipeline (traži potvrdu). params: {name}
- open — otvori stranicu repozitorijuma. params: {name}
```

`_shared/tools/repo.md`:

```markdown
---
id: codium-tool-repo
type: tool
title: Repozitorijumi
---
Komande nad repozitorijumima: list_repos (sve), repo_status (po imenu),
sync_repo (pull, potvrda), open (otvori stranicu repo-a). `name` = ime repozitorijuma.
```

`_shared/tools/pipeline.md`:

```markdown
---
id: codium-tool-pipeline
type: tool
title: Pipeline-i
---
Komande nad pipeline-ima: list_pipelines (sve), run_pipeline (pokreni, potvrda).
`name` = ime pipeline-a.
```

- [ ] **Step 4: Pokreni — mora da prođe**

Run (CODIUM): `./.venv/Scripts/python.exe -m pytest tests/test_codium_curator_atoms.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .ai/atomi/personas tests/test_codium_curator_atoms.py
git commit -m "feat(kurator): seed atomi — 12 CODIUM persona + deljeni katalog/tools"
```

---

## Task 5: Runtime + codium_curator API — CODIUM

**Files:**
- Create: `apps/api/codium_curator_runtime.py`, `apps/api/routers/codium_curator.py`, `apps/api/schemas/codium_curator.py`
- Modify: `cell_app.py` (`API_ROUTERS`)
- Test: `tests/test_codium_curator_api.py`

**Interfaces:**
- Consumes: `CuratorAgent`, `AtomLoader` (kanon), `CodiumExecutors`/`CODIUM_INTENTS` (Task 3), `RepositoryService`/`PipelineService`, `AgentResult`.
- Produces: `get_agent(persona_id="opsti") -> CuratorAgent`; endpointi `/api/v1/codium/curator/{command,confirm,refute}`.

- [ ] **Step 1: Napiši failing test**

```python
# tests/test_codium_curator_api.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.routers import codium_curator
from core.cell.curator.agent import AgentResult


class _FakeAgent:
    def handle(self, message):
        return AgentResult(kind="answer", intent="list_repos", reply="Evo.", sources=["alfa"])

    def confirm(self, token):
        return {"synced": True}

    def refute(self, log_id=None):
        return True


def _client():
    app = FastAPI()
    app.include_router(codium_curator.router)
    app.dependency_overrides[codium_curator.get_agent_dep] = lambda: _FakeAgent()
    return TestClient(app)


def test_command():
    r = _client().post("/api/v1/codium/curator/command", json={"message": "listaj repoe"})
    assert r.status_code == 200
    assert r.json()["sources"] == ["alfa"]


def test_confirm():
    r = _client().post("/api/v1/codium/curator/confirm", json={"token": "t"})
    assert r.status_code == 200
    assert r.json()["synced"] is True


def test_refute():
    r = _client().post("/api/v1/codium/curator/refute", json={})
    assert r.status_code == 200
    assert r.json()["refuted"] is True
```

- [ ] **Step 2: Pokreni — mora da padne** (instaliraj httpx u CODIUM `.venv` ako fali: `./.venv/Scripts/python.exe -m pip install httpx`).

Run (CODIUM): `./.venv/Scripts/python.exe -m pytest tests/test_codium_curator_api.py -v` → FAIL.

- [ ] **Step 3: Implementacija**

`apps/api/schemas/codium_curator.py` — po uzoru na FILMIUM `filmium_curator` scheme
(`CuratorCommandRequest{message, persona_id?}`, `CuratorCommandResponse.from_domain`,
`CuratorConfirmRequest{token}`, `CuratorRefuteRequest{log_id?}`). Pogledaj kanon
`AgentResult` polja (kind,intent,params,reply,preview,confirm_token,sources,log_id).

`apps/api/codium_curator_runtime.py`:

```python
# ========== CODIUM KURATOR RUNTIME ==========
from __future__ import annotations

from pathlib import Path

from core.ai.ollama_client import OllamaClient
from core.cell.curator.agent import CuratorAgent
from core.cell.curator.atoms import AtomLoader
from core.cell.curator.confirm import ConfirmStore
from core.cell.curator.interaction_log import InteractionLog
from core.cell.manifest import load_cell_manifest
from core.domains.codium.curator.executors import CodiumExecutors
from core.domains.codium.curator.intents import CODIUM_INTENTS
from core.domains.codium.repositories.service import RepositoryService
from core.domains.codium.pipelines.service import PipelineService

_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST = load_cell_manifest(_ROOT)
_PERSONAS = _ROOT / ".ai" / "atomi" / "personas"
_SHARED = _PERSONAS / "_shared"

# Servisi (bez argumenata ako podrazumevani konstruktor postoji; inače proveri
# stvarne konstruktore u repositories/service.py i pipelines/service.py i uskladi).
_repositories = RepositoryService()
_pipelines = PipelineService()
_executors = CodiumExecutors(_repositories, _pipelines)

_ollama = OllamaClient(endpoint=_MANIFEST.ai_endpoint, timeout=60.0)


def _generate(model, prompt, *, system=None, fmt=None):
    return _ollama.generate(model, prompt, system=system, fmt=fmt)


def get_agent(persona_id: str = "opsti") -> CuratorAgent:
    pid = persona_id if (_PERSONAS / persona_id / "persona.md").is_file() else "opsti"
    atoms = AtomLoader(_PERSONAS / pid, shared_root=_SHARED)
    return CuratorAgent(
        intents=CODIUM_INTENTS, executors=_executors, resolver=None,
        atoms=atoms, confirm=ConfirmStore(),
        log=InteractionLog(_ROOT / ".ai" / "atomi" / "logs" / pid),
        generate=_generate, model=_MANIFEST.ai_curator_model or "qwen2.5",
    )
```

Napomena: proveri stvarne konstruktore `RepositoryService`/`PipelineService`
(mogu tražiti repozitorijum/DB putanju). Uskladi konstrukciju kao što to radi
postojeći `apps/api/routers/codium_repositories.py::get_service` /
`codium_pipelines` runtime — preuzmi isti obrazac sklapanja servisa.

`apps/api/routers/codium_curator.py`:

```python
# ========== ROUTER: CODIUM KURATOR ==========
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from apps.api import codium_curator_runtime
from apps.api.schemas.codium_curator import (
    CuratorCommandRequest, CuratorCommandResponse,
    CuratorConfirmRequest, CuratorRefuteRequest,
)
from core.cell.curator.agent import CuratorAgent
from core.cell.curator.protocols import CuratorActionError

router = APIRouter(prefix="/api/v1/codium/curator", tags=["CODIUM Kurator"])


def get_agent_dep(persona_id: str = "opsti") -> CuratorAgent:
    return codium_curator_runtime.get_agent(persona_id)


@router.post("/command", response_model=CuratorCommandResponse)
def command(payload: CuratorCommandRequest) -> CuratorCommandResponse:
    agent = get_agent_dep(payload.persona_id or "opsti")
    return CuratorCommandResponse.from_domain(agent.handle(payload.message))


@router.post("/confirm")
def confirm(payload: CuratorConfirmRequest) -> dict:
    agent = get_agent_dep()
    try:
        return agent.confirm(payload.token)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except CuratorActionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)) from e


@router.post("/refute")
def refute(payload: CuratorRefuteRequest) -> dict:
    return {"refuted": get_agent_dep().refute(payload.log_id)}
```

Napomena: test override-uje `codium_curator.get_agent_dep`. Pošto endpointi zovu
`get_agent_dep(...)` direktno (ne kroz `Depends`), test ga override-uje preko
`app.dependency_overrides` NE radi — zato u testu koristi `monkeypatch` ILI
prepravi endpointe da koriste `Depends(get_agent_dep)`. **Odluka:** prepravi da
`command`/`confirm`/`refute` uzimaju `agent: CuratorAgent = Depends(get_agent_dep)`
(za command je potreban persona_id — koristi `Depends` sa query/telo; jednostavnije:
u testu `monkeypatch.setattr(codium_curator_runtime, "get_agent", lambda pid="opsti": _FakeAgent())`).
Uskladi test i implementaciju da override radi (monkeypatch runtime.get_agent je najčistije).

Dopuni `cell_app.py`: dodaj `'apps.api.routers.codium_curator'` u `API_ROUTERS` tuple.

- [ ] **Step 4: Pokreni — mora da prođe**

Run (CODIUM): `./.venv/Scripts/python.exe -m pytest tests/test_codium_curator_api.py -v`
Expected: PASS (3 testa). Uskladi test/impl mehanizam override-a (monkeypatch runtime.get_agent).

- [ ] **Step 5: Commit**

```bash
git add apps/api/codium_curator_runtime.py apps/api/routers/codium_curator.py apps/api/schemas/codium_curator.py cell_app.py tests/test_codium_curator_api.py
git commit -m "feat(kurator): CODIUM runtime + codium_curator API (command/confirm/refute)"
```

---

## Task 6: GUI — Kurator chat (persona picker) + Settings paneli — CODIUM

**Files:**
- Modify: `gui/src/cell/cellApi.ts` (curator command/confirm/refute funkcije)
- Create: `gui/src/features/codium/CodiumKuratorChat.tsx`
- Modify: CODIUM Settings (ugradi `CuratorSettingsPanels`) — nađi CODIUM settings stranicu/rutu

**Interfaces:**
- Consumes: `/api/v1/codium/curator/*` (Task 5), `CuratorSettingsPanels` (Task 2).

- [ ] **Step 1: Dodaj curator klijent u cellApi**

U CODIUM `gui/src/cell/cellApi.ts` dodaj, po uzoru na FILMIUM
`F:\FILMIUM\gui\src\features\filmium\lib\curatorClient.ts`, funkcije koje gađaju
`/api/v1/codium/curator/command|confirm|refute` (`sendCommand(message, personaId)`,
`confirmAction(token)`, `refuteAction(logId?)`) + `CuratorResult` tip. `command`
telo nosi `{message, persona_id}`.

- [ ] **Step 2: Napravi Kurator chat sa persona pickerom**

Kreiraj `gui/src/features/codium/CodiumKuratorChat.tsx`: dropdown 12 persona
(id + prikazno ime), tekst-unos, dugme pošalji → `sendCommand(message, persona)`;
prikaz `answer` (reply+sources), `proposal` (preview + Potvrdi/Otkaži →
confirmAction/refuteAction), `navigate` (navlači `preview.route`). Sledi obrazac
FILMIUM `FilmiumKuratorChat.tsx` (koristi postojeći `CoreChat` ili prost custom UI
ako je jednostavnije). Persona lista (id→ime): opsti→Opšti, arhitekta→Arhitekta,
graditelj→Graditelj, recenzent→Recenzent, dizajner→Dizajner, menadzer→Menadžer,
debager→Debager, pisac→Pisac, bezbednjak→Bezbednjak, devops→DevOps, tester→Tester,
data-engineer→Data Engineer.

- [ ] **Step 3: Ugradi Settings panele**

Nađi CODIUM settings ekran (proveri `gui/src/features/settings/` i `gui/src/cell/`;
ako CODIUM nema `CellSettingsPage`, dodaj `ModelPanel`/`AtomiPanel` iz
`CuratorSettingsPanels` u postojeći settings ekran sa `brand="CODIUM"`). Ako nema
jasnog mesta, izloži rutu `/codium/kurator` koja montira `CodiumKuratorChat` i
zaseban settings tab — minimalno, bez restrukturiranja CODIUM UI-ja.

- [ ] **Step 4: Typecheck + build**

Run (iz CODIUM `gui`): `npx tsc -p tsconfig.app.json --noEmit` (0 novih grešaka),
pa `npx vite build` (exit 0). Ne commituj `dist`/lock.

- [ ] **Step 5: Commit**

```bash
git add gui/src/cell/cellApi.ts gui/src/features/codium/CodiumKuratorChat.tsx <settings fajl>
git commit -m "feat(kurator): CODIUM Kurator chat (persona picker) + Settings paneli"
```

---

## Napomene za izvršioce

- **Redosled:** Task 1 (CORE) PRVI — Task 2 kopira osnaženi kanon. Zatim 2→3→4→5→6 u CODIUM ćeliji.
- **Grane:** CORE `feat/codium-kurator` (Task 1); CODIUM ćelija `feat/kurator` (Task 2 pravi je). Ne diraj master.
- **Servisi u runtime-u (Task 5):** proveri STVARNE konstruktore `RepositoryService`/`PipelineService` (mogu tražiti DB/repozitorijume) — preuzmi obrazac iz `apps/api/routers/codium_repositories.py`/`codium_pipelines.py`. Ako je sklapanje netrivijalno, prijavi i uskladi.
- **httpx** je test-only; instaliraj u ciljni `.venv`, ne commituj.

## Self-Review (popunjeno)

- **Spec coverage:** §4 K amandman → Task 1; §5 domenski deo → Task 3 (intenti/izvršioci) + Task 4 (atomi); §6 multi-persona wiring → Task 1 (shared_root) + Task 5 (runtime po personi); §7 API → Task 5; §8 GUI → Task 6; kopija kanona → Task 2; §9 testovi → svaki task. FILMIUM netaknut.
- **Placeholder scan:** kopije (Task 2) referišu stvaran CORE kanon; 12 persona tekstova iz stvarnog Codium Persone.md; jedini otvoreni detalj — konstruktori CODIUM servisa (Task 5) i mesto Settings ekrana (Task 6) — eksplicitno označeni „proveri stvarno" jer variraju.
- **Type consistency:** `CuratorActionError` isti u Task 1 (kernel), Task 3 (executors dižu), Task 5 (API hvata). `CODIUM_INTENTS`/`CodiumExecutors` isti u Task 3/5. `AtomLoader(root, shared_root)` isti u Task 1/4/5. `AgentResult` polja iz kanona u Task 5 scheme.
