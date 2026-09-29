---
id: codium-671cf87a-2026-08-29-codium-e9-agenti-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: CODIUM E9 — agenti sa alatima
summary: '> **Za agentne izvođače:** OBAVEZNA POD-VEŠTINA: koristi'
keywords:
- codium
- agenti
- alatima
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-29-codium-e9-agenti.md
edges:
- type: references
  target: core-7687f8e1-2026-08-28-codium-odobrenja-i-agenti-design-md
  weight: 0.3
---

# CODIUM E9 — agenti sa alatima

> **Za agentne izvođače:** OBAVEZNA POD-VEŠTINA: koristi
> superpowers:subagent-driven-development (preporučeno) ili
> superpowers:executing-plans za izvođenje zadatak po zadatak. Koraci koriste
> `- [ ]` sintaksu za praćenje.

**Cilj:** Agent `ARCHITECT` dobija zadatak, radi u koracima kroz alate, svaki
potez mu proverava `ScopeGate`, svaki korak se zapisuje, a potez koji menja
stanje pauzira posao dok čovek ne odluči.

**Arhitektura:** Agent je red u bazi, ne klasa po agentu — dodavanje agenta je
unos, nov kod treba samo za nov **alat**. Alat je tanak omotač oko postojećeg
servisa, sa jednim registrom iz kojeg se izvodi i opis koji ide modelu i akcija
koja ide kapiji. Petlja je čista funkcija nad ubrizganim zavisnostima; oko nje
stoji daemon nit, a stanje živi u bazi, pa restart API-ja ne gubi posao i pauza
ne traži nit koja spava.

**Tehnologije:** Python 3.14, FastAPI, SQLite kroz `core.database`, pytest;
React + TypeScript + Vite, vitest, lucide-react.

**Spec:** [`docs/superpowers/specs/2026-08-28-codium-odobrenja-i-agenti-design.md`](../specs/2026-08-28-codium-odobrenja-i-agenti-design.md) (Deo 2)

## Opšta ograničenja

- Migracija je **`codium v8`** (v7 je zauzet odobrenjima). Aditivna — nijedna
  postojeća tabela se ne dira.
- Tri nove tabele idu u **`codium.db`**. Iako su koraci append-heavy, run i
  njegovi koraci su nedeljivi od definicije agenta i idu u bekap zajedno s njom;
  `codium_ops.db` ostaje za saobraćaj bez vlasnika (dnevnik, potrošnja).
- `core/security/scope_gate.py` se **ne menja**. Kapija vraća verdikt i ništa
  više; upis molbe radi pozivalac kroz `ApprovalRepository`.
- `ChatProvider` protokol se **ne menja**. Model traži alat JSON blokom u
  tekstu; nativni tool-calling je kasnija nadogradnja sloja ispod petlje.
- Nijedan alat ne piše sopstvenu proveru putanje. `CodiumExplorer._safe(rel)`
  već brani izlazak iz korena projekta.
- Nijedan test ne poziva pravi model. Lažni model vraća unapred određen niz
  poteza.
- Kod i identifikatori na engleskom, komentari i dokumentacija na srpskom, kao u
  postojećim fajlovima domena.
- Testovi: `./.venv/Scripts/python.exe -m pytest`. Trenutno stanje **1333**.
- GUI: `npx vitest run` (trenutno **701**) i `npx tsc -b tsconfig.app.json` u
  `apps/gui`. Dve greške postoje pre ovog rada i nisu tvoje:
  `CoreDockLayout.tsx(42,52)` i `CodiumWorkspace.tsx(14,3)`.
- Uvoz `MemoryRouter` ide iz `react-router`, ne `react-router-dom` — repo je na
  react-router v8 gde je paket jedan.
- Poruke commit-a kroz `git commit -F- <<'EOF'`, nikad `-m` sa navodnicima.

## Zatečeni interfejsi koje ovaj plan koristi

```python
# core/security/scope_gate.py
ALLOW = "allow"; DENY = "deny"; NEEDS_APPROVAL = "needs_approval"
@dataclass(frozen=True)
class Decision: verdict: str; rule_id: int | None; reason: str
class ScopeGate:
    def check(self, *, actor: str, action: str, target: str = "") -> Decision

# core/domains/codium/audit/ (paket izvozi sve navedeno)
@dataclass(frozen=True)
class Approval:
    actor: str; action: str; target: str = ""; payload: str = ""
    status: str = "pending"; note: str = ""; requested_at: str = ""
    decided_at: str | None = None; id: int | None = None
class ApprovalRepository:
    def request(self, approval: Approval) -> Approval
    def get(self, approval_id: int) -> Approval | None
@dataclass(frozen=True)
class AuditEntry:
    actor: str; action: str; verdict: str; target: str = ""
    outcome: str = "ok"; detail: str = ""; project_id: int | None = None
class AuditRepository:
    def record(self, entry: AuditEntry) -> None

# core/domains/codium/explorer.py
class CodiumExplorer:
    def __init__(self, root: Path, ignore: frozenset[str] = DEFAULT_IGNORE)
    def list_dir(self, rel: str = "") -> list[FileNode]      # .name .path .is_dir .size
    def read_file(self, rel: str) -> FileContent             # .path .content .truncated .binary
    def write_file(self, rel: str, content: str) -> FileNode

# core/domains/codium/service.py
class CodiumService:
    def create_task(self, task: TaskCreate) -> Task          # TaskCreate(title, project_id=None, ...)
    def create_note(self, note: NoteCreate,
                    active_project_id: int | None = None) -> Note   # NoteCreate(title, body="", project_id=None, ...)

# core/ai/model_router.py
@dataclass(frozen=True)
class ResolvedModel: provider_name: str; model: str; source: str
class ModelRouter:
    def resolve(self, *, project_id=None, persona="",
                override_provider=None, override_model=None) -> ResolvedModel
    def chat(self, messages: list[ChatMessage],
             resolved: ResolvedModel, **options) -> ChatResult   # .text .prompt_tokens .output_tokens .duration_ms

# core/ai/usage.py
class UsageRecorder:
    def record(self, *, provider, model, project_id, persona, prompt_tokens,
               output_tokens, duration_ms, ok, actor="human") -> None
```

## Struktura fajlova

| Fajl | Odgovornost |
|---|---|
| `core/domains/codium/migrations.py` | `CODIUM_MIGRATION_V8` — tri tabele + `ARCHITECT` |
| `core/domains/codium/agents/models.py` | **nov** — `Agent`, `AgentRun`, `AgentStep`, `ToolResult` |
| `core/domains/codium/agents/repository.py` | **nov** — `AgentRepository`, `RunRepository` |
| `core/domains/codium/agents/tools/registry.py` | **nov** — `ToolSpec`, `ToolRegistry` |
| `core/domains/codium/agents/tools/builtin.py` | **nov** — šest alata |
| `core/domains/codium/agents/protocol.py` | **nov** — čitanje poteza modela iz teksta |
| `core/domains/codium/agents/loop.py` | **nov** — `AgentLoop` |
| `core/domains/codium/agents/runner.py` | **nov** — daemon nit |
| `apps/api/codium_agents_runtime.py` | **nov** — primerci za `Depends` |
| `apps/api/schemas/codium_agents.py` | **nov** — šeme |
| `apps/api/routers/codium_agents.py` | **nov** — rute |
| `apps/api/main.py` | registruje router |
| `apps/gui/src/types/codium.ts` | tipovi agenata i run-ova |
| `apps/gui/src/services/codiumApi.ts` | pozivi |
| `apps/gui/src/features/codium/agentRun.ts` | **nov** — prikaz koraka |
| `apps/gui/src/pages/CodiumAgents.tsx` | **nov** — strana agenata |
| `apps/gui/src/pages/CodiumOverview.tsx` | AI Agents panel prestaje da bude mock |
| `apps/gui/src/styles/codium-agents.css` | **nov** |
| `apps/gui/src/App.tsx`, `components/layout/Sidebar.tsx` | ruta i stavka |

---

### Zadatak 1: Migracija v8 — agenti, run-ovi, koraci

**Fajlovi:**
- Menja: `core/domains/codium/migrations.py`
- Test: `tests/test_codium_agents_schema.py` (nov)

**Interfejsi:**
- Koristi: `DatabaseMigration`, `initialize_codium_database`
- Daje: tabele `codium_agents`, `codium_agent_runs`, `codium_agent_steps` i
  početni red `architect`

- [ ] **Korak 1: Napiši testove koji padaju**

Nov fajl `tests/test_codium_agents_schema.py`:

```python
# ========== TESTOVI: sema agenata ==========
from __future__ import annotations

import sqlite3

import pytest

from core.database import core_database_connection
from core.domains.codium.runtime import initialize_codium_database


def _columns(path, table: str) -> set[str]:
    with core_database_connection(path) as connection:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


@pytest.fixture
def baza(tmp_path):
    put = tmp_path / "codium.db"
    initialize_codium_database(put)
    return put


def test_agenti_imaju_svoje_kolone(baza):
    assert _columns(baza, "codium_agents") == {
        "id", "slug", "name", "description", "system_prompt", "model",
        "provider", "tools_json", "max_steps", "enabled", "created_at",
        "updated_at",
    }


def test_run_i_koraci_imaju_svoje_kolone(baza):
    assert _columns(baza, "codium_agent_runs") == {
        "id", "agent_id", "project_id", "task", "status", "result",
        "steps_used", "cost_usd", "pending_approval_id", "started_at",
        "finished_at",
    }
    assert _columns(baza, "codium_agent_steps") == {
        "id", "run_id", "idx", "kind", "tool", "payload", "at",
    }


def test_status_run_a_je_ogranicen(baza):
    # Nepoznat status bi tiho prosao, a GUI bi crtao stanje koje petlja
    # ne poznaje.
    with core_database_connection(baza) as connection:
        connection.execute(
            "INSERT INTO codium_agent_runs (agent_id, task, status) "
            "VALUES (1, 'proba', 'running')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO codium_agent_runs (agent_id, task, status) "
                "VALUES (1, 'proba', 'nesto')"
            )


def test_architect_je_upisan(baza):
    with core_database_connection(baza) as connection:
        row = connection.execute(
            "SELECT slug, max_steps, enabled FROM codium_agents"
        ).fetchall()
    assert [(r[0], r[1], r[2]) for r in row] == [("architect", 12, 1)]


def test_brisanje_run_a_brise_i_korake(baza):
    # ON DELETE CASCADE mora stvarno da radi, a ne samo da stoji u semi:
    # SQLite ga postuje tek uz ukljucene strane kljuceve.
    with core_database_connection(baza) as connection:
        connection.execute(
            "INSERT INTO codium_agent_runs (agent_id, task) VALUES (1, 'p')"
        )
        connection.execute(
            "INSERT INTO codium_agent_steps (run_id, idx, kind) "
            "VALUES (1, 0, 'answer')"
        )
        connection.execute("DELETE FROM codium_agent_runs WHERE id = 1")
        ostalo = connection.execute(
            "SELECT COUNT(*) FROM codium_agent_steps"
        ).fetchone()[0]
    assert ostalo == 0


def test_odobrenja_iz_v7_ostaju_netaknuta(baza):
    assert "payload" in _columns(baza, "codium_approvals")
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agents_schema.py -v`
Očekivano: `sqlite3.OperationalError: no such table: codium_agents`.

- [ ] **Korak 3: Dodaj migraciju**

U `core/domains/codium/migrations.py`, ispod `CODIUM_MIGRATION_V7`:

```python
# ---------- v8: agenti, njihovi poslovi i koraci ----------

CODIUM_MIGRATION_V8 = DatabaseMigration(
    scope="codium",
    version=8,
    name="create_agents",
    statements=(
        # Agent je red, ne klasa: dodavanje agenta je unos u tabelu, a nov kod
        # treba samo za nov alat.
        """
        CREATE TABLE codium_agents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            slug          TEXT NOT NULL UNIQUE,
            name          TEXT NOT NULL,
            description   TEXT NOT NULL DEFAULT '',
            system_prompt TEXT NOT NULL DEFAULT '',
            model         TEXT NOT NULL DEFAULT '',
            provider      TEXT NOT NULL DEFAULT '',
            tools_json    TEXT NOT NULL DEFAULT '[]',
            max_steps     INTEGER NOT NULL DEFAULT 12,
            enabled       INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Prazan `model` i `provider` znace „koristi ono sto bi chat koristio" —
        # nasledjivanje kroz ModelRouter, ne greska.
        """
        INSERT INTO codium_agents (slug, name, description, system_prompt)
        VALUES (
            'architect',
            'Architect',
            'Cita kod, analizira i predlaze plan izmene. Ne izvrsava.',
            'Ti si ARCHITECT, agent koji analizira postojeci kod i predlaze '
            || 'plan izmene. Citas fajlove, trazis obrasce i pises predlog. '
            || 'Ne menjas stanje bez potrebe; kad ti treba izmena, trazi je '
            || 'alatom i cekaj odluku coveka.'
        )
        """,
        """
        CREATE TABLE codium_agent_runs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id            INTEGER NOT NULL
                                REFERENCES codium_agents (id) ON DELETE CASCADE,
            project_id          INTEGER
                                REFERENCES codium_projects (id)
                                ON DELETE SET NULL,
            task                TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'running'
                                CHECK (status IN ('running','waiting_approval',
                                                  'done','failed','cancelled')),
            result              TEXT NOT NULL DEFAULT '',
            steps_used          INTEGER NOT NULL DEFAULT 0,
            cost_usd            REAL NOT NULL DEFAULT 0,
            pending_approval_id INTEGER,
            started_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at         TEXT
        )
        """,
        "CREATE INDEX idx_codium_agent_runs_agent "
        "ON codium_agent_runs (agent_id, id DESC)",
        # Korak se samo dopisuje. Petlja koja se ne moze procitati unazad je
        # petlja kojoj se ne moze verovati.
        """
        CREATE TABLE codium_agent_steps (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id  INTEGER NOT NULL
                    REFERENCES codium_agent_runs (id) ON DELETE CASCADE,
            idx     INTEGER NOT NULL,
            kind    TEXT NOT NULL,
            tool    TEXT,
            payload TEXT NOT NULL DEFAULT '',
            at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX idx_codium_agent_steps_run "
        "ON codium_agent_steps (run_id, idx)",
    ),
)
```

Dopiši `CODIUM_MIGRATION_V8` u `CODIUM_MIGRATIONS`.

- [ ] **Korak 4: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agents_schema.py -v`

Ako `test_brisanje_run_a_brise_i_korake` padne, `PRAGMA foreign_keys` nije
uključen u `core_database_connection`. Ne menjaj `core/database.py` zbog toga —
prijavi to kao nalaz i preformuliši test tako da tvrdi ono što veza stvarno
garantuje u ovom okruženju.

- [ ] **Korak 5: Commit**

```bash
git add core/domains/codium/migrations.py tests/test_codium_agents_schema.py
git commit -F- <<'EOF'
feat(codium): codium v8 agenti, njihovi poslovi i koraci

Agent je red u tabeli, ne klasa: dodavanje agenta je unos, a nov kod
treba samo za nov alat. ARCHITECT ulazi kao pocetni red iste migracije.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 2: Modeli i repozitorijumi

