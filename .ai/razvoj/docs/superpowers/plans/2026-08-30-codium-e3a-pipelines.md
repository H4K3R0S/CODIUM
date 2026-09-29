---
id: codium-61ed0935-2026-08-30-codium-e3a-pipelines-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: E3a Pipelines — plan izvođenja
summary: '> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
  (recommended) or superpowers:executing-plans to implement this plan t'
keywords:
- e3a
- pipelines
- izvođenja
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-30-codium-e3a-pipelines.md
edges:
- type: references
  target: core-aeff2a12-2026-08-30-codium-e3a-pipelines-design-md
  weight: 0.3
---

# E3a Pipelines — plan izvođenja

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CODIUM dobija sopstveni lokalni runner — niz komandi se definiše u JSON-u, pokreće nad registrovanim repozitorijumom, pamti svako pokretanje i čuva pun log.

**Architecture:** Novi paket `core/domains/codium/pipelines/` po obrascu enterprise trake. `definition.py` je čist parser bez ulaza/izlaza; `runner.py` je motor koji prima `RunStore` i `LogSink` kao protokole, pa se testira bez baze i bez čekanja; `sinks.py` drži serijski upis; `service.py` je jedino mesto koje zove kapiju i dnevnik. Ispod stoje dve migracije — poslovne tabele u `codium.db` (v11), append-heavy log u `codium_ops.db` (ops v3).

**Tech Stack:** Python 3.14, `asyncio.create_subprocess_shell`, FastAPI, SQLite (dve baze), pytest.

**Spec:** [docs/superpowers/specs/2026-08-30-codium-e3a-pipelines-design.md](../specs/2026-08-30-codium-e3a-pipelines-design.md)

## Global Constraints

- **Jezik.** Kod i identifikatori na engleskom; komentari, docstring-ovi, UI stringovi i dokumentacija na srpskom.
- **Veličina fajla.** 150–300 linija je cilj; preko 500 razmotriti podelu.
- **Nema nove Python biblioteke.** Definicije su JSON, ne YAML, upravo zato — `PyYAML` se ne uvodi.
- **Provera putanje se ne piše iznova.** `working_dir` se proverava kroz `CodiumExplorer._safe(rel)` iz `core/domains/codium/explorer.py`.
- **Audit.** Svaka mutacija u servisu zove `AuditRepository.record(...)`.
- **ScopeGate.** `pipeline.run` prolazi `ScopeGate.check(...)` PRE pokretanja. Odbijeno znači da se ne pokreće ništa, ali sa tragom.
- **`_DEFAULTS` u `core/security/scope_gate.py` se ne dira.** Nova pravila idu u migraciju.
- **Bez WebSocket-a.** Live log je polling `logs?after_seq=`.
- **Tajne su van dometa.** `${{ ... }}` se ne parsira, ne razrešava i ne maskira. Ulazi sa E4.
- **Motor ne piše u bazu direktno.** Piše kroz ubrizgan `LogSink` i `RunStore`.
- **Gašenje gasi celo stablo procesa**, obrascem koji `core/domains/codium/dev_server.py::_terminate_tree` već koristi.
- **Testovi backend-a:** `./.venv/Scripts/python.exe -m pytest` iz korena repozitorijuma — ne sistemski `python`.
- **Van dometa:** ekran i Monaco uređivač (E3b), okidači osim ručnog (E10), pokretanje koje preživljava gašenje aplikacije.

---

### Task 1: Modeli i parser definicije

**Files:**
- Create: `core/domains/codium/pipelines/__init__.py`
- Create: `core/domains/codium/pipelines/models.py`
- Create: `core/domains/codium/pipelines/definition.py`
- Test: `tests/test_pipeline_definition.py`

**Interfaces:**
- Consumes: `CodiumExplorer` i `ExplorerError` iz `core/domains/codium/explorer.py`.
- Produces:
  - `RunStatus` (StrEnum): `QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELLED`, `TIMEOUT`
  - `StepStatus` (StrEnum): `QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, `SKIPPED`
  - `Pipeline(id, repository_id, name, definition, enabled, created_at, updated_at)`
  - `PipelineRun(id, pipeline_id, status, trigger, commit_sha, branch, exit_code, detail, started_at, finished_at, created_at)`
  - `RunStep(id, run_id, idx, name, status, exit_code, started_at, finished_at)`
  - `RunLogLine(run_id, step_idx, seq, stream, line, at="", id=None)`
  - `StepDefinition(name, run, working_dir="", continue_on_error=False)`
  - `PipelineDefinition(name, steps, timeout_minutes=20, env=dict)`
  - `DefinitionError(ValueError)`
  - `parse(text: str, root: Path | None = None) -> PipelineDefinition`

- [ ] **Step 1: Napiši test koji pada**

`tests/test_pipeline_definition.py`:

```python
# ========== TESTOVI: parser definicije pipeline-a ==========
# Cist modul — nijedan test ovde ne dodiruje bazu ni podproces.
from __future__ import annotations

import json

import pytest

from core.domains.codium.pipelines.definition import DefinitionError, parse
from core.domains.codium.pipelines.models import StepDefinition

ISPRAVNA = {
    "name": "test-i-build",
    "timeout_minutes": 20,
    "env": {"CI": "1"},
    "steps": [
        {"name": "instalacija", "run": "npm ci"},
        {"name": "lint", "run": "npm run lint", "continue_on_error": True},
        {"name": "build", "run": "npm run build", "working_dir": "apps/gui"},
    ],
}


def test_ispravna_definicija_se_parsira():
    definicija = parse(json.dumps(ISPRAVNA))
    assert definicija.name == "test-i-build"
    assert definicija.timeout_minutes == 20
    assert definicija.env == {"CI": "1"}
    assert len(definicija.steps) == 3
    assert definicija.steps[0] == StepDefinition(name="instalacija", run="npm ci")
    assert definicija.steps[1].continue_on_error is True
    assert definicija.steps[2].working_dir == "apps/gui"


def test_podrazumevane_vrednosti():
    definicija = parse(json.dumps({
        "name": "minimalna",
        "steps": [{"name": "jedan", "run": "echo zdravo"}],
    }))
    assert definicija.timeout_minutes == 20
    assert definicija.env == {}
    assert definicija.steps[0].continue_on_error is False
    assert definicija.steps[0].working_dir == ""


def test_neispravan_json_daje_urednu_gresku():
    with pytest.raises(DefinitionError) as greska:
        parse("{ ovo nije json")
    assert "JSON" in str(greska.value)


def test_prazno_ime_pada():
    with pytest.raises(DefinitionError) as greska:
        parse(json.dumps({"name": "  ", "steps": [{"name": "a", "run": "b"}]}))
    assert "name" in str(greska.value)


def test_prazna_lista_koraka_pada():
    with pytest.raises(DefinitionError) as greska:
        parse(json.dumps({"name": "prazna", "steps": []}))
    assert "steps" in str(greska.value)


def test_korak_bez_run_polja_pada():
    with pytest.raises(DefinitionError) as greska:
        parse(json.dumps({"name": "x", "steps": [{"name": "bez komande"}]}))
    assert "run" in str(greska.value)


def test_nepozitivan_timeout_pada():
    with pytest.raises(DefinitionError) as greska:
        parse(json.dumps({
            "name": "x", "timeout_minutes": 0,
            "steps": [{"name": "a", "run": "b"}],
        }))
    assert "timeout_minutes" in str(greska.value)


def test_env_vrednost_koja_nije_tekst_pada():
    with pytest.raises(DefinitionError) as greska:
        parse(json.dumps({
            "name": "x", "env": {"CI": 1},
            "steps": [{"name": "a", "run": "b"}],
        }))
    assert "env" in str(greska.value)


def test_working_dir_unutar_korena_prolazi(tmp_path):
    (tmp_path / "apps" / "gui").mkdir(parents=True)
    definicija = parse(json.dumps({
        "name": "x",
        "steps": [{"name": "a", "run": "b", "working_dir": "apps/gui"}],
    }), root=tmp_path)
    assert definicija.steps[0].working_dir == "apps/gui"


def test_working_dir_koji_izlazi_iz_korena_pada(tmp_path):
    with pytest.raises(DefinitionError) as greska:
        parse(json.dumps({
            "name": "x",
            "steps": [{"name": "a", "run": "b", "working_dir": "../tudje"}],
        }), root=tmp_path)
    assert "working_dir" in str(greska.value)


def test_bez_korena_se_working_dir_ne_proverava():
    # Snimanje definicije pre nego sto se zna repozitorijum mora da prodje;
    # proveru radi servis, koji koren zna.
    definicija = parse(json.dumps({
        "name": "x",
        "steps": [{"name": "a", "run": "b", "working_dir": "../tudje"}],
    }))
    assert definicija.steps[0].working_dir == "../tudje"
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_definition.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: No module named 'core.domains.codium.pipelines'`.

- [ ] **Step 3: Napiši modele**

`core/domains/codium/pipelines/models.py`:

```python
# ========== MODELI PIPELINE-A ==========
# Oblici kroz koje podaci putuju od motora do baze i do API-ja.
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RunStatus(StrEnum):
    """Stanje jednog pokretanja."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class StepStatus(StrEnum):
    """Stanje jednog koraka.

    `SKIPPED` postoji da bi se korak koji nije stigao na red posle prekida
    razlikovao od koraka koji nikad nije ni krenuo.
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class StepDefinition:
    """Jedan korak iz JSON definicije."""

    name: str
    run: str
    working_dir: str = ""
    continue_on_error: bool = False


@dataclass(frozen=True)
class PipelineDefinition:
    """Cela definicija, posle parsiranja i provere."""

    name: str
    steps: tuple[StepDefinition, ...]
    timeout_minutes: int = 20
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Pipeline:
    """Red iz `codium_pipelines`."""

    repository_id: int
    name: str
    definition: str
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class PipelineRun:
    """Red iz `codium_pipeline_runs`."""

    pipeline_id: int
    status: str = RunStatus.QUEUED
    trigger: str = "manual"
    commit_sha: str | None = None
    branch: str | None = None
    exit_code: int | None = None
    # Zasto je pokretanje zavrsilo bas tako: „istek", „aplikacija zatvorena".
    detail: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class RunStep:
    """Red iz `codium_run_steps`."""

    run_id: int
    idx: int
    name: str
    status: str = StepStatus.QUEUED
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class RunLogLine:
    """Jedan red loga. `seq` je monoton po pokretanju, ne po koraku."""

    run_id: int
    step_idx: int
    seq: int
    stream: str
    line: str
    at: str = ""
    id: int | None = None
```

- [ ] **Step 4: Napiši parser**

`core/domains/codium/pipelines/definition.py`:

```python
# ========== PARSER DEFINICIJE ==========
# Cist modul: ulaz je tekst, izlaz je `PipelineDefinition` ili uredna greska.
# Bez baze, bez podprocesa, bez mreze — zato je i najlaksi za testiranje.
from __future__ import annotations

import json
from pathlib import Path

from core.domains.codium.explorer import CodiumExplorer, ExplorerError
from core.domains.codium.pipelines.models import PipelineDefinition, StepDefinition

PODRAZUMEVAN_TIMEOUT = 20


class DefinitionError(ValueError):
    """Definicija nije ispravna. Poruka kaze koje polje i zasto."""


def _tekst(vrednost: object, polje: str) -> str:
    if not isinstance(vrednost, str) or not vrednost.strip():
        raise DefinitionError(f"Polje `{polje}` mora biti neprazan tekst.")
    return vrednost.strip()


def _proveri_working_dir(root: Path, rel: str) -> None:
    """Brani izlazak iz korena repozitorijuma.

    Provera se NE pise iznova: `CodiumExplorer._safe` je vec brani za
    Explorer, a dve provere putanje znace dva mesta na kojima se gresi.
    """

    try:
        CodiumExplorer(root)._safe(rel)  # noqa: SLF001 — namerno deljena provera
    except ExplorerError as greska:
        raise DefinitionError(
            f"Polje `working_dir` izlazi iz korena repozitorijuma: {rel}"
        ) from greska


def _korak(sirovi: object, redni: int, root: Path | None) -> StepDefinition:
    if not isinstance(sirovi, dict):
        raise DefinitionError(f"Korak {redni} nije objekat.")

    ime = _tekst(sirovi.get("name"), f"steps[{redni}].name")
    komanda = _tekst(sirovi.get("run"), f"steps[{redni}].run")

    radni = sirovi.get("working_dir", "")
    if not isinstance(radni, str):
        raise DefinitionError(f"Polje `steps[{redni}].working_dir` mora biti tekst.")
    if radni and root is not None:
        _proveri_working_dir(root, radni)

    nastavi = sirovi.get("continue_on_error", False)
    if not isinstance(nastavi, bool):
        raise DefinitionError(
            f"Polje `steps[{redni}].continue_on_error` mora biti tacno ili netacno."
        )

    return StepDefinition(name=ime, run=komanda, working_dir=radni,
                          continue_on_error=nastavi)


