# ========== PROTOKOL PROVAJDERA MODELA ==========
# Jedan ulaz za sve modele: lokalne (Ollama) i online (kasnije faze). Tipovi su
# naši, ne SDK-ovi, jer sloj apstrahuje više provajdera; konverzija u oblik koji
# pojedini SDK očekuje dešava se unutar tog provajdera i nigde drugde.
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ProviderUnavailable(RuntimeError):
    """Provajder ne odgovara (servis ugašen, mreža, ključ nedostaje)."""


# ========== TIPOVI ==========

@dataclass(frozen=True)
class ChatMessage:
    """Jedna poruka razgovora. `role` je 'system', 'user' ili 'assistant'."""

    role: str
    content: str


@dataclass(frozen=True)
class ModelInfo:
    """Opis jednog modela za prikaz u izborniku."""

    id: str
    label: str
    provider: str
    is_local: bool
    context_window: int = 0
    # Cena po milionu tokena; nula za lokalne modele.
    price_in_per_mtok: float = 0.0
    price_out_per_mtok: float = 0.0
    # Veličina na disku u GB (Ollama); približna mera potrebe za VRAM-om.
    size_gb: float | None = None
    # Veći od budžeta VRAM-a — sme da se izabere, ali nosi upozorenje.
    oversized: bool = False
    available: bool = True
    unavailable_reason: str = ""
    # Red koji stoji umesto liste modela kad provajder ne odgovara. Nije model:
    # nema ga ni u Ollami ni kod provajdera, pa se ne moze ni ukljuciti ni
    # iskljuciti u podesavanjima.
    is_placeholder: bool = False


@dataclass(frozen=True)
class ChatResult:
    """Odgovor modela sa merenjima poziva."""

    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


# ========== PROTOKOL ==========

@runtime_checkable
class ChatProvider(Protocol):
    """Ugovor koji svaki provajder modela ispunjava."""

    name: str
    is_local: bool

    def available(self) -> bool:
        """Da li provajder trenutno odgovara."""

    def models(self) -> list[ModelInfo]:
        """Modeli koje provajder nudi. Diže ProviderUnavailable ako ne može."""

    def chat(self, messages: list[ChatMessage], model: str,
             **options: object) -> ChatResult:
        """Jedan ne-stream poziv modela."""