**Fajlovi:**
- Pravi: `core/domains/codium/agents/__init__.py`
- Pravi: `core/domains/codium/agents/models.py`
- Pravi: `core/domains/codium/agents/repository.py`
- Test: `tests/test_codium_agent_repository.py` (nov)

**Interfejsi:**
- Koristi: `core_database_connection`, `codium_database_path`; obrazac iz
  `core/domains/codium/audit/approvals.py`
- Daje:
  ```python
  @dataclass(frozen=True)
  class Agent:
      slug: str; name: str; description: str = ""; system_prompt: str = ""
      model: str = ""; provider: str = ""; tools: tuple[str, ...] = ()
      max_steps: int = 12; enabled: bool = True; id: int | None = None

  @dataclass(frozen=True)
  class AgentRun:
      agent_id: int; task: str; project_id: int | None = None
      status: str = "running"; result: str = ""; steps_used: int = 0
      cost_usd: float = 0.0; pending_approval_id: int | None = None
      started_at: str = ""; finished_at: str | None = None; id: int | None = None

  @dataclass(frozen=True)
  class AgentStep:
      run_id: int; idx: int; kind: str; tool: str = ""; payload: str = ""
      at: str = ""; id: int | None = None

  @dataclass(frozen=True)
  class ToolResult:
      ok: bool; output: str; verdict: str = "allow"; approval_id: int | None = None

  class AgentRepository:
      def __init__(self, database_path: Path | None = None) -> None
      def list(self) -> list[Agent]
      def get(self, agent_id: int) -> Agent | None
      def by_slug(self, slug: str) -> Agent | None
      def add(self, agent: Agent) -> Agent
      def update(self, agent_id: int, change: dict[str, object]) -> Agent | None
      def delete(self, agent_id: int) -> None

  class RunRepository:
      def __init__(self, database_path: Path | None = None) -> None
      def start(self, run: AgentRun) -> AgentRun
      def get(self, run_id: int) -> AgentRun | None
      def recent(self, *, limit: int = 20) -> list[AgentRun]
      def append_step(self, step: AgentStep) -> AgentStep
      def steps(self, run_id: int, *, since_idx: int = -1) -> list[AgentStep]
      def finish(self, run_id: int, *, status: str, result: str = "",
                 steps_used: int = 0, cost_usd: float = 0.0) -> AgentRun | None
      def wait_for_approval(self, run_id: int, approval_id: int) -> AgentRun | None
      def resume(self, run_id: int) -> AgentRun | None
  ```
  `tools` je torka u modelu, a `tools_json` JSON lista u bazi — prevod radi
  repozitorijum i niko drugi.

- [ ] **Korak 1: Napiši testove koji padaju**

Nov fajl `tests/test_codium_agent_repository.py`:

```python
# ========== TESTOVI: repozitorijumi agenata i poslova ==========
from __future__ import annotations

import pytest

from core.domains.codium.agents import (
    Agent,
    AgentRepository,
    AgentRun,
    AgentStep,
    RunRepository,
)
from core.domains.codium.runtime import initialize_codium_database


@pytest.fixture
def baza(tmp_path):
    put = tmp_path / "codium.db"
    initialize_codium_database(put)
    return put


@pytest.fixture
def agenti(baza) -> AgentRepository:
    return AgentRepository(baza)


@pytest.fixture
def poslovi(baza) -> RunRepository:
    return RunRepository(baza)


# ---------- agenti ----------
def test_architect_stize_iz_migracije(agenti):
    svi = agenti.list()
    assert [a.slug for a in svi] == ["architect"]
    assert svi[0].max_steps == 12
    assert svi[0].enabled is True


def test_spisak_alata_ide_kroz_json(agenti):
    upisan = agenti.add(Agent(slug="reviewer", name="Reviewer",
                              tools=("read_file", "search_code")))
    assert agenti.get(upisan.id).tools == ("read_file", "search_code")


def test_prazan_spisak_alata_je_prazna_torka(agenti):
    # Kolona ima default '[]'; model ne sme da ga vrati kao [''] ni kao None.
    assert agenti.by_slug("architect").tools == ()


def test_izmena_menja_samo_zadata_polja(agenti):
    agenti.update(1, {"max_steps": 4, "tools": ("read_file",)})
    posle = agenti.get(1)
    assert posle.max_steps == 4
    assert posle.tools == ("read_file",)
    assert posle.slug == "architect"


def test_brisanje_agenta(agenti):
    agenti.delete(1)
    assert agenti.list() == []


# ---------- poslovi ----------
def test_novi_posao_pocinje_kao_running(poslovi):
    run = poslovi.start(AgentRun(agent_id=1, task="analiziraj"))
    assert run.id is not None
    assert run.status == "running"
    assert run.finished_at is None


def test_koraci_se_citaju_inkrementalno(poslovi):
    run = poslovi.start(AgentRun(agent_id=1, task="t"))
    for i in range(3):
        poslovi.append_step(AgentStep(run_id=run.id, idx=i, kind="thought",
                                      payload=f"korak {i}"))
    assert [s.idx for s in poslovi.steps(run.id)] == [0, 1, 2]
    assert [s.idx for s in poslovi.steps(run.id, since_idx=0)] == [1, 2]


def test_zavrsen_posao_nosi_ishod_i_vreme(poslovi):
    run = poslovi.start(AgentRun(agent_id=1, task="t"))
    gotov = poslovi.finish(run.id, status="done", result="plan", steps_used=3,
                           cost_usd=0.0012)
    assert gotov.status == "done"
    assert gotov.result == "plan"
    assert gotov.steps_used == 3
    assert gotov.cost_usd == pytest.approx(0.0012)
    assert gotov.finished_at


def test_pauza_pamti_molbu_a_nastavak_je_brise(poslovi):
    run = poslovi.start(AgentRun(agent_id=1, task="t"))
    pauziran = poslovi.wait_for_approval(run.id, 77)
    assert pauziran.status == "waiting_approval"
    assert pauziran.pending_approval_id == 77

    nastavljen = poslovi.resume(run.id)
    assert nastavljen.status == "running"
    assert nastavljen.pending_approval_id is None


def test_nastavak_posla_koji_ne_ceka_ne_radi_nista(poslovi):
    # Inace bi zavrsen posao mogao da se „ozivi" i nastavi da trosi.
    run = poslovi.start(AgentRun(agent_id=1, task="t"))
    poslovi.finish(run.id, status="done")
    assert poslovi.resume(run.id) is None


def test_poslednji_poslovi_su_najnoviji_prvi(poslovi):
    prvi = poslovi.start(AgentRun(agent_id=1, task="a"))
    drugi = poslovi.start(AgentRun(agent_id=1, task="b"))
    assert [r.id for r in poslovi.recent(limit=5)] == [drugi.id, prvi.id]
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_repository.py -v`
Očekivano: `ModuleNotFoundError: No module named 'core.domains.codium.agents'`.

- [ ] **Korak 3: Napiši modele**

Nov fajl `core/domains/codium/agents/models.py`:

```python
# ========== MODELI AGENATA ==========
# Agent je zapis, ne klasa po agentu: dodavanje agenta je unos u tabelu, a nov
# kod treba samo za nov alat.
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    """Jedan agent: uloga, model i spisak alata koje sme."""

    slug: str
    name: str
    description: str = ""
    system_prompt: str = ""
    # Prazan model i provajder znace „koristi ono sto bi chat koristio" —
    # nasledjivanje kroz ModelRouter, a ne greska.
    model: str = ""
    provider: str = ""
    tools: tuple[str, ...] = ()
    max_steps: int = 12
    enabled: bool = True
    id: int | None = None


@dataclass(frozen=True)
class AgentRun:
    """Jedan posao agenta, od zadatka do ishoda."""

    agent_id: int
    task: str
    project_id: int | None = None
    status: str = "running"
    result: str = ""
    steps_used: int = 0
    cost_usd: float = 0.0
    # Popunjeno samo dok posao stoji u `waiting_approval`.
    pending_approval_id: int | None = None
    started_at: str = ""
    finished_at: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class AgentStep:
    """Jedan korak posla. `kind`: thought | tool_call | tool_result | answer."""

    run_id: int
    idx: int
    kind: str
    tool: str = ""
    payload: str = ""
    at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class ToolResult:
    """Ishod jednog poteza: sta je alat vratio i sta je kapija rekla.

    `approval_id` je popunjen samo kad je verdikt `needs_approval` — tada alat
    nije ni pokrenut, nego ceka odluku coveka.
    """

    ok: bool
    output: str
    verdict: str = "allow"
    approval_id: int | None = None
```

- [ ] **Korak 4: Napiši repozitorijume**

Nov fajl `core/domains/codium/agents/repository.py`:

```python
# ========== REPOZITORIJUMI AGENATA I POSLOVA ==========
# Prevod `tools` <-> `tools_json` radi ovaj sloj i niko drugi: ostatak koda
# vidi torku imena, baza vidi JSON.
from __future__ import annotations

import json
from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.agents.models import Agent, AgentRun, AgentStep
from core.domains.codium.runtime import codium_database_path

_AGENT_KOLONE = ("id, slug, name, description, system_prompt, model, "
                 "provider, tools_json, max_steps, enabled")
_RUN_KOLONE = ("id, agent_id, project_id, task, status, result, steps_used, "
               "cost_usd, pending_approval_id, started_at, finished_at")
_STEP_KOLONE = "id, run_id, idx, kind, tool, payload, at"

# Sta `update` sme da menja. Spisak stoji u kodu, jer bi inace naziv kolone
# stizao spolja pravo u SQL.
_IZMENJIVO = frozenset({
    "name", "description", "system_prompt", "model", "provider", "tools",
    "max_steps", "enabled",
})


def _to_agent(row) -> Agent:
    return Agent(
        id=row[0], slug=row[1], name=row[2], description=row[3],
        system_prompt=row[4], model=row[5], provider=row[6],
        tools=tuple(json.loads(row[7] or "[]")),
        max_steps=row[8], enabled=bool(row[9]),
    )


def _to_run(row) -> AgentRun:
    return AgentRun(
        id=row[0], agent_id=row[1], project_id=row[2], task=row[3],
        status=row[4], result=row[5], steps_used=row[6], cost_usd=row[7],
        pending_approval_id=row[8], started_at=row[9], finished_at=row[10],
    )


def _to_step(row) -> AgentStep:
    return AgentStep(id=row[0], run_id=row[1], idx=row[2], kind=row[3],
                     tool=row[4] or "", payload=row[5], at=row[6])


class AgentRepository:
    """Citanje i izmena definicija agenata."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def list(self) -> list[Agent]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                f"SELECT {_AGENT_KOLONE} FROM codium_agents ORDER BY id"
            ).fetchall()
        return [_to_agent(row) for row in rows]

    def get(self, agent_id: int) -> Agent | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_AGENT_KOLONE} FROM codium_agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
        return _to_agent(row) if row else None

    def by_slug(self, slug: str) -> Agent | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_AGENT_KOLONE} FROM codium_agents WHERE slug = ?",
                (slug,),
            ).fetchone()
        return _to_agent(row) if row else None

    def add(self, agent: Agent) -> Agent:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO codium_agents (
                    slug, name, description, system_prompt, model, provider,
                    tools_json, max_steps, enabled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (agent.slug, agent.name, agent.description,
                 agent.system_prompt, agent.model, agent.provider,
                 json.dumps(list(agent.tools)), agent.max_steps,
                 1 if agent.enabled else 0),
            )
            novi_id = cursor.lastrowid
        return self.get(novi_id)

    def update(self, agent_id: int,
               change: dict[str, object]) -> Agent | None:
        """Menja samo prosledjena polja; nepoznat kljuc se ignorise."""

        postavke: list[str] = []
        vrednosti: list[object] = []
        for kljuc, vrednost in change.items():
            if kljuc not in _IZMENJIVO:
                continue
            if kljuc == "tools":
                postavke.append("tools_json = ?")
                vrednosti.append(json.dumps(list(vrednost)))
            elif kljuc == "enabled":
                postavke.append("enabled = ?")
                vrednosti.append(1 if vrednost else 0)
            else:
                postavke.append(f"{kljuc} = ?")
                vrednosti.append(vrednost)

        if not postavke:
            return self.get(agent_id)

        postavke.append("updated_at = CURRENT_TIMESTAMP")
        vrednosti.append(agent_id)
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                f"UPDATE codium_agents SET {', '.join(postavke)} WHERE id = ?",
                tuple(vrednosti),
            )
        return self.get(agent_id)

    def delete(self, agent_id: int) -> None:
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                "DELETE FROM codium_agents WHERE id = ?", (agent_id,)
            )


class RunRepository:
    """Poslovi agenata i njihovi koraci."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def start(self, run: AgentRun) -> AgentRun:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO codium_agent_runs (agent_id, project_id, task) "
                "VALUES (?, ?, ?)",
                (run.agent_id, run.project_id, run.task),
            )
            novi_id = cursor.lastrowid
        return self.get(novi_id)

    def get(self, run_id: int) -> AgentRun | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_agent_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return _to_run(row) if row else None

    def recent(self, *, limit: int = 20) -> list[AgentRun]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_agent_runs "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_to_run(row) for row in rows]

    def append_step(self, step: AgentStep) -> AgentStep:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO codium_agent_steps (run_id, idx, kind, tool, "
                "payload) VALUES (?, ?, ?, ?, ?)",
                (step.run_id, step.idx, step.kind, step.tool or None,
                 step.payload),
            )
            novi_id = cursor.lastrowid
            row = connection.execute(
                f"SELECT {_STEP_KOLONE} FROM codium_agent_steps WHERE id = ?",
                (novi_id,),
            ).fetchone()
        return _to_step(row)

    def steps(self, run_id: int, *, since_idx: int = -1) -> list[AgentStep]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                f"SELECT {_STEP_KOLONE} FROM codium_agent_steps "
                "WHERE run_id = ? AND idx > ? ORDER BY idx",
                (run_id, since_idx),
            ).fetchall()
        return [_to_step(row) for row in rows]

    def finish(self, run_id: int, *, status: str, result: str = "",
               steps_used: int = 0, cost_usd: float = 0.0) -> AgentRun | None:
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                """
                UPDATE codium_agent_runs
                SET status = ?, result = ?, steps_used = ?, cost_usd = ?,
                    pending_approval_id = NULL,
                    finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, result, steps_used, cost_usd, run_id),
            )
        return self.get(run_id)

    def wait_for_approval(self, run_id: int,
                          approval_id: int) -> AgentRun | None:
        """Pauzira posao koji trazi odobrenje.

        Uslov stanja stoji u samom upitu, isto kao kod odobrenja: zavrsen
        posao ne sme da se vrati u cekanje.
        """

        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "UPDATE codium_agent_runs "
                "SET status = 'waiting_approval', pending_approval_id = ? "
                "WHERE id = ? AND status = 'running'",
                (approval_id, run_id),
            )
            promenjeno = cursor.rowcount
        return self.get(run_id) if promenjeno else None

    def resume(self, run_id: int) -> AgentRun | None:
        """Vraca posao u rad posle odluke; `None` ako nije cekao."""

        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "UPDATE codium_agent_runs "
                "SET status = 'running', pending_approval_id = NULL "
                "WHERE id = ? AND status = 'waiting_approval'",
                (run_id,),
            )
            promenjeno = cursor.rowcount
        return self.get(run_id) if promenjeno else None
```