def parse(text: str, root: Path | None = None) -> PipelineDefinition:
    """Cita JSON definiciju i proverava je.

    Args:
        text: JSON tekst definicije.
        root: Koren repozitorijuma. Kad je zadat, `working_dir` se proverava
            protiv njega. Bez njega se ta provera preskace — definicija sme
            da se snimi i pre nego sto se zna nad cim se pokrece.
    """

    try:
        sirovo = json.loads(text)
    except json.JSONDecodeError as greska:
        raise DefinitionError(f"Definicija nije ispravan JSON: {greska}") from greska

    if not isinstance(sirovo, dict):
        raise DefinitionError("Definicija mora biti JSON objekat.")

    ime = _tekst(sirovo.get("name"), "name")

    koraci_sirovi = sirovo.get("steps")
    if not isinstance(koraci_sirovi, list) or not koraci_sirovi:
        raise DefinitionError("Polje `steps` mora biti neprazna lista.")

    timeout = sirovo.get("timeout_minutes", PODRAZUMEVAN_TIMEOUT)
    # `bool` je podtip `int` u Python-u; bez ove provere `true` prolazi kao 1.
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise DefinitionError("Polje `timeout_minutes` mora biti pozitivan ceo broj.")

    okruzenje = sirovo.get("env", {})
    if not isinstance(okruzenje, dict):
        raise DefinitionError("Polje `env` mora biti objekat.")
    for kljuc, vrednost in okruzenje.items():
        if not isinstance(kljuc, str) or not isinstance(vrednost, str):
            raise DefinitionError(
                "Polje `env` sme da drzi samo tekst kao kljuc i kao vrednost."
            )

    koraci = tuple(_korak(sirovi, redni, root)
                   for redni, sirovi in enumerate(koraci_sirovi))

    return PipelineDefinition(name=ime, steps=koraci, timeout_minutes=timeout,
                              env=dict(okruzenje))
```

`core/domains/codium/pipelines/__init__.py`:

```python
from core.domains.codium.pipelines.definition import DefinitionError, parse
from core.domains.codium.pipelines.models import (
    Pipeline,
    PipelineDefinition,
    PipelineRun,
    RunLogLine,
    RunStatus,
    RunStep,
    StepDefinition,
    StepStatus,
)

__all__ = [
    "DefinitionError", "Pipeline", "PipelineDefinition", "PipelineRun",
    "RunLogLine", "RunStatus", "RunStep", "StepDefinition", "StepStatus",
    "parse",
]
```

- [ ] **Step 5: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_definition.py -v
```

Očekivano: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/domains/codium/pipelines tests/test_pipeline_definition.py
git commit -m "feat(codium): modeli i parser definicije pipeline-a"
```

---

### Task 2: Migracije i SQL sloj

**Files:**
- Modify: `core/domains/codium/migrations.py` (`CODIUM_MIGRATION_V11` + unos u `CODIUM_MIGRATIONS`)
- Modify: `core/domains/codium/ops_migrations.py` (`CODIUM_OPS_MIGRATION_V3` + unos u `CODIUM_OPS_MIGRATIONS`)
- Create: `core/domains/codium/pipelines/repository.py`
- Create: `core/domains/codium/pipelines/log_repository.py`
- Modify: `core/domains/codium/pipelines/__init__.py`
- Test: `tests/test_pipeline_repository.py`

**Interfaces:**
- Consumes: modeli iz Task-a 1.
- Produces:
  - `PipelineRepository(database_path)` sa `add(pipeline) -> Pipeline`, `list(repository_id=None) -> list[Pipeline]`, `get(pipeline_id) -> Pipeline | None`, `get_by_name(repository_id, name) -> Pipeline | None`, `update_definition(pipeline_id, name, definition) -> Pipeline`, `delete(pipeline_id) -> None`
  - `RunRepository(database_path)` sa `create(run, step_names) -> PipelineRun`, `get(run_id) -> PipelineRun | None`, `list(pipeline_id=None, status=None, limit=50) -> list[PipelineRun]`, `steps(run_id) -> list[RunStep]`, `mark_run_started(run_id)`, `mark_run_finished(run_id, status, exit_code, detail)`, `mark_step_started(run_id, idx)`, `mark_step_finished(run_id, idx, status, exit_code)`, `stale_running() -> list[int]`, `older_run_ids(pipeline_id, keep) -> list[int]`
  - `RunLogRepository(database_path)` sa `append(lines: list[RunLogLine]) -> None`, `read(run_id, after_seq=0, limit=1000) -> list[RunLogLine]`, `delete_for_runs(run_ids: list[int]) -> None`

- [ ] **Step 1: Napiši test koji pada**

`tests/test_pipeline_repository.py`:

```python
# ========== TESTOVI: SQL sloj pipeline-a ==========
from __future__ import annotations

import pytest

from core.database import core_database_connection
from core.domains.codium.pipelines.log_repository import RunLogRepository
from core.domains.codium.pipelines.models import (
    Pipeline,
    PipelineRun,
    RunLogLine,
    RunStatus,
    StepStatus,
)
from core.domains.codium.pipelines.repository import PipelineRepository, RunRepository
from core.domains.codium.repositories import Repository
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)


@pytest.fixture
def poslovna(tmp_path):
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    # Pipeline trazi repozitorijum: strani kljuc je NOT NULL i FK je ukljucen.
    RepositoryRepository(baza).add(Repository(name="core", local_path="C:/kod/core"))
    return baza


@pytest.fixture
def operativna(tmp_path):
    baza = tmp_path / "codium_ops.db"
    initialize_codium_ops_database(baza)
    return baza


def _pipeline(baza, ime="test") -> Pipeline:
    return PipelineRepository(baza).add(Pipeline(
        repository_id=1, name=ime,
        definition='{"name": "x", "steps": [{"name": "a", "run": "b"}]}',
    ))


def test_upisan_pipeline_se_cita_nazad(poslovna):
    upisan = _pipeline(poslovna)
    assert upisan.id is not None
    svi = PipelineRepository(poslovna).list(repository_id=1)
    assert [p.name for p in svi] == ["test"]


def test_get_by_name_nalazi_i_promasuje(poslovna):
    _pipeline(poslovna, "build")
    registar = PipelineRepository(poslovna)
    assert registar.get_by_name(1, "build") is not None
    assert registar.get_by_name(1, "nema") is None


def test_izmena_definicije_menja_ime_i_tekst(poslovna):
    upisan = _pipeline(poslovna)
    izmenjen = PipelineRepository(poslovna).update_definition(
        upisan.id, "novo-ime", '{"name": "novo-ime", "steps": []}',
    )
    assert izmenjen.name == "novo-ime"
    assert "novo-ime" in izmenjen.definition


def test_brisanje_pipeline_a_brise_i_pokretanja(poslovna):
    upisan = _pipeline(poslovna)
    pokretanja = RunRepository(poslovna)
    pokretanja.create(PipelineRun(pipeline_id=upisan.id), ["a", "b"])
    PipelineRepository(poslovna).delete(upisan.id)
    assert pokretanja.list(pipeline_id=upisan.id) == []


def test_create_pravi_i_korake_po_redosledu(poslovna):
    upisan = _pipeline(poslovna)
    pokretanja = RunRepository(poslovna)
    run = pokretanja.create(PipelineRun(pipeline_id=upisan.id),
                            ["instalacija", "testovi"])
    koraci = pokretanja.steps(run.id)
    assert [(k.idx, k.name, k.status) for k in koraci] == [
        (0, "instalacija", StepStatus.QUEUED),
        (1, "testovi", StepStatus.QUEUED),
    ]


def test_oznacavanje_kraja_upisuje_status_kod_i_razlog(poslovna):
    upisan = _pipeline(poslovna)
    pokretanja = RunRepository(poslovna)
    run = pokretanja.create(PipelineRun(pipeline_id=upisan.id), ["a"])
    pokretanja.mark_run_started(run.id)
    pokretanja.mark_run_finished(run.id, RunStatus.TIMEOUT, None, "istek od 1 min")

    posle = pokretanja.get(run.id)
    assert posle.status == RunStatus.TIMEOUT
    assert posle.detail == "istek od 1 min"
    assert posle.started_at is not None
    assert posle.finished_at is not None


def test_stale_running_vraca_samo_zaostala(poslovna):
    upisan = _pipeline(poslovna)
    pokretanja = RunRepository(poslovna)
    prvo = pokretanja.create(PipelineRun(pipeline_id=upisan.id), ["a"])
    drugo = pokretanja.create(PipelineRun(pipeline_id=upisan.id), ["a"])
    pokretanja.mark_run_started(prvo.id)
    pokretanja.mark_run_started(drugo.id)
    pokretanja.mark_run_finished(drugo.id, RunStatus.SUCCESS, 0, "")

    assert pokretanja.stale_running() == [prvo.id]


def test_older_run_ids_vraca_ono_izvan_poslednjih_n(poslovna):
    upisan = _pipeline(poslovna)
    pokretanja = RunRepository(poslovna)
    napravljena = [pokretanja.create(PipelineRun(pipeline_id=upisan.id), ["a"]).id
                   for _ in range(5)]
    # Zadrzi poslednja dva; prva tri su „starija".
    assert sorted(pokretanja.older_run_ids(upisan.id, keep=2)) == sorted(napravljena[:3])


def test_log_se_cita_od_zadatog_seq(operativna):
    dnevnik = RunLogRepository(operativna)
    dnevnik.append([
        RunLogLine(run_id=7, step_idx=0, seq=1, stream="stdout", line="prvi"),
        RunLogLine(run_id=7, step_idx=0, seq=2, stream="stderr", line="drugi"),
        RunLogLine(run_id=7, step_idx=1, seq=3, stream="stdout", line="treci"),
    ])
    assert [r.line for r in dnevnik.read(7)] == ["prvi", "drugi", "treci"]
    assert [r.line for r in dnevnik.read(7, after_seq=2)] == ["treci"]
    assert dnevnik.read(8) == []


def test_brisanje_loga_za_pokretanja(operativna):
    dnevnik = RunLogRepository(operativna)
    dnevnik.append([RunLogLine(run_id=1, step_idx=0, seq=1, stream="stdout", line="a")])
    dnevnik.append([RunLogLine(run_id=2, step_idx=0, seq=1, stream="stdout", line="b")])
    dnevnik.delete_for_runs([1])
    assert dnevnik.read(1) == []
    assert [r.line for r in dnevnik.read(2)] == ["b"]


def test_migracija_v11_upisuje_pravila_kapije(poslovna):
    with core_database_connection(poslovna) as veza:
        redovi = veza.execute(
            "SELECT action, verdict FROM codium_scope_rules "
            "WHERE action LIKE 'pipeline.%' ORDER BY action"
        ).fetchall()
    assert [(r[0], r[1]) for r in redovi] == [
        ("pipeline.run", "needs_approval"),
        ("pipeline.write", "deny"),
    ]
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_repository.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: ... pipelines.repository`.

- [ ] **Step 3: Napiši migraciju poslovne baze**

U `core/domains/codium/migrations.py`, iza `CODIUM_MIGRATION_V10`:

```python
# ---------- v11: pipeline-i, pokretanja i koraci ----------

