---
id: codium-2026-09-16-agent-rag-retrieval
type: log
domain: codium
title: 2026-09-16-agent-rag-retrieval
tags:
- dev-log
- entries
---

# 2026-09-16 — CODIUM Agent: RAG retrieval preko CORE-a

Cilj: Agent (CODIUM) pri komandi povlači relevantno znanje/prošle interakcije iz
RAG-a i obogaćuje odgovor. Ćelija ne nosi pgvector — retrieval HTTP-om ka CORE-u.

## Urađeno

Kanon kernel (`core/cell/curator/protocols.py`+`agent.py`) kopiran byte-identično
iz CORE (`Retriever` + injekcija u `_ask_model`, opciono, write-safe). Nov
`apps/api/agent_retriever.py` — `HttpRetriever` (stdlib urllib; GET
`/api/v1/rag/retrieve` sa `domain=codium`; non-200/greška → `[]`). Runtime
`codium_curator_runtime.py`: module-level `_retriever` (core_url iz manifesta,
fallback localhost:8000) + `retrieve=_retriever` u `CuratorAgent`. Import bez
mrežnog poziva.

## Provereno

py 18 testa (2 nova + regresija), kernel byte-identičan CORE kanonu, offline
import. Live retrieval tek kad korisnik pokrene Postgres + `rag_ingest_cells.py`.

## Napomene

Deo cross-repo D. Restart ćelije za nov backend.