- [ ] **Korak 5: Izvezi iz paketa**

Nov fajl `core/domains/codium/agents/__init__.py`:

```python
# ========== CODIUM AGENTI ==========
# Agent sa alatima, za razliku od persone iz F9 koja je samo drugi sistemski
# prompt nad istom petljom pitanje-odgovor.
from core.domains.codium.agents.models import (
    Agent,
    AgentRun,
    AgentStep,
    ToolResult,
)
from core.domains.codium.agents.repository import (
    AgentRepository,
    RunRepository,
)

__all__ = [
    "Agent",
    "AgentRepository",
    "AgentRun",
    "AgentStep",
    "RunRepository",
    "ToolResult",
]
```

- [ ] **Korak 6: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_repository.py -v`

- [ ] **Korak 7: Commit**

```bash
git add core/domains/codium/agents tests/test_codium_agent_repository.py
git commit -F- <<'EOF'
feat(codium): modeli i repozitorijumi agenata

Uslov stanja stoji u samom UPDATE upitu i za pauzu i za nastavak, isto
kao kod odobrenja: zavrsen posao ne sme da se ozivi i nastavi da trosi.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 3: Registar alata i šest alata

**Fajlovi:**
- Pravi: `core/domains/codium/agents/tools/__init__.py`
- Pravi: `core/domains/codium/agents/tools/registry.py`
- Pravi: `core/domains/codium/agents/tools/builtin.py`
- Test: `tests/test_codium_agent_tools.py` (nov)

**Interfejsi:**
- Koristi: `CodiumExplorer`, `CodiumService`, `TaskCreate`, `NoteCreate`,
  `ScopeGate`, `ApprovalRepository`, `Approval`, `ToolResult`
- Daje:
  ```python
  @dataclass(frozen=True)
  class ToolSpec:
      name: str
      description: str
      args: dict[str, str]          # ime -> opis, ide modelu
      action: str                   # ide kapiji, npr. "file.write"
      run: Callable[..., str]       # sirov posao; kapija je iznad njega
      writes_content: bool = False  # payload molbe nosi otisak sadrzaja

  class ToolRegistry:
      def __init__(self, specs: list[ToolSpec]) -> None
      def names(self) -> list[str]
      def get(self, name: str) -> ToolSpec | None
      def describe(self, allowed: Sequence[str]) -> str

  def build_tools(explorer: CodiumExplorer,
                  service: CodiumService,
                  project_id: int | None) -> ToolRegistry

  def search_code(explorer: CodiumExplorer, query: str,
                  *, limit: int = 40) -> str
  ```

- [ ] **Korak 1: Napiši testove koji padaju**

Nov fajl `tests/test_codium_agent_tools.py`:

```python
# ========== TESTOVI: registar i alati agenta ==========
from __future__ import annotations

import pytest

from core.domains.codium.agents.tools import build_tools, search_code
from core.domains.codium.explorer import CodiumExplorer


@pytest.fixture
def projekat(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "api.py").write_text(
        "def handler():\n    return 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("naslov\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def registar(projekat):
    # Servis nije potreban za alate nad fajlovima; `None` bi pao samo ako
    # test pozove `write_note` ili `create_task`, sto ovde ne radimo.
    return build_tools(CodiumExplorer(projekat), None, project_id=None)


def test_svaki_alat_prijavljuje_svoju_akciju(registar):
    ocekivano = {
        "read_file": "file.read",
        "list_dir": "file.read",
        "search_code": "file.read",
        "write_note": "note.write",
        "create_task": "task.write",
        "write_file": "file.write",
    }
    assert {ime: registar.get(ime).action for ime in ocekivano} == ocekivano


def test_registar_nema_alat_koji_brise(registar):
    # Prvi rez nema brisanje. Alat koji brise ulazi tek uz svesnu odluku.
    assert not [ime for ime in registar.names() if "delete" in ime]


def test_opis_pokriva_samo_dozvoljene_alate(registar):
    opis = registar.describe(["read_file", "list_dir"])
    assert "read_file" in opis
    assert "write_file" not in opis


def test_opis_nosi_imena_argumenata(registar):
    # Model ne moze da pozove alat cije argumente ne zna.
    assert "rel" in registar.describe(["read_file"])


def test_alat_koji_pise_sadrzaj_je_oznacen(registar):
    assert registar.get("write_file").writes_content is True
    assert registar.get("read_file").writes_content is False


def test_read_file_vraca_sadrzaj(registar, projekat):
    assert "handler" in registar.get("read_file").run(rel="src/api.py")


def test_alat_ne_izlazi_iz_korena(registar):
    # Zastita je u exploreru; alat je ne pise ponovo, ali mora da je propusti.
    from core.domains.codium.explorer import ExplorerError

    with pytest.raises(ExplorerError):
        registar.get("read_file").run(rel="../tajna.txt")


def test_search_code_nalazi_pogodak_sa_putanjom_i_linijom(projekat):
    izlaz = search_code(CodiumExplorer(projekat), "handler")
    assert "src/api.py" in izlaz
    assert "1" in izlaz


def test_search_code_bez_pogotka_to_i_kaze(projekat):
    assert "nema" in search_code(
        CodiumExplorer(projekat), "nepostojeci_niz").lower()


def test_search_code_preskace_binarne_fajlove(projekat):
    (projekat / "slika.bin").write_bytes(b"\x00\x01handler\x00")
    izlaz = search_code(CodiumExplorer(projekat), "handler")
    assert "slika.bin" not in izlaz
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_tools.py -v`
Očekivano: `ModuleNotFoundError` za `...agents.tools`.

- [ ] **Korak 3: Napiši registar**

`core/domains/codium/agents/tools/registry.py`:

```python
# ==========          REGISTAR ALATA          ==========
# Jedan zapis po alatu iz kojeg se izvodi i opis koji cita model i akcija koju
# proverava kapija. Dva mesta bi znacila alat koji modelu kaze jedno a kapiji
# prijavi drugo.
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolSpec:
    """Opis jednog alata: sta radi, sta trazi i sta pokrece."""

    name: str
    description: str
    args: dict[str, str]
    action: str
    run: Callable[..., str]
    # Kad alat pise sadrzaj, molba za odobrenje nosi otisak tog sadrzaja, pa
    # covek odobrava tekst koji je stvarno video.
    writes_content: bool = False


class ToolRegistry:
    """Alati dostupni petlji, po imenu."""

    def __init__(self, specs: list[ToolSpec]) -> None:
        self._specs = {spec.name: spec for spec in specs}

    def names(self) -> list[str]:
        return list(self._specs)

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def describe(self, allowed: Sequence[str]) -> str:
        """Opis alata za sistemski prompt — samo oni koje agent sme."""

        redovi: list[str] = []
        for ime in allowed:
            spec = self._specs.get(ime)
            if spec is None:
                continue
            argumenti = ", ".join(
                f"{kljuc} ({opis})" for kljuc, opis in spec.args.items()
            ) or "bez argumenata"
            redovi.append(f"- {spec.name}: {spec.description} | argumenti: {argumenti}")
        return "\n".join(redovi)
```

- [ ] **Korak 4: Napiši alate**

Nov fajl `core/domains/codium/agents/tools/builtin.py`:

```python
# ==========          ALATI PRVOG REZA          ==========
# Svaki alat je tanak omotac oko servisa koji vec postoji. Zastitu putanje ne
# pise nijedan od njih: `CodiumExplorer._safe` je vec brani, a dve provere
# znace dva mesta na kojima se gresi.
from __future__ import annotations

from core.domains.codium.agents.tools.registry import ToolRegistry, ToolSpec
from core.domains.codium.explorer import CodiumExplorer
from core.domains.codium.models import NoteCreate, TaskCreate
from core.domains.codium.service import CodiumService

# Koliko pogodaka pretrage se vraca modelu. Vise od ovoga je zid teksta u
# kojem se ni covek ni model ne snalaze.
MAX_POGODAKA = 40


def search_code(explorer: CodiumExplorer, query: str,
                *, limit: int = MAX_POGODAKA) -> str:
    """Trazi niz po linijama celog stabla projekta.

    Jedini alat sa nesto novog koda: obilazak ide kroz explorer, pa i ovde
    vazi njegova ignore lista i njegova zabrana izlaska iz korena.
    """

    trazeno = (query or "").strip()
    if not trazeno:
        return "Prazan upit."

    pogoci: list[str] = []

    def obidji(rel: str) -> None:
        if len(pogoci) >= limit:
            return
        for node in explorer.list_dir(rel):
            if len(pogoci) >= limit:
                return
            if node.is_dir:
                obidji(node.path)
                continue
            sadrzaj = explorer.read_file(node.path)
            # Binarno i preveliko explorer ne ucitava; nema sta da se trazi.
            if sadrzaj.binary or sadrzaj.truncated:
                continue
            for broj, linija in enumerate(sadrzaj.content.splitlines(), start=1):
                if trazeno in linija:
                    pogoci.append(f"{node.path}:{broj}: {linija.strip()}")
                    if len(pogoci) >= limit:
                        return

    obidji("")
    if not pogoci:
        # Prazan string bi model procitao kao gresku alata.
        return f"Nema pogotka za `{trazeno}`."
    return "\n".join(pogoci)


def build_tools(explorer: CodiumExplorer, service: CodiumService | None,
                project_id: int | None) -> ToolRegistry:
    """Sklapa alate vezane za jedan projekat."""

    def alat_read_file(rel: str = "") -> str:
        sadrzaj = explorer.read_file(rel)
        if sadrzaj.binary:
            return f"Fajl `{rel}` je binaran i ne cita se."
        if sadrzaj.truncated:
            return f"Fajl `{rel}` je prevelik za citanje."
        return sadrzaj.content

    def alat_list_dir(rel: str = "") -> str:
        stavke = explorer.list_dir(rel)
        if not stavke:
            return f"Folder `{rel or '.'}` je prazan."
        return "\n".join(
            f"{node.path}/" if node.is_dir else f"{node.path} ({node.size} B)"
            for node in stavke
        )

    def alat_search_code(query: str = "", limit: int = MAX_POGODAKA) -> str:
        return search_code(explorer, query, limit=int(limit))

    def alat_write_note(title: str = "", body: str = "") -> str:
        beleska = service.create_note(
            NoteCreate(title=title, body=body, project_id=project_id),
            active_project_id=project_id,
        )
        return f"Beleska upisana (id {beleska.id})."

    def alat_create_task(title: str = "", description: str = "") -> str:
        task = service.create_task(
            TaskCreate(title=title, description=description,
                       project_id=project_id),
        )
        return f"Zadatak napravljen (id {task.id})."

    def alat_write_file(rel: str = "", content: str = "") -> str:
        node = explorer.write_file(rel, content)
        return f"Upisano u `{node.path}` ({node.size} B)."

    return ToolRegistry([
        ToolSpec(
            name="read_file",
            description="Cita sadrzaj tekstualnog fajla projekta.",
            args={"rel": "relativna putanja fajla"},
            action="file.read",
            run=alat_read_file,
        ),
        ToolSpec(
            name="list_dir",
            description="Izlistava jedan nivo foldera projekta.",
            args={"rel": "relativna putanja foldera, prazno za koren"},
            action="file.read",
            run=alat_list_dir,
        ),
        ToolSpec(
            name="search_code",
            description="Trazi niz po linijama celog projekta.",
            args={"query": "niz koji se trazi",
                  "limit": "najvise pogodaka (podrazumevano 40)"},
            action="file.read",
            run=alat_search_code,
        ),
        ToolSpec(
            name="write_note",
            description="Upisuje belesku uz projekat.",
            args={"title": "naslov beleske", "body": "tekst beleske"},
            action="note.write",
            run=alat_write_note,
        ),
        ToolSpec(
            name="create_task",
            description="Pravi zadatak u agendi projekta.",
            args={"title": "naslov zadatka", "description": "opis"},
            action="task.write",
            run=alat_create_task,
        ),
        ToolSpec(
            name="write_file",
            description="Upisuje sadrzaj u postojeci fajl projekta.",
            args={"rel": "relativna putanja fajla", "content": "nov sadrzaj"},
            action="file.write",
            run=alat_write_file,
            # Molba za odobrenje nosi otisak ovog sadrzaja.
            writes_content=True,
        ),
    ])
```

Nov fajl `core/domains/codium/agents/tools/__init__.py`:

```python
# ========== ALATI AGENATA ==========
from core.domains.codium.agents.tools.builtin import build_tools, search_code
from core.domains.codium.agents.tools.registry import ToolRegistry, ToolSpec

__all__ = ["ToolRegistry", "ToolSpec", "build_tools", "search_code"]
```

- [ ] **Korak 5: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_tools.py -v`

- [ ] **Korak 6: Commit**

```bash
git add core/domains/codium/agents/tools tests/test_codium_agent_tools.py
git commit -F- <<'EOF'
feat(codium): registar alata i sest alata prvog reza

Iz jednog zapisa se izvodi i opis koji cita model i akcija koju proverava
kapija — dva mesta bi znacila alat koji modelu kaze jedno a kapiji drugo.
Zastitu putanje ne pise nijedan alat: explorer je vec ima.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 4: Čitanje poteza modela

**Fajlovi:**
- Pravi: `core/domains/codium/agents/protocol.py`
- Test: `tests/test_codium_agent_protocol.py` (nov)

**Interfejsi:**
- Daje:
  ```python
  @dataclass(frozen=True)
  class ToolCall:
      tool: str
      args: dict[str, object]

  @dataclass(frozen=True)
  class Move:
      call: ToolCall | None
      answer: str
      error: str = ""      # nije prazan kad model nije dao citljiv potez

  def parse_move(text: str) -> Move
  def system_prompt(agent_prompt: str, tools_description: str) -> str
  ```

- [ ] **Korak 1: Napiši testove koji padaju**

Nov fajl `tests/test_codium_agent_protocol.py`:

```python
# ========== TESTOVI: citanje poteza modela ==========
from __future__ import annotations

from core.domains.codium.agents.protocol import parse_move, system_prompt


def test_ciste_json_naredbe():
    potez = parse_move('{"tool": "read_file", "args": {"rel": "a.py"}}')
    assert potez.call.tool == "read_file"
    assert potez.call.args == {"rel": "a.py"}
    assert potez.error == ""


def test_json_u_ogradi_koda():
    # Modeli redovno umotavaju JSON u ```json ogradu.
    tekst = 'Evo poziva:\n```json\n{"tool": "list_dir", "args": {}}\n```'
    assert parse_move(tekst).call.tool == "list_dir"


def test_obican_tekst_je_konacan_odgovor():
    potez = parse_move("Plan je da se izdvoji servis.")
    assert potez.call is None
    assert potez.answer == "Plan je da se izdvoji servis."
    assert potez.error == ""


def test_neispravan_json_daje_gresku_a_ne_pad():
    # Greska se vraca modelu kao rezultat koraka; on dobija priliku da se
    # popravi, a pravilo o dve iste greske hvata onog ko ne ume.
    potez = parse_move('{"tool": "read_file", "args": {rel}}')
    assert potez.call is None
    assert potez.error


def test_poziv_bez_imena_alata_je_greska():
    potez = parse_move('{"args": {"rel": "a.py"}}')
    assert potez.call is None
    assert potez.error