CODIUM_MIGRATION_V11 = DatabaseMigration(
    scope="codium",
    version=11,
    name="pipelines",
    statements=(
        """
        CREATE TABLE codium_pipelines (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            repository_id INTEGER NOT NULL
                          REFERENCES codium_repositories (id) ON DELETE CASCADE,
            name          TEXT NOT NULL,
            definition    TEXT NOT NULL,
            enabled       INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # `detail` nosi zasto je pokretanje zavrsilo bas tako. Bez njega se
        # „istek" i „aplikacija zatvorena" ne razlikuju od obicnog pada.
        """
        CREATE TABLE codium_pipeline_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_id INTEGER NOT NULL
                        REFERENCES codium_pipelines (id) ON DELETE CASCADE,
            status      TEXT NOT NULL DEFAULT 'queued',
            trigger     TEXT NOT NULL DEFAULT 'manual',
            commit_sha  TEXT,
            branch      TEXT,
            exit_code   INTEGER,
            detail      TEXT NOT NULL DEFAULT '',
            started_at  TEXT,
            finished_at TEXT,
            created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX idx_codium_runs_pipeline "
        "ON codium_pipeline_runs (pipeline_id, id DESC)",
        """
        CREATE TABLE codium_run_steps (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL
                        REFERENCES codium_pipeline_runs (id) ON DELETE CASCADE,
            idx         INTEGER NOT NULL,
            name        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'queued',
            exit_code   INTEGER,
            started_at  TEXT,
            finished_at TEXT
        )
        """,
        "CREATE INDEX idx_codium_run_steps_run ON codium_run_steps (run_id, idx)",
        # Glagol `run` i inace pada na needs_approval u `_DEFAULTS`, ali
        # izricito pravilo nosi razlog u dnevniku umesto „podrazumevano".
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'pipeline.run', '*', 'needs_approval',
                'agent pokrece tudje komande — covek odobrava')
        """,
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'pipeline.write', '*', 'deny',
                'definiciju pipeline-a pise covek')
        """,
    ),
)
```

I dodaj `CODIUM_MIGRATION_V11,` na kraj torke `CODIUM_MIGRATIONS`.

- [ ] **Step 4: Napiši migraciju operativne baze**

U `core/domains/codium/ops_migrations.py`, iza `CODIUM_OPS_MIGRATION_V2`:

```python
# ---------- ops v3: log pokretanja ----------

CODIUM_OPS_MIGRATION_V3 = DatabaseMigration(
    scope="codium_ops",
    version=3,
    name="create_run_logs",
    statements=(
        # Bez stranog kljuca: `run_id` pokazuje na red u drugoj bazi.
        # Ciscenje posle brisanja pokretanja radi servis, ne kaskada.
        """
        CREATE TABLE codium_run_logs (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id   INTEGER NOT NULL,
            step_idx INTEGER NOT NULL,
            seq      INTEGER NOT NULL,
            stream   TEXT NOT NULL DEFAULT 'stdout',
            line     TEXT NOT NULL,
            at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX idx_codium_run_logs_seq ON codium_run_logs (run_id, seq)",
    ),
)
```

I dodaj `CODIUM_OPS_MIGRATION_V3,` na kraj torke `CODIUM_OPS_MIGRATIONS`.

- [ ] **Step 5: Napiši SQL sloj poslovne baze**

`core/domains/codium/pipelines/repository.py`:

```python
# ========== SQL SLOJ PIPELINE-A ==========
# Samo redovi. Kapija, dnevnik i pokretanje procesa su u servisu i motoru.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.pipelines.models import (
    Pipeline,
    PipelineRun,
    RunStatus,
    RunStep,
    StepStatus,
)
from core.domains.codium.runtime import codium_database_path

_PIPELINE_KOLONE = ("id, repository_id, name, definition, enabled, "
                    "created_at, updated_at")
_RUN_KOLONE = ("id, pipeline_id, status, trigger, commit_sha, branch, "
               "exit_code, detail, started_at, finished_at, created_at")
_STEP_KOLONE = ("id, run_id, idx, name, status, exit_code, started_at, "
                "finished_at")


def _u_pipeline(row) -> Pipeline:
    return Pipeline(id=row[0], repository_id=row[1], name=row[2],
                    definition=row[3], enabled=bool(row[4]),
                    created_at=row[5], updated_at=row[6])


def _u_run(row) -> PipelineRun:
    return PipelineRun(id=row[0], pipeline_id=row[1], status=row[2],
                       trigger=row[3], commit_sha=row[4], branch=row[5],
                       exit_code=row[6], detail=row[7], started_at=row[8],
                       finished_at=row[9], created_at=row[10])


def _u_step(row) -> RunStep:
    return RunStep(id=row[0], run_id=row[1], idx=row[2], name=row[3],
                   status=row[4], exit_code=row[5], started_at=row[6],
                   finished_at=row[7])


class PipelineRepository:
    """Definicije pipeline-a."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, pipeline: Pipeline) -> Pipeline:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_pipelines (repository_id, name, definition, "
                "enabled) VALUES (?, ?, ?, ?)",
                (pipeline.repository_id, pipeline.name, pipeline.definition,
                 int(pipeline.enabled)),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self, repository_id: int | None = None) -> list[Pipeline]:
        uslov = " WHERE repository_id = ?" if repository_id is not None else ""
        parametri = (repository_id,) if repository_id is not None else ()
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_PIPELINE_KOLONE} FROM codium_pipelines{uslov} "
                "ORDER BY id",
                parametri,
            ).fetchall()
        return [_u_pipeline(red) for red in redovi]

    def get(self, pipeline_id: int) -> Pipeline | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_PIPELINE_KOLONE} FROM codium_pipelines WHERE id = ?",
                (pipeline_id,),
            ).fetchone()
        return _u_pipeline(red) if red else None

    def get_by_name(self, repository_id: int, name: str) -> Pipeline | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_PIPELINE_KOLONE} FROM codium_pipelines "
                "WHERE repository_id = ? AND name = ?",
                (repository_id, name),
            ).fetchone()
        return _u_pipeline(red) if red else None

    def update_definition(self, pipeline_id: int, name: str,
                          definition: str) -> Pipeline:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_pipelines SET name = ?, definition = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, definition, pipeline_id),
            )
        return self.get(pipeline_id)

    def delete(self, pipeline_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute("DELETE FROM codium_pipelines WHERE id = ?",
                         (pipeline_id,))


class RunRepository:
    """Pokretanja i njihovi koraci."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def create(self, run: PipelineRun, step_names: list[str]) -> PipelineRun:
        """Upisuje pokretanje i sve njegove korake u stanju `queued`."""

        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_pipeline_runs (pipeline_id, status, "
                "trigger, commit_sha, branch) VALUES (?, ?, ?, ?, ?)",
                (run.pipeline_id, str(run.status), run.trigger,
                 run.commit_sha, run.branch),
            )
            novi_id = kursor.lastrowid
            veza.executemany(
                "INSERT INTO codium_run_steps (run_id, idx, name) "
                "VALUES (?, ?, ?)",
                [(novi_id, redni, ime) for redni, ime in enumerate(step_names)],
            )
        return self.get(novi_id)

    def get(self, run_id: int) -> PipelineRun | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_pipeline_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return _u_run(red) if red else None

    def list(self, pipeline_id: int | None = None, status: str | None = None,
             limit: int = 50) -> list[PipelineRun]:
        uslovi: list[str] = []
        parametri: list[object] = []
        if pipeline_id is not None:
            uslovi.append("pipeline_id = ?")
            parametri.append(pipeline_id)
        if status is not None:
            uslovi.append("status = ?")
            parametri.append(str(status))
        where = f" WHERE {' AND '.join(uslovi)}" if uslovi else ""
        parametri.append(limit)

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_pipeline_runs{where} "
                "ORDER BY id DESC LIMIT ?",
                tuple(parametri),
            ).fetchall()
        return [_u_run(red) for red in redovi]

    def steps(self, run_id: int) -> list[RunStep]:
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_STEP_KOLONE} FROM codium_run_steps "
                "WHERE run_id = ? ORDER BY idx",
                (run_id,),
            ).fetchall()
        return [_u_step(red) for red in redovi]

    # ----------          OZNACAVANJE STANJA          ----------

    def mark_run_started(self, run_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_pipeline_runs SET status = ?, "
                "started_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(RunStatus.RUNNING), run_id),
            )

    def mark_run_finished(self, run_id: int, status: str,
                          exit_code: int | None, detail: str = "") -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_pipeline_runs SET status = ?, exit_code = ?, "
                "detail = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(status), exit_code, detail, run_id),
            )

    def mark_step_started(self, run_id: int, idx: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_run_steps SET status = ?, "
                "started_at = CURRENT_TIMESTAMP WHERE run_id = ? AND idx = ?",
                (str(StepStatus.RUNNING), run_id, idx),
            )

    def mark_step_finished(self, run_id: int, idx: int, status: str,
                           exit_code: int | None = None) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_run_steps SET status = ?, exit_code = ?, "
                "finished_at = CURRENT_TIMESTAMP WHERE run_id = ? AND idx = ?",
                (str(status), exit_code, run_id, idx),
            )

    # ----------          ODRZAVANJE          ----------

    def stale_running(self) -> list[int]:
        """Pokretanja zatecena u `running` — posle restarta su zaostala."""

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                "SELECT id FROM codium_pipeline_runs WHERE status = ? "
                "ORDER BY id",
                (str(RunStatus.RUNNING),),
            ).fetchall()
        return [red[0] for red in redovi]

    def older_run_ids(self, pipeline_id: int, keep: int) -> list[int]:
        """Pokretanja izvan poslednjih `keep` za taj pipeline."""

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                "SELECT id FROM codium_pipeline_runs WHERE pipeline_id = ? "
                "AND id NOT IN (SELECT id FROM codium_pipeline_runs "
                "WHERE pipeline_id = ? ORDER BY id DESC LIMIT ?)",
                (pipeline_id, pipeline_id, keep),
            ).fetchall()
        return [red[0] for red in redovi]
```

- [ ] **Step 6: Napiši SQL sloj operativne baze**

`core/domains/codium/pipelines/log_repository.py`:

```python
# ========== SQL SLOJ LOGA ==========
# Odvojen fajl jer je odvojena baza: `codium_ops.db` raste hiljadama redova
# po pokretanju i ne sme da zakljucava poslovnu bazu.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.pipelines.models import RunLogLine
from core.domains.codium.runtime import codium_ops_database_path


class RunLogRepository:
    """Upis i citanje redova loga."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_ops_database_path()

    def append(self, lines: list[RunLogLine]) -> None:
        """Upisuje seriju redova u jednoj transakciji."""

        if not lines:
            return
        with core_database_connection(self._database_path) as veza:
            veza.executemany(
                "INSERT INTO codium_run_logs (run_id, step_idx, seq, stream, "
                "line) VALUES (?, ?, ?, ?, ?)",
                [(red.run_id, red.step_idx, red.seq, red.stream, red.line)
                 for red in lines],
            )

    def read(self, run_id: int, after_seq: int = 0,
             limit: int = 1000) -> list[RunLogLine]:
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                "SELECT id, run_id, step_idx, seq, stream, line, at "
                "FROM codium_run_logs WHERE run_id = ? AND seq > ? "
                "ORDER BY seq LIMIT ?",
                (run_id, after_seq, limit),
            ).fetchall()
        return [
            RunLogLine(id=red[0], run_id=red[1], step_idx=red[2], seq=red[3],
                       stream=red[4], line=red[5], at=red[6])
            for red in redovi
        ]

    def delete_for_runs(self, run_ids: list[int]) -> None:
        if not run_ids:
            return
        mesta = ", ".join("?" for _ in run_ids)
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                f"DELETE FROM codium_run_logs WHERE run_id IN ({mesta})",
                tuple(run_ids),
            )
```

Dopuni `core/domains/codium/pipelines/__init__.py` sa `PipelineRepository`, `RunRepository`, `RunLogRepository` i dodaj ih u `__all__`.

- [ ] **Step 7: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_repository.py -v
```

Očekivano: PASS.

- [ ] **Step 8: Pokreni ceo CODIUM skup da migracije ne obore postojeće**

```bash
./.venv/Scripts/python.exe -m pytest tests -k codium -q
```

Očekivano: PASS.

- [ ] **Step 9: Commit**

```bash
git add core/domains/codium/migrations.py core/domains/codium/ops_migrations.py core/domains/codium/pipelines tests/test_pipeline_repository.py
git commit -m "feat(codium): migracije v11 i ops v3 sa SQL slojem pipeline-a"
```

---

### Task 3: Serijski upis loga

**Files:**
- Create: `core/domains/codium/pipelines/sinks.py`
- Modify: `core/domains/codium/pipelines/__init__.py`
- Test: `tests/test_pipeline_log_sink.py`

**Interfaces:**
- Consumes: `RunLogLine` (Task 1), `RunLogRepository` (Task 2).
- Produces:
  - `LogWriter` Protocol sa `append(lines: list[RunLogLine]) -> None` (`RunLogRepository` ga ispunjava)
  - `LogSink` Protocol sa `write(line: RunLogLine) -> None` i `flush() -> None`
  - `BatchingLogSink(writer, clock=time.monotonic, batch_size=50, window_seconds=0.2)`
  - `CollectingLogSink()` — sink koji skuplja u listu `lines`, za testove motora

- [ ] **Step 1: Napiši test koji pada**

`tests/test_pipeline_log_sink.py`:

