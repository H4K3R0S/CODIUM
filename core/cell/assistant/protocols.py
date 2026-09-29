# ========== PROTOKOLI (domenski slojevi koje agent očekuje) ==========
# Domen ubacuje svoje izvršioce i razrešivač entiteta preko ovih protokola.
from __future__ import annotations

from typing import Protocol


class AssistantActionError(Exception):
    """Domenski izvršilac je diže kad namera ne može gracioznо da se izvrši
    (npr. „nema entiteta tog imena"). Agent je hvata i vraća uredan odgovor."""


class Resolver(Protocol):
    """Razrešava slobodan tekst (npr. naslov) u id entiteta domena."""

    def resolve(self, text: str) -> object | None: ...


class Executors(Protocol):
    """Izvršava namere nad domenskim servisima.

    `run` — čitanje/navigacija/odmah-izvršenje; rezultat sme da nosi `kind`
    ("navigate" za GUI navigaciju, inače tretirano kao "answer") i `sources`.
    `preview` — za upisne namere: pregled izmene BEZ upisa.
    `apply` — izvršava potvrđenu upisnu nameru.
    """

    def run(self, intent_name: str, params: dict) -> dict: ...
    def preview(self, intent_name: str, params: dict) -> dict: ...
    def apply(self, intent_name: str, params: dict) -> dict: ...


class Retriever(Protocol):
    """Vraća relevantne isečke iz RAG memorije za dati upit (opcion)."""

    def retrieve(self, query: str) -> list[str]: ...
