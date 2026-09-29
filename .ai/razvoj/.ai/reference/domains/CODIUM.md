---
id: core-94c33301-codium-md
type: reference
domain: core
namespace: global
visibility: global
tier: core
title: CODIUM (Level-1)
summary: 'Namena: programersko + dizajn okruženje. Još nedorečeno. Status: skeleton
  (manifest.py). Nizak prioritet (iza IMPERIUM/KALIMA). Agenti: **15 planirano** (manife'
keywords:
- codium
- level
- reference
- domains
tags:
- reference
- domains
source_path: .ai/reference/domains/CODIUM.md
---

# CODIUM (Level-1)

Namena: programersko + dizajn okruženje. Još nedorečeno. Status: skeleton (manifest.py). Nizak prioritet (iza IMPERIUM/KALIMA). Agenti: **15 planirano** (manifest). Agentna arhitektura: `reference/AGENTS.md`.

Razmišljanja: programiranje se oslanja na VS Code (ne izmišljati toplu vodu); dizajn preko Claude/ChatGPT. Konkretna struktura kasnije.

## CODIUM_SICA + korpus agenata (plan)
Domenska SICA pokriva softverski lifecycle; SICA pattern za samounapređenje koda. Predlog iz manifesta: prvi SEED agent celog sistema = **CODIUM/ARCHITECT** (test SICA petlje) — NE u 0.1.
- Arhitektura/dizajn (4): ARCHITECT (system), BLUEPRINT (dijagrami C4/UML/ER), INTERFACE (UI/UX, WCAG), PATTERN (dizajn paterni/anti-paterni).
- Implementacija (5): COMPILER (codegen/boilerplate), SYNTAX (Py/TS/Rust/Go idiomi), BUS (integracije/queue/webhook), HEAP (memorija/N+1/cache/async), STACK (DevOps/CI-CD/Docker/Terraform).
- Kvalitet/održavanje (4): DEBUG (root cause), TEST (unit/e2e/property/mutation), REFACTOR (code smell, dead code), SECURITY (SAST, secret scan, dep vuln, crypto misuse).
- Dokumentacija/znanje (2): DOC (OpenAPI/README/ADR/changelog), WIKI (FAQ/runbook/decision log).

OTVORENO: šta CODIUM dodaje iznad VS Code + Claude/ChatGPT (orkestracija projekata, skafold generacija, repo upravljanje, asset pipeline).