```python
# ========== TESTOVI: serijski upis loga ==========
# Lazan sat: nijedan test ovde ne ceka stvarnih 200 ms.
from __future__ import annotations

from core.domains.codium.pipelines.models import RunLogLine
from core.domains.codium.pipelines.sinks import BatchingLogSink, CollectingLogSink


class _LazanUpisivac:
    def __init__(self) -> None:
        self.serije: list[list[RunLogLine]] = []

    def append(self, lines: list[RunLogLine]) -> None:
        self.serije.append(list(lines))


def _red(seq: int) -> RunLogLine:
    return RunLogLine(run_id=1, step_idx=0, seq=seq, stream="stdout",
                      line=f"red {seq}")


def test_serija_odlazi_kad_se_napuni():
    upisivac = _LazanUpisivac()
    sat = {"t": 0.0}
    sink = BatchingLogSink(upisivac, clock=lambda: sat["t"], batch_size=3)

    sink.write(_red(1))
    sink.write(_red(2))
    assert upisivac.serije == []

    sink.write(_red(3))
    assert len(upisivac.serije) == 1
    assert [r.seq for r in upisivac.serije[0]] == [1, 2, 3]


def test_serija_odlazi_kad_prozor_istekne():
    upisivac = _LazanUpisivac()
    sat = {"t": 0.0}
    sink = BatchingLogSink(upisivac, clock=lambda: sat["t"], batch_size=50,
                           window_seconds=0.2)

    sink.write(_red(1))
    assert upisivac.serije == []

    # Prozor je istekao — sledeci upis nosi i prethodni red.
    sat["t"] = 0.25
    sink.write(_red(2))
    assert [r.seq for r in upisivac.serije[0]] == [1, 2]


def test_flush_ne_ostavlja_nijedan_red():
    upisivac = _LazanUpisivac()
    sink = BatchingLogSink(upisivac, clock=lambda: 0.0, batch_size=50)
    sink.write(_red(1))
    sink.flush()
    assert [r.seq for r in upisivac.serije[0]] == [1]


def test_flush_bez_redova_ne_zove_upisivaca():
    upisivac = _LazanUpisivac()
    sink = BatchingLogSink(upisivac, clock=lambda: 0.0)
    sink.flush()
    assert upisivac.serije == []


def test_collecting_sink_skuplja_sve():
    sink = CollectingLogSink()
    sink.write(_red(1))
    sink.write(_red(2))
    sink.flush()
    assert [r.seq for r in sink.lines] == [1, 2]
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_log_sink.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: ... pipelines.sinks`.

- [ ] **Step 3: Napiši sink**

`core/domains/codium/pipelines/sinks.py`:

```python
# ========== SERIJSKI UPIS LOGA ==========
# Hiljadu redova loga ne sme da znaci hiljadu transakcija. Serije zive ovde,
# a ne u motoru — tako se motor testira sa sink-om koji samo skuplja, a
# serije se testiraju laznim satom, bez cekanja.
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from core.domains.codium.pipelines.models import RunLogLine

# Koliko redova ide u jednu transakciju i koliko dugo se ceka na dopunu.
VELICINA_SERIJE = 50
PROZOR_SEKUNDI = 0.2


class LogWriter(Protocol):
    """Ono sto sink zove da bi red stvarno zavrsio u bazi."""

    def append(self, lines: list[RunLogLine]) -> None: ...


class LogSink(Protocol):
    """Ono sto motor zove za svaki red."""

    def write(self, line: RunLogLine) -> None: ...

    def flush(self) -> None: ...


class BatchingLogSink:
    """Skuplja redove i salje ih u serijama.

    Serija odlazi kad se napuni ili kad prozor istekne. Prozor se proverava
    pri upisu, ne tajmerom u pozadini: tajmer bi trazio svoj zadatak, svoje
    gasenje i svoj skup gresaka, a `flush()` na kraju koraka i na kraju
    pokretanja ionako zatvara rep.
    """

    def __init__(self, writer: LogWriter,
                 clock: Callable[[], float] = time.monotonic,
                 batch_size: int = VELICINA_SERIJE,
                 window_seconds: float = PROZOR_SEKUNDI) -> None:
        self._writer = writer
        self._clock = clock
        self._batch_size = batch_size
        self._window = window_seconds
        self._buffer: list[RunLogLine] = []
        self._prvi_u_seriji: float | None = None

    def write(self, line: RunLogLine) -> None:
        if self._prvi_u_seriji is None:
            self._prvi_u_seriji = self._clock()
        self._buffer.append(line)

        napunjena = len(self._buffer) >= self._batch_size
        istekla = self._clock() - self._prvi_u_seriji >= self._window
        if napunjena or istekla:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        self._writer.append(self._buffer)
        self._buffer = []
        self._prvi_u_seriji = None


class CollectingLogSink:
    """Sink koji nista ne upisuje — skuplja u listu, za testove motora."""

    def __init__(self) -> None:
        self.lines: list[RunLogLine] = []

    def write(self, line: RunLogLine) -> None:
        self.lines.append(line)

    def flush(self) -> None:
        return None
```

Dopuni `__init__.py` sa `BatchingLogSink`, `CollectingLogSink`, `LogSink`, `LogWriter`.

- [ ] **Step 4: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_log_sink.py -v
```

Očekivano: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/domains/codium/pipelines tests/test_pipeline_log_sink.py
git commit -m "feat(codium): serijski upis loga pipeline-a"
```

---

### Task 4: Motor

**Files:**
- Create: `core/domains/codium/pipelines/runner.py`
- Modify: `core/domains/codium/pipelines/__init__.py`
- Test: `tests/test_pipeline_runner.py`

**Interfaces:**
- Consumes: `PipelineDefinition`, `RunStatus`, `StepStatus`, `RunLogLine` (Task 1); `LogSink`, `CollectingLogSink` (Task 3).
- Produces:
  - `RunStore` Protocol: `mark_run_started(run_id)`, `mark_run_finished(run_id, status, exit_code, detail)`, `mark_step_started(run_id, idx)`, `mark_step_finished(run_id, idx, status, exit_code)`
  - `PipelineRunner(runs: RunStore, sink: LogSink)` sa `start(run_id, definition, root) -> None`, `await wait(run_id) -> None`, `cancel(run_id) -> bool`, `is_running(run_id) -> bool`

`wait(run_id)` postoji radi testova i radi urednog gašenja; rute je ne zovu.

- [ ] **Step 1: Napiši test koji pada**

`tests/test_pipeline_runner.py`:

```python
# ========== TESTOVI: motor pipeline-a ==========
# Motor pokrece prave podprocese (`python -c ...`), ali ne dodiruje bazu:
# `RunStore` i `LogSink` su lazni.
from __future__ import annotations

import asyncio
import sys

import pytest

from core.domains.codium.pipelines.models import (
    PipelineDefinition,
    RunStatus,
    StepDefinition,
    StepStatus,
)
from core.domains.codium.pipelines.runner import PipelineRunner
from core.domains.codium.pipelines.sinks import CollectingLogSink


class _LazanStore:
    """Pamti sta je motor prijavio, redom."""

    def __init__(self) -> None:
        self.run_finished: tuple | None = None
        self.run_started = False
        self.steps: dict[int, tuple[str, int | None]] = {}
        self.step_started: list[int] = []

    def mark_run_started(self, run_id: int) -> None:
        self.run_started = True

    def mark_run_finished(self, run_id: int, status: str,
                          exit_code: int | None, detail: str = "") -> None:
        self.run_finished = (status, exit_code, detail)

    def mark_step_started(self, run_id: int, idx: int) -> None:
        self.step_started.append(idx)

    def mark_step_finished(self, run_id: int, idx: int, status: str,
                           exit_code: int | None = None) -> None:
        self.steps[idx] = (status, exit_code)


def _korak(ime: str, kod: str, **ostalo) -> StepDefinition:
    # `-u` iskljucuje bafer, pa se redovi vide odmah, ne tek na kraju.
    return StepDefinition(name=ime, run=f'{sys.executable} -u -c "{kod}"', **ostalo)


def _pokreni(definicija: PipelineDefinition, tmp_path) -> tuple:
    store = _LazanStore()
    sink = CollectingLogSink()
    runner = PipelineRunner(store, sink)

    async def vozi():
        runner.start(1, definicija, tmp_path)
        await runner.wait(1)

    asyncio.run(vozi())
    return store, sink


def test_dva_uspesna_koraka_daju_success(tmp_path):
    definicija = PipelineDefinition(name="x", steps=(
        _korak("prvi", "print('jedan')"),
        _korak("drugi", "print('dva')"),
    ))
    store, sink = _pokreni(definicija, tmp_path)

    assert store.run_started is True
    assert store.run_finished[0] == RunStatus.SUCCESS
    assert store.run_finished[1] == 0
    assert store.steps[0][0] == StepStatus.SUCCESS
    assert store.steps[1][0] == StepStatus.SUCCESS


def test_seq_je_monoton_preko_koraka(tmp_path):
    definicija = PipelineDefinition(name="x", steps=(
        _korak("prvi", "print('a')"),
        _korak("drugi", "print('b')"),
    ))
    _, sink = _pokreni(definicija, tmp_path)

    seq_evi = [red.seq for red in sink.lines]
    assert seq_evi == sorted(seq_evi)
    assert len(set(seq_evi)) == len(seq_evi)
    assert {red.line for red in sink.lines} >= {"a", "b"}


def test_stderr_nosi_svoju_oznaku(tmp_path):
    definicija = PipelineDefinition(name="x", steps=(
        _korak("greska", "import sys; sys.stderr.write('lose\\n')"),
    ))
    _, sink = _pokreni(definicija, tmp_path)

    greske = [red for red in sink.lines if red.stream == "stderr"]
    assert [red.line for red in greske] == ["lose"]


def test_nenulti_kod_prekida_pokretanje(tmp_path):
    definicija = PipelineDefinition(name="x", steps=(
        _korak("pada", "import sys; sys.exit(3)"),
        _korak("nikad", "print('ne bi trebalo')"),
    ))
    store, sink = _pokreni(definicija, tmp_path)

    assert store.run_finished[0] == RunStatus.FAILED
    assert store.run_finished[1] == 3
    assert store.steps[0] == (StepStatus.FAILED, 3)
    # Preskocen korak se razlikuje od onog koji nikad nije ni krenuo.
    assert store.steps[1][0] == StepStatus.SKIPPED
    assert 1 not in store.step_started
    assert all(red.line != "ne bi trebalo" for red in sink.lines)


def test_continue_on_error_ne_prekida(tmp_path):
    definicija = PipelineDefinition(name="x", steps=(
        _korak("pada ali sme", "import sys; sys.exit(1)", continue_on_error=True),
        _korak("ipak radi", "print('stigao')"),
    ))
    store, sink = _pokreni(definicija, tmp_path)

    assert store.run_finished[0] == RunStatus.SUCCESS
    assert store.steps[0] == (StepStatus.FAILED, 1)
    assert store.steps[1][0] == StepStatus.SUCCESS
    assert any(red.line == "stigao" for red in sink.lines)


def test_istek_gasi_pokretanje(tmp_path):
    # Jedna sekunda kao „nula minuta i nesto" — motor prima sekunde iznutra.
    definicija = PipelineDefinition(name="x", timeout_minutes=1, steps=(
        _korak("dugacak", "import time; time.sleep(30)"),
    ))
    store = _LazanStore()
    runner = PipelineRunner(store, CollectingLogSink(), timeout_seconds_override=1)

    async def vozi():
        runner.start(1, definicija, tmp_path)
        await runner.wait(1)

    asyncio.run(vozi())

    assert store.run_finished[0] == RunStatus.TIMEOUT
    assert "istek" in store.run_finished[2].lower()


def test_otkazivanje_daje_cancelled(tmp_path):
    definicija = PipelineDefinition(name="x", steps=(
        _korak("dugacak", "import time; time.sleep(30)"),
    ))
    store = _LazanStore()
    runner = PipelineRunner(store, CollectingLogSink())

    async def vozi():
        runner.start(1, definicija, tmp_path)
        # Sacekaj da proces stvarno krene, pa otkazi.
        for _ in range(50):
            if runner.is_running(1):
                break
            await asyncio.sleep(0.05)
        assert runner.cancel(1) is True
        await runner.wait(1)

    asyncio.run(vozi())

    assert store.run_finished[0] == RunStatus.CANCELLED


def test_otkazivanje_nepostojeceg_pokretanja_vraca_false(tmp_path):
    runner = PipelineRunner(_LazanStore(), CollectingLogSink())
    assert runner.cancel(999) is False


def test_env_iz_definicije_stize_do_procesa(tmp_path):
    definicija = PipelineDefinition(name="x", env={"MOJA_PROMENLJIVA": "zdravo"},
                                    steps=(
        _korak("ispis", "import os; print(os.environ['MOJA_PROMENLJIVA'])"),
    ))
    _, sink = _pokreni(definicija, tmp_path)
    assert any(red.line == "zdravo" for red in sink.lines)


def test_working_dir_pomera_koren_koraka(tmp_path):
    (tmp_path / "pod").mkdir()
    definicija = PipelineDefinition(name="x", steps=(
        _korak("gde sam", "import os; print(os.path.basename(os.getcwd()))",
               working_dir="pod"),
    ))
    _, sink = _pokreni(definicija, tmp_path)
    assert any(red.line == "pod" for red in sink.lines)
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_runner.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: ... pipelines.runner`.

