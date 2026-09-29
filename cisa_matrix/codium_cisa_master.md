---
id: codium-cisa-master
type: cisa_global_core
domain: codium
title: CODIUM CISA — globalni koordinator situacione svesti
summary: Koordinator razvojne situacione svesti CODIUM-a; Commander delegira Architect/Coder/Janitor pod-agentima.
status: stable
agent_owner: menadzer
active_sub_agents: [cisa-code-architect, cisa-delta-coder, cisa-debug-janitor]
situation_awareness_level: high
total_learned_code_patterns: 3
last_check_success_rate: "n/a (skuplja se kroz petlju)"
keywords: [cisa, codium, situaciona svest, architect, coder, janitor, ast, linter, git, samoucenje]
tags: [cisa, codium, koordinator, agenti]
source_path: cisa_matrix/codium_cisa_master.md
atom_kreiran: 2026-09-19T15:58:24-04:00
atom_azuriran: 2026-09-19T15:58:24-04:00
edges:
- {type: has_part, target: cisa-code-architect, weight: 0.9}
- {type: has_part, target: cisa-delta-coder, weight: 0.9}
- {type: has_part, target: cisa-debug-janitor, weight: 0.9}
- {type: references, target: menadzer, weight: 0.6}
- {type: references, target: learn-proven-code-solutions, weight: 0.7}
---

# 🧠 CODIUM CISA — situaciona svest razvoja

Koordinator (`menadzer` kao Commander) prati status koda, aktivne projekte i Git grane. Kada zadaš programerski zadatak, analizira CISA bazu, prepoznaje arhitektonske obrasce i delegira pod-agentima.

> **Grounded:** „TokenJuice" iz izvorne vizije = naša **žetva/context_harvest** (selektivni delta-upis); nema „rudarenja"/GPU-drajvera. Alati STVARNI: `ruff`/`mypy`/`pytest` (Python), `tsc`/`eslint` (TS), `cargo check` (Tauri Rust sloj), `radon`, naš `qa.py`, `git`, `atom_factory` (v3).

## 🔀 DELEGACIJA (faza → pod-agent)
| Faza razvoja | Pod-agent (persona) | Lokalni CISA fajl | Fokus |
|---|---|---|---|
| 1. Dizajn & AST mapa | Architect (`arhitekta`) | `[[cisa-code-architect]]` | Skeniranje zavisnosti i strukture |
| 2. Pisanje & Delta patch | Vibe-Coder (`graditelj`) | `[[cisa-delta-coder]]` | Generisanje koda + štednja konteksta |
| 3. Debug & Linter | Debug-Janitor (`debager`) | `[[cisa-debug-janitor]]` | Greške kompajlera/lintera + git rollback |

## 🔄 CROSS-AGENT PETLJA UČENJA
1. **Architect** mapira AST postojećeg koda i predlaže tačno mesto/fajl za novi modul, bez lomljenja zavisnosti.
2. **Vibe-Coder** preuzima nacrt, primenjuje žetva/delta (šalje modelu samo izmenjeni opseg + kontekst), generiše kod. Ako `qa.py`/`cargo check`/`tsc` javi grešku → staje.
3. **Debug-Janitor** presreće grešku, proverava `[[cisa-debug-janitor]]` za poznata rešenja, sam ispravi sintaksu/tip, i upisuje lekciju u `[[learn-proven-code-solutions]]`.
4. **Commander** osvežava ovaj master, stabilizuje kod i vezuje za Git commit (Time-Travel = istorija commit-ova).

## 🛡️ Bezbednost
Agenti poboljšavaju SOPSTVENI CODIUM kod (kvalitet/ispravnost), lokalno. Nema ofanzivnih akcija; osetljive sistemske akcije kroz Approval Gate.