def test_argumenti_koji_nisu_recnik_su_greska():
    potez = parse_move('{"tool": "read_file", "args": ["a.py"]}')
    assert potez.call is None
    assert potez.error


def test_poziv_bez_argumenata_je_dozvoljen():
    assert parse_move('{"tool": "list_dir"}').call.args == {}


def test_sistemski_prompt_nosi_ulogu_i_alate():
    tekst = system_prompt("Ti si ARCHITECT.", "- read_file: cita fajl")
    assert "ARCHITECT" in tekst
    assert "read_file" in tekst
    # Model mora da zna oba izlaza: poziv alata ili konacan odgovor.
    assert "tool" in tekst
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_protocol.py -v`

- [ ] **Korak 3: Napiši modul**

Nov fajl `core/domains/codium/agents/protocol.py`:

```python
# ==========          POTEZ MODELA          ==========
# Protokol provajdera se ne dira. Model odgovara ili JSON blokom (poziv alata)
# ili prozom (konacan odgovor); ovaj modul razlikuje to dvoje.
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# Ograda koda oko JSON-a je toliko cesta kod modela da se ne isplati boriti
# protiv nje — jednostavnije je procitati je.
_OGRADA = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


@dataclass(frozen=True)
class ToolCall:
    """Poziv jednog alata."""

    tool: str
    args: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Move:
    """Potez modela: poziv alata, konacan odgovor, ili neprocitljiv pokusaj."""

    call: ToolCall | None
    answer: str
    # Nije prazan kad model jeste pokusao poziv, ali nerazumljivo. Petlja tu
    # poruku vraca modelu kao rezultat koraka — dobija priliku da se popravi.
    error: str = ""


def _kandidati(text: str) -> list[str]:
    """Delovi teksta koji bi mogli biti JSON objekat, po redu verovatnoce."""

    kandidati = [text.strip()]
    kandidati.extend(m.strip() for m in _OGRADA.findall(text))
    pocetak = text.find("{")
    kraj = text.rfind("}")
    if pocetak != -1 and kraj > pocetak:
        kandidati.append(text[pocetak:kraj + 1])
    return [k for k in kandidati if k]


def parse_move(text: str) -> Move:
    """Cita potez iz odgovora modela."""

    sirovo = text or ""
    poslednja_greska = ""
    # Objekat bez polja `tool` je pokusaj poziva, ne proza. Bez ove zastavice
    # bi takav tekst prosao kao konacan odgovor, jer se niz `"tool"` u njemu
    # po definiciji ne pojavljuje.
    objekat_bez_alata = False

    for kandidat in _kandidati(sirovo):
        try:
            podaci = json.loads(kandidat)
        except ValueError:
            continue
        if not isinstance(podaci, dict):
            continue
        if "tool" not in podaci:
            objekat_bez_alata = True
            poslednja_greska = "Objekat mora imati polje `tool` sa imenom alata."
            continue

        ime = podaci.get("tool")
        if not isinstance(ime, str) or not ime.strip():
            poslednja_greska = "Polje `tool` mora biti ime alata."
            continue

        argumenti = podaci.get("args", {})
        if argumenti is None:
            argumenti = {}
        if not isinstance(argumenti, dict):
            poslednja_greska = "Polje `args` mora biti objekat sa imenovanim argumentima."
            continue

        return Move(call=ToolCall(tool=ime.strip(), args=argumenti), answer="")

    # Tekst koji uopste ne lici na poziv je konacan odgovor: agent koji je
    # zavrsio pise prozu, i to nije greska.
    lici_na_poziv = objekat_bez_alata or ("{" in sirovo and '"tool"' in sirovo)
    if not lici_na_poziv:
        return Move(call=None, answer=sirovo.strip())

    greska = poslednja_greska or (
        "Poziv alata nije citljiv JSON. Posalji tacno jedan objekat oblika "
        '{"tool": "ime_alata", "args": {...}}.'
    )
    return Move(call=None, answer="", error=greska)


def system_prompt(agent_prompt: str, tools_description: str) -> str:
    """Sklapa ulogu agenta sa uputstvom kako se poziva alat."""

    return (
        f"{agent_prompt.strip()}\n\n"
        "Radis u koracima. U svakom koraku biras tacno jedno:\n\n"
        "1. Poziv alata — odgovori ISKLJUCIVO JSON objektom oblika\n"
        '   {"tool": "ime_alata", "args": {"argument": "vrednost"}}\n'
        "   Jedan alat po koraku. Bez teksta oko JSON-a.\n\n"
        "2. Konacan odgovor — obican tekst, bez JSON-a. Pisi ga tek kad si "
        "prikupio sve sto ti treba.\n\n"
        "Rezultat svakog poziva stize ti kao sledeca poruka.\n\n"
        f"Alati koje smes da koristis:\n{tools_description}"
    )
```

- [ ] **Korak 4: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_protocol.py -v`

- [ ] **Korak 5: Commit**

```bash
git add core/domains/codium/agents/protocol.py tests/test_codium_agent_protocol.py
git commit -F- <<'EOF'
feat(codium): citanje poteza modela iz teksta

Protokol provajdera se ne dira: model odgovara JSON blokom ili prozom.
Tekst bez citljivog JSON-a je konacan odgovor, a ne greska — agent koji
je zavrsio pise prozu.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 5: Petlja

**Fajlovi:**
- Pravi: `core/domains/codium/agents/loop.py`
- Test: `tests/test_codium_agent_loop.py` (nov)

**Interfejsi:**
- Koristi: `Agent`, `AgentRun`, `AgentStep`, `RunRepository`, `ToolRegistry`,
  `parse_move`, `system_prompt`, `ScopeGate`, `ApprovalRepository`, `Approval`,
  `AuditRepository`, `AuditEntry`
- Daje:
  ```python
  Chat = Callable[[list[dict[str, str]]], str]   # poruke -> tekst modela

  class AgentLoop:
      def __init__(self, *, runs: RunRepository, tools: ToolRegistry,
                   gate: ScopeGate, approvals: ApprovalRepository,
                   audit: AuditRepository, chat: Chat) -> None
      def run(self, agent: Agent, run: AgentRun) -> AgentRun
      def resume(self, agent: Agent, run: AgentRun) -> AgentRun
  ```
  `chat` je ubrizgan da se petlja testira lažnim modelom. Pravi poziv kroz
  `ModelRouter` sklapa runtime u Zadatku 6.

- [ ] **Korak 1: Napiši testove koji padaju**

Nov fajl `tests/test_codium_agent_loop.py`:

```python
# ========== TESTOVI: petlja agenta ==========
from __future__ import annotations

import json

import pytest

from core.domains.codium.agents import (
    Agent,
    AgentRepository,
    AgentRun,
    RunRepository,
)
from core.domains.codium.agents.loop import AgentLoop
from core.domains.codium.agents.tools import build_tools
from core.domains.codium.audit import (
    ApprovalRepository,
    AuditRepository,
    ScopeRuleRepository,
)
from core.domains.codium.explorer import CodiumExplorer
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)
from core.security.scope_gate import ScopeGate, ScopeRule


class LazniModel:
    """Vraca unapred odredjen niz poteza; nijedan test ne zove pravi model."""

    def __init__(self, potezi: list[str]) -> None:
        self._potezi = list(potezi)
        self.pozivi: list[list[dict[str, str]]] = []

    def __call__(self, messages):
        self.pozivi.append(messages)
        return self._potezi.pop(0) if self._potezi else "Nemam vise poteza."


@pytest.fixture
def okruzenje(tmp_path):
    poslovna = tmp_path / "codium.db"
    ops = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(ops)

    koren = tmp_path / "projekat"
    koren.mkdir()
    (koren / "api.py").write_text("def handler():\n    pass\n", encoding="utf-8")

    return {
        "poslovna": poslovna,
        "ops": ops,
        "koren": koren,
        "runs": RunRepository(poslovna),
        "agenti": AgentRepository(poslovna),
        "pravila": ScopeRuleRepository(poslovna),
        "odobrenja": ApprovalRepository(poslovna),
        "dnevnik": AuditRepository(ops),
    }


def _petlja(okruzenje, model: LazniModel) -> AgentLoop:
    return AgentLoop(
        runs=okruzenje["runs"],
        tools=build_tools(CodiumExplorer(okruzenje["koren"]), None, None),
        gate=ScopeGate(lambda: okruzenje["pravila"].list()),
        approvals=okruzenje["odobrenja"],
        audit=okruzenje["dnevnik"],
        chat=model,
    )


def _pokreni(okruzenje, model, *, tools=("read_file", "list_dir", "write_file"),
             max_steps=12):
    agent = okruzenje["agenti"].update(1, {"tools": tools,
                                           "max_steps": max_steps})
    run = okruzenje["runs"].start(AgentRun(agent_id=agent.id, task="analiziraj"))
    return _petlja(okruzenje, model).run(agent, run), agent


def test_petlja_zove_alat_pa_zavrsava(okruzenje):
    model = LazniModel([
        '{"tool": "read_file", "args": {"rel": "api.py"}}',
        "Plan: izdvoj handler u servis.",
    ])
    run, _ = _pokreni(okruzenje, model)

    assert run.status == "done"
    assert run.result == "Plan: izdvoj handler u servis."
    vrste = [s.kind for s in okruzenje["runs"].steps(run.id)]
    assert vrste == ["tool_call", "tool_result", "answer"]


def test_rezultat_alata_stize_modelu(okruzenje):
    model = LazniModel([
        '{"tool": "read_file", "args": {"rel": "api.py"}}',
        "gotovo",
    ])
    _pokreni(okruzenje, model)
    # Drugi poziv modela mora da sadrzi ono sto je alat vratio.
    poslednji = json.dumps(model.pozivi[-1], ensure_ascii=False)
    assert "handler" in poslednji


def test_max_steps_zaustavlja_petlju(okruzenje):
    model = LazniModel(['{"tool": "list_dir", "args": {}}'] * 10)
    run, _ = _pokreni(okruzenje, model, max_steps=3)
    assert run.status == "failed"
    assert run.steps_used == 3


def test_dve_iste_greske_zaredom_prekidaju(okruzenje):
    # Model koji ne ume da se popravi ne sme da vrti krug do max_steps.
    model = LazniModel(['{"tool": "nepostojeci", "args": {}}'] * 8)
    run, _ = _pokreni(okruzenje, model, max_steps=12)
    assert run.status == "failed"
    assert run.steps_used < 8


def test_odbijen_alat_zavrsava_posao_i_ostavlja_trag(okruzenje):
    okruzenje["pravila"].add(ScopeRule(
        actor="agent:architect", action="file.write", target="*",
        verdict="deny", note="bez pisanja"))
    model = LazniModel([
        '{"tool": "write_file", "args": {"rel": "api.py", "content": "x"}}',
    ])
    run, _ = _pokreni(okruzenje, model)

    assert run.status == "failed"
    unosi = okruzenje["dnevnik"].query(action="file.write")
    assert unosi and unosi[0].verdict == "deny"
    assert unosi[0].actor == "agent:architect"


def test_potreba_za_odobrenjem_pauzira_i_upisuje_molbu(okruzenje):
    model = LazniModel([
        '{"tool": "write_file", "args": {"rel": "api.py", "content": "novo"}}',
    ])
    run, _ = _pokreni(okruzenje, model)

    assert run.status == "waiting_approval"
    ceka = okruzenje["odobrenja"].pending()
    assert len(ceka) == 1
    assert ceka[0].actor == "agent:architect"
    assert ceka[0].action == "file.write"
    assert run.pending_approval_id == ceka[0].id
    # Payload nosi pun poziv i otisak sadrzaja koji se pise.
    payload = json.loads(ceka[0].payload)
    assert payload["tool"] == "write_file"
    assert payload["content_hash"]


def test_fajl_se_ne_menja_dok_molba_ceka(okruzenje):
    model = LazniModel([
        '{"tool": "write_file", "args": {"rel": "api.py", "content": "novo"}}',
    ])
    _pokreni(okruzenje, model)
    assert "handler" in (okruzenje["koren"] / "api.py").read_text(
        encoding="utf-8")


def test_odobrena_molba_nastavlja_od_istog_koraka(okruzenje):
    model = LazniModel([
        '{"tool": "write_file", "args": {"rel": "api.py", "content": "novo"}}',
        "Izmena je upisana.",
    ])
    run, agent = _pokreni(okruzenje, model)
    molba = okruzenje["odobrenja"].pending()[0]
    okruzenje["odobrenja"].decide(molba.id, "approved")

    nastavljen = _petlja(okruzenje, model).resume(
        agent, okruzenje["runs"].get(run.id))

    assert nastavljen.status == "done"
    assert (okruzenje["koren"] / "api.py").read_text(encoding="utf-8") == "novo"


def test_odbijena_molba_zavrsava_posao_bez_izmene(okruzenje):
    model = LazniModel([
        '{"tool": "write_file", "args": {"rel": "api.py", "content": "novo"}}',
    ])
    run, agent = _pokreni(okruzenje, model)
    molba = okruzenje["odobrenja"].pending()[0]
    okruzenje["odobrenja"].decide(molba.id, "rejected", note="ne sada")

    zavrsen = _petlja(okruzenje, model).resume(
        agent, okruzenje["runs"].get(run.id))

    assert zavrsen.status == "cancelled"
    assert "handler" in (okruzenje["koren"] / "api.py").read_text(
        encoding="utf-8")
    poslednji = okruzenje["runs"].steps(run.id)[-1]
    assert "ne sada" in poslednji.payload


def test_alat_van_dozvoljenih_ne_izvrsava_se(okruzenje):
    # Agent sme samo ono sto mu je upisano u `tools`, bez obzira na kapiju.
    model = LazniModel([
        '{"tool": "write_file", "args": {"rel": "api.py", "content": "x"}}',
        "gotovo",
    ])
    run, _ = _pokreni(okruzenje, model, tools=("read_file",))
    assert "handler" in (okruzenje["koren"] / "api.py").read_text(
        encoding="utf-8")
    assert run.status in {"done", "failed"}
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_loop.py -v`

- [ ] **Korak 3: Napiši petlju**

Nov fajl `core/domains/codium/agents/loop.py`:

```python
# ==========          PETLJA AGENTA          ==========
# Cista petlja: sve zavisnosti su ubrizgane, pa se testira laznim modelom bez
# ijednog pravog poziva.
#
# Istorija razgovora se gradi iz koraka zapisanih u bazi, ne iz promenljive u
# memoriji. To je isti izvor iz kojeg `resume` krece dalje posle odobrenja, pa
# pauza ne trazi nit koja spava — nit umre, a nastavak je nova nit.
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from core.domains.codium.agents.models import Agent, AgentRun, AgentStep
from core.domains.codium.agents.protocol import ToolCall, parse_move, system_prompt
from core.domains.codium.agents.repository import RunRepository
from core.domains.codium.agents.tools.registry import ToolRegistry, ToolSpec
from core.domains.codium.audit import (
    Approval,
    ApprovalRepository,
    AuditEntry,
    AuditRepository,
)
from core.security.scope_gate import ALLOW, DENY, NEEDS_APPROVAL, ScopeGate

# Poruke -> tekst modela. Ubrizgano da bi petlja bila testabilna bez provajdera.
Chat = Callable[[list[dict[str, str]]], str]

