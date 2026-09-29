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
class ArtifactDefinition:
    """Sta uspesno pokretanje ostavlja iza sebe, kao ulaz za isporuku (E4).

    `path` je folder ili fajl relativan na koren repozitorijuma. Bez ovog
    polja pokretanje ne pravi artefakt i ne moze da se isporuci — deploy
    nema svoj build.
    """

    path: str


@dataclass(frozen=True)
class PipelineDefinition:
    """Cela definicija, posle parsiranja i provere."""

    name: str
    steps: tuple[StepDefinition, ...]
    timeout_minutes: int = 20
    env: dict[str, str] = field(default_factory=dict)
    artifact: ArtifactDefinition | None = None


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
