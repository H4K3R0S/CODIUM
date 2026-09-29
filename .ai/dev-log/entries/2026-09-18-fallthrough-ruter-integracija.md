---
id: codium-2026-09-18-fallthrough-ruter-integracija
type: log
domain: codium
title: 2026-09-18-fallthrough-ruter-integracija
tags:
- dev-log
- entries
---

# 2026-09-18 — FALLTHROUGH integracija sa centralnim ruterom

## Cilj
Isto kao ostali domeni: lokalni RAG miss → FALLTHROUGH ka ruteru → upis naučenog
atoma. CODIUM je i tipičan CILJ rutiranja (capability `code`).

## Urađeno
- `core/cell/fallthrough.py` (deljeni modul, domen-agnostičan) i `apps/api/routers/solve.py`.
- `apps/api/codium_assistant_runtime.py`: `_retriever` umotan u `build_fallthrough_retriever(..., _CELL_ROOT)`.
- `/solve` registrovan u `cell_app.py`.
- Port ćelije vraćen na kanonski **4802**.

## Provereno
- Import ćelije čist (`import cell_app`), `/solve` ruta registrovana.
- Ruter podignut kao systemd user servis `ai-router` (127.0.0.1:4800), `enable --now`.
- Uživo: KALIMA→ruter→CODIUM vratio traženu skriptu (primer iz specifikacije);
  graf-keš pogodak preko `ggraph get`; nepoznat upit → prazan rezultat (graciozno).
- Direktno: seed naučenog atoma → `POST /solve` (capability code) vratio skriptu.

## Napomene
- Sve tolerantno; bez novih zavisnosti.
