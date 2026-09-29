---
id: codium-2026-09-18-linux-electron-optimizacija
type: log
domain: codium
title: 2026-09-18-linux-electron-optimizacija
tags:
- dev-log
- entries
---

# 2026-09-18 — Linux prelazak, Electron prozor, duboka optimizacija, preimenovanje agenta

Cilj: CODIUM ćelija brza na Kali Linuxu, u Electron prozoru, sa ispravnim
imenom agenta (ne „Kurator").

## Urađeno

- Linux prelazak: `start.sh`, Linux `.venv`, `dependencies.py` platformski svestan.
- Prozor: Electron (Chromium) `cell-shell` — frameless, maksimizovan; ~4x brži
  od WebKit2GTK na NVIDIA. `cell_window.py` (WebKit) fallback.
- Duboka optimizacija: 13 fajlova sa lenjim importom teških `*_runtime` modula
  (grade se na prvi zahtev, ne pri startu; ~28 modula skinuto sa boot putanje),
  popravljen N+1 u `repositories.list()`, `PRAGMA synchronous = NORMAL`.
- Lokacija: `~/ai/domains/codium`.
- AI: `ai.assistant_model = qwen2.5:7b` (Ollama, GPU).
- Preimenovanje: interno `curator`→`assistant` (rute `/api/v1/codium/curator`→
  `/api/v1/codium/assistant`, dirovi `core/cell/curator`, `core/domains/codium/curator`,
  runtime, klase, css); prikazano ime agenta = `Codium`. VAŽNO: postojeći
  `CodiumAssistant` chat (ruta `/api/v1/codium/ai`) je zadržan — procureli
  „curator" intent-executor je spojen pod `/assistant`, bez sudara.

## Provereno

Import OK; server 8784 → HTTP 200; nova ruta `/api/v1/codium/assistant/{command,confirm,refute}`
radi, stara `/curator` uklonjena; `/cell/status` → `ai_assistant_model: qwen2.5:7b`;
GUI rebildovan; `grep curator/kurator` = 0 u kodu/dist/atomi.

## Napomene

CORE više ne postoji — izmene trajne. Istorijski `.ai/dev-log`/`razvoj/docs`
namerno i dalje pominju „kurator" (arhiva).
