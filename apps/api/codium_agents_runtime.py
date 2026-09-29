# ========== RUNTIME AGENATA ==========
# Rute traze repozitorijume i pokretac kroz `Depends`, pa im ovde stoji jedan
# primerak. Testovi ih menjaju kroz `app.dependency_overrides`.
from __future__ import annotations

import time
from pathlib import Path

from apps.api import (
    codium_assistant_runtime,
    codium_pipelines_runtime,
    codium_repositories_runtime,
    codium_security_runtime,
)
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
                       get_service(), project_id,
                       repos=codium_repositories_runtime.get_service(),
                       pipelines=codium_pipelines_runtime.get_service())


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
    router = codium_assistant_runtime.get_router()

    def resolve_model() -> tuple[str, str, bool]:
        """Cime bi ovaj posao odgovorio, i da li je to lokalan model."""

        resolved = router.resolve(
            project_id=run.project_id, persona=f"agent:{agent.slug}",
            override_provider=agent.provider or None,
            override_model=agent.model or None,
        )
        provajder = next(
            (p for p in codium_assistant_runtime.get_providers()
             if p.name == resolved.provider_name), None,
        )
        lokalan = bool(getattr(provajder, "is_local", False))
        return (resolved.provider_name, resolved.model, lokalan)

    return AgentLoop(
        runs=get_runs(),
        tools=tools_for(run.project_id),
        gate=codium_security_runtime.get_scope_gate(),
        approvals=codium_security_runtime.get_approvals(),
        audit=codium_security_runtime.get_audit(),
        chat=_chat_for(agent, run),
        resolve_model=resolve_model,
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