- [ ] **Step 3: Napiši motor**

`core/domains/codium/pipelines/runner.py`:

```python
# ========== MOTOR PIPELINE-A ==========
# Pokretanje ide kao `asyncio.Task` u procesu backend-a. Motor ne zna za bazu:
# stanja prijavljuje kroz `RunStore`, redove loga kroz `LogSink`. Zato se
# testira nad laznim obema, bez SQLite-a.
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Protocol

from core.domains.codium.pipelines.models import (
    PipelineDefinition,
    RunLogLine,
    RunStatus,
    StepDefinition,
    StepStatus,
)
from core.domains.codium.pipelines.sinks import LogSink

SEKUNDI_U_MINUTU = 60


class RunStore(Protocol):
    """Ono cime motor prijavljuje stanje pokretanja i koraka."""

    def mark_run_started(self, run_id: int) -> None: ...

    def mark_run_finished(self, run_id: int, status: str,
                          exit_code: int | None, detail: str = "") -> None: ...

    def mark_step_started(self, run_id: int, idx: int) -> None: ...

    def mark_step_finished(self, run_id: int, idx: int, status: str,
                           exit_code: int | None = None) -> None: ...


def _terminate_tree(process: asyncio.subprocess.Process) -> None:
    """Obara proces i svu njegovu decu.

    `create_subprocess_shell` na Windows-u pravi `cmd.exe`, koji pravi `npm`,
    koji pravi `node`. Gasiti samo dete znaci ostaviti unuke da rade. Isti
    obrazac koji `dev_server.py` vec koristi.
    """

    if process.returncode is not None:
        return

    if sys.platform == "win32":
        subprocess.run(  # noqa: S603, S607
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
        return

    try:
        os.killpg(os.getpgid(process.pid), 9)
    except (ProcessLookupError, PermissionError):
        process.kill()


class PipelineRunner:
    """Pokrece definiciju nad korenom repozitorijuma."""

    def __init__(self, runs: RunStore, sink: LogSink,
                 timeout_seconds_override: int | None = None) -> None:
        self._runs = runs
        self._sink = sink
        # Samo za testove: pravi istek od minuta bi test drzao ceo minut.
        self._timeout_override = timeout_seconds_override
        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._processes: dict[int, asyncio.subprocess.Process] = {}
        self._cancelled: set[int] = set()
        self._seq: dict[int, int] = {}

    # ----------          JAVNO          ----------

    def start(self, run_id: int, definition: PipelineDefinition,
              root: Path) -> None:
        """Pokrece pokretanje. Ne blokira."""

        self._seq[run_id] = 0
        self._tasks[run_id] = asyncio.create_task(
            self._vozi(run_id, definition, root),
        )

    def is_running(self, run_id: int) -> bool:
        zadatak = self._tasks.get(run_id)
        return zadatak is not None and not zadatak.done()

    def cancel(self, run_id: int) -> bool:
        """Gasi stablo procesa. Status upisuje sama petlja, ne ovaj poziv."""

        if not self.is_running(run_id):
            return False
        self._cancelled.add(run_id)
        proces = self._processes.get(run_id)
        if proces is not None:
            _terminate_tree(proces)
        return True

    async def wait(self, run_id: int) -> None:
        """Ceka kraj pokretanja. Za testove i za uredno gasenje."""

        zadatak = self._tasks.get(run_id)
        if zadatak is not None:
            await asyncio.gather(zadatak, return_exceptions=True)

    # ----------          PETLJA          ----------

    async def _vozi(self, run_id: int, definition: PipelineDefinition,
                    root: Path) -> None:
        self._runs.mark_run_started(run_id)
        istek = self._timeout_override or (
            definition.timeout_minutes * SEKUNDI_U_MINUTU
        )

        try:
            status, kod = await asyncio.wait_for(
                self._koraci(run_id, definition, root), timeout=istek,
            )
            detalj = ""
        except TimeoutError:
            self._ugasi_i_preskoci(run_id, definition, od_koraka=0)
            status, kod = RunStatus.TIMEOUT, None
            detalj = f"istek od {definition.timeout_minutes} min"
        finally:
            self._sink.flush()
            self._processes.pop(run_id, None)

        if run_id in self._cancelled:
            status, kod, detalj = RunStatus.CANCELLED, None, "otkazano"
            self._cancelled.discard(run_id)

        self._runs.mark_run_finished(run_id, status, kod, detalj)

    async def _koraci(self, run_id: int, definition: PipelineDefinition,
                      root: Path) -> tuple[str, int | None]:
        """Vozi korake redom. Vraca konacni status i izlazni kod."""

        for redni, korak in enumerate(definition.steps):
            self._runs.mark_step_started(run_id, redni)
            kod = await self._korak(run_id, redni, korak, definition, root)

            if kod == 0:
                self._runs.mark_step_finished(run_id, redni, StepStatus.SUCCESS, 0)
                continue

            self._runs.mark_step_finished(run_id, redni, StepStatus.FAILED, kod)
            if korak.continue_on_error:
                # Korak sme da padne — pokretanje ide dalje i moze da uspe.
                continue

            self._preskoci_ostatak(run_id, definition, od_koraka=redni + 1)
            return (RunStatus.FAILED, kod)

        return (RunStatus.SUCCESS, 0)

    async def _korak(self, run_id: int, idx: int, korak: StepDefinition,
                     definition: PipelineDefinition, root: Path) -> int:
        """Pokrece jedan korak i vraca njegov izlazni kod."""

        radni = root / korak.working_dir if korak.working_dir else root
        okruzenje = {**os.environ, **definition.env}

        dodatno: dict[str, object] = {}
        if sys.platform == "win32":
            dodatno["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            # Svoja grupa procesa, da `killpg` obori i decu.
            dodatno["start_new_session"] = True

        proces = await asyncio.create_subprocess_shell(  # noqa: S604
            korak.run,
            cwd=str(radni),
            env=okruzenje,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **dodatno,
        )
        self._processes[run_id] = proces

        await asyncio.gather(
            self._citaj(run_id, idx, proces.stdout, "stdout"),
            self._citaj(run_id, idx, proces.stderr, "stderr"),
        )
        kod = await proces.wait()
        self._sink.flush()
        return kod

    async def _citaj(self, run_id: int, idx: int,
                     stream: asyncio.StreamReader | None, ime: str) -> None:
        """Cita jedan tok red po red i salje ga sink-u."""

        if stream is None:
            return
        async for sirovo in stream:
            linija = sirovo.decode("utf-8", "replace").rstrip("\r\n")
            self._seq[run_id] = self._seq.get(run_id, 0) + 1
            self._sink.write(RunLogLine(
                run_id=run_id, step_idx=idx, seq=self._seq[run_id],
                stream=ime, line=linija,
            ))

    # ----------          POMOCNO          ----------

    def _preskoci_ostatak(self, run_id: int, definition: PipelineDefinition,
                          od_koraka: int) -> None:
        """Koraci koji nisu stigli na red nose `skipped`, ne `queued`."""

        for redni in range(od_koraka, len(definition.steps)):
            self._runs.mark_step_finished(run_id, redni, StepStatus.SKIPPED, None)

    def _ugasi_i_preskoci(self, run_id: int, definition: PipelineDefinition,
                          od_koraka: int) -> None:
        proces = self._processes.get(run_id)
        if proces is not None:
            _terminate_tree(proces)
        self._preskoci_ostatak(run_id, definition, od_koraka)
```

Dopuni `__init__.py` sa `PipelineRunner` i `RunStore`.

- [ ] **Step 4: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_runner.py -v
```

Očekivano: PASS. Test otkazivanja i test isteka svaki traju par sekundi — to je očekivano, jer pokreću pravi proces.

- [ ] **Step 5: Commit**

```bash
git add core/domains/codium/pipelines tests/test_pipeline_runner.py
git commit -m "feat(codium): motor pipeline-a sa otkazivanjem i istekom"
```

---

### Task 5: Servis

**Files:**
- Create: `core/domains/codium/pipelines/service.py`
- Modify: `core/domains/codium/pipelines/__init__.py`
- Test: `tests/test_pipeline_service.py`

**Interfaces:**
- Consumes: sve iz Task-ova 1–4; `RepositoryService` iz `core/domains/codium/repositories/service.py`; `ScopeGate` i `ALLOW` iz `core/security/scope_gate.py`; `AuditEntry`, `AuditRepository` iz `core/domains/codium/audit`.
- Produces:
  - `PipelineService(pipelines, runs, logs, runner, gate, audit, repositories, keep_runs=50)`
  - Metode: `create(repository_id, definition_text, actor="human") -> Pipeline`, `update(pipeline_id, definition_text, actor="human") -> Pipeline`, `delete(pipeline_id, actor="human") -> None`, `list(repository_id=None) -> list[Pipeline]`, `run(pipeline_id, actor="human", trigger="manual") -> PipelineRun`, `cancel(run_id, actor="human") -> bool`, `run_detail(run_id) -> tuple[PipelineRun, list[RunStep]]`, `run_history(pipeline_id=None, status=None, limit=50) -> list[PipelineRun]`, `logs(run_id, after_seq=0) -> list[RunLogLine]`, `recover_stale() -> int`
  - Izuzeci: `PipelineNotFound`, `RunNotFound`, `RepositoryMissing`, `RunDenied`

- [ ] **Step 1: Napiši test koji pada**

`tests/test_pipeline_service.py`:

```python
# ========== TESTOVI: servis pipeline-a ==========
from __future__ import annotations

import asyncio
import sys

import pytest

from core.domains.codium.audit import AuditRepository
from core.domains.codium.pipelines.log_repository import RunLogRepository
from core.domains.codium.pipelines.models import PipelineRun, RunStatus
from core.domains.codium.pipelines.repository import PipelineRepository, RunRepository
from core.domains.codium.pipelines.runner import PipelineRunner
from core.domains.codium.pipelines.service import (
    PipelineNotFound,
    PipelineService,
    PruningRunStore,
    RepositoryMissing,
    RunDenied,
)
from core.domains.codium.pipelines.sinks import BatchingLogSink
from core.domains.codium.repositories import Repository
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)
from core.security.scope_gate import DENY, ScopeGate, ScopeRule

DEFINICIJA = (
    '{"name": "brzi", "timeout_minutes": 1, "steps": ['
    '{"name": "jedan", "run": "%s -u -c \\"print(1)\\""}]}'
) % sys.executable.replace("\\", "\\\\")


@pytest.fixture
def okruzenje(tmp_path):
    poslovna = tmp_path / "codium.db"
    operativna = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(operativna)

    koren = tmp_path / "repo"
    koren.mkdir()
    RepositoryRepository(poslovna).add(
        Repository(name="repo", local_path=str(koren)),
    )

    logovi = RunLogRepository(operativna)
    runs = RunRepository(poslovna)
    servis: PipelineService | None = None

    def posle_kraja(run_id: int) -> None:
        """Zadrzavanje se sprovodi cim pokretanje zavrsi."""
        pokretanje = runs.get(run_id)
        if servis is not None and pokretanje is not None:
            servis.prune_logs(pokretanje.pipeline_id)

    servis = PipelineService(
        pipelines=PipelineRepository(poslovna),
        runs=runs,
        logs=logovi,
        runner=PipelineRunner(PruningRunStore(runs, posle_kraja),
                              BatchingLogSink(logovi)),
        gate=ScopeGate(lambda: []),
        audit=AuditRepository(operativna),
        repositories=RepositoryRepository(poslovna),
    )
    return servis, runs, AuditRepository(operativna), koren


def test_snimanje_neispravne_definicije_pada(okruzenje):
    servis, _, _, _ = okruzenje
    with pytest.raises(Exception) as greska:
        servis.create(1, "{ nije json")
    assert "JSON" in str(greska.value)


