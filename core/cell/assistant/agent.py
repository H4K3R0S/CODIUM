# ========== GENERIČKI ASISTENT AGENT ==========
# Jedan LLM prolaz (fmt=json) mapira poruku u nameru iz DOMENSKOG registra; kod
# deterministički izvršava preko `Executors` protokola. Upisi ne diraju bazu u
# handle — samo predlog + token. Entitet (npr. media_id) se po potrebi razrešava
# iz naslova preko `Resolver`-a. Bez ijednog domenskog imena.
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from core.cell.assistant.atoms import AtomLoader
from core.cell.assistant.confirm import ConfirmStore
from core.cell.assistant.intents import IntentSpec, get_intent, validate_params
from core.cell.assistant.interaction_log import InteractionLog
from core.cell.assistant.protocols import (
    AssistantActionError,
    Executors,
    Resolver,
    Retriever,
)

Generate = Callable[..., str]

_SYSTEM = (
    "Iz korisnikove poruke prepoznaj TAČNO jednu nameru sa spiska i vrati "
    'ISKLJUČIVO JSON oblika {{"intent": "...", "params": {{...}}, "reply": "..."}}. '
    "Dozvoljene namere i primeri:\n{katalog}\n"
    "Ako ne razumeš, vrati intent \"unknown\". Ne izmišljaj namere van spiska."
)


def _je_entity_valid(vrednost: object) -> bool:
    """Da li je id entiteta celobrojan (int ili string koji je ceo broj)."""

    if isinstance(vrednost, bool):
        return False
    if isinstance(vrednost, int):
        return True
    if isinstance(vrednost, str):
        try:
            int(vrednost)
        except ValueError:
            return False
        return True
    return False


@dataclass
class AgentResult:
    kind: str                       # answer | proposal | navigate
    intent: str
    params: dict = field(default_factory=dict)
    reply: str = ""
    preview: dict | None = None
    confirm_token: str | None = None
    sources: list[str] = field(default_factory=list)
    log_id: str | None = None


class AssistantAgent:
    """Prepoznavanje komandi i deterministično izvršenje (domen-agnostično)."""

    def __init__(
        self,
        intents: dict[str, IntentSpec],
        executors: Executors,
        resolver: Resolver | None,
        atoms: AtomLoader,
        confirm: ConfirmStore,
        log: InteractionLog,
        generate: Generate,
        model: str,
        entity_key: str = "media_id",
        retrieve: Retriever | None = None,
    ) -> None:
        self._intents = intents
        self._executors = executors
        self._resolver = resolver
        self._atoms = atoms
        self._confirm = confirm
        self._log = log
        self._generate = generate
        self._model = model
        self._entity_key = entity_key
        self._retrieve = retrieve

    def handle(self, message: str) -> AgentResult:
        self._log.settle_silent()
        parsed = self._ask_model(message)
        intent_name = parsed.get("intent", "unknown")
        params = parsed.get("params") or {}
        reply = parsed.get("reply") or ""

        spec = get_intent(self._intents, intent_name)
        if spec is None or validate_params(spec, params):
            return AgentResult(kind="answer", intent="unknown",
                               reply=reply or "Ne razumem komandu.")

        if spec.needs_entity and not _je_entity_valid(params.get(self._entity_key)):
            razresen = self._razresi_entity(params)
            if razresen is not None:
                params[self._entity_key] = razresen
            else:
                log_id = self._log.record(message, intent_name, params, spec.tool, reply)
                return AgentResult(kind="answer", intent="unknown",
                                   reply="Ne razumem tačno šta — reci jasnije.",
                                   log_id=log_id)

        if spec.is_write:
            try:
                preview = self._executors.preview(intent_name, params)
            except AssistantActionError as error:
                log_id = self._log.record(message, intent_name, params, spec.tool, reply)
                return AgentResult(kind="answer", intent="unknown",
                                   reply=str(error), log_id=log_id)
            token = self._confirm.issue(intent_name, params)
            log_id = self._log.record(message, intent_name, params, spec.tool, reply)
            return AgentResult(kind="proposal", intent=intent_name, params=params,
                               reply=reply, preview=preview, confirm_token=token,
                               log_id=log_id)

        try:
            out = self._executors.run(intent_name, params)
        except AssistantActionError as error:
            log_id = self._log.record(message, intent_name, params, spec.tool, reply)
            return AgentResult(kind="answer", intent="unknown",
                               reply=str(error), log_id=log_id)
        kind = out.get("kind", "answer")
        sources = out.get("sources", [])
        log_id = self._log.record(message, intent_name, params, spec.tool, reply)
        return AgentResult(kind=kind, intent=intent_name, params=params, reply=reply,
                           preview=out, sources=sources, log_id=log_id)

    def confirm(self, token: str) -> dict:
        intent_name, params = self._confirm.take(token)
        return self._executors.apply(intent_name, params)

    def refute(self, log_id: str | None = None) -> bool:
        return self._log.refute(log_id)

    def _razresi_entity(self, params: dict) -> object | None:
        if self._resolver is None:
            return None
        for kljuc in ("title", "naslov", "query"):
            tekst = params.get(kljuc)
            if isinstance(tekst, str) and tekst.strip():
                nadjen = self._resolver.resolve(tekst)
                if nadjen is not None:
                    return nadjen
        return None

    def _ask_model(self, message: str) -> dict:
        system = _SYSTEM.format(katalog=self._atoms.command_catalog())
        system = self._sa_personom(system)
        system = self._sa_kontekstom(system, message)
        try:
            raw = self._generate(self._model, message, system=system, fmt="json")
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError, TypeError):
            return {"intent": "unknown", "params": {}, "reply": ""}

    def _sa_kontekstom(self, system: str, message: str) -> str:
        """Doda blok relevantnog konteksta iz RAG-a ako retriever postoji.
        Greška/nedostupnost retrievera je bezopasna — vrati prompt kao pre."""
        if self._retrieve is None:
            return system
        try:
            fn = getattr(self._retrieve, "retrieve", self._retrieve)
            isecci = fn(message) or []
        except Exception:  # noqa: BLE001
            return system
        if not isecci:
            return system
        blok = "\n".join(f"- {s}" for s in isecci)
        return f"{system}\n\nRelevantan kontekst iz memorije:\n{blok}"

    def _sa_personom(self, system: str) -> str:
        """Prefiksuje sistemski prompt tekstom aktivne persone (ton/rezon).
        Persona oblikuje glas `reply` polja; instrukcija za JSON ostaje ispod.
        Nedostatak persona.md je bezopasan — vrati prompt kao pre."""
        try:
            persona = self._atoms.persona().body.strip()
        except Exception:  # noqa: BLE001
            persona = ""
        if not persona:
            return system
        return f"{persona}\n\n{system}"
