"""AI sloj ćelije (generički): lokalna Ollama i jedno vezivanje modela iz `cell.json`.

CORE ima pun registar modela sa provajderima, ključevima, vidljivošću i
scope-gate-om (`apps.api.core_ai_runtime`, `core.security`) — ćelija NIŠTA od
toga ne nosi. Nosi samo adresu lokalne Ollame i ime modela iz `cell.json`
(`ai.endpoint`, `ai.assistant_model`). Ovaj sloj je domen-agnostičan: bilo koji
domen dobija isti prosti asistent nad lokalnom Ollamom preko `/cell/assistant/ask`.
Bogatiji, domen-specifičan asistent (npr. CODIUM personas/kontekst) može doći
kasnije kroz domensku prepravku runtime-a; ovo je zajednička osnova.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.ai.ollama_client import OllamaClient, OllamaUnavailable
from core.cell.manifest import CellManifest

_ASSISTANT_TIMEOUT_SECONDS = 60.0

# Poruka kad `cell.json` nema upisan model — uputstvo umesto greške (500).
_NO_MODEL_ANSWER = (
    "Asistent još nije podešen. Upiši lokalni Ollama model u cell.json "
    "(ai.assistant_model) i ponovo pokreni ćeliju."
)
# Poruka kad Ollama ne odgovara — razumljivo, bez tehničkog stack trace-a.
_OLLAMA_DOWN_ANSWER = (
    "Asistent nije dostupan. Proveri da li lokalna Ollama radi na adresi iz "
    "cell.json (ai.endpoint)."
)

Generate = Callable[..., str]


@dataclass(frozen=True)
class CellAssistantAnswer:
    """Odgovor asistenta ćelije. `is_fallback` = nije bio pravi poziv modela."""

    answer: str
    sources: tuple[str, ...]
    is_fallback: bool


class CellAssistant:
    """
    Najmanji asistent ćelije: pitanje → lokalna Ollama → odgovor.

    Preživi nepodešen model (`ai.assistant_model = null` u svežoj ćeliji) i
    nedostupnu Ollamu: u oba slučaja vraća razumljivu poruku sa
    `is_fallback=True` umesto da probije API ćelije kao 500.
    """

    def __init__(
        self,
        manifest: CellManifest,
        *,
        system_prompt: str = "",
        generate: Generate | None = None,
    ) -> None:
        """
        Args:
            manifest: Učitan manifest ćelije (nosi `ai_endpoint`/`ai_assistant_model`).
            system_prompt: Sistemski prompt (npr. persona domena). Prazan = bez.
            generate: Injektabilan poziv modela radi testiranja; podrazumevano
                `OllamaClient(manifest.ai_endpoint).generate`.
        """
        self._manifest = manifest
        self._system = system_prompt
        self._generate = generate or OllamaClient(
            manifest.ai_endpoint, timeout=_ASSISTANT_TIMEOUT_SECONDS
        ).generate

    def ask(self, question: str) -> CellAssistantAnswer:
        """Postavi pitanje modelu; vrati odgovor ili razumljiv fallback."""

        model = self._manifest.ai_assistant_model
        if not model:
            return CellAssistantAnswer(_NO_MODEL_ANSWER, (), True)

        try:
            answer = self._generate(
                model, question, system=self._system or None
            )
        except OllamaUnavailable:
            return CellAssistantAnswer(_OLLAMA_DOWN_ANSWER, (), True)

        return CellAssistantAnswer(answer.strip(), (), False)


def build_cell_assistant(
    manifest: CellManifest,
    *,
    system_prompt: str = "",
    generate: Generate | None = None,
) -> CellAssistant:
    """Sastavlja asistenta ćelije iz manifesta (lokalna Ollama iz `cell.json`)."""

    return CellAssistant(manifest, system_prompt=system_prompt, generate=generate)
