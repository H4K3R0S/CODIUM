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
    def from_domain(cls, agent: Agent) -> AgentResponse:
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
    def from_domain(cls, spec: ToolSpec) -> ToolResponse:
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
    def from_domain(cls, step: AgentStep) -> StepResponse:
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
    def from_domain(cls, run: AgentRun, agent_slug: str = "") -> RunSummary:
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
