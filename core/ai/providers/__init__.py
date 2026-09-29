# ========== SLOJ PROVAJDERA MODELA (ĆELIJA) ==========
# Ćelijska (trimovana) verzija: re-exportuje SAMO bezbedne provajdere — `base`
# (apstrakcije) i `ollama` (lokalni). Online provajderi (anthropic/openai/
# openrouter) su izostavljeni jer vuku `core.integrations`/`core.security.secrets`,
# koje ćelija ne nosi. Ćelija radi isključivo nad lokalnom Ollamom.
from core.ai.providers.base import (
    ChatMessage,
    ChatProvider,
    ChatResult,
    ModelInfo,
    ProviderUnavailable,
)
from core.ai.providers.ollama import VRAM_BUDGET_GB, OllamaProvider

__all__ = [
    "VRAM_BUDGET_GB",
    "ChatMessage",
    "ChatProvider",
    "ChatResult",
    "ModelInfo",
    "OllamaProvider",
    "ProviderUnavailable",
]
