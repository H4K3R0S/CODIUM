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