def test_snimljen_pipeline_nosi_ime_iz_definicije(okruzenje):
    servis, _, _, _ = okruzenje
    upisan = servis.create(1, DEFINICIJA)
    assert upisan.name == "brzi"
    assert servis.list(repository_id=1)[0].id == upisan.id


def test_pokretanje_nepostojeceg_pipeline_a(okruzenje):
    servis, _, _, _ = okruzenje
    with pytest.raises(PipelineNotFound):
        servis.run(999)


def test_pokretanje_kad_koren_nestane_daje_repository_missing(okruzenje):
    servis, _, _, koren = okruzenje
    upisan = servis.create(1, DEFINICIJA)
    koren.rmdir()
    with pytest.raises(RepositoryMissing):
        asyncio.run(_pokreni(servis, upisan.id))


def test_pokretanje_bez_dozvole_ne_pravi_pokretanje_ali_ostavlja_trag(tmp_path):
    poslovna = tmp_path / "codium.db"
    operativna = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(operativna)
    koren = tmp_path / "repo"
    koren.mkdir()
    RepositoryRepository(poslovna).add(Repository(name="r", local_path=str(koren)))

    logovi = RunLogRepository(operativna)
    runs = RunRepository(poslovna)
    dnevnik = AuditRepository(operativna)
    zabrana = ScopeGate(lambda: [ScopeRule(id=1, actor="agent:x",
                                           action="pipeline.run", target="*",
                                           verdict=DENY, note="bez pokretanja")])
    servis = PipelineService(
        pipelines=PipelineRepository(poslovna), runs=runs, logs=logovi,
        runner=PipelineRunner(runs, BatchingLogSink(logovi)),
        gate=zabrana, audit=dnevnik,
        repositories=RepositoryRepository(poslovna),
    )
    upisan = servis.create(1, DEFINICIJA)

    with pytest.raises(RunDenied):
        servis.run(upisan.id, actor="agent:x")

    assert runs.list(pipeline_id=upisan.id) == []
    tragovi = [u for u in dnevnik.query(limit=10) if u.action == "pipeline.run"]
    assert tragovi[0].verdict == DENY
    assert tragovi[0].outcome == "blocked"


async def _pokreni(servis, pipeline_id):
    """Pokrece i saceka kraj — servis sam ne blokira."""
    pokretanje = servis.run(pipeline_id)
    await servis._runner.wait(pokretanje.id)  # noqa: SLF001 — test ceka motor
    return pokretanje


def test_pokretanje_do_kraja_daje_success_i_log(okruzenje):
    servis, _, _, _ = okruzenje
    upisan = servis.create(1, DEFINICIJA)

    pokretanje = asyncio.run(_pokreni(servis, upisan.id))

    zaglavlje, koraci = servis.run_detail(pokretanje.id)
    assert zaglavlje.status == RunStatus.SUCCESS
    assert len(koraci) == 1
    assert any(red.line == "1" for red in servis.logs(pokretanje.id))


def test_logs_od_zadatog_seq(okruzenje):
    servis, _, _, _ = okruzenje
    upisan = servis.create(1, DEFINICIJA)
    pokretanje = asyncio.run(_pokreni(servis, upisan.id))

    svi = servis.logs(pokretanje.id)
    assert servis.logs(pokretanje.id, after_seq=svi[-1].seq) == []


def test_recover_stale_prebacuje_zaostala_u_failed(okruzenje):
    servis, runs, _, _ = okruzenje
    upisan = servis.create(1, DEFINICIJA)
    zaostalo = runs.create(PipelineRun(pipeline_id=upisan.id), ["a"])
    runs.mark_run_started(zaostalo.id)

    assert servis.recover_stale() == 1

    posle = runs.get(zaostalo.id)
    assert posle.status == RunStatus.FAILED
    assert "aplikacija" in posle.detail.lower()


def test_zadrzavanje_brise_log_starijih_pokretanja(tmp_path):
    poslovna = tmp_path / "codium.db"
    operativna = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(operativna)
    koren = tmp_path / "repo"
    koren.mkdir()
    RepositoryRepository(poslovna).add(Repository(name="r", local_path=str(koren)))

    logovi = RunLogRepository(operativna)
    runs = RunRepository(poslovna)
    servis: PipelineService | None = None

    def posle_kraja(run_id: int) -> None:
        pokretanje = runs.get(run_id)
        if servis is not None and pokretanje is not None:
            servis.prune_logs(pokretanje.pipeline_id)

    servis = PipelineService(
        pipelines=PipelineRepository(poslovna), runs=runs, logs=logovi,
        runner=PipelineRunner(PruningRunStore(runs, posle_kraja),
                              BatchingLogSink(logovi)),
        gate=ScopeGate(lambda: []), audit=AuditRepository(operativna),
        repositories=RepositoryRepository(poslovna),
        # Zadrzi samo jedno pokretanje, da test ne pravi 51.
        keep_runs=1,
    )
    upisan = servis.create(1, DEFINICIJA)

    prvo = asyncio.run(_pokreni(servis, upisan.id))
    assert servis.logs(prvo.id) != []

    drugo = asyncio.run(_pokreni(servis, upisan.id))

    # Zaglavlje prvog ostaje, log mu je obrisan.
    assert runs.get(prvo.id) is not None
    assert servis.logs(prvo.id) == []
    assert servis.logs(drugo.id) != []
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_service.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: ... pipelines.service`.

- [ ] **Step 3: Napiši servis**

`core/domains/codium/pipelines/service.py`:

```python
# ========== SERVIS PIPELINE-A ==========
# Jedino mesto u fazi koje zove kapiju i dnevnik. Motor ne zna za dozvole,
# SQL sloj ne zna za pravila.
from __future__ import annotations

from pathlib import Path

from core.domains.codium.audit import AuditEntry, AuditRepository
from core.domains.codium.pipelines.definition import parse
from core.domains.codium.pipelines.log_repository import RunLogRepository
from core.domains.codium.pipelines.models import (
    Pipeline,
    PipelineRun,
    RunLogLine,
    RunStatus,
    RunStep,
)
from core.domains.codium.pipelines.repository import PipelineRepository, RunRepository
from core.domains.codium.pipelines.runner import PipelineRunner
from core.domains.codium.repositories.repository import RepositoryRepository
from core.security.scope_gate import ALLOW, ScopeGate

# Za koliko poslednjih pokretanja po pipeline-u se cuva pun log.
ZADRZI_POKRETANJA = 50


class PipelineError(RuntimeError):
    """Zajednicki koren gresaka ovog servisa."""


class PipelineNotFound(PipelineError):
    """Trazen pipeline ne postoji."""


class RunNotFound(PipelineError):
    """Trazeno pokretanje ne postoji."""


class RepositoryMissing(PipelineError):
    """Koren repozitorijuma vise ne postoji na disku."""


class RunDenied(PipelineError):
    """Kapija nije dozvolila pokretanje."""


class PipelineService:
    """Definicije, pokretanja i log."""

    def __init__(self, *, pipelines: PipelineRepository, runs: RunRepository,
                 logs: RunLogRepository, runner: PipelineRunner,
                 gate: ScopeGate, audit: AuditRepository,
                 repositories: RepositoryRepository,
                 keep_runs: int = ZADRZI_POKRETANJA) -> None:
        self._pipelines = pipelines
        self._runs = runs
        self._logs = logs
        self._runner = runner
        self._gate = gate
        self._audit = audit
        self._repositories = repositories
        self._keep_runs = keep_runs

    # ----------          DEFINICIJE          ----------

    def create(self, repository_id: int, definition_text: str,
               actor: str = "human") -> Pipeline:
        koren = self._koren(repository_id, mora_da_postoji=False)
        definicija = parse(definition_text, root=koren)
        upisan = self._pipelines.add(Pipeline(
            repository_id=repository_id, name=definicija.name,
            definition=definition_text,
        ))
        self._trag(actor, "pipeline.write", f"pipeline:{upisan.id}", ALLOW,
                   "ok", "nov pipeline")
        return upisan

    def update(self, pipeline_id: int, definition_text: str,
               actor: str = "human") -> Pipeline:
        postojeci = self._nadji(pipeline_id)
        koren = self._koren(postojeci.repository_id, mora_da_postoji=False)
        definicija = parse(definition_text, root=koren)
        izmenjen = self._pipelines.update_definition(
            pipeline_id, definicija.name, definition_text,
        )
        self._trag(actor, "pipeline.write", f"pipeline:{pipeline_id}", ALLOW,
                   "ok", "izmenjena definicija")
        return izmenjen

    def delete(self, pipeline_id: int, actor: str = "human") -> None:
        self._nadji(pipeline_id)
        self._pipelines.delete(pipeline_id)
        self._trag(actor, "pipeline.write", f"pipeline:{pipeline_id}", ALLOW,
                   "ok", "obrisan pipeline")

    def list(self, repository_id: int | None = None) -> list[Pipeline]:
        return self._pipelines.list(repository_id)

    # ----------          POKRETANJE          ----------

    def run(self, pipeline_id: int, actor: str = "human",
            trigger: str = "manual") -> PipelineRun:
        """Pokrece pipeline. Ne ceka kraj — vraca pokretanje odmah."""

        pipeline = self._nadji(pipeline_id)
        cilj = f"pipeline:{pipeline_id}"

        odluka = self._gate.check(actor=actor, action="pipeline.run", target=cilj)
        if odluka.verdict != ALLOW:
            self._trag(actor, "pipeline.run", cilj, odluka.verdict, "blocked",
                       odluka.reason)
            raise RunDenied(odluka.reason)

        koren = self._koren(pipeline.repository_id, mora_da_postoji=True)
        definicija = parse(pipeline.definition, root=koren)

        pokretanje = self._runs.create(
            PipelineRun(pipeline_id=pipeline_id, trigger=trigger),
            [korak.name for korak in definicija.steps],
        )
        self._runner.start(pokretanje.id, definicija, koren)
        self._trag(actor, "pipeline.run", cilj, odluka.verdict, "ok",
                   f"run {pokretanje.id}")
        return pokretanje

    def cancel(self, run_id: int, actor: str = "human") -> bool:
        self._nadji_pokretanje(run_id)
        otkazano = self._runner.cancel(run_id)
        self._trag(actor, "pipeline.cancel", f"run:{run_id}", ALLOW,
                   "ok" if otkazano else "blocked",
                   "otkazano" if otkazano else "pokretanje vise ne radi")
        return otkazano

    # ----------          CITANJE          ----------

    def run_detail(self, run_id: int) -> tuple[PipelineRun, list[RunStep]]:
        pokretanje = self._nadji_pokretanje(run_id)
        return (pokretanje, self._runs.steps(run_id))

    def run_history(self, pipeline_id: int | None = None,
                    status: str | None = None,
                    limit: int = 50) -> list[PipelineRun]:
        return self._runs.list(pipeline_id, status, limit)

    def logs(self, run_id: int, after_seq: int = 0) -> list[RunLogLine]:
        self._nadji_pokretanje(run_id)
        return self._logs.read(run_id, after_seq)

    # ----------          ODRZAVANJE          ----------

    def recover_stale(self) -> int:
        """Zaostala pokretanja posle restarta prelaze u `failed`.

        Bez ovoga pokretanje prekinuto gasenjem aplikacije zauvek visi u
        „radi", pa se u istoriji ne razlikuje od onog koje jos traje.
        """

        zaostala = self._runs.stale_running()
        for run_id in zaostala:
            self._runs.mark_run_finished(run_id, RunStatus.FAILED, None,
                                         "aplikacija zatvorena")
        return len(zaostala)

    def prune_logs(self, pipeline_id: int) -> None:
        """Brise log pokretanjima izvan poslednjih `keep_runs`."""

        stari = self._runs.older_run_ids(pipeline_id, self._keep_runs)
        self._logs.delete_for_runs(stari)

    # ----------          POMOCNO          ----------

    def _nadji(self, pipeline_id: int) -> Pipeline:
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            raise PipelineNotFound(f"Pipeline {pipeline_id} ne postoji.")
        return pipeline

    def _nadji_pokretanje(self, run_id: int) -> PipelineRun:
        pokretanje = self._runs.get(run_id)
        if pokretanje is None:
            raise RunNotFound(f"Pokretanje {run_id} ne postoji.")
        return pokretanje

    def _koren(self, repository_id: int, *, mora_da_postoji: bool) -> Path | None:
        repo = self._repositories.get(repository_id)
        if repo is None:
            raise RepositoryMissing(f"Repozitorijum {repository_id} ne postoji.")
        koren = Path(repo.local_path)
        if koren.is_dir():
            return koren
        if mora_da_postoji:
            raise RepositoryMissing(
                f"Putanja repozitorijuma vise ne postoji: {repo.local_path}",
            )
        # Snimanje definicije sme i kad koren trenutno nije dostupan;
        # tada se `working_dir` ne proverava.
        return None

    def _trag(self, actor: str, action: str, target: str, verdict: str,
              outcome: str, detail: str) -> None:
        self._audit.record(AuditEntry(
            actor=actor, action=action, target=target, verdict=verdict,
            outcome=outcome, detail=detail,
        ))
