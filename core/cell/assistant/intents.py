# ========== INTENTS FRAMEWORK (domen-agnostičan) ==========
# `IntentSpec` opisuje jednu dozvoljenu nameru. Registar (mapa naziv→spec) je
# DOMENSKI i prosleđuje se agentu — framework ne drži nijednu konkretnu nameru.
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentSpec:
    """Jedna dozvoljena namera i njena pravila."""

    name: str
    is_write: bool          # traži potvrdu pre izvršenja
    is_navigate: bool       # GUI ga izvršava (informativno; izvršilac vraća kind)
    needs_entity: bool      # traži konkretan entitet (id ili tekst za razrešavanje)
    tool: str | None        # ime `tools/<tool>.md` uputstva, ako ga ima
    required_params: tuple[str, ...]


def get_intent(registry: dict[str, IntentSpec], name: str) -> IntentSpec | None:
    """Spec namere iz DOMENSKOG registra, ili None ako nije na allowlisti."""

    return registry.get(name)


def validate_params(spec: IntentSpec, params: dict) -> list[str]:
    """Imena obaveznih polja kojih nema (prazna lista = validno)."""

    return [key for key in spec.required_params if key not in params]
