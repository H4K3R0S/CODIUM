# ========== PROVAJDER: OLLAMA (lokalni modeli) ==========
# Omotač nad postojećim OllamaClient-om. Ne zamenjuje ga — `generate()` i dalje
# koriste CoreRouter i domenski agenti; ovde se koriste `tags()` i `chat()`.
from __future__ import annotations

import time

from core.ai.ollama_client import OllamaClient, OllamaUnavailable
from core.ai.providers.base import (
    ChatMessage,
    ChatResult,
    ModelInfo,
    ProviderUnavailable,
)

# Budžet VRAM-a mašine: jedan GPU sa 8 GB (isti razlog zbog kog postoji
# vram_guard mutex). Model veći od ovoga se OZNAČAVA, nikad ne odbija —
# `size` iz /api/tags je veličina na disku, samo približna mera potrebe za
# VRAM-om, pa bi tvrdo odbijanje odbilo i modele koji bi radili.
VRAM_BUDGET_GB = 8.0

_BYTES_PER_GB = 1_000_000_000

# Embedding modeli stoje u istoj listi kao chat modeli, ali `/api/chat` nad njima
# vraća HTTP 400. Zato se označavaju kao nedostupni — vide se, sa razlogom, i ne
# mogu da se izaberu.
#
# Prepoznavanje je heuristika nad `/api/tags`, namerno: pouzdan podatak je
# `capabilities` iz `/api/show`, ali to je poziv PO modelu i izmereno traje ~2.2 s
# svaki (7 modela = 15 s po otvaranju izbornika). Keširanje kataloga je Faza 3.
# Ako heuristika promaši, poziv i dalje završi urednom porukom sa pravim razlogom.
_EMBEDDING_FAMILIES = frozenset({"bert", "nomic-bert"})
_EMBEDDING_RAZLOG = "embedding model — ne služi za chat"


class OllamaProvider:
    """Lokalni modeli kroz Ollama."""

    name = "ollama"
    is_local = True

    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    def available(self) -> bool:
        try:
            self._client.tags()
        except OllamaUnavailable:
            return False
        return True

    def models(self) -> list[ModelInfo]:
        try:
            raw = self._client.tags()
        except OllamaUnavailable as error:
            raise ProviderUnavailable(str(error)) from error
        return [self._to_info(item) for item in raw if isinstance(item, dict)]

    def chat(self, messages: list[ChatMessage], model: str,
             **options: object) -> ChatResult:
        started = time.perf_counter()
        payload = [{"role": m.role, "content": m.content} for m in messages]

        try:
            data = self._client.chat(model, payload)
        except OllamaUnavailable as error:
            raise ProviderUnavailable(str(error)) from error

        message = data.get("message")
        text = str(message.get("content", "")) if isinstance(message, dict) else ""
        return ChatResult(
            text=text,
            model=model,
            provider=self.name,
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            output_tokens=int(data.get("eval_count") or 0),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ---------- interno ----------

    @staticmethod
    def _je_embedding(model_id: str, item: dict) -> bool:
        """Heuristika: da li je model namenjen embedding-u, a ne razgovoru."""

        if "embed" in model_id.lower():
            return True
        details = item.get("details")
        if not isinstance(details, dict):
            return False
        return str(details.get("family", "")).lower() in _EMBEDDING_FAMILIES

    @classmethod
    def _to_info(cls, item: dict) -> ModelInfo:
        model_id = str(item.get("model") or item.get("name") or "")
        raw_size = item.get("size")
        size_gb = (
            round(raw_size / _BYTES_PER_GB, 1)
            if isinstance(raw_size, int | float) and raw_size > 0
            else None
        )
        embedding = cls._je_embedding(model_id, item)
        return ModelInfo(
            id=model_id,
            label=model_id,
            provider=cls.name,
            is_local=True,
            size_gb=size_gb,
            oversized=size_gb is not None and size_gb > VRAM_BUDGET_GB,
            available=not embedding,
            unavailable_reason=_EMBEDDING_RAZLOG if embedding else "",
        )
