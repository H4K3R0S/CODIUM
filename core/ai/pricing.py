# ========== CENE MODELA ==========
# Anthropic Models API (`GET /v1/models`) vraća id, display_name,
# max_input_tokens, max_tokens i capabilities — ali NE vraća cenu. Zato je cena
# ručno održavana tabela.
#
# Proveri na https://www.anthropic.com/pricing pre nego što je menjaš.
# Poslednja provera: 2026-08-25.
#
# Lokalni modeli (Ollama) nemaju unos — trošak im je nula.
from __future__ import annotations

from collections.abc import Callable
from datetime import date

# (ulaz, izlaz) u dolarima po milionu tokena.
_CENE: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # OpenAI (developers.openai.com/api/docs/pricing, provereno 26.8.2026).
    # Tabela je rucno odrzavana: Models API vraca ID-jeve, ali ne i cene.
    "gpt-5.6-sol": (4.0, 20.0),
    "gpt-5.6-terra": (2.0, 12.0),
    "gpt-5.6-luna": (0.2, 1.2),
    "gpt-5.5": (5.0, 30.0),
    "gpt-5.5-pro": (30.0, 180.0),
    "gpt-5.4": (2.5, 15.0),
    "gpt-5.4-mini": (0.75, 4.5),
    "gpt-5.4-nano": (0.2, 1.25),
    "gpt-5.4-pro": (30.0, 180.0),
    "gpt-5.2": (1.75, 14.0),
    "gpt-5.2-pro": (21.0, 168.0),
    "gpt-5.1": (1.25, 10.0),
    "gpt-5": (1.25, 10.0),
    "gpt-5-mini": (0.25, 2.0),
    "gpt-5-nano": (0.05, 0.4),
    "gpt-5-pro": (15.0, 120.0),
    "gpt-4.1": (2.0, 8.0),
    "gpt-4.1-mini": (0.4, 1.6),
    "gpt-4.1-nano": (0.1, 0.4),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "gpt-3.5-turbo": (0.5, 1.5),
}

# Uvodne cene sa rokom. Posle roka važi vrednost iz `_CENE`.
# Bez ovoga bi tabela od 1.9.2026. tiho prikazivala nižu cenu nego što se
# stvarno naplaćuje.
_UVODNE: dict[str, tuple[tuple[float, float], date]] = {
    "claude-sonnet-5": ((2.0, 10.0), date(2026, 8, 31)),
}

# Drugi izvor cena, za provajdera cija ih lista donosi sama (OpenRouter).
# Rucna tabela ostaje PRVA: za direktan Anthropic ili OpenAI poziv ona je
# tacnija od OpenRouter-ove marze.
#
# Modul-nivo namerno: `usage.py` i ostali zovu `price_for` kao slobodnu
# funkciju, pa bi provlacenje izvora kroz sve pozivaoce bilo veca izmena od
# same funkcije. Postavlja se jednom, u `core_ai_runtime`.
_DODATNI_IZVOR: Callable[[str], tuple[float, float] | None] | None = None


def set_extra_price_source(
    izvor: Callable[[str], tuple[float, float] | None] | None,
) -> None:
    """Postavlja (ili sklanja) drugi izvor cena."""

    global _DODATNI_IZVOR
    _DODATNI_IZVOR = izvor


def price_for(model_id: str, *,
              na_dan: date | None = None) -> tuple[float, float] | None:
    """Cena ulaza i izlaza po milionu tokena, ili None za nepoznat model."""

    if model_id not in _CENE:
        # Nepoznat rucnoj tabeli — pitaj katalog, ako ga ima.
        return None if _DODATNI_IZVOR is None else _DODATNI_IZVOR(model_id)

    uvodna = _UVODNE.get(model_id)
    if uvodna is not None:
        vrednost, vazi_do = uvodna
        if (na_dan or date.today()) <= vazi_do:  # noqa: DTZ011
            return vrednost

    return _CENE[model_id]


def cost_usd(model_id: str, prompt_tokens: int, output_tokens: int, *,
             na_dan: date | None = None) -> float:
    """Trošak jednog poziva. Nepoznat model (npr. lokalni) košta nula."""

    cena = price_for(model_id, na_dan=na_dan)
    if cena is None:
        return 0.0
    ulaz, izlaz = cena
    return round(
        prompt_tokens / 1_000_000 * ulaz + output_tokens / 1_000_000 * izlaz,
        6,
    )
