---
id: codium-ab5c8ca7-90-kasnije-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: CODIUM — zamrznute faze F10–F12
summary: 'Prioritet: kasnije. Ovde sažeto; kad neka od ovih faza dođe na red, izvuci
  je u'
keywords:
- codium
- zamrznute
- faze
- f10
- f12
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/90-kasnije.md
edges:
- type: references
  target: codium-bd38c530-10-e0-integracije-i-vault-md
  weight: 0.3
- type: references
  target: codium-0933a37b-21-e11-integrations-ekran-md
  weight: 0.3
- type: references
  target: codium-f9a6cc01-18-e8-omniroute-md
  weight: 0.3
- type: references
  target: codium-30e8c7e3-19-e9-ai-agents-md
  weight: 0.3
---

# CODIUM — zamrznute faze F10–F12

Prioritet: kasnije. Ovde sažeto; kad neka od ovih faza dođe na red, izvuci je u
zaseban fajl i razradi.

> **Napomena (2026-08-22).** Ovaj fajl je nekada držao i F4–F9 i F13–F16.
> F4–F9 su u međuvremenu završene i imaju svoje fazne fajlove (`04`–`08`).
> F13–F16 su preseljene u enterprise traku, jer su se njihove oznake sudarale sa
> oznakama u `Sidebar.tsx`:
>
> | Bila | Sada |
> |---|---|
> | F13 Integracije | [E0](10-E0-integracije-i-vault.md) sloj + [E11](21-E11-integrations-ekran.md) ekran |
> | F14 OneRoute | [E8](18-E8-omniroute.md) |
> | F15 OmniRoute | [E8](18-E8-omniroute.md) |
> | F16 CODIUM_SICA | [E9](19-E9-ai-agents.md) |
>
> Ostaju samo F10, F11 i F12. Odeljci F4–F9 su zadržani niže kao istorijski
> kontekst prvobitnog plana.

---

## F4 — Workspace shell
Radno okruženje projekta. Layout: leva alatna traka · file explorer · centralni
editor (multi-tab) · desni panel (AI/preview) · donji panel (terminal/log/test) ·
gornji project toolbar. Drži aktivni projekat kontekst. Inspiracija: VS Code layout,
Sublime brzina.

## F5 — Explorer
File tree. **Ne postoji generički "CORE System Layer" za fajlove** — mora se graditi
servis ili reuse FILMIUM scanner koda. Funkcije: Open Folder, Add Project, New
File/Folder, Rename, Delete (uz potvrdu), Reveal, Refresh, Search, Collapse all.
Default ignore: node_modules, .venv, dist, build, target, .git, cache.

## F6 — Editor
Monaco editor (proveren, syntax highlight, multi-language, tabovi, minimap, diff
kasnije). Multi-tab: path, title, dirty, language, cursor pos, pinned. Bez stalnog
LLM autocomplete. Autokorekcija samo na zahtev (format/fix/explain/suggest), lakim
modelima (`llama3.2` sitno, `qwen2.5:7b` ozbiljnije).

## F7 — Preview Orchestrator
Preview u odvojenim Tauri prozorima (CORE već ima multi-window profile — reuse).
Profili: Desktop, Mobile, Tablet, Custom. Monitor placement po projektu. Dev server:
u MVP-u ručno (korisnik unese command + URL); auto-detekcija iz package.json/pyproject
kasnije. Funkcije: start/stop/reload/move-to-monitor/screenshot → sačuvaj za karticu (F2).

## F8 — Notes / reminders / kalendar
Proširenje Note modela iz F1. Auto vezivanje project_id/client_id dok je projekat
aktivan. `reminder_at` + prikaz u dashboardu. Kalendar: rokovi projekata/taskova,
reminders. Google/Outlook integracija kasnije kroz CORE integrations.

## F9 — AI panel
Chat panel. **Ide kroz postojeći `core/ai/`** (`model_registry`, `core_router`,
`ollama_client`) — ne novi router. Persona = chat modovi (Architect, Builder,
Reviewer, Designer, Manager, Debugger, Writer), ne pravi agenti prvo. Attach: otvoreni
fajl, selekcija, log/test output, screenshot. Akcije: save note, create task, write
dev-log. Executor apstrakcija: CODIUM traži role+task+context+constraints, routing
sloj bira izvršioca. Claude/Codex = glavni executor u v0.x; lokalni modeli za lagano.

Realno korišćenje modela (po `core/ai/model_registry.py`, ne po starom planu):
- `nomic-embed-text:latest` — indeks/pretraga (F10)
- `llama3.2:latest` — lagani intent/routing/kratke komande
- `qwen2.5:7b` — povremeno autokorekcija/kratka pomoć
- Veći modeli (qwen2.5:14b i sl.) — samo manual on-demand ako računar izdrži.

## F10 — Embeddings / project search
Indeks fajlova projekta preko `nomic-embed-text`. Semantička pretraga, "gde se ovo
koristi?", context retrieval za AI panel.

## F11 — AI Development Protocol
Radni standard: učitaj System Brain → učitaj Project Brain (F3) → razumi cilj →
plan → fajlovi → izmene → testovi → popravi → dev-log → update task/status. UI panel:
Plan/Fajlovi/Izmene/Testovi/Rezultat/Dev-log/Sledeće. U prvoj verziji status/record;
kasnije aktivni execution loop. Bezbednost: AI ne briše fajlove/secrets/destructive git
bez odobrenja.

## F12 — Visual Design shell
Shell za budući vision sistem (hardver još slab). MVP: dodaj referentnu sliku, poveži
sa projektom/taskom, ručno označi boje/layout, sačuvaj preview screenshot, ručno poredi.
DesignAsset model: id, project_id, task_id, path, type, title, notes, extracted_colors,
extracted_components, created_at. Kasnije: vision analiza, izvlačenje boja/spacing,
prepoznavanje komponenti, design tokens, screenshot compare.

## F13–F16 — preseljeno

Vidi napomenu na vrhu fajla. Sadržaj je razrađen u E0, E8, E9 i E11.

Nerazrađeni ostatak nekadašnjeg F13 koji **nije** pokupljen u E0/E11, pa ostaje
kao ideja za kasnije: email (klijent → task/beleška/podsetnik), kalendar,
freelancer stranice preko browser agenta, i plugin sistem (CORE-native alati prvo
— ne kopija VS Code marketplace-a).

Nekadašnji F16 je nosio i pun korpus od 15 agenata: ARCHITECT, BLUEPRINT,
INTERFACE, PATTERN, COMPILER, SYNTAX, BUS, HEAP, STACK, DEBUG, TEST, REFACTOR,
SECURITY, DOC, WIKI. E9 pravi petlju i prvi agent (ARCHITECT); ostatak korpusa
dolazi posle, kao unosi u bazu. Detalji: `.ai/reference/AGENTS.md` i
`.ai/reference/domains/CODIUM.md`.

---

## Globalna pravila implementacije (važe za sve faze)

- GUI ne čita bazu/OS direktno; kroz API → service → repository i kroz CORE.
- Putanje kroz `CodiumPaths` (kao `FilmiumPaths`), ne "PathService".
- Modeli kroz `core/ai/`, ne paralelni router.
- Kod/identifikatori engleski; UI/komentari/dokumentacija srpski.
- Veliki fajlovi se cepaju.
- Model je zamenljiv, protokol je trajan.
