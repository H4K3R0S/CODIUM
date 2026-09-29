# ========== ŠEME CODIUM ASISTENT ==========
from __future__ import annotations

from pydantic import BaseModel, Field

from apps.api.schemas.core_models import (
    ModelEnabledRequest,
    ModelEnabledResponse,
    ModelInfoSchema,
    ModelsResponse,
)
from core.ai.usage import UsageSummary
from core.domains.codium.assistant import AssistantAnswer, Persona
from core.domains.codium.models import ModelPref

# Seme kataloga modela zive na CORE nivou (apps/api/schemas/core_models.py) —
# isti oblik koriste i CORE i domenske rute. Ovde se samo re-eksportuju da
# postojeci uvozi iz codium_ai nastave da rade.
__all__ = [
    "ModelEnabledRequest",
    "ModelEnabledResponse",
    "ModelInfoSchema",
    "ModelsResponse",
]


class ChatTurnSchema(BaseModel):
    author: str = Field(..., pattern="^(me|assistant)$")
    text: str


class AssistantAskRequest(BaseModel):
    project_id: int | None = None
    # Podrazumevan je opsti razvojni pomocnik; uze uloge se biraju izricito.
    persona: str = "global"
    message: str = Field(..., min_length=1)
    history: list[ChatTurnSchema] = Field(default_factory=list)
    # Izričit izbor korisnika; prazno znači "odluči po postavci pa registru".
    model: str | None = None
    provider: str | None = None
    # Ko traži odgovor. Podrazumevano čovek — on ne prolazi kroz ScopeGate.
    # Agenti i automatizacije se predstavljaju kao `agent:<slug>` /
    # `automation:<id>` i za njih važe pravila dozvola.
    actor: str = "human"


class AssistantAnswerResponse(BaseModel):
    reply: str
    persona: str
    model: str
    provider: str
    source: str
    is_fallback: bool
    sources: list[str]
    # Merenja poziva; GUI ih prikazuje kao trošak ispod odgovora.
    prompt_tokens: int
    output_tokens: int
    duration_ms: int
    cost_usd: float

    @classmethod
    def from_domain(cls, result: AssistantAnswer) -> AssistantAnswerResponse:
        return cls(
            reply=result.reply,
            persona=result.persona,
            model=result.model,
            provider=result.provider,
            source=result.source,
            is_fallback=result.is_fallback,
            sources=list(result.sources),
            prompt_tokens=result.prompt_tokens,
            output_tokens=result.output_tokens,
            duration_ms=result.duration_ms,
            cost_usd=result.cost_usd,
        )


class PersonaSchema(BaseModel):
    id: str
    name: str

    @classmethod
    def from_domain(cls, item: Persona) -> PersonaSchema:
        return cls(id=item.id, name=item.name)


class PersonasResponse(BaseModel):
    personas: list[PersonaSchema]


# ========== POSTAVKA MODELA ==========

class ModelPrefSchema(BaseModel):
    project_id: int | None
    persona: str
    model: str
    provider: str

    @classmethod
    def from_domain(cls, item: ModelPref) -> ModelPrefSchema:
        return cls(
            project_id=item.project_id,
            persona=item.persona,
            model=item.model,
            provider=item.provider,
        )


class ModelPrefResponse(BaseModel):
    pref: ModelPrefSchema | None


class ModelPrefRequest(BaseModel):
    project_id: int | None = None
    persona: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)


# ========== POTROSNJA ==========

class UsageSummaryResponse(BaseModel):
    """Zbir evidentiranih poziva za izabrani period i projekat."""

    calls: int
    prompt_tokens: int
    output_tokens: int
    cost_usd: float

    @classmethod
    def from_domain(cls, item: UsageSummary) -> UsageSummaryResponse:
        return cls(
            calls=item.calls,
            prompt_tokens=item.prompt_tokens,
            output_tokens=item.output_tokens,
            cost_usd=item.cost_usd,
        )
