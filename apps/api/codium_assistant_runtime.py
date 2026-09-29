# ========== CODIUM ASISTENT RUNTIME (ĆELIJA) ==========
# Ćelijska verzija: gradi CodiumAssistant nad LOKALNOM Ollamom iz `cell.json`,
# bez CORE-ovog punog AI registra (`core_ai_runtime` → `core.integrations`/
# `core.security.secrets`, koje ćelija ne nosi). Jedini provajder je Ollama;
# podrazumevani model je `ai.assistant_model` iz `cell.json`.
#
# Modul nosi DVA sloja asistenta CODIUM ćelije, oba nad istom lokalnom Ollamom:
#   1) chat servis (`CodiumAssistant`, `get_service`/`get_router`/…) za /codium/ai;
#   2) komandni agent (`AssistantAgent`, `get_agent`) za /codium/assistant —
#      prepoznaje nameru i deterministički je izvršava (repo/pipeline komande).
from __future__ import annotations

from pathlib import Path

from core.ai.model_router import ModelRouter
from core.ai.ollama_client import OllamaClient
from core.ai.persona_store import PersonaStore
from core.ai.providers import OllamaProvider
from core.ai.usage import UsageRecorder
from core.cell.assistant.agent import AssistantAgent
from core.cell.assistant.atoms import AtomLoader
from core.cell.assistant.confirm import ConfirmStore
from core.cell.assistant.interaction_log import InteractionLog
from core.cell.manifest import load_cell_manifest
from core.domains.codium.assistant import CodiumAssistant
from core.domains.codium.assistant.executors import CodiumExecutors
from core.domains.codium.assistant.intents import CODIUM_INTENTS
from core.domains.codium.repository import CodiumRepository

# Koren ćelije: ovaj fajl živi na `<koren>/apps/api/codium_assistant_runtime.py`.
_MANIFEST = load_cell_manifest(Path(__file__).resolve().parents[2])
_FALLBACK_MODEL = "llama3.2:latest"

_repository = CodiumRepository()
_persona_store = PersonaStore()
_client = OllamaClient(_MANIFEST.ai_endpoint)
_ollama = OllamaProvider(_client)
_providers = [_ollama]


def _default_model() -> tuple[str, str]:
    """Podrazumevani lokalni model iz cell.json (ai.assistant_model)."""

    return ("ollama", _MANIFEST.ai_assistant_model or _FALLBACK_MODEL)


def _pref(project_id: int | None, persona: str) -> tuple[str, str] | None:
    pref = _repository.get_model_pref(project_id, persona)
    return (pref.provider, pref.model) if pref is not None else None


_router = ModelRouter(
    providers={p.name: p for p in _providers},
    pref_lookup=_pref,
    default_lookup=_default_model,
)
_service = CodiumAssistant(
    _router,
    _repository.get_project,
    personas=lambda pid: _persona_store.persona("codium", pid),
)
_usage = UsageRecorder()


def get_service() -> CodiumAssistant:
    return _service


def get_router() -> ModelRouter:
    return _router


def get_providers() -> list:
    return list(_providers)


def get_repository() -> CodiumRepository:
    return _repository


def get_usage_recorder() -> UsageRecorder:
    return _usage


# ========== KOMANDNI AGENT (/codium/assistant) ==========
# Sklapa AssistantAgent po personi. Servisi (repo/pipeline) NISU napravljeni
# ovde direktno — konstruktori traže repozitorijume/kapiju/dnevnik, pa se
# preuzimaju iz postojećih runtime modula (isti primerak kao API rute).
_CELL_ROOT = _MANIFEST.root
_PERSONAS = _CELL_ROOT / ".ai" / "atomi" / "personas"
_SHARED = _PERSONAS / "_shared"

_agent_client = OllamaClient(endpoint=_MANIFEST.ai_endpoint, timeout=60.0)

# Deljen između zahteva (i persona): token izdat u /command mora da ga nađe
# /confirm u SLEDEĆEM zahtevu. Nov AssistantAgent se pravi po pozivu (persona,
# izvršioci), ali ConfirmStore MORA da preživi taj poziv — inače je token
# uvek nepoznat i /confirm uvek vraća 400. Tokeni nose (intent, params) i
# nisu vezani za personu, pa je jedan deljen store ispravan.
_confirm = ConfirmStore()

# Deljen dnevnik interakcija (persona-agnostičan): /command upisuje predlog
# pod izabranom personom, a /refute i /confirm grade agenta bez znanja koja
# je persona bila aktivna — ako je dnevnik po personi, oni vide samo "opsti"
# i refute/confirm se ne poklapaju sa log_id iz drugih persona. Jedan deljen
# direktorijum rešava to (po uzoru na deljen ConfirmStore iznad).
_log = InteractionLog(_CELL_ROOT / ".ai" / "atomi" / "logs" / "assistant")

# DOMEN-LOKALNO (v. ai_workplace/.ai/DOMENSKI-AGENTI.md): komandni agent je
# ROUTER (repo/pipeline komande) — ne treba mu RAG. Ranije je ovde stajao
# `build_fallthrough_retriever` koji je na promašaj lokalnog RAG-a pitao centralni
# ruter (:4800) i gradio FTS/vektor indeks NA request-putanji → sporo i van domena.
# Uklonjeno: `retrieve=None` (AssistantAgent._sa_kontekstom graciozno preskače).

# Model ostaje topao 10min → sledeći upit ~1s umesto ~5s (hladno učitavanje).
_KEEP_ALIVE = "10m"


def _agent_generate(
    model: str, prompt: str, *, system: str | None = None, fmt: str | None = None
) -> str:
    return _agent_client.generate(
        model, prompt, system=system, fmt=fmt, keep_alive=_KEEP_ALIVE
    )


def get_agent(persona_id: str = "opsti") -> AssistantAgent:
    """Sklopi agenta za datu personu (pada nazad na `opsti` ako persona ne postoji)."""

    # Lazy: runtime moduli repozitorijuma/pipeline-a uvoze se tek pri prvom
    # pozivu (isti primerak kao API rute), bez uvoznog vezivanja pri startu.
    from apps.api import codium_pipelines_runtime, codium_repositories_runtime

    pid = persona_id if (_PERSONAS / persona_id / "persona.md").is_file() else "opsti"
    atoms = AtomLoader(_PERSONAS / pid, shared_root=_SHARED)
    executors = CodiumExecutors(
        codium_repositories_runtime.get_service(),
        codium_pipelines_runtime.get_service(),
    )
    return AssistantAgent(
        intents=CODIUM_INTENTS, executors=executors, resolver=None,
        atoms=atoms, confirm=_confirm,
        log=_log,
        generate=_agent_generate, model=_MANIFEST.ai_assistant_model or "qwen2.5:7b",
        retrieve=None,  # domen-lokalno: bez RAG-a/centralnog rutera (v. napomenu gore)
    )