```

- [ ] **Step 4: Poveži zadržavanje sa krajem pokretanja**

Servis mora da očisti log kad pokretanje završi, ali kraj prijavljuje motor, ne servis. Zato `PipelineService.run` ne prosleđuje `RunRepository` motoru direktno, nego omotač koji posle `mark_run_finished` pozove `prune_logs`.

Dodaj na dno `service.py`:

```python
class PruningRunStore:
    """`RunStore` koji posle kraja pokretanja pocisti stari log.

    Kraj pokretanja zna motor, a zadrzavanje je posao servisa. Ovaj omotac
    spaja to dvoje, bez rasporedjivaca i bez posla pri startu.
    """

    def __init__(self, runs: RunRepository, on_finished) -> None:
        self._runs = runs
        self._on_finished = on_finished

    def mark_run_started(self, run_id: int) -> None:
        self._runs.mark_run_started(run_id)

    def mark_run_finished(self, run_id: int, status: str,
                          exit_code: int | None, detail: str = "") -> None:
        self._runs.mark_run_finished(run_id, status, exit_code, detail)
        self._on_finished(run_id)

    def mark_step_started(self, run_id: int, idx: int) -> None:
        self._runs.mark_step_started(run_id, idx)

    def mark_step_finished(self, run_id: int, idx: int, status: str,
                           exit_code: int | None = None) -> None:
        self._runs.mark_step_finished(run_id, idx, status, exit_code)
```

Runtime (Task 6) sklapa motor sa `PruningRunStore(runs, on_finished)`, gde `on_finished` nađe `pipeline_id` pokretanja i pozove `service.prune_logs`. Testovi iz Step-a 1 već sklapaju motor tako — `PruningRunStore` je deo ovog fajla, pa ga napiši pre nego što pokreneš testove.

- [ ] **Step 5: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_service.py -v
```

Očekivano: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/domains/codium/pipelines tests/test_pipeline_service.py
git commit -m "feat(codium): servis pipeline-a sa kapijom, dnevnikom i zadrzavanjem"
```

---

### Task 6: Šeme, runtime, router, oporavak pri startu

**Files:**
- Create: `apps/api/schemas/codium_pipelines.py`
- Create: `apps/api/codium_pipelines_runtime.py`
- Create: `apps/api/routers/codium_pipelines.py`
- Modify: `apps/api/main.py` (import, `include_router`, poziv oporavka u `core_lifespan`)
- Test: `tests/test_api_codium_pipelines.py`

**Interfaces:**
- Consumes: `PipelineService` i njegove izuzetke (Task 5), `DefinitionError` (Task 1), `PruningRunStore` (Task 5).
- Produces: `apps/api/codium_pipelines_runtime.get_service()` (koristi ga Task 7), router pod `/api/v1/codium/pipelines`, i zavisnost `get_service` koju testovi menjaju kroz `app.dependency_overrides`.

- [ ] **Step 1: Napiši test koji pada**

`tests/test_api_codium_pipelines.py`:

```python
# ========== TESTOVI: API pipeline-a ==========
from __future__ import annotations

import sys
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers.codium_pipelines import get_service
from core.domains.codium.audit import AuditRepository
from core.domains.codium.pipelines.log_repository import RunLogRepository
from core.domains.codium.pipelines.repository import PipelineRepository, RunRepository
from core.domains.codium.pipelines.runner import PipelineRunner
from core.domains.codium.pipelines.service import PipelineService, PruningRunStore
from core.domains.codium.pipelines.sinks import BatchingLogSink
from core.domains.codium.repositories import Repository
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)
from core.security.scope_gate import ScopeGate

DEFINICIJA = (
    '{"name": "brzi", "timeout_minutes": 1, "steps": ['
    '{"name": "jedan", "run": "%s -u -c \\"print(1)\\""}]}'
) % sys.executable.replace("\\", "\\\\")


def _servis(tmp_path) -> PipelineService:
    poslovna = tmp_path / "codium.db"
    operativna = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(operativna)
    koren = tmp_path / "repo"
    koren.mkdir()
    RepositoryRepository(poslovna).add(Repository(name="r", local_path=str(koren)))

    logovi = RunLogRepository(operativna)
    runs = RunRepository(poslovna)
    servis: PipelineService | None = None

    def posle_kraja(run_id: int) -> None:
        pokretanje = runs.get(run_id)
        if servis is not None and pokretanje is not None:
            servis.prune_logs(pokretanje.pipeline_id)

    servis = PipelineService(
        pipelines=PipelineRepository(poslovna), runs=runs, logs=logovi,
        runner=PipelineRunner(PruningRunStore(runs, posle_kraja),
                              BatchingLogSink(logovi)),
        gate=ScopeGate(lambda: []), audit=AuditRepository(operativna),
        repositories=RepositoryRepository(poslovna),
    )
    return servis


@pytest.fixture
def klijent(tmp_path) -> Iterator[TestClient]:
    servis = _servis(tmp_path)
    app.dependency_overrides[get_service] = lambda: servis
    with TestClient(app) as klijent:
        yield klijent
    app.dependency_overrides.clear()


def test_snimanje_i_lista(klijent):
    odgovor = klijent.post("/api/v1/codium/pipelines/",
                           json={"repository_id": 1, "definition": DEFINICIJA})
    assert odgovor.status_code == 200
    assert odgovor.json()["name"] == "brzi"

    lista = klijent.get("/api/v1/codium/pipelines/?repository_id=1").json()
    assert len(lista["pipelines"]) == 1


def test_neispravna_definicija_daje_400(klijent):
    odgovor = klijent.post("/api/v1/codium/pipelines/",
                           json={"repository_id": 1, "definition": "{ nije json"})
    assert odgovor.status_code == 400


def test_nepostojeci_pipeline_daje_404(klijent):
    assert klijent.post("/api/v1/codium/pipelines/999/run").status_code == 404


def test_pokretanje_vraca_run_id_odmah(klijent):
    upisan = klijent.post("/api/v1/codium/pipelines/",
                          json={"repository_id": 1,
                                "definition": DEFINICIJA}).json()
    odgovor = klijent.post(f"/api/v1/codium/pipelines/{upisan['id']}/run")
    assert odgovor.status_code == 200
    telo = odgovor.json()
    assert telo["id"] > 0
    # Status je `queued` ili `running` — kraj se ne ceka.
    assert telo["status"] in ("queued", "running")


def test_after_seq_vraca_samo_nove_redove(klijent):
    upisan = klijent.post("/api/v1/codium/pipelines/",
                          json={"repository_id": 1,
                                "definition": DEFINICIJA}).json()
    run_id = klijent.post(
        f"/api/v1/codium/pipelines/{upisan['id']}/run").json()["id"]

    # Polling do zavrsetka, kao sto ce GUI raditi.
    for _ in range(100):
        detalj = klijent.get(f"/api/v1/codium/pipelines/runs/{run_id}").json()
        if detalj["run"]["status"] not in ("queued", "running"):
            break

    svi = klijent.get(
        f"/api/v1/codium/pipelines/runs/{run_id}/logs").json()["lines"]
    assert svi, "log ne sme da bude prazan posle zavrsenog pokretanja"

    posle = klijent.get(
        f"/api/v1/codium/pipelines/runs/{run_id}/logs"
        f"?after_seq={svi[-1]['seq']}").json()["lines"]
    assert posle == []


def test_detalj_pokretanja_nosi_i_korake(klijent):
    upisan = klijent.post("/api/v1/codium/pipelines/",
                          json={"repository_id": 1,
                                "definition": DEFINICIJA}).json()
    run_id = klijent.post(
        f"/api/v1/codium/pipelines/{upisan['id']}/run").json()["id"]

    detalj = klijent.get(f"/api/v1/codium/pipelines/runs/{run_id}").json()
    assert [k["name"] for k in detalj["steps"]] == ["jedan"]


def test_brisanje_pipeline_a(klijent):
    upisan = klijent.post("/api/v1/codium/pipelines/",
                          json={"repository_id": 1,
                                "definition": DEFINICIJA}).json()
    assert klijent.delete(
        f"/api/v1/codium/pipelines/{upisan['id']}").status_code == 200
    assert klijent.get("/api/v1/codium/pipelines/").json()["pipelines"] == []
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api_codium_pipelines.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: ... routers.codium_pipelines`.

- [ ] **Step 3: Napiši šeme**

`apps/api/schemas/codium_pipelines.py`:

```python
# ========== SEME: PIPELINE-I (CODIUM) ==========
from __future__ import annotations

from pydantic import BaseModel


class PipelineCreateRequest(BaseModel):
    """Nov pipeline nad registrovanim repozitorijumom."""

    repository_id: int
    definition: str


class PipelineUpdateRequest(BaseModel):
    definition: str


class PipelineResponse(BaseModel):
    id: int
    repository_id: int
    name: str
    definition: str
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""


class PipelinesResponse(BaseModel):
    pipelines: list[PipelineResponse]


class RunResponse(BaseModel):
    id: int
    pipeline_id: int
    status: str
    trigger: str = "manual"
    commit_sha: str | None = None
    branch: str | None = None
    exit_code: int | None = None
    detail: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str = ""


class RunsResponse(BaseModel):
    runs: list[RunResponse]


class StepResponse(BaseModel):
    idx: int
    name: str
    status: str
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None


class RunDetailResponse(BaseModel):
    run: RunResponse
    steps: list[StepResponse]


class LogLineResponse(BaseModel):
    seq: int
    step_idx: int
    stream: str
    line: str
    at: str = ""


class RunLogsResponse(BaseModel):
    lines: list[LogLineResponse]


class CancelResponse(BaseModel):
    """`cancelled=False` znaci da pokretanje vise nije radilo."""

    cancelled: bool


class PipelineDeletedResponse(BaseModel):
    deleted: int
```

- [ ] **Step 4: Napiši runtime**

`apps/api/codium_pipelines_runtime.py`:

```python
# ========== RUNTIME PIPELINE-A ==========
# `PipelineRunner` je JEDAN primerak po procesu: pokretanja koja traju zive
# u njemu, pa ga `reset()` iz testa ne sme uzeti olako.
from __future__ import annotations

from pathlib import Path

from apps.api import codium_security_runtime
from core.domains.codium.pipelines.log_repository import RunLogRepository
from core.domains.codium.pipelines.repository import PipelineRepository, RunRepository
from core.domains.codium.pipelines.runner import PipelineRunner
from core.domains.codium.pipelines.service import PipelineService, PruningRunStore
from core.domains.codium.pipelines.sinks import BatchingLogSink
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)

_service: PipelineService | None = None


def _database_path() -> Path:
    return codium_database_path()


def _ops_database_path() -> Path:
    return codium_ops_database_path()


def get_service() -> PipelineService:
    global _service
    if _service is None:
        poslovna = _database_path()
        operativna = _ops_database_path()
        runs = RunRepository(poslovna)
        logovi = RunLogRepository(operativna)

        def posle_kraja(run_id: int) -> None:
            """Zadrzavanje se sprovodi cim pokretanje zavrsi."""
            pokretanje = runs.get(run_id)
            if _service is not None and pokretanje is not None:
                _service.prune_logs(pokretanje.pipeline_id)

        _service = PipelineService(
            pipelines=PipelineRepository(poslovna),
            runs=runs,
            logs=logovi,
            runner=PipelineRunner(PruningRunStore(runs, posle_kraja),
                                  BatchingLogSink(logovi)),
            gate=codium_security_runtime.get_scope_gate(),
            audit=codium_security_runtime.get_audit(),
            repositories=RepositoryRepository(poslovna),
        )
    return _service


def reset() -> None:
    """Zaboravi napravljen primerak (koristi se u testovima)."""
    global _service
    _service = None
