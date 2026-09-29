# ========== ROUTER: CODIUM ASISTENT ==========
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from apps.api.schemas.codium_assistant import (
    AssistantCommandRequest,
    AssistantCommandResponse,
    AssistantConfirmRequest,
    AssistantRefuteRequest,
)
from core.cell.assistant.agent import AssistantAgent
from core.cell.assistant.protocols import AssistantActionError

router = APIRouter(prefix="/api/v1/codium/assistant", tags=["CODIUM Asistent"])


def get_agent_dep(persona_id: str = "opsti") -> AssistantAgent:
    """Tanak omotač oko runtime-a — pozvan direktno (ne kroz `Depends`), pa
    testovi menjaju ponašanje monkeypatch-om `codium_assistant_runtime.get_agent`."""

    from apps.api import codium_assistant_runtime
    return codium_assistant_runtime.get_agent(persona_id)


@router.post("/command", response_model=AssistantCommandResponse)
def command(payload: AssistantCommandRequest) -> AssistantCommandResponse:
    """Prepoznaj komandu i izvrši (ili predloži za upis)."""

    agent = get_agent_dep(payload.persona_id or "opsti")
    return AssistantCommandResponse.from_domain(agent.handle(payload.message))


@router.post("/confirm")
def confirm(payload: AssistantConfirmRequest) -> dict:
    """Izvrši potvrđeni upis po tokenu."""

    agent = get_agent_dep()
    try:
        return agent.confirm(payload.token)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error
    except AssistantActionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@router.post("/refute")
def refute(payload: AssistantRefuteRequest) -> dict:
    """Obeleži poslednju (ili datu) akciju kao pogrešnu u RAG-logu."""

    return {"refuted": get_agent_dep().refute(payload.log_id)}
