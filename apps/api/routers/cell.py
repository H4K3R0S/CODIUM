"""Ćelijski API: ono što ćelija izlaže CORE-u.

Ruta je namerno `/cell/status`, a ne `/status`, da se ne sudari sa sistemskim
statusom iz `apps/api/routers/system.py`.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from apps.api.schemas.cell import (
    CellAiConfigResponse,
    CellAiConfigUpdateRequest,
    CellAssistantAskRequest,
    CellAssistantAskResponse,
    CellAtomResponse,
    CellAtomUpdateRequest,
    CellPersonaResponse,
    CellPersonaUpdateRequest,
    CellStatusResponse,
)
from core.ai.persona_store import PersonaStore
from core.cell.ai import build_cell_assistant
from core.cell.ai_config import read_ai_config, write_ai_config
from core.cell.assistant import atom_files
from core.cell.manifest import CellManifest
from core.cell.status import build_cell_status

router = APIRouter(prefix="/cell", tags=["cell"])

_PERSONA_ID = "opsti"  # podrazumevana persona CODIUM ćelije

_manifest: CellManifest | None = None


def bind_manifest(manifest: CellManifest | None) -> None:
    """Vezuje manifest za router; poziva se pri podizanju ćelije."""

    global _manifest
    _manifest = manifest


def _persona_scope() -> str:
    """Opseg persone ćelije = domen iz manifesta (generički, ne hardkodiran)."""

    return _manifest.domain_id if _manifest is not None else "core"


def _persona_store() -> PersonaStore:
    """Persona store ćelije; zasebna funkcija da bi test mogao da je zameni."""

    return PersonaStore()


@router.get("/status", response_model=CellStatusResponse)
def read_cell_status() -> CellStatusResponse:
    """Vraća stanje ćelije."""

    if _manifest is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ćelija nema učitan manifest.",
        )

    return CellStatusResponse(**build_cell_status(_manifest))


@router.get("/personas", response_model=list[CellPersonaResponse])
def list_cell_personas() -> list[CellPersonaResponse]:
    """Vraća persone opsega domena ćelije."""

    return [
        CellPersonaResponse(id=doc.id, name=doc.name, markdown=doc.markdown, customized=doc.customized)
        for doc in _persona_store().list(_persona_scope())
    ]


@router.post("/assistant/ask", response_model=CellAssistantAskResponse)
def ask_cell_assistant(body: CellAssistantAskRequest) -> CellAssistantAskResponse:
    """
    Pitanje asistentu ćelije nad lokalnom Ollamom (generički, bez CORE AI
    registra). Nepodešen model ili nedostupna Ollama vraćaju razumljivu poruku
    (`is_fallback=True`), ne grešku.
    """

    if _manifest is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ćelija nema učitan manifest.",
        )

    answer = build_cell_assistant(_manifest).ask(body.question)
    return CellAssistantAskResponse(
        answer=answer.answer,
        sources=list(answer.sources),
        is_fallback=answer.is_fallback,
    )


@router.put("/personas/{persona_id}", response_model=CellPersonaResponse)
def save_cell_persona(persona_id: str, body: CellPersonaUpdateRequest) -> CellPersonaResponse:
    """Upisuje izmenjen tekst persone; prazan tekst se odbija."""

    try:
        doc = _persona_store().save(_persona_scope(), persona_id, body.markdown)
    except ValueError as error:
        # `HTTP_422_UNPROCESSABLE_ENTITY` je zastareo u Starlette-u (baca
        # `StarletteDeprecationWarning`); ovo je nov ćelijski kod, pa koristi
        # `HTTP_422_UNPROCESSABLE_CONTENT`. 13 postojećih FILMIUM routera i
        # dalje koristi stari naziv — repo-širok zamenjivanje je van dometa
        # ovog taska (parkiran nalaz).
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Nepoznata persona: {persona_id}") from error

    return CellPersonaResponse(id=doc.id, name=doc.name, markdown=doc.markdown, customized=doc.customized)


def get_manifest() -> CellManifest:
    """Trenutni manifest ćelije ili 503 ako još nije vezan."""

    if _manifest is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ćelija nema učitan manifest.",
        )
    return _manifest


def atoms_root(manifest: CellManifest, persona_id: str = _PERSONA_ID) -> Path:
    """Koren atom fajlova persone unutar korena ćelije."""

    return manifest.root / ".ai" / "atomi" / "personas" / persona_id


@router.get("/ai-config", response_model=CellAiConfigResponse)
def read_cell_ai_config() -> CellAiConfigResponse:
    """Vraća AI podešavanja ćelije (model, adresa, dostupni lokalni modeli)."""

    cfg = read_ai_config(get_manifest().root)
    return CellAiConfigResponse(
        assistant_model=cfg.assistant_model,
        endpoint=cfg.endpoint,
        default_endpoint=cfg.default_endpoint,
        available_models=cfg.available_models,
    )


@router.put("/ai-config", response_model=CellAiConfigResponse)
def save_cell_ai_config(body: CellAiConfigUpdateRequest) -> CellAiConfigResponse:
    """Upisuje AI podešavanja ćelije; primenjuje se po ponovnom pokretanju."""

    cfg = write_ai_config(get_manifest().root, assistant_model=body.assistant_model, endpoint=body.endpoint)
    return CellAiConfigResponse(
        assistant_model=cfg.assistant_model,
        endpoint=cfg.endpoint,
        default_endpoint=cfg.default_endpoint,
        available_models=cfg.available_models,
    )


@router.get("/atoms", response_model=list[CellAtomResponse])
def list_cell_atoms() -> list[CellAtomResponse]:
    """Nabraja atom fajlove podrazumevane persone (perzona-neutralna ruta)."""

    root = atoms_root(get_manifest())
    return [CellAtomResponse(path=a.path, content=a.content) for a in atom_files.list_atoms(root)]


@router.put("/atoms/{atom_path:path}", response_model=CellAtomResponse)
def save_cell_atom(atom_path: str, body: CellAtomUpdateRequest) -> CellAtomResponse:
    """Upisuje izmenjen sadržaj atoma; prazan sadržaj ili loša putanja se odbijaju."""

    root = atoms_root(get_manifest())
    try:
        atom = atom_files.write_atom(root, atom_path, body.content)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return CellAtomResponse(path=atom.path, content=atom.content)


import urllib.request as _sp2_urllib


def _ollama_reachable(endpoint: str) -> bool:
    """Kratka provera da li je Ollama dostupna (bez sistemskog proxy-ja)."""

    url = endpoint.rstrip("/") + "/api/tags"
    opener = _sp2_urllib.build_opener(_sp2_urllib.ProxyHandler({}))
    try:
        with opener.open(url, timeout=1.0) as response:
            return 200 <= response.status < 500
    except Exception:  # noqa: BLE001
        return False


@router.get("/health")
def read_cell_health() -> dict:
    """Zdravlje celije: sopstveni podsistemi (API, Ollama, RAG) — bez CORE-a."""

    try:
        if _manifest is None:
            return {"api": True, "ollama": False, "rag": None}
        st = build_cell_status(_manifest)
        endpoint = st.get("ai_endpoint") or "http://localhost:11434"
        rag_enabled = bool(st.get("rag_enabled"))
        return {"api": True, "ollama": _ollama_reachable(endpoint), "rag": True if rag_enabled else None}
    except Exception:  # noqa: BLE001 — health ruta nikad ne baca (ugovor)
        return {"api": True, "ollama": False, "rag": None}


@router.post("/rag/init")
def init_cell_rag() -> dict:
    """Osigura sopstvenu RAG bazu celije (napravi + migriraj); tolerantno."""

    from core.cell.rag_bootstrap import ensure_cell_rag_db

    return {"ready": ensure_cell_rag_db()}


@router.post("/rag/ingest")
def ingest_cell_rag() -> dict:
    """Ingestuje atome/logove celije u SOPSTVENU bazu (namespace cell:<domen>)."""

    if _manifest is None:
        return {"ok": False, "reason": "nema manifesta"}
    try:
        from core.rag.agent_knowledge import ingest_cell
        from core.rag.config import load_rag_config
        from core.rag.connection import rag_connection
        from core.rag.embedder import Embedder

        cfg = load_rag_config()
        embedder = Embedder(cfg.embedding_model, endpoint=cfg.embedding_endpoint)
        with rag_connection(cfg.dsn) as conn:
            summary = ingest_cell(conn, _manifest.domain_id, _manifest.root, embedder=embedder)
        return {"ok": True, **summary}
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "reason": str(error)[:200]}