# Model koji dva puta zaredom napravi istu gresku ne ume da se popravi. Bez
# ovoga bi vrteo krug do `max_steps` i trosio na svakom.
MAX_PONOVLJENIH_GRESAKA = 2


def _otisak(content: str) -> str:
    """Otisak sadrzaja koji se pise — covek odobrava tekst koji je video."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AgentLoop:
    """Vodi jedan posao agenta od zadatka do ishoda."""

    def __init__(self, *, runs: RunRepository, tools: ToolRegistry,
                 gate: ScopeGate, approvals: ApprovalRepository,
                 audit: AuditRepository, chat: Chat) -> None:
        self._runs = runs
        self._tools = tools
        self._gate = gate
        self._approvals = approvals
        self._audit = audit
        self._chat = chat

    # ----------          ULAZI          ----------

    def run(self, agent: Agent, run: AgentRun) -> AgentRun:
        return self._vrti(agent, run, koraka=0, poslednja_greska="",
                          ponovljeno=0)

    def resume(self, agent: Agent, run: AgentRun) -> AgentRun:
        """Nastavlja posao posle odluke coveka o molbi."""

        if run.status != "waiting_approval" or run.pending_approval_id is None:
            return run

        molba = self._approvals.get(run.pending_approval_id)
        if molba is None or molba.status == "pending":
            # Jos se ceka; posao ostaje kakav jeste.
            return run

        payload = self._procitaj_payload(molba.payload)
        ime_alata = str(payload.get("tool", ""))

        if molba.status != "approved":
            razlog = molba.note or "bez obrazlozenja"
            self._korak(run.id, "tool_result", ime_alata,
                        f"Odbijeno: {razlog}")
            return self._runs.finish(
                run.id, status="cancelled",
                result=f"Covek je odbio potez `{ime_alata}`: {razlog}",
                steps_used=self._broj_poteza(run.id),
            )

        spec = self._tools.get(ime_alata)
        if spec is None:
            self._korak(run.id, "tool_result", ime_alata,
                        f"Alat `{ime_alata}` vise ne postoji.")
            return self._runs.finish(
                run.id, status="failed",
                result=f"Odobren alat `{ime_alata}` vise ne postoji.",
                steps_used=self._broj_poteza(run.id),
            )

        argumenti = payload.get("args") or {}
        if not isinstance(argumenti, dict):
            argumenti = {}

        if spec.writes_content:
            sada = _otisak(str(argumenti.get("content", "")))
            if sada != payload.get("content_hash"):
                # Sadrzaj se promenio izmedju molbe i nastavka. Odobreno je
                # bilo ono sto je covek video, a ne ovo.
                self._korak(run.id, "tool_result", ime_alata,
                            "Sadrzaj se promenio posle odobrenja; potez pada.")
                return self._runs.finish(
                    run.id, status="failed",
                    result="Otisak sadrzaja se ne poklapa sa odobrenim.",
                    steps_used=self._broj_poteza(run.id),
                )

        izlaz, _ = self._izvrsi(spec, argumenti)
        self._korak(run.id, "tool_result", ime_alata, izlaz)

        nastavljen = self._runs.resume(run.id)
        if nastavljen is None:
            return self._runs.get(run.id)
        return self._vrti(agent, nastavljen,
                          koraka=self._broj_poteza(run.id),
                          poslednja_greska="", ponovljeno=0)

    # ----------          JEZGRO          ----------

    def _vrti(self, agent: Agent, run: AgentRun, *, koraka: int,
              poslednja_greska: str, ponovljeno: int) -> AgentRun:
        while True:
            # Prekid je zapis, ne signal: nit ga vidi pre sledeceg poteza.
            tekuci = self._runs.get(run.id)
            if tekuci is None or tekuci.status != "running":
                return tekuci if tekuci is not None else run

            if koraka >= agent.max_steps:
                return self._runs.finish(
                    run.id, status="failed",
                    result=f"Dostignut limit od {agent.max_steps} koraka.",
                    steps_used=koraka,
                )

            potez = parse_move(self._chat(self._poruke(agent, run)))
            koraka += 1

            # Proza bez poziva alata je konacan odgovor.
            if potez.call is None and not potez.error:
                self._korak(run.id, "answer", "", potez.answer)
                return self._runs.finish(run.id, status="done",
                                         result=potez.answer,
                                         steps_used=koraka)

            if potez.error:
                ishod = self._greska(run.id, "", potez.error,
                                     poslednja_greska, ponovljeno, koraka)
                if ishod is not None:
                    return ishod
                poslednja_greska, ponovljeno = potez.error, (
                    ponovljeno + 1 if potez.error == poslednja_greska else 1)
                continue

            call = potez.call
            self._korak(run.id, "tool_call", call.tool,
                        json.dumps({"tool": call.tool, "args": call.args},
                                   ensure_ascii=False))

            # Agent sme samo ono sto mu je upisano, bez obzira na kapiju.
            if call.tool not in agent.tools:
                poruka = f"Alat `{call.tool}` nije dozvoljen ovom agentu."
            else:
                spec = self._tools.get(call.tool)
                poruka = (f"Alat `{call.tool}` ne postoji."
                          if spec is None else "")

            if poruka:
                ishod = self._greska(run.id, call.tool, poruka,
                                     poslednja_greska, ponovljeno, koraka)
                if ishod is not None:
                    return ishod
                ponovljeno = (ponovljeno + 1
                              if poruka == poslednja_greska else 1)
                poslednja_greska = poruka
                continue

            spec = self._tools.get(call.tool)
            odluka = self._gate.check(
                actor=f"agent:{agent.slug}", action=spec.action,
                target=self._meta(call),
            )

            if odluka.verdict == DENY:
                self._trag(agent, run, spec, call, "deny", "blocked",
                           odluka.reason)
                self._korak(run.id, "tool_result", call.tool,
                            f"Odbijeno pravilom: {odluka.reason}")
                return self._runs.finish(
                    run.id, status="failed",
                    result=f"Kapija je odbila `{spec.action}`: {odluka.reason}",
                    steps_used=koraka,
                )

            if odluka.verdict == NEEDS_APPROVAL:
                molba = self._zatrazi_odobrenje(agent, run, spec, call)
                self._trag(agent, run, spec, call, NEEDS_APPROVAL, "pending",
                           f"molba {molba.id}")
                self._korak(run.id, "tool_result", call.tool,
                            f"Ceka odobrenje coveka (molba {molba.id}).")
                pauziran = self._runs.wait_for_approval(run.id, molba.id)
                return pauziran if pauziran is not None else self._runs.get(run.id)

            if odluka.verdict != ALLOW:
                # Nepoznat verdikt se ponasa kao odbijanje. Tiho izvrsavanje
                # onoga sto kapija nije izricito dozvolila je rupa.
                self._trag(agent, run, spec, call, odluka.verdict, "blocked",
                           odluka.reason)
                self._korak(run.id, "tool_result", call.tool,
                            f"Nepoznat odgovor kapije: {odluka.verdict}")
                return self._runs.finish(
                    run.id, status="failed",
                    result=f"Kapija je vratila nepoznat verdikt "
                           f"`{odluka.verdict}`.",
                    steps_used=koraka,
                )

            # Citanja se ne upisuju u dnevnik — vec stoje kao koraci posla, a
            # dnevnik bi se ugusio u njima.
            izlaz, greska = self._izvrsi(spec, call.args)
            self._korak(run.id, "tool_result", call.tool, izlaz)

            if greska:
                ishod = self._greska(run.id, call.tool, izlaz,
                                     poslednja_greska, ponovljeno, koraka,
                                     vec_upisano=True)
                if ishod is not None:
                    return ishod
                ponovljeno = (ponovljeno + 1
                              if izlaz == poslednja_greska else 1)
                poslednja_greska = izlaz
            else:
                poslednja_greska, ponovljeno = "", 0

    # ----------          POMOCNO          ----------

    def _poruke(self, agent: Agent, run: AgentRun) -> list[dict[str, str]]:
        poruke = [
            {"role": "system",
             "content": system_prompt(agent.system_prompt,
                                      self._tools.describe(agent.tools))},
            {"role": "user", "content": run.task},
        ]
        for step in self._runs.steps(run.id):
            if step.kind == "tool_call":
                poruke.append({"role": "assistant", "content": step.payload})
            elif step.kind == "tool_result":
                poruke.append({"role": "user", "content": step.payload})
        return poruke

    def _korak(self, run_id: int, kind: str, tool: str, payload: str) -> None:
        self._runs.append_step(AgentStep(
            run_id=run_id, idx=self._sledeci_idx(run_id), kind=kind,
            tool=tool, payload=payload,
        ))

    def _sledeci_idx(self, run_id: int) -> int:
        koraci = self._runs.steps(run_id)
        return koraci[-1].idx + 1 if koraci else 0

    def _broj_poteza(self, run_id: int) -> int:
        return sum(1 for s in self._runs.steps(run_id) if s.kind == "tool_call")

    def _meta(self, call: ToolCall) -> str:
        """Cilj koji ide kapiji: putanja kad je ima, inace prazno."""

        rel = call.args.get("rel")
        return str(rel) if isinstance(rel, str) else ""

    def _izvrsi(self, spec: ToolSpec, args: dict) -> tuple[str, bool]:
        """Pokrece alat; izuzetak postaje rezultat koraka, ne pad petlje."""

        try:
            return str(spec.run(**args)), False
        except TypeError as greska:
            return f"Pogresni argumenti za `{spec.name}`: {greska}", True
        except Exception as greska:  # noqa: BLE001 - alat sme da pukne bilo cime
            return f"Greska alata `{spec.name}`: {greska}", True

    def _greska(self, run_id: int, tool: str, poruka: str,
                poslednja: str, ponovljeno: int, koraka: int,
                *, vec_upisano: bool = False) -> AgentRun | None:
        """Upisuje gresku kao rezultat koraka i gasi petlju na ponavljanju."""

        if not vec_upisano:
            self._korak(run_id, "tool_result", tool, poruka)
        if poruka == poslednja and ponovljeno + 1 >= MAX_PONOVLJENIH_GRESAKA:
            return self._runs.finish(
                run_id, status="failed",
                result=f"Ista greska dva puta zaredom: {poruka}",
                steps_used=koraka,
            )
        return None

    def _zatrazi_odobrenje(self, agent: Agent, run: AgentRun, spec: ToolSpec,
                           call: ToolCall) -> Approval:
        payload: dict[str, object] = {"tool": call.tool, "args": call.args}
        if spec.writes_content:
            payload["content_hash"] = _otisak(str(call.args.get("content", "")))
        return self._approvals.request(Approval(
            actor=f"agent:{agent.slug}", action=spec.action,
            target=self._meta(call),
            payload=json.dumps(payload, ensure_ascii=False),
        ))

    def _trag(self, agent: Agent, run: AgentRun, spec: ToolSpec,
              call: ToolCall, verdict: str, outcome: str, detail: str) -> None:
        self._audit.record(AuditEntry(
            actor=f"agent:{agent.slug}", action=spec.action, verdict=verdict,
            target=self._meta(call), outcome=outcome, detail=detail,
            project_id=run.project_id,
        ))

    def _procitaj_payload(self, sirovo: str) -> dict:
        try:
            podaci = json.loads(sirovo or "{}")
        except ValueError:
            return {}
        return podaci if isinstance(podaci, dict) else {}
```

- [ ] **Korak 4: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_loop.py -v`

- [ ] **Korak 5: Commit**

```bash
git add core/domains/codium/agents/loop.py tests/test_codium_agent_loop.py
git commit -F- <<'EOF'
feat(codium): petlja agenta sa kapijom, pauzom i nastavkom

Istorija se gradi iz koraka u bazi, ne iz promenljive u memoriji — to je
isti izvor iz kojeg nastavak posle odobrenja krece dalje, pa pauza ne
trazi nit koja spava.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 6: Nit, runtime i rute

**Fajlovi:**
- Pravi: `core/domains/codium/agents/runner.py`
- Pravi: `apps/api/codium_agents_runtime.py`
- Pravi: `apps/api/schemas/codium_agents.py`
- Pravi: `apps/api/routers/codium_agents.py`
- Menja: `apps/api/main.py`
- Test: `tests/test_api_codium_agents.py` (nov)

**Interfejsi:**
- Koristi: sve iz Zadataka 2–5; `ModelRouter`, `UsageRecorder`, obrazac iz
  `apps/api/codium_security_runtime.py` i `apps/api/routers/codium_audit.py`
- Daje rute pod `/api/v1/codium/agents`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/` | agenti |
| POST | `/` | nov agent |
| PATCH | `/{id}` | izmena |
| DELETE | `/{id}` | brisanje |
| GET | `/tools` | registar alata i dozvole koje traže |
| POST | `/{id}/run` | pokretanje; vraća `run_id` odmah |
| GET | `/runs` | poslednji poslovi |
| GET | `/runs/{run_id}` | stanje i koraci (`since_idx`) |
| POST | `/runs/{run_id}/cancel` | prekid |

- [ ] **Korak 1: Napiši testove koji padaju**

Nov fajl `tests/test_api_codium_agents.py`. Fixture prati obrazac iz
`tests/test_api_codium_audit.py`: prave baze u `tmp_path`, zavisnosti kroz
`app.dependency_overrides`. Petlja se u testu zamenjuje lažnom koja odmah
završava posao — **nijedan test ne pokreće pravu nit ni pravi model**.

```python
def test_spisak_agenata_nosi_architect(client):
    data = client.get("/api/v1/codium/agents/").json()
    assert [a["slug"] for a in data["agents"]] == ["architect"]


def test_registar_alata_kaze_koju_dozvolu_alat_trazi(client):
    data = client.get("/api/v1/codium/agents/tools").json()
    po_imenu = {t["name"]: t["action"] for t in data["tools"]}
    assert po_imenu["write_file"] == "file.write"
    assert po_imenu["read_file"] == "file.read"


def test_izmena_agenta_menja_spisak_alata(client):
    resp = client.patch("/api/v1/codium/agents/1",
                        json={"tools": ["read_file"], "max_steps": 5})
    assert resp.status_code == 200
    assert resp.json()["tools"] == ["read_file"]
    assert resp.json()["max_steps"] == 5


def test_pokretanje_vraca_run_id_odmah(client):
    resp = client.post("/api/v1/codium/agents/1/run",
                       json={"task": "analiziraj", "project_id": None})
    assert resp.status_code == 200
    assert resp.json()["run_id"] > 0


def test_koraci_se_citaju_inkrementalno(client):
    run_id = client.post("/api/v1/codium/agents/1/run",
                         json={"task": "t"}).json()["run_id"]
    svi = client.get(f"/api/v1/codium/agents/runs/{run_id}").json()
    assert svi["steps"]
    posle = client.get(f"/api/v1/codium/agents/runs/{run_id}",
                       params={"since_idx": svi["steps"][-1]["idx"]}).json()
    assert posle["steps"] == []


def test_prekid_posla(client):
    run_id = client.post("/api/v1/codium/agents/1/run",
                         json={"task": "t"}).json()["run_id"]
    resp = client.post(f"/api/v1/codium/agents/runs/{run_id}/cancel")
    assert resp.status_code in {200, 409}


def test_nepoznat_agent_je_404(client):
    assert client.post("/api/v1/codium/agents/999/run",
                       json={"task": "t"}).status_code == 404
```

Dopiši i test koji tvrdi da `POST /{id}/run` **ne čeka** rezultat — da odgovor
stigne pre nego što posao dođe u završno stanje kada lažna petlja namerno kasni.

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_api_codium_agents.py -v`

- [ ] **Korak 3: Napiši nit**

`core/domains/codium/agents/runner.py`:

```python
# ==========          POKRETAC POSLA          ==========
# Daemon nit, isti obrazac koji projekat vec koristi (`streaming.py`,
# `installer.py`, `disk_monitor.py`). Nema reda poslova i ne uvodi se.
#
# Stanje zivi u bazi, ne u niti: zato restart API-ja ne gubi posao, a pauza na
# odobrenju ne trazi nit koja spava — nit umre, a nastavak je nova nit.
```

Puna sadržina fajla:

```python
# ==========          POKRETAC POSLA          ==========
# Daemon nit, isti obrazac koji projekat vec koristi (`streaming.py`,
# `installer.py`, `disk_monitor.py`). Nema reda poslova i ne uvodi se.
#
# Stanje zivi u bazi, ne u niti: zato restart API-ja ne gubi posao, a pauza na
# odobrenju ne trazi nit koja spava — nit umre, a nastavak je nova nit.
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from core.domains.codium.agents.loop import AgentLoop
from core.domains.codium.agents.models import Agent, AgentRun
from core.domains.codium.agents.repository import RunRepository

logger = logging.getLogger(__name__)

# Fabrika petlje za jedan posao: petlja zavisi od projekta (explorer), pa se
# pravi po poslu, a ne jednom za ceo proces.
LoopFactory = Callable[[Agent, AgentRun], AgentLoop]


class AgentRunner:
    """Pokrece posao u pozadini i garantuje da nece ostati bez ishoda."""

    def __init__(self, loop_factory: LoopFactory, runs: RunRepository) -> None:
        self._loop_factory = loop_factory
        self._runs = runs

    def start(self, agent: Agent, run: AgentRun) -> None:
        self._u_niti(agent, run, nastavak=False)

    def resume(self, agent: Agent, run: AgentRun) -> None:
        self._u_niti(agent, run, nastavak=True)

    def _u_niti(self, agent: Agent, run: AgentRun, *, nastavak: bool) -> None:
        def posao() -> None:
            try:
                petlja = self._loop_factory(agent, run)
                if nastavak:
                    petlja.resume(agent, run)
                else:
                    petlja.run(agent, run)
            except Exception as greska:  # noqa: BLE001
                # Nit koja umre bez traga ostavila bi posao zauvek u
                # „running", i GUI bi ga vecno osvezavao.
                logger.exception("Posao agenta je pukao")
                self._runs.finish(
                    run.id, status="failed",
                    result=f"Posao je pukao: {greska}",
                )

        threading.Thread(target=posao, daemon=True,
                         name=f"codium-agent-{run.id}").start()
```

- [ ] **Korak 4: Napiši runtime**

Prvo dopuni `apps/api/codium_assistant_runtime.py` jednim izlazom, da se ruter
ne sklapa dva puta:

```python
def get_router() -> ModelRouter:
    """Ruter modela — agenti koriste isti kao chat, sa svojim override-om."""

    return _router
```

Nov fajl `apps/api/codium_agents_runtime.py`:

```python
# ========== RUNTIME AGENATA ==========
# Rute traze repozitorijume i pokretac kroz `Depends`, pa im ovde stoji jedan
# primerak. Testovi ih menjaju kroz `app.dependency_overrides`.
from __future__ import annotations

import time
from pathlib import Path

from apps.api import codium_assistant_runtime
from core.ai.providers.base import ChatMessage
from core.ai.usage import UsageRecorder
from core.domains.codium.agents import Agent, AgentRepository, AgentRun, RunRepository
from core.domains.codium.agents.loop import AgentLoop
from core.domains.codium.agents.runner import AgentRunner
from core.domains.codium.agents.tools import ToolRegistry, build_tools
from core.domains.codium.explorer import CodiumExplorer
from core.domains.codium.repository import CodiumRepository
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)
from core.domains.codium.service import CodiumService
from apps.api import codium_security_runtime

_agents: AgentRepository | None = None
_runs: RunRepository | None = None
_runner: AgentRunner | None = None
_service: CodiumService | None = None


def _database_path() -> Path:
    """Poslovna baza. Izdvojeno da test moze da je zameni."""
    return codium_database_path()


def _ops_database_path() -> Path:
    return codium_ops_database_path()


def get_agents() -> AgentRepository:
    global _agents
    if _agents is None:
        _agents = AgentRepository(_database_path())
    return _agents


def get_runs() -> RunRepository:
    global _runs
    if _runs is None:
        _runs = RunRepository(_database_path())
    return _runs


def get_service() -> CodiumService:
    global _service
    if _service is None:
        _service = CodiumService(CodiumRepository(_database_path()))
    return _service


def project_root(project_id: int | None) -> Path:
    """Koren projekta nad kojim agent radi.

    Bez projekta agent radi nad korenom repozitorijuma — tako alati za citanje
    imaju smisla i pre nego sto se izabere projekat.
    """

    if project_id is None:
        return Path.cwd()
    projekat = get_service().get_project(project_id)
    if projekat is None or not projekat.local_path:
        return Path.cwd()
    koren = Path(projekat.local_path)
    return koren if koren.is_dir() else Path.cwd()


def tools_for(project_id: int | None) -> ToolRegistry:
    return build_tools(CodiumExplorer(project_root(project_id)),
                       get_service(), project_id)


def tool_catalog() -> ToolRegistry:
    """Registar samo radi opisa (ruta `/tools`); alati se odavde ne pokrecu."""

    return tools_for(None)


def _chat_for(agent: Agent, run: AgentRun):
    """Pravi poziv modela za jednog agenta, uz evidenciju potrosnje."""

    router = codium_assistant_runtime.get_router()
    usage = UsageRecorder(_ops_database_path())
    persona = f"agent:{agent.slug}"

    def chat(messages: list[dict[str, str]]) -> str:
        # Prazan `model` znaci nasledjivanje onoga sto bi chat koristio.
        resolved = router.resolve(
            project_id=run.project_id, persona=persona,
            override_provider=agent.provider or None,
            override_model=agent.model or None,
        )
        pocetak = time.monotonic()
        try:
            rezultat = router.chat(
                [ChatMessage(role=m["role"], content=m["content"])
                 for m in messages],
                resolved,
            )
        except Exception:
            usage.record(
                provider=resolved.provider_name, model=resolved.model,
                project_id=run.project_id, persona=persona,
                prompt_tokens=0, output_tokens=0,
                duration_ms=int((time.monotonic() - pocetak) * 1000),
                ok=False, actor=persona,
            )
            raise

        usage.record(
            provider=rezultat.provider, model=rezultat.model,
            project_id=run.project_id, persona=persona,
            prompt_tokens=rezultat.prompt_tokens,
            output_tokens=rezultat.output_tokens,
            duration_ms=rezultat.duration_ms, ok=True, actor=persona,
        )
        return rezultat.text

    return chat


def build_loop(agent: Agent, run: AgentRun) -> AgentLoop:
    return AgentLoop(
        runs=get_runs(),
        tools=tools_for(run.project_id),
        gate=codium_security_runtime.get_scope_gate(),
        approvals=codium_security_runtime.get_approvals(),
        audit=codium_security_runtime.get_audit(),
        chat=_chat_for(agent, run),
    )


def get_runner() -> AgentRunner:
    global _runner
    if _runner is None:
        _runner = AgentRunner(build_loop, get_runs())
    return _runner


def reset() -> None:
    """Zaboravi napravljene primerke (koristi se u testovima)."""
    global _agents, _runs, _runner, _service
    _agents = None
    _runs = None
    _runner = None
    _service = None
```

- [ ] **Korak 5: Napiši šeme**

Nov fajl `apps/api/schemas/codium_agents.py`:

```python
# ========== ŠEME: agenti i njihovi poslovi ==========
from __future__ import annotations

from pydantic import BaseModel, Field

from core.domains.codium.agents import Agent, AgentRun, AgentStep
from core.domains.codium.agents.tools.registry import ToolSpec


# ==========          AGENTI          ==========

class AgentResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    system_prompt: str
    model: str
    provider: str
    tools: list[str]
    max_steps: int
    enabled: bool

    @classmethod
    def from_domain(cls, agent: Agent) -> "AgentResponse":
        return cls(
            id=agent.id, slug=agent.slug, name=agent.name,
            description=agent.description, system_prompt=agent.system_prompt,
            model=agent.model, provider=agent.provider,
            tools=list(agent.tools), max_steps=agent.max_steps,
            enabled=agent.enabled,
        )


class AgentsResponse(BaseModel):
    count: int
    agents: list[AgentResponse]


class AgentRequest(BaseModel):
    slug: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    system_prompt: str = ""
    model: str = ""
    provider: str = ""
    tools: list[str] = []
    max_steps: int = Field(default=12, ge=1, le=50)


class AgentPatchRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    provider: str | None = None
    tools: list[str] | None = None
    max_steps: int | None = Field(default=None, ge=1, le=50)
    enabled: bool | None = None


class AgentDeletedResponse(BaseModel):
    ok: bool
    id: int


# ==========          ALATI          ==========

class ToolResponse(BaseModel):
    name: str
    description: str
    action: str
    args: dict[str, str]
    writes_content: bool

    @classmethod
    def from_domain(cls, spec: ToolSpec) -> "ToolResponse":
        return cls(
            name=spec.name, description=spec.description, action=spec.action,
            args=spec.args, writes_content=spec.writes_content,
        )


class ToolsResponse(BaseModel):
    count: int
    tools: list[ToolResponse]


# ==========          POSLOVI          ==========

class RunRequest(BaseModel):
    task: str = Field(..., min_length=1)
    project_id: int | None = None


class RunStartedResponse(BaseModel):
    run_id: int


class StepResponse(BaseModel):
    idx: int
    kind: str
    tool: str
    payload: str
    at: str

    @classmethod
    def from_domain(cls, step: AgentStep) -> "StepResponse":
        return cls(idx=step.idx, kind=step.kind, tool=step.tool,
                   payload=step.payload, at=step.at)


class RunSummary(BaseModel):
    id: int
    agent_id: int
    # Slug stoji uz posao da kontrolna tabla ne mora da dovuce ceo spisak
    # agenata samo da bi ispisala ime.
    agent_slug: str
    project_id: int | None
    task: str
    status: str
    result: str
    steps_used: int
    cost_usd: float
    pending_approval_id: int | None
    started_at: str
    finished_at: str | None

    @classmethod
    def from_domain(cls, run: AgentRun, agent_slug: str = "") -> "RunSummary":
        return cls(
            id=run.id, agent_id=run.agent_id, agent_slug=agent_slug,
            project_id=run.project_id, task=run.task, status=run.status,
            result=run.result, steps_used=run.steps_used,
            cost_usd=run.cost_usd,
            pending_approval_id=run.pending_approval_id,
            started_at=run.started_at, finished_at=run.finished_at,
        )


class RunsResponse(BaseModel):
    count: int
    runs: list[RunSummary]


class RunResponse(BaseModel):
    run: RunSummary
    steps: list[StepResponse]
```

- [ ] **Korak 6: Napiši rute**

Nov fajl `apps/api/routers/codium_agents.py`:

```python
# ========== ROUTER: AGENTI (CODIUM) ==========
# Pokretanje ne ceka rezultat: upisuje posao, dize nit i vraca `run_id` odmah.
# GUI dalje cita korake u stranicama.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api import codium_agents_runtime
from apps.api.schemas.codium_agents import (
    AgentDeletedResponse,
    AgentPatchRequest,
    AgentRequest,
    AgentResponse,
    AgentsResponse,
    RunRequest,
    RunResponse,
    RunStartedResponse,
    RunSummary,
    RunsResponse,
    StepResponse,
    ToolResponse,
    ToolsResponse,
)
from core.domains.codium.agents import (
    Agent,
    AgentRepository,
    AgentRun,
    RunRepository,
)
from core.domains.codium.agents.runner import AgentRunner

router = APIRouter(
    prefix="/api/v1/codium/agents",
    tags=["CODIUM Agenti"],
)


def get_agents() -> AgentRepository:
    return codium_agents_runtime.get_agents()


def get_runs() -> RunRepository:
    return codium_agents_runtime.get_runs()


def get_runner() -> AgentRunner:
    return codium_agents_runtime.get_runner()


def _require_agent(agent_id: int, agents: AgentRepository) -> Agent:
    agent = agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent ne postoji.")
    return agent


def _summary(run: AgentRun, agents: AgentRepository) -> RunSummary:
    agent = agents.get(run.agent_id)
    # Obrisan agent ne obara prikaz posla — posao je i dalje istorija.
    return RunSummary.from_domain(run, agent.slug if agent else "")


# ==========          AGENTI          ==========

@router.get("/", response_model=AgentsResponse)
def list_agents(
    agents: AgentRepository = Depends(get_agents),
) -> AgentsResponse:
    """Svi definisani agenti."""

    svi = agents.list()
    return AgentsResponse(count=len(svi),
                          agents=[AgentResponse.from_domain(a) for a in svi])


@router.post("/", response_model=AgentResponse)
def add_agent(
    payload: AgentRequest,
    agents: AgentRepository = Depends(get_agents),
) -> AgentResponse:
    """Nov agent. Dodavanje je unos u bazu, ne nov modul."""

    upisan = agents.add(Agent(
        slug=payload.slug, name=payload.name, description=payload.description,
        system_prompt=payload.system_prompt, model=payload.model,
        provider=payload.provider, tools=tuple(payload.tools),
        max_steps=payload.max_steps,
    ))
    return AgentResponse.from_domain(upisan)


@router.patch("/{agent_id}", response_model=AgentResponse)
def patch_agent(
    agent_id: int,
    payload: AgentPatchRequest,
    agents: AgentRepository = Depends(get_agents),
) -> AgentResponse:
    """Izmena agenta; menja se samo ono sto je poslato."""

    _require_agent(agent_id, agents)
    izmena = payload.model_dump(exclude_none=True)
    if "tools" in izmena:
        izmena["tools"] = tuple(izmena["tools"])
    return AgentResponse.from_domain(agents.update(agent_id, izmena))


@router.delete("/{agent_id}", response_model=AgentDeletedResponse)
def delete_agent(
    agent_id: int,
    agents: AgentRepository = Depends(get_agents),
) -> AgentDeletedResponse:
    """Brise agenta. Brisanje nepostojeceg nije greska — ishod je isti."""

    agents.delete(agent_id)
    return AgentDeletedResponse(ok=True, id=agent_id)


# ==========          ALATI          ==========

@router.get("/tools", response_model=ToolsResponse)
def list_tools() -> ToolsResponse:
    """Alati i dozvole koje traze — covek mora videti sta cekiranjem otvara."""

    registar = codium_agents_runtime.tool_catalog()
    specs = [registar.get(ime) for ime in registar.names()]
    return ToolsResponse(count=len(specs),
                         tools=[ToolResponse.from_domain(s) for s in specs])


# ==========          POSLOVI          ==========

@router.post("/{agent_id}/run", response_model=RunStartedResponse)
def start_run(
    agent_id: int,
    payload: RunRequest,
    agents: AgentRepository = Depends(get_agents),
    runs: RunRepository = Depends(get_runs),
    runner: AgentRunner = Depends(get_runner),
) -> RunStartedResponse:
    """Pokrece posao i vraca `run_id` odmah — rad ide u pozadini."""

    agent = _require_agent(agent_id, agents)
    if not agent.enabled:
        raise HTTPException(status_code=409, detail="Agent je iskljucen.")

    run = runs.start(AgentRun(agent_id=agent.id, task=payload.task,
                              project_id=payload.project_id))
    runner.start(agent, run)
    return RunStartedResponse(run_id=run.id)


@router.get("/runs", response_model=RunsResponse)
def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    agents: AgentRepository = Depends(get_agents),
    runs: RunRepository = Depends(get_runs),
) -> RunsResponse:
    """Poslednji poslovi, najnoviji prvi."""

    poslednji = runs.recent(limit=limit)
    return RunsResponse(count=len(poslednji),
                        runs=[_summary(r, agents) for r in poslednji])


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(
    run_id: int,
    since_idx: int = Query(default=-1, ge=-1),
    agents: AgentRepository = Depends(get_agents),
    runs: RunRepository = Depends(get_runs),
) -> RunResponse:
    """Stanje posla i koraci; `since_idx` da poll ne prenosi isto u krug."""

    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Posao ne postoji.")
    koraci = runs.steps(run_id, since_idx=since_idx)
    return RunResponse(
        run=_summary(run, agents),
        steps=[StepResponse.from_domain(s) for s in koraci],
    )


@router.post("/runs/{run_id}/cancel", response_model=RunSummary)
def cancel_run(
    run_id: int,
    agents: AgentRepository = Depends(get_agents),
    runs: RunRepository = Depends(get_runs),
) -> RunSummary:
    """Prekida posao koji jos traje.

    Nit se ne ubija: ona upisuje sledeci korak i vidi da posao vise nije
    `running`. Prekid je zapis, ne signal.
    """

    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Posao ne postoji.")
    if run.status not in {"running", "waiting_approval"}:
        raise HTTPException(status_code=409, detail="Posao vise ne traje.")

    prekinut = runs.finish(run_id, status="cancelled",
                           result="Prekinuto na zahtev coveka.",
                           steps_used=run.steps_used)
    return _summary(prekinut, agents)
```

U `apps/api/main.py` dodaj uvoz i registraciju odmah posle `codium_audit_router`:

```python
app.include_router(codium_agents_router)
```

`apps/api/schemas/codium_agents.py`: `AgentResponse`, `AgentsResponse`,
`AgentRequest`, `AgentPatchRequest`, `ToolResponse`, `ToolsResponse`,
`RunRequest`, `RunStartedResponse`, `StepResponse`, `RunResponse`,
`RunsResponse`.

`RunResponse` nosi i **`agent_slug`** pored `agent_id`. Bez toga bi kontrolna
tabla morala da dovuče ceo spisak agenata samo da bi ispisala ime uz posao.
Slug se dobija iz `AgentRepository.get(run.agent_id)`; kad agent više ne
postoji, polje je prazan string, a ne greška.

`apps/api/routers/codium_agents.py` sa prefiksom `/api/v1/codium/agents` i
rutama iz tabele gore. `POST /{id}/run` upisuje red, diže nit i **odmah** vraća
`run_id`.

U `apps/api/main.py` registruj router odmah posle `codium_audit_router`.

- [ ] **Korak 7: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_api_codium_agents.py -v`
Pa ceo paket: `./.venv/Scripts/python.exe -m pytest -q`

- [ ] **Korak 8: Commit**

```bash
git add core/domains/codium/agents/runner.py apps/api tests/test_api_codium_agents.py
git commit -F- <<'EOF'
feat(api): rute agenata, posao u niti, koraci u stranicama

Nit hvata svaki izuzetak i upisuje ga kao neuspeh: nit koja umre bez
traga ostavila bi posao zauvek u stanju „running".

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 7: GUI — tipovi, pozivi i prikaz koraka

**Fajlovi:**
- Menja: `apps/gui/src/types/codium.ts`
- Menja: `apps/gui/src/services/codiumApi.ts`
- Pravi: `apps/gui/src/features/codium/agentRun.ts`
- Test: `apps/gui/src/features/codium/agentRun.test.ts` (nov)

**Interfejsi:**
- Daje tipove `AgentSummary`, `AgentsResponse`, `AgentTool`, `ToolsResponse`,
  `AgentStep`, `AgentRunSummary` (nosi i `agent_slug`), `RunResponse`,
  `RunsResponse`; pozive
  `getAgents`, `updateAgent`, `getAgentTools`, `startAgentRun`, `getAgentRun`,
  `getAgentRuns`, `cancelAgentRun`; i:
  ```ts
  export type StepTone = "thought" | "call" | "result" | "answer" | "blocked";
  export function stepTone(step: { kind: string; payload: string }): StepTone
  export function runLabel(status: string): string
  export function isRunLive(status: string): boolean
  ```

- [ ] **Korak 1: Napiši test koji pada**

Nov fajl `apps/gui/src/features/codium/agentRun.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { isRunLive, runLabel, stepTone } from "./agentRun";

describe("ton koraka", () => {
  it("poziv alata i njegov rezultat se razlikuju", () => {
    expect(stepTone({ kind: "tool_call", payload: "" })).toBe("call");
    expect(stepTone({ kind: "tool_result", payload: "" })).toBe("result");
  });

  it("konacan odgovor ima svoj ton", () => {
    expect(stepTone({ kind: "answer", payload: "" })).toBe("answer");
  });

  it("nepoznata vrsta ne rusi prikaz", () => {
    expect(stepTone({ kind: "nesto", payload: "" })).toBe("thought");
  });
});

describe("stanje posla", () => {
  it("posao koji ceka odluku jos traje", () => {
    // Dok ceka odobrenje, posao nije gotov — prikaz mora da se osvezava.
    expect(isRunLive("waiting_approval")).toBe(true);
    expect(isRunLive("running")).toBe(true);
  });

  it("zavrsen posao se vise ne osvezava", () => {
    expect(isRunLive("done")).toBe(false);
    expect(isRunLive("failed")).toBe(false);
    expect(isRunLive("cancelled")).toBe(false);
  });

  it("nepoznato stanje se ne osvezava u beskraj", () => {
    // Inace bi greska na serveru znacila poll koji nikad ne prestaje.
    expect(isRunLive("nesto")).toBe(false);
  });

  it("stanja imaju citljive nazive", () => {
    expect(runLabel("waiting_approval")).toBe("Čeka odobrenje");
    expect(runLabel("done")).toBe("Gotovo");
    expect(runLabel("nesto")).toBe("nesto");
  });
});
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

Pokreni (u `apps/gui`): `npx vitest run src/features/codium/agentRun.test.ts`

- [ ] **Korak 3: Napiši modul**

Nov fajl `apps/gui/src/features/codium/agentRun.ts`:

```ts
// ==========          PRIKAZ POSLA AGENTA          ==========
// Cist modul bez ijednog uvoza — prevod stanja sa servera u ono sto se vidi.

export type StepTone = "thought" | "call" | "result" | "answer" | "blocked";

const TON_PO_VRSTI: Record<string, StepTone> = {
  tool_call: "call",
  tool_result: "result",
  answer: "answer",
  thought: "thought",
};

/** Ton jednog koraka; nepoznata vrsta se crta kao misao, ne kao greska. */
export function stepTone(step: { kind: string; payload: string }): StepTone {
  if (step.kind === "tool_result" && /^(Odbijeno|Ceka odobrenje)/i.test(step.payload)) {
    // Odbijanje i cekanje na coveka nisu obican rezultat alata.
    return "blocked";
  }
  return TON_PO_VRSTI[step.kind] ?? "thought";
}

const NAZIV_STANJA: Record<string, string> = {
  running: "Radi",
  waiting_approval: "Čeka odobrenje",
  done: "Gotovo",
  failed: "Neuspeh",
  cancelled: "Prekinuto",
};

/** Citljiv naziv stanja; nepoznato stanje se prikazuje kakvo jeste. */
export function runLabel(status: string): string {
  return NAZIV_STANJA[status] ?? status;
}

/**
 * Da li posao još traje, pa prikaz treba osvežavati.
 *
 * Nepoznato stanje vraća `false`: greška na serveru bi inače značila poll
 * koji nikad ne prestaje.
 */
export function isRunLive(status: string): boolean {
  return status === "running" || status === "waiting_approval";
}
```

- [ ] **Korak 4: Dodaj tipove**

Na kraj `apps/gui/src/types/codium.ts`:

```ts
// ==========          AGENTI          ==========

export type AgentSummary = {
  id: number;
  slug: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  provider: string;
  tools: string[];
  max_steps: number;
  enabled: boolean;
};

export type AgentsResponse = { count: number; agents: AgentSummary[] };

export type AgentPatch = {
  name?: string;
  description?: string;
  system_prompt?: string;
  model?: string;
  provider?: string;
  tools?: string[];
  max_steps?: number;
  enabled?: boolean;
};

export type AgentTool = {
  name: string;
  description: string;
  action: string;
  args: Record<string, string>;
  writes_content: boolean;
};

export type AgentToolsResponse = { count: number; tools: AgentTool[] };

export type AgentStep = {
  idx: number;
  kind: string;
  tool: string;
  payload: string;
  at: string;
};

export type AgentRunSummary = {
  id: number;
  agent_id: number;
  agent_slug: string;
  project_id: number | null;
  task: string;
  status: string;
  result: string;
  steps_used: number;
  cost_usd: number;
  pending_approval_id: number | null;
  started_at: string;
  finished_at: string | null;
};

export type AgentRunsResponse = { count: number; runs: AgentRunSummary[] };

export type AgentRunResponse = { run: AgentRunSummary; steps: AgentStep[] };

export type AgentRunStarted = { run_id: number };
```

- [ ] **Korak 5: Dodaj pozive**

Na kraj `apps/gui/src/services/codiumApi.ts` (uz dopunjen blok uvoza tipova):

```ts
// ==========          AGENTI          ==========

export function getAgents(): Promise<AgentsResponse> {
  return getJson("/api/v1/codium/agents/");
}

export function updateAgent(
  agentId: number,
  change: AgentPatch,
): Promise<AgentSummary> {
  return patchJson(`/api/v1/codium/agents/${agentId}`, change);
}

export function getAgentTools(): Promise<AgentToolsResponse> {
  return getJson("/api/v1/codium/agents/tools");
}

export function startAgentRun(
  agentId: number,
  task: string,
  projectId: number | null = null,
): Promise<AgentRunStarted> {
  return postJson(`/api/v1/codium/agents/${agentId}/run`, {
    task,
    project_id: projectId,
  });
}

export function getAgentRun(
  runId: number,
  sinceIdx = -1,
): Promise<AgentRunResponse> {
  return getJson(
    `/api/v1/codium/agents/runs/${runId}?since_idx=${sinceIdx}`,
  );
}

export function getAgentRuns(limit = 20): Promise<AgentRunsResponse> {
  return getJson(`/api/v1/codium/agents/runs?limit=${limit}`);
}

export function cancelAgentRun(runId: number): Promise<AgentRunSummary> {
  return postJson(`/api/v1/codium/agents/runs/${runId}/cancel`, {});
}
```

- [ ] **Korak 6: Pokreni test i proveru tipova**

Pokreni (u `apps/gui`): `npx vitest run src/features/codium/agentRun.test.ts`
pa `npx tsc -b tsconfig.app.json`

- [ ] **Korak 7: Commit**

```bash
git add apps/gui/src/types apps/gui/src/services apps/gui/src/features/codium
git commit -F- <<'EOF'
feat(gui): tipovi, pozivi i prikaz koraka agenta

`isRunLive` vraca `false` za nepoznato stanje: greska na serveru bi inace
znacila poll koji nikad ne prestaje.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 8: Strana agenata

**Fajlovi:**
- Pravi: `apps/gui/src/pages/CodiumAgents.tsx`
- Pravi: `apps/gui/src/styles/codium-agents.css`
- Menja: `apps/gui/src/App.tsx`, `apps/gui/src/components/layout/Sidebar.tsx`
- Test: `apps/gui/src/pages/CodiumAgents.test.tsx` (nov)

**Interfejsi:**
- Koristi sve iz Zadatka 7; `relativeTime` iz `features/codium/activity`
- Daje podrazumevani izvoz `CodiumAgents`

- [ ] **Korak 1: Napiši test koji pada**

Nov fajl `apps/gui/src/pages/CodiumAgents.test.tsx`, sa `vi.mock("../services/codiumApi")`.
Testovi:

```tsx
it("prikazuje agenta sa brojem alata", async () => { /* „architect", „2 alata" */ });

it("uz svaki alat pise koju dozvolu trazi", async () => {
  // Covek koji cekira alat mora da vidi sta time otvara.
});

it("pokretanje salje zadatak i prikazuje korake", async () => {
  // startAgentRun pozvan sa tekstom zadatka; koraci iz getAgentRun se crtaju.
});

it("posao koji ceka odobrenje vodi na stranu odobrenja", async () => {
  // Link ka #/codium/access, jer se odluka donosi tamo.
});

it("zavrsen posao prestaje da se osvezava", async () => {
  // Broj poziva getAgentRun se ne uvecava posle statusa `done`.
});
```

Za poslednji test koristi `vi.useFakeTimers()`; zapamti broj poziva posle
`done`, pomeri vreme i tvrdi da se broj nije promenio.

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

Pokreni (u `apps/gui`): `npx vitest run src/pages/CodiumAgents.test.tsx`

- [ ] **Korak 3: Napiši stranu**

Nov fajl `apps/gui/src/pages/CodiumAgents.tsx`:

```tsx
// ==========          AI AGENTS          ==========
// Agent radi u koracima i svaki mu potez prolazi kroz kapiju. Zato uz svaki
// alat u uredjivacu pise koju dozvolu trazi: covek koji cekira alat mora da
// vidi sta time otvara.
import { Bot, Play, ShieldAlert, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { isRunLive, runLabel, stepTone } from "../features/codium/agentRun";
import { relativeTime } from "../features/codium/activity";
import {
  cancelAgentRun,
  getAgentRun,
  getAgentTools,
  getAgents,
  startAgentRun,
  updateAgent,
} from "../services/codiumApi";
import type {
  AgentRunSummary,
  AgentStep,
  AgentSummary,
  AgentTool,
} from "../types/codium";
import "../styles/codium-agents.css";

// Razmak izmedju provera stanja posla. Kratko dovoljno da izgleda zivo,
// dugacko dovoljno da ne tuce server dok model razmislja.
const POLL_MS = 1500;

export default function CodiumAgents() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [tools, setTools] = useState<AgentTool[]>([]);
  const [izabran, setIzabran] = useState<AgentSummary | null>(null);
  const [zadatak, setZadatak] = useState("");
  const [run, setRun] = useState<AgentRunSummary | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [error, setError] = useState("");

  // Poslednji viđen korak — poll trazi samo ono sto jos nije stiglo.
  const poslednjiIdx = useRef(-1);

  const ucitaj = useCallback(async () => {
    try {
      const [spisak, alati] = await Promise.all([getAgents(), getAgentTools()]);
      setAgents(spisak.agents);
      setTools(alati.tools);
      setIzabran((prev) =>
        prev ? spisak.agents.find((a) => a.id === prev.id) ?? prev
             : spisak.agents[0] ?? null,
      );
      setError("");
    } catch {
      setError("Učitavanje agenata nije uspelo.");
    }
  }, []);

  useEffect(() => {
    void ucitaj();
  }, [ucitaj]);

  // ----------          POLL          ----------

  useEffect(() => {
    if (run === null || !isRunLive(run.status)) {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        const sveze = await getAgentRun(run.id, poslednjiIdx.current);
        if (sveze.steps.length > 0) {
          poslednjiIdx.current = sveze.steps[sveze.steps.length - 1].idx;
          setSteps((prev) => [...prev, ...sveze.steps]);
        }
        setRun(sveze.run);
      } catch {
        // Jedan promasen poll nije razlog da se prikaz obori; sledeci ce
        // doneti isto stanje.
      }
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [run]);

  // ----------          RADNJE          ----------

  const promeniAlat = async (ime: string, ukljucen: boolean) => {
    if (izabran === null) {
      return;
    }
    const novi = ukljucen
      ? [...izabran.tools, ime]
      : izabran.tools.filter((t) => t !== ime);
    try {
      const posle = await updateAgent(izabran.id, { tools: novi });
      setIzabran(posle);
      setAgents((prev) => prev.map((a) => (a.id === posle.id ? posle : a)));
    } catch {
      setError("Izmena alata nije uspela.");
    }
  };

  const sacuvajPrompt = async (prompt: string, maxSteps: number) => {
    if (izabran === null) {
      return;
    }
    try {
      const posle = await updateAgent(izabran.id, {
        system_prompt: prompt,
        max_steps: maxSteps,
      });
      setIzabran(posle);
      setAgents((prev) => prev.map((a) => (a.id === posle.id ? posle : a)));
    } catch {
      setError("Čuvanje agenta nije uspelo.");
    }
  };

  const pokreni = async () => {
    if (izabran === null || !zadatak.trim()) {
      return;
    }
    try {
      const { run_id } = await startAgentRun(izabran.id, zadatak.trim());
      poslednjiIdx.current = -1;
      setSteps([]);
      const prvo = await getAgentRun(run_id);
      setSteps(prvo.steps);
      if (prvo.steps.length > 0) {
        poslednjiIdx.current = prvo.steps[prvo.steps.length - 1].idx;
      }
      setRun(prvo.run);
      setError("");
    } catch {
      setError("Pokretanje posla nije uspelo.");
    }
  };

  const prekini = async () => {
    if (run === null) {
      return;
    }
    try {
      setRun(await cancelAgentRun(run.id));
    } catch {
      setError("Prekid nije prošao — možda je posao već završen.");
    }
  };

  // ----------          PRIKAZ          ----------

  return (
    <div className="cag-page">
      <header className="cag-head">
        <p className="cag-eyebrow">CODIUM · AI &amp; Automation</p>
        <h1>AI Agents</h1>
        <p className="cag-sub">
          Agent ima alate, radi u koracima, i svaki potez mu proverava kapija.
        </p>
      </header>

      {error && <p className="cag-error">{error}</p>}

      <div className="cag-grid">
        <section className="cag-panel cag-list">
          <h2>Agenti</h2>
          <ul>
            {agents.map((agent) => (
              <li key={agent.id}>
                <button
                  className={agent.id === izabran?.id ? "is-active" : ""}
                  onClick={() => setIzabran(agent)}
                  type="button"
                >
                  <Bot aria-hidden="true" size={15} />
                  <span className="cag-name">{agent.name}</span>
                  <span className="cag-meta">
                    {agent.model || "nasleđuje iz chata"} ·{" "}
                    {agent.tools.length} alata
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        {izabran && (
          <section className="cag-panel cag-editor">
            <h2>{izabran.name}</h2>

            <label htmlFor="cag-prompt">Sistemski prompt</label>
            <textarea
              id="cag-prompt"
              onChange={(e) =>
                setIzabran({ ...izabran, system_prompt: e.target.value })
              }
              rows={6}
              value={izabran.system_prompt}
            />

            <label htmlFor="cag-steps">Najviše koraka</label>
            <input
              id="cag-steps"
              max={50}
              min={1}
              onChange={(e) =>
                setIzabran({ ...izabran, max_steps: Number(e.target.value) })
              }
              type="number"
              value={izabran.max_steps}
            />

            <button
              onClick={() =>
                void sacuvajPrompt(izabran.system_prompt, izabran.max_steps)
              }
              type="button"
            >
              Sačuvaj
            </button>

            <h3>Alati</h3>
            <ul className="cag-tools">
              {tools.map((alat) => (
                <li key={alat.name}>
                  <label>
                    <input
                      checked={izabran.tools.includes(alat.name)}
                      onChange={(e) =>
                        void promeniAlat(alat.name, e.target.checked)
                      }
                      type="checkbox"
                    />
                    <span className="cag-tool-name">{alat.name}</span>
                  </label>
                  <span className="cag-tool-desc">{alat.description}</span>
                  <span className="cag-tool-action">
                    traži dozvolu <code>{alat.action}</code>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="cag-panel cag-run">
          <h2>Zadatak</h2>
          <textarea
            aria-label="Zadatak za agenta"
            onChange={(e) => setZadatak(e.target.value)}
            placeholder="Analiziraj sloj API-ja i predloži izmenu."
            rows={3}
            value={zadatak}
          />
          <div className="cag-run-actions">
            <button onClick={() => void pokreni()} type="button">
              <Play aria-hidden="true" size={14} /> Pokreni
            </button>
            {run !== null && isRunLive(run.status) && (
              <button onClick={() => void prekini()} type="button">
                <Square aria-hidden="true" size={14} /> Prekini
              </button>
            )}
          </div>

          {run !== null && (
            <>
              <p className={`cag-status s-${run.status}`}>
                {runLabel(run.status)}
                {run.steps_used > 0 && ` · ${run.steps_used} koraka`}
                {run.started_at && ` · ${relativeTime(run.started_at)}`}
              </p>

              {run.status === "waiting_approval" && (
                <p className="cag-approval">
                  <ShieldAlert aria-hidden="true" size={15} />
                  Potez čeka tvoju odluku.{" "}
                  <a href="#/codium/access">Otvori red odobrenja</a>
                </p>
              )}

              <ol className="cag-steps">
                {steps.map((step) => (
                  <li className={`cag-step t-${stepTone(step)}`} key={step.idx}>
                    <span className="cag-step-kind">
                      {step.tool || step.kind}
                    </span>
                    <pre>{step.payload}</pre>
                  </li>
                ))}
              </ol>

              {run.result && <p className="cag-result">{run.result}</p>}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
```

- [ ] **Korak 4: Napiši stil**

Nov fajl `apps/gui/src/styles/codium-agents.css`, u tonu
`codium-access.css` i `codium-dashboard.css`: oštre ivice (`border-radius: 0`),
tamna podloga, tanke linije. Klase koje strana koristi: `.cag-page`,
`.cag-head`, `.cag-eyebrow`, `.cag-sub`, `.cag-error`, `.cag-grid`,
`.cag-panel`, `.cag-list`, `.cag-name`, `.cag-meta`, `.cag-editor`,
`.cag-tools`, `.cag-tool-name`, `.cag-tool-desc`, `.cag-tool-action`,
`.cag-run`, `.cag-run-actions`, `.cag-status` sa varijantama
`s-running` / `s-waiting_approval` / `s-done` / `s-failed` / `s-cancelled`,
`.cag-approval`, `.cag-steps`, `.cag-step` sa tonovima `t-call` / `t-result` /
`t-answer` / `t-blocked` / `t-thought`, `.cag-result`.

Boje prate isto pravilo kao ostatak domena: `s-failed` crveno,
`s-waiting_approval` i `t-blocked` žuto, ostalo neutralno. Čekanje na čoveka
nije greška i ne sme da izgleda kao kvar.

- [ ] **Korak 5: Ruta i sidebar**

U `apps/gui/src/App.tsx`, uz ostale CODIUM rute:

```tsx
        <Route
          path="/codium/agents"
          element={<CodiumAgents />}
        />
```

U `apps/gui/src/components/layout/Sidebar.tsx`, sekcija `AI & AUTOMATION`:

```tsx
        { id: "ai-agents", label: "AI Agents", icon: Bot, kind: "route", path: "/codium/agents" },
```

- [ ] **Korak 6: Pokreni ceo GUI paket i proveru tipova**

Pokreni (u `apps/gui`): `npx vitest run` pa `npx tsc -b tsconfig.app.json`

- [ ] **Korak 7: Commit**

```bash
git add apps/gui/src/pages/CodiumAgents.tsx apps/gui/src/pages/CodiumAgents.test.tsx apps/gui/src/styles/codium-agents.css apps/gui/src/App.tsx apps/gui/src/components/layout/Sidebar.tsx
git commit -F- <<'EOF'
feat(gui): strana agenata sa uredjivacem alata i prikazom koraka

Uz svaki alat pise koju dozvolu trazi: covek koji cekira alat mora da
vidi sta time otvara.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 9: AI Agents panel prestaje da bude mock

**Fajlovi:**
- Menja: `apps/gui/src/pages/CodiumOverview.tsx`
- Menja: `apps/gui/src/styles/codium-dashboard.css`
- Test: `apps/gui/src/pages/CodiumOverview.test.tsx`

**Interfejsi:**
- Koristi: `getAgentRuns`, `runLabel`, `isRunLive`

Ovo je povod za ceo korak. `AI_AGENTS` je poslednja mock konstanta u fajlu:

```tsx
const AI_AGENTS: { name: string; role: string; status: "working" | "idle" }[] = [
  { name: "Architect Agent", role: "Analiza arhitekture sistema", status: "working" },
  ...
];
```

- [ ] **Korak 1: Napiši test koji pada**

Dopuni `CodiumOverview.test.tsx`:

```tsx
it("AI Agents panel prikazuje prave poslove", async () => {
  vi.mocked(api.getAgentRuns).mockResolvedValue({
    count: 1,
    runs: [{
      id: 3, agent_id: 1, agent_slug: "architect", task: "analiziraj api",
      status: "waiting_approval", result: "", steps_used: 2, cost_usd: 0,
      pending_approval_id: 9, started_at: "2026-08-29 10:00:00",
      finished_at: null, project_id: null,
    }],
  });
  // Prikazuje zadatak i citljivo stanje, ne izmisljeno ime agenta.
});

it("bez ijednog posla panel to i kaze", async () => {
  vi.mocked(api.getAgentRuns).mockResolvedValue({ count: 0, runs: [] });
  // „Nijedan agent još nije radio."
});
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

Pokreni (u `apps/gui`): `npx vitest run src/pages/CodiumOverview.test.tsx`

- [ ] **Korak 3: Zameni mock**

U `apps/gui/src/pages/CodiumOverview.tsx`:

1. Ukloni konstantu `AI_AGENTS` u celini.
2. Dopuni uvoze:

```tsx
import { isRunLive, runLabel } from "../features/codium/agentRun";
import { getAgentRuns } from "../services/codiumApi";
import type { AgentRunSummary } from "../types/codium";
```

3. Dodaj stanje i proširi postojeće učitavanje:

```tsx
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
```

U postojećem `Promise.all([...])` dodaj `getAgentRuns(5)` kao poslednji član i
`setRuns(...)` uz ostale `set*` pozive.

4. Zameni telo panela:

```tsx
  const agentsPanel = runs.length === 0 ? (
    <p className="cdash-empty">Nijedan agent još nije radio.</p>
  ) : (
    <ul className="cdash-agents">
      {runs.map((run) => (
        <li className="cdash-agent" key={run.id}>
          <span className="cdash-agent-avatar">
            <Bot size={14} />
          </span>
          <div className="cdash-agent-body">
            <p className="cdash-agent-name">{run.task}</p>
            <p className="cdash-agent-role">
              {run.agent_slug || "agent"} · {run.steps_used} koraka
            </p>
          </div>
          <span
            className={`cdash-agent-status ${
              isRunLive(run.status) ? "working" : "idle"
            } s-${run.status}`}
          >
            {runLabel(run.status)}
          </span>
        </li>
      ))}
    </ul>
  );
```

5. Ukloni `soon: "E9 AI Agents"` sa te kartice.

6. U `apps/gui/src/styles/codium-dashboard.css` dodaj
`.cdash-agent-status.s-waiting_approval` u žutoj i `.s-failed` u crvenoj boji.
Ostala stanja zadržavaju postojeći izgled. Čekanje na čoveka nije greška i ne
sme da izgleda kao kvar.

- [ ] **Korak 4: Pokreni ceo GUI paket i proveru tipova**

Pokreni (u `apps/gui`): `npx vitest run` pa `npx tsc -b tsconfig.app.json`

- [ ] **Korak 5: Provera uživo**

Pokreni API i GUI, pa:

1. `#/codium/agents` — `architect` se vidi, uređivač otvara spisak alata sa
   akcijama.
2. Čekiraj `read_file`, `list_dir`, `search_code` i pokreni zadatak nad pravim
   projektom. Koraci se pojavljuju jedan po jedan.
3. Dodaj `write_file` u alate i zadaj izmenu. Posao staje u `waiting_approval`,
   molba se vidi na `#/codium/access`, fajl je **nepromenjen**.
4. Odobri molbu i potvrdi da posao nastavlja i fajl se menja.
5. `#/codium` — AI Agents panel prikazuje te poslove umesto mock reda.
6. Očisti za sobom: vrati izmenjeni fajl i obriši probna pravila.

Ako lokalni model ne ume da ispoštuje JSON format, to je nalaz — zapiši šta je
vratio, ne prećuti.

- [ ] **Korak 6: Commit**

```bash
git add apps/gui/src/pages/CodiumOverview.tsx apps/gui/src/pages/CodiumOverview.test.tsx apps/gui/src/styles/codium-dashboard.css
git commit -F- <<'EOF'
feat(gui): AI Agents panel prikazuje prave poslove umesto mock redova

Poslednja izmisljena tabla na kontrolnoj tabli. Stanje „ceka odobrenje"
nosi zutu boju: cekanje na coveka nije greska.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Definicija završetka

- `ARCHITECT` se definiše, pokreće, koristi alate za čitanje i vraća plan.
- Svaki korak je zapisan i čitljiv unazad.
- Alat koji menja stanje traži odobrenje, pauzira posao, i posle odluke
  nastavlja ili završava — a fajl se ne dira dok molba čeka.
- Otisak sadržaja koji se ne poklapa obara potez.
- AI Agents panel na kontrolnoj tabli prikazuje prave poslove.
- Ceo pytest i ceo vitest paket prolaze; `npx tsc -b tsconfig.app.json` nema
  nijednu novu grešku.

## Šta ostaje za kasnije

- Nativni tool-calling za Anthropic i OpenAI — sloj ispod petlje, petlja se ne
  menja.
- Alati nad E2 i E3 (`git_log`, `git_diff`, `read_run_log`, `run_pipeline`).
- Alati koji brišu — ulaze kao `deny` po podrazumevanom pravilu iz E1.
- Više agenata od jednog; svaki je unos u tabelu, ne nov modul.
