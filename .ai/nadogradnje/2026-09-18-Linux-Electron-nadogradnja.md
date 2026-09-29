# Nadogradnja  — stanje posle prelaska na Linux + Electron

> Referenca trenutne arhitekture (posle nadogradnje). Zamenjuje planske beleške
> tipa `Linux-Kali-migracija.md` — migracija je ZAVRŠENA.

## Pokretanje
- Dvoklik na `.desktop` → `start.sh` → Electron (Chromium) prozor `cell-shell`
  (`~/ai/core-infrastructure/cell-shell`): frameless, maksimizovan, app-ov
  TitleBar. WebKit (`cell_window.py`) je samo fallback.
- Server: FastAPI/uvicorn iz .venv na portu 8784.

## AI
- Ollama (sistemski servis, GPU) na `http://localhost:11434`.
- `cell.json`: `ai.assistant_model = qwen2.5:7b`. Agent se u UI-ju zove `Codium`.
- Interni naziv sloja je `assistant` (ranije pogrešno „curator\"; „Kurator\" je
  isključivo FILMIUM-ov agent).

## Napomene
- CORE više ne postoji — ova ćelija je izvor istine; izmene su trajne.
- Detalji promene: vidi `.ai/dev-log/entries/-linux-electron-optimizacija.md`.
