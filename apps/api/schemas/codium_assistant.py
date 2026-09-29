# ========== ŠEME CODIUM ASISTENT ==========
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from core.cell.assistant.agent import AgentResult


class AssistantCommandRequest(BaseModel):
    message: str = Field(..., min_length=1)
    persona_id: str | None = None


class AssistantCommandResponse(BaseModel):
    kind: str
    intent: str
    params: dict[str, Any] = Field(default_factory=dict)
    reply: str = ""
    preview: dict[str, Any] | None = None
    confirm_token: str | None = None
    sources: list[str] = Field(default_factory=list)
    log_id: str | None = None

    @classmethod
    def from_domain(cls, result: AgentResult) -> AssistantCommandResponse:
        return cls(
            kind=result.kind, intent=result.intent, params=result.params,
            reply=result.reply, preview=result.preview,
            confirm_token=result.confirm_token, sources=list(result.sources),
            log_id=result.log_id,
        )


class AssistantConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1)


class AssistantRefuteRequest(BaseModel):
    log_id: str | None = None