```

- [ ] **Step 5: Napiši router**

`apps/api/routers/codium_pipelines.py`:

```python
# ========== ROUTER: PIPELINE-I (CODIUM) ==========
# Rute nose `actor="human"`. Live log je polling `logs?after_seq=`, bez
# WebSocket-a — pravilo CORE-a.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api import codium_pipelines_runtime
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
def pokreni(pipeline_id: int,
            servis: PipelineService = Depends(get_service)) -> RunResponse:
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
```

- [ ] **Step 6: Registruj router i oporavak pri startu**

U `apps/api/main.py`, uz ostale CODIUM import-e:

```python
from apps.api.routers.codium_pipelines import (
    router as codium_pipelines_router,
)
```

uz ostale `include_router` pozive:

```python
app.include_router(codium_pipelines_router)
```

i u `core_lifespan`, odmah posle `initialize_codium_ops_database()`:

```python
        # Pokretanje prekinuto gasenjem aplikacije zauvek bi visilo u „radi".
        _recover_stale_pipeline_runs()
```

pa iznad `core_lifespan` dodaj funkciju:

```python
def _recover_stale_pipeline_runs() -> None:
    """Zaostala pokretanja pipeline-a prelaze u `failed` pri startu."""

    from apps.api import codium_pipelines_runtime

    try:
        codium_pipelines_runtime.get_service().recover_stale()
    except Exception:  # noqa: BLE001 — start ne sme da padne zbog ciscenja
        _logger.exception("Ciscenje zaostalih pokretanja pipeline-a nije uspelo")
```

(Ako u `main.py` logger nosi drugo ime od `_logger`, uskladi poziv sa postojećim imenom u tom fajlu.)

- [ ] **Step 7: Pokreni test da prođe**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api_codium_pipelines.py -v
```

Očekivano: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/api/schemas/codium_pipelines.py apps/api/codium_pipelines_runtime.py apps/api/routers/codium_pipelines.py apps/api/main.py tests/test_api_codium_pipelines.py
git commit -m "feat(api): rute za CODIUM pipeline-e i ciscenje zaostalih pokretanja"
```

---

### Task 7: Alati agenta

**Files:**
- Modify: `core/domains/codium/agents/tools/builtin.py`
- Modify: `apps/api/codium_agents_runtime.py` (`tools_for`)
- Test: `tests/test_codium_agent_tools.py`

**Interfaces:**
- Consumes: `PipelineService` (Task 5), `codium_pipelines_runtime.get_service()` (Task 6).
- Produces: `build_tools(explorer, service, project_id, repos=None, pipelines=None)` — peti parametar je opcion sa podrazumevanim `None`. Registar dobija `run_pipeline` (`action="pipeline.run"`) i `list_pipeline_runs` (`action="pipeline.read"`), ukupno deset alata.

- [ ] **Step 1: Napiši test koji pada**

Dopuni `tests/test_codium_agent_tools.py` (postojeće testove ne diraj):

```python
# ---------- alati pipeline-a ----------

class _LazniPipelineServis:
    """Servis pipeline-a sveden na ono sto alati koriste."""

    def __init__(self, pipelines: list, runs: list | None = None) -> None:
        self._pipelines = pipelines
        self._runs = runs or []
        self.pokrenuto: list[int] = []

    def list(self, repository_id=None):
        return self._pipelines

    def run(self, pipeline_id, actor="human", trigger="manual"):
        from core.domains.codium.pipelines.models import PipelineRun, RunStatus
        self.pokrenuto.append(pipeline_id)
        return PipelineRun(id=42, pipeline_id=pipeline_id,
                           status=RunStatus.QUEUED, trigger=trigger)

    def run_history(self, pipeline_id=None, status=None, limit=50):
        return self._runs[:limit]


def _pipeline(ime: str):
    from core.domains.codium.pipelines.models import Pipeline
    return Pipeline(id=1, repository_id=1, name=ime, definition="{}")


def test_run_pipeline_bez_servisa_vraca_recenicu(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer

    alati = build_tools(CodiumExplorer(tmp_path), None, 1)
    odgovor = alati.get("run_pipeline").run(name="bilo sta")
    assert "pipeline" in odgovor.lower()


def test_run_pipeline_za_nepoznato_ime_vraca_recenicu(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer

    alati = build_tools(CodiumExplorer(tmp_path), None, 1,
                        pipelines=_LazniPipelineServis([_pipeline("build")]))
    odgovor = alati.get("run_pipeline").run(name="nema-ovakvog")
    assert "nema-ovakvog" in odgovor


def test_run_pipeline_pokrece_i_vraca_run_id_bez_cekanja(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer

    servis = _LazniPipelineServis([_pipeline("build")])
    alati = build_tools(CodiumExplorer(tmp_path), None, 1, pipelines=servis)
    odgovor = alati.get("run_pipeline").run(name="build")

    assert servis.pokrenuto == [1]
    assert "42" in odgovor


def test_alati_pipeline_a_nose_ocekivane_akcije(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer

    alati = build_tools(CodiumExplorer(tmp_path), None, None)
    assert alati.get("run_pipeline").action == "pipeline.run"
    assert alati.get("list_pipeline_runs").action == "pipeline.read"


def test_list_pipeline_runs_ispisuje_istoriju(tmp_path):
    from core.domains.codium.agents.tools import build_tools
    from core.domains.codium.explorer import CodiumExplorer
    from core.domains.codium.pipelines.models import PipelineRun, RunStatus

    istorija = [PipelineRun(id=9, pipeline_id=1, status=RunStatus.SUCCESS,
                            exit_code=0, finished_at="2026-08-30 10:00:00")]
    alati = build_tools(CodiumExplorer(tmp_path), None, 1,
                        pipelines=_LazniPipelineServis([_pipeline("build")],
                                                       istorija))
    odgovor = alati.get("list_pipeline_runs").run(name="build")
    assert "9" in odgovor
    assert "success" in odgovor
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_tools.py -v
```

Očekivano: FAIL — `build_tools() got an unexpected keyword argument 'pipelines'`.

- [ ] **Step 3: Dopuni alate**

U `core/domains/codium/agents/tools/builtin.py` dodaj import:

```python
from core.domains.codium.pipelines.service import PipelineService
```

Izmeni potpis i dodaj alate unutar `build_tools`, pre `return ToolRegistry([...])`:

```python
def build_tools(explorer: CodiumExplorer, service: CodiumService | None,
                project_id: int | None,
                repos: RepositoryService | None = None,
                pipelines: PipelineService | None = None) -> ToolRegistry:
```

```python
    # Najvise pokretanja koja se ispisuju modelu; vise je zid teksta.
    MAX_POKRETANJA = 10

    def _nadji_pipeline(name: str):
        """Pipeline po imenu, u okviru prvog repozitorijuma projekta."""

        if pipelines is None:
            return None
        trazeno = (name or "").strip()
        if not trazeno:
            return None
        repo = _prvi_repo()
        repo_id = repo.id if repo is not None else None
        for pipeline in pipelines.list(repo_id):
            if pipeline.name == trazeno:
                return pipeline
        return None

    def alat_run_pipeline(name: str = "") -> str:
        if pipelines is None:
            return "Pipeline servis nije dostupan."
        pipeline = _nadji_pipeline(name)
        if pipeline is None:
            return f"Nema pipeline-a po imenu `{name}`."
        pokretanje = pipelines.run(pipeline.id, actor="agent")
        # Kraj se NE ceka: petlja agenta ne sme da visi dvadeset minuta.
        # Ishod se cita kroz `list_pipeline_runs`.
        return (f"Pipeline `{pipeline.name}` pokrenut, run {pokretanje.id}, "
                f"status {pokretanje.status}. Ishod procitaj kroz "
                f"list_pipeline_runs.")

    def alat_list_pipeline_runs(name: str = "",
                                limit: int = MAX_POKRETANJA) -> str:
        if pipelines is None:
            return "Pipeline servis nije dostupan."
        pipeline = _nadji_pipeline(name)
        if pipeline is None:
            return f"Nema pipeline-a po imenu `{name}`."
        try:
            koliko = max(1, min(int(limit), MAX_POKRETANJA))
        except (TypeError, ValueError):
            koliko = MAX_POKRETANJA
        istorija = pipelines.run_history(pipeline.id, limit=koliko)
        if not istorija:
            return f"Pipeline `{pipeline.name}` jos nije pokretan."
        redovi = [
            f"run {r.id}: {r.status} (kod {r.exit_code}) {r.finished_at or ''}".strip()
            for r in istorija
        ]
        return f"Pipeline `{pipeline.name}`:\n" + "\n".join(redovi)
```

I dva `ToolSpec`-a u listi koja se vraća:

```python
        ToolSpec(
            name="run_pipeline",
            description="Pokrece pipeline projekta po imenu; ne ceka kraj.",
            args={"name": "ime pipeline-a"},
            action="pipeline.run",
            run=alat_run_pipeline,
        ),
        ToolSpec(
            name="list_pipeline_runs",
            description="Istorija pokretanja jednog pipeline-a.",
            args={"name": "ime pipeline-a",
                  "limit": "najvise pokretanja (podrazumevano 10)"},
            action="pipeline.read",
            run=alat_list_pipeline_runs,
        ),
```

- [ ] **Step 4: Ožiči servis u runtime agenata**

U `apps/api/codium_agents_runtime.py` dodaj import `from apps.api import codium_pipelines_runtime` i izmeni `tools_for`:

```python
def tools_for(project_id: int | None) -> ToolRegistry:
    return build_tools(CodiumExplorer(project_root(project_id)),
                       get_service(), project_id,
                       repos=codium_repositories_runtime.get_service(),
                       pipelines=codium_pipelines_runtime.get_service())
```

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
git commit -m "feat(codium): agent dobija run_pipeline i list_pipeline_runs"
```

---

### Task 8: Dokumentacija i zatvaranje faze

**Files:**
- Create: `.ai/dev-log/entries/<današnji-datum>.md` (ili dopuna postojećeg unosa za taj dan)
- Modify: `.ai/dev-log/INDEX.md`
- Modify: `.ai/izgradnja/codium/00-INDEX.md`
- Modify: `.ai/izgradnja/codium/13-E3-pipelines.md`

**Interfaces:**
- Consumes: sve prethodne task-ove.
- Produces: ništa u kodu; zatvara E3a.

- [ ] **Step 1: Pokreni ceo backend skup**

```bash
./.venv/Scripts/python.exe -m pytest tests -q
```

Očekivano: sve prolazi. Zabeleži tačan broj testova za dev-log.

- [ ] **Step 2: Proveri da GUI skup nije dirnut**

```bash
npm run test
```

(iz `apps/gui`.) E3a ne dira GUI, pa je očekivano da brojevi budu isti kao pre faze. Dva postojeća `tsc` upozorenja u `CoreDockLayout.tsx` i `CodiumWorkspace.tsx` prethode ovoj grani i ne diraju se.

- [ ] **Step 3: Napiši dev-log unos**

Napravi unos u `.ai/dev-log/entries/` po konvenciji `GGGG-MM-DD.md` (ako fajl za današnji datum već postoji, dopuni ga umesto da praviš nov), i dodaj red u `.ai/dev-log/INDEX.md` na vrh tabele. Uskladi oblik sa susednim unosima — pročitaj poslednja dva pre pisanja.

Sadržaj: šta je stvarno napravljeno; da je E3 podeljen na E3a i E3b i zašto; odstupanja od faznog fajla (tajne izbačene iz dometa; korak ide kroz shell; migracije su dobile brojeve v11 i ops v3 umesto zastarelih v6/ops v2 iz faznog fajla; kolona `detail` je dodata); šta ostaje za E3b; i spisak onoga što još treba proveriti uživo, jer se automatski nije proveravalo.

- [ ] **Step 4: Upiši status u indeks**

U `.ai/izgradnja/codium/00-INDEX.md`:

- Red `E3` u tabeli enterprise trake dobija `codium v11 + ops v3` u koloni „Baza", status `**backend zavrsen (E3a); ekran ceka E3b**` i današnji datum.
- Pasus koji imenuje sledeći posao zameni novim: sledeći je `E3b` (ekran pipeline-a) ili `E4 Deployments`, po odluci korisnika — napiši da E3a otključava oboje.

U `.ai/izgradnja/codium/13-E3-pipelines.md` upiši na vrh kratak odeljak „Podela na E3a i E3b" sa dodeljenim brojevima migracija (v11, ops v3) i napomenom da odeljak o tajnama čeka E4.

- [ ] **Step 5: Commit**

```bash
git add .ai/dev-log .ai/izgradnja/codium/00-INDEX.md .ai/izgradnja/codium/13-E3-pipelines.md
git commit -m "docs(codium): E3a Pipelines zavrsen, indeks i dev-log"
```
