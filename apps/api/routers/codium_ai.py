# ========== ROUTER: CODIUM ASISTENT (ĆELIJA) ==========
# Ćelijska verzija: lokalno (Ollama), bez CORE-ovog registra modela
# (`core_ai_runtime`) i bez sloja vidljivosti/allowlist/kataloga (upravljanje
# online modelima nema smisla u ćeliji sa jednim lokalnim modelom). Persone,
# razgovor, postavke i potrošnja rade; katalog modela je degradiran (prazan).
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends

from apps.api.schemas.codium_ai import (
    AssistantAnswerResponse,
    AssistantAskRequest,
    ModelEnabledRequest,
    ModelEnabledResponse,
    ModelPrefRequest,
    ModelPrefResponse,
    ModelPrefSchema,
    ModelsResponse,
    PersonaSchema,
    PersonasResponse,
    UsageSummaryResponse,
)
from core.ai.persona_store import PersonaStore
from core.ai.usage import UsageRecorder
from core.domains.codium.assistant import ChatTurn, CodiumAssistant
from core.domains.codium.audit import AuditRepository
from core.domains.codium.repository import CodiumRepository
from core.security.scope_gate import ScopeGate

_OPSEG = "codium"

router = APIRouter(
    prefix="/api/v1/codium/ai",
    tags=["CODIUM Asistent"],
)


def get_service() -> CodiumAssistant:
    from apps.api import codium_assistant_runtime
    return codium_assistant_runtime.get_service()


def get_providers() -> list:
    from apps.api import codium_assistant_runtime
    return codium_assistant_runtime.get_providers()


def get_repository() -> CodiumRepository:
    from apps.api import codium_assistant_runtime
    return codium_assistant_runtime.get_repository()


def get_usage_recorder() -> UsageRecorder:
    from apps.api import codium_assistant_runtime
    return codium_assistant_runtime.get_usage_recorder()


def get_persona_store() -> PersonaStore:
    return PersonaStore()


def get_scope_gate() -> ScopeGate:
    from apps.api import codium_security_runtime
    return codium_security_runtime.get_scope_gate()


def get_audit() -> AuditRepository:
    from apps.api import codium_security_runtime
    return codium_security_runtime.get_audit()


# ==========          PERSONE          ==========

@router.get("/personas", response_model=PersonasResponse)
def list_personas(
    store: PersonaStore = Depends(get_persona_store),
) -> PersonasResponse:
    """Persone (chat modovi) CODIUM opsega."""

    return PersonasResponse(
        personas=[PersonaSchema(id=doc.id, name=doc.name) for doc in store.list(_OPSEG)],
    )


# ==========          RAZGOVOR          ==========

@router.post("/ask", response_model=AssistantAnswerResponse)
def ask_assistant(
    payload: AssistantAskRequest,
    service: CodiumAssistant = Depends(get_service),
    usage: UsageRecorder = Depends(get_usage_recorder),
    gate: ScopeGate = Depends(get_scope_gate),
    audit: AuditRepository = Depends(get_audit),
) -> AssistantAnswerResponse:
    """Odgovor asistenta nad lokalnim modelom (Ollama).

    Ćelija radi samo lokalno, pa nema „online" provere kroz `ScopeGate` kao u
    CORE-u; poziv i evidencija su isti. Nedostupan model → is_fallback=true.
    """

    model = payload.model.strip() if payload.model and payload.model.strip() else None
    provider = payload.provider.strip() if payload.provider and payload.provider.strip() else None

    result = service.ask(
        project_id=payload.project_id,
        persona_id=payload.persona,
        message=payload.message,
        history=[ChatTurn(author=t.author, text=t.text) for t in payload.history],
        model=model,
        provider=provider,
    )

    usage.record(
        provider=result.provider,
        model=result.model,
        project_id=payload.project_id,
        persona=result.persona,
        prompt_tokens=result.prompt_tokens,
        output_tokens=result.output_tokens,
        duration_ms=result.duration_ms,
        ok=not result.is_fallback,
    )

    return AssistantAnswerResponse.from_domain(result)


# ==========          KATALOG MODELA (degradiran u ćeliji)          ==========

@router.get("/models", response_model=ModelsResponse)
def list_models(only_enabled: bool = False) -> ModelsResponse:
    """
    U ćeliji nema CORE kataloga/vidljivosti modela — vraća prazno. Chat koristi
    podrazumevani lokalni model iz `cell.json` (bez izbornika).
    """

    _ = only_enabled
    return ModelsResponse(models=[])


@router.put("/models/enabled", response_model=ModelEnabledResponse)
def set_model_enabled(payload: ModelEnabledRequest) -> ModelEnabledResponse:
    """Bez efekta u ćeliji (nema sloja vidljivosti); vraća zahtev radi API oblika."""

    return ModelEnabledResponse(
        provider=payload.provider, model=payload.model,
        enabled=payload.enabled, scope=_OPSEG,
    )


# ==========          POSTAVKA MODELA          ==========

@router.get("/prefs", response_model=ModelPrefResponse)
def read_model_pref(
    persona: str,
    project_id: int | None = None,
    repository: CodiumRepository = Depends(get_repository),
) -> ModelPrefResponse:
    """Zapamćen model za par (projekat, persona)."""

    pref = repository.get_model_pref(project_id, persona)
    return ModelPrefResponse(
        pref=ModelPrefSchema.from_domain(pref) if pref is not None else None,
    )


@router.put("/prefs", response_model=ModelPrefResponse)
def write_model_pref(
    payload: ModelPrefRequest,
    repository: CodiumRepository = Depends(get_repository),
) -> ModelPrefResponse:
    """Pamti izbor modela za par (projekat, persona)."""

    pref = repository.set_model_pref(
        payload.project_id, payload.persona, payload.model, payload.provider,
    )
    return ModelPrefResponse(pref=ModelPrefSchema.from_domain(pref))


@router.delete("/prefs", response_model=ModelPrefResponse)
def clear_model_pref(
    persona: str,
    project_id: int | None = None,
    repository: CodiumRepository = Depends(get_repository),
) -> ModelPrefResponse:
    """Vraća par (projekat, persona) na podrazumevani model."""

    repository.delete_model_pref(project_id, persona)
    return ModelPrefResponse(pref=None)


# ==========          POTROSNJA          ==========

@router.get("/usage", response_model=UsageSummaryResponse)
def read_usage(
    period: Literal["day", "month"] | None = None,
    project_id: int | None = None,
    usage: UsageRecorder = Depends(get_usage_recorder),
) -> UsageSummaryResponse:
    """Zbir potrošnje za izabrani period i projekat."""

    return UsageSummaryResponse.from_domain(
        usage.summary(period=period, project_id=project_id),
    )
