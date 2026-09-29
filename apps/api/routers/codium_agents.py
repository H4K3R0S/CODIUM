# ========== ROUTER: AGENTI (CODIUM) ==========
# Pokretanje ne ceka rezultat: upisuje posao, dize nit i vraca `run_id` odmah.
# GUI dalje cita korake u stranicama.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas.codium_agents import (
    AgentDeletedResponse,
    AgentPatchRequest,
    AgentRequest,
    AgentResponse,
    AgentsResponse,
    RunRequest,
    RunResponse,
    RunsResponse,
    RunStartedResponse,
    RunSummary,
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
    from apps.api import codium_agents_runtime
    return codium_agents_runtime.get_agents()


def get_runs() -> RunRepository:
    from apps.api import codium_agents_runtime
    return codium_agents_runtime.get_runs()


def get_runner() -> AgentRunner:
    from apps.api import codium_agents_runtime
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

    from apps.api import codium_agents_runtime
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
