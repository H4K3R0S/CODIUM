# ========== RUTER MODELA ==========
# Bira KOJIM modelom se odgovara. Nije isto što i core_router.py — taj
# klasifikuje nameru korisnika u JSON intent i sa izborom modela nema veze.
#
# Ruter ne zna za ModelRegistry ni za bazu: postavku i podrazumevani model
# dobija kao ubrizgane funkcije, pa se testira bez ijednog od ta dva.
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.ai.providers.base import (
    ChatMessage,
    ChatProvider,
    ChatResult,
    ProviderUnavailable,
)

# pref_lookup(project_id, persona) -> (provajder, model) | None
PrefLookup = Callable[[int | None, str], tuple[str, str] | None]
# default_lookup() -> (provajder, model)
DefaultLookup = Callable[[], tuple[str, str]]


@dataclass(frozen=True)
class ResolvedModel:
    """Odluka rutera: čime se odgovara i odakle je odluka došla."""

    provider_name: str
    model: str
    source: str  # "override" | "pref" | "registry"


class ModelRouter:
    """Redosled odlučivanja: override, pa zapamćeno, pa podrazumevano."""

    def __init__(self, providers: dict[str, ChatProvider],
                 pref_lookup: PrefLookup,
                 default_lookup: DefaultLookup) -> None:
        self._providers = providers
        self._pref_lookup = pref_lookup
        self._default_lookup = default_lookup

    def resolve(self, *, project_id: int | None = None, persona: str = "",
                override_provider: str | None = None,
                override_model: str | None = None) -> ResolvedModel:
        # 1. Izričit izbor korisnika u chatu uvek pobeđuje.
        if override_model:
            # Samo ako nije eksplicitno naveden provajder, uzmi podrazumevani.
            provider = override_provider
            if not provider:
                provider, _ = self._default_lookup()
            return ResolvedModel(provider, override_model, "override")

        # 2. Zapamćena postavka za taj projekat i tu personu.
        pref = self._pref_lookup(project_id, persona)
        if pref is not None:
            return ResolvedModel(pref[0], pref[1], "pref")

        # 3. Podrazumevano po domenu i ulozi (postojeće ponašanje).
        default_provider, default_model = self._default_lookup()
        return ResolvedModel(default_provider, default_model, "registry")

    def chat(self, messages: list[ChatMessage], resolved: ResolvedModel,
             **options: object) -> ChatResult:
        provider = self._providers.get(resolved.provider_name)
        if provider is None:
            raise ProviderUnavailable(
                f"Nepoznat provajder: {resolved.provider_name}",
            )
        return provider.chat(messages, resolved.model, **options)
