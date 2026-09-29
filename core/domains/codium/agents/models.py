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
