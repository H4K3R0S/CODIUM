# ========== CODIUM ASISTENT (chat servis) ==========
# Kognitivni sloj CODIUM domena: razgovor sa modelom kroz ModelRouter. Persona
# (chat mod) bira sistemski prompt; kratak kontekst projekta (ime/stack/status)
# ide u istu sistemsku poruku. Ako provajder nije dostupan, vraća se uredan
# fallback (bez pada). Servis ne zna koji je provajder u igri — to je posao
# rutera.
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.ai.model_router import ModelRouter, ResolvedModel
from core.ai.pricing import cost_usd
from core.ai.providers import ChatMessage, ProviderUnavailable
from core.domains.codium.assistant.personas import Persona
from core.domains.codium.assistant.personas import persona as ugradjena_persona

# project_lookup(project_id) -> Project | None (dataclass sa name/slug/stack/status)
ProjectLookup = Callable[[int], Any]

# Koliko poslednjih poruka istorije ide u razgovor (da ostane sažeto).
_HISTORY_LIMIT = 8


@dataclass
class ChatTurn:
    """Jedna prethodna poruka u razgovoru (za kontekst)."""

    author: str  # "me" | "assistant"
    text: str


@dataclass
class AssistantAnswer:
    reply: str
    persona: str
    model: str
    provider: str = ""
    # Odakle je došla odluka o modelu: "override" | "pref" | "registry".
    source: str = ""
    is_fallback: bool = False
    sources: list[str] = field(default_factory=list)
    # Merenja poziva. Servis ih samo prenosi — upis u evidenciju radi ruta, da
    # domenski servis ostane bez zavisnosti na bazu.
    prompt_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    cost_usd: float = 0.0


# ========== SERVIS ==========
class CodiumAssistant:
    """Razgovor sa asistentom po personi, sa kontekstom projekta."""

    def __init__(self, router: ModelRouter,
                 project_lookup: ProjectLookup,
                 personas: Callable[[str], Persona] | None = None) -> None:
        self._router = router
        self._project_lookup = project_lookup
        # Tekst persone je uređiv (vidi core.ai.persona_store), pa se uzima
        # kroz funkciju umesto iz tvrdo uvezenog spiska.
        self._personas = personas or ugradjena_persona

    def resolve(
        self,
        *,
        project_id: int | None,
        persona_id: str,
        model: str | None = None,
        provider: str | None = None,
    ) -> ResolvedModel:
        """Koji bi model bio pozvan, bez pozivanja.

        Ruta ovim saznaje provajdera pre nego što pusti poziv, pa dozvola može
        da se proveri unapred. Ista odluka se posle prosleđuje `ask`-u kao
        override, da se ne resolvuje dvaput i da se dve odluke ne raziđu.
        """
        active = self._personas(persona_id)
        return self._router.resolve(
            project_id=project_id,
            persona=active.id,
            override_provider=provider,
            override_model=model,
        )

    def ask(
        self,
        *,
        project_id: int | None,
        persona_id: str,
        message: str,
        history: list[ChatTurn] | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> AssistantAnswer:
        active = self._personas(persona_id)
        resolved = self._router.resolve(
            project_id=project_id,
            persona=active.id,
            override_provider=provider,
            override_model=model,
        )
        messages = self._build_messages(
            project_id, history or [], message, active.system,
        )

        try:
            result = self._router.chat(messages, resolved)
        except ProviderUnavailable as error:
            return AssistantAnswer(
                reply=f"Model {resolved.model} nije dostupan: {error}",
                persona=active.id,
                model=resolved.model,
                provider=resolved.provider_name,
                source=resolved.source,
                is_fallback=True,
            )

        return AssistantAnswer(
            reply=result.text.strip(),
            persona=active.id,
            model=resolved.model,
            provider=resolved.provider_name,
            source=resolved.source,
            prompt_tokens=result.prompt_tokens,
            output_tokens=result.output_tokens,
            duration_ms=result.duration_ms,
            # Cena po modelu koji je stvarno odgovorio; lokalni košta nulu.
            cost_usd=cost_usd(resolved.model, result.prompt_tokens,
                              result.output_tokens),
        )

    # ---------- interno ----------

    def _build_messages(
        self,
        project_id: int | None,
        history: list[ChatTurn],
        message: str,
        system: str,
    ) -> list[ChatMessage]:
        """Sistemska poruka (persona + kontekst), pa istorija, pa novo pitanje."""

        context = self._project_context(project_id)
        if context:
            system = f"{system}\n\nKontekst projekta: {context}"

        messages = [ChatMessage(role="system", content=system)]
        for turn in history[-_HISTORY_LIMIT:]:
            messages.append(ChatMessage(
                role="user" if turn.author == "me" else "assistant",
                content=turn.text,
            ))
        messages.append(ChatMessage(role="user", content=message))
        return messages

    def _project_context(self, project_id: int | None) -> str:
        if project_id is None:
            return ""
        project = self._project_lookup(project_id)
        if project is None:
            return ""
        bits = [f"{project.name} ({project.slug})"]
        stack = getattr(project, "stack", "") or ""
        if stack:
            bits.append(f"stack: {stack}")
        status = getattr(project, "status", "")
        status_value = getattr(status, "value", status)
        if status_value:
            bits.append(f"status: {status_value}")
        return ", ".join(bits)
