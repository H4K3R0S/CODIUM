---
id: codium-0d3e24f5-04-workspace-shell-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: F4 — CODIUM Workspace shell
summary: 'Prioritet: odmrznuto (posle v0.1 MVP F1–F3). Status: vidi [00-INDEX.md](00-INDEX.md).'
keywords:
- codium
- workspace
- shell
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/04-workspace-shell.md
edges:
- type: references
  target: codium-66d262ea-00-index-md
  weight: 0.3
---

# F4 — CODIUM Workspace shell

Prioritet: odmrznuto (posle v0.1 MVP F1–F3). Status: vidi [00-INDEX.md](00-INDEX.md).

## Cilj

Radno okruženje jednog projekta. Ljuska (layout + regioni + navigacija), NE same
funkcije. Explorer (F5), Editor (F6), Preview (F7), AI (F9) su zasebne faze — ovde
su placeholder regioni. Inspiracija: VS Code layout, Sublime brzina.

## Lokacija

- `apps/gui/src/pages/CodiumWorkspace.tsx` + `styles/codium-workspace.css`
- Ruta: `/codium/workspace/:projectId`
- Ulaz: „Otvori" na kartici projekta (F2) vodi u workspace i postavlja aktivni
  projekat u kontekstu.

## Regioni (6)

```
┌───────────────── top toolbar (projekat, status, akcije, nazad) ─────────────────┐
│ rail │ explorer        │ editor (multi-tab placeholder)        │ right panel     │
│ ikon │ (F5 placeholder)│ (F6 placeholder)                      │ (AI/info F9)    │
├──────┴─────────────────┴───────────────────────────────────────┴─────────────────┤
│ bottom panel (terminal / log / test — F7/F9 placeholder)                          │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## Levi tool rail (navigacija)

Projekti (nazad na hub) · Explorer · Editor · Preview · Terminal · Git · AI Chat ·
Tasks · Beleške · Brain · Settings.

U ovoj fazi aktivno: **Tasks, Beleške, Brain** (reuse F1/F3 paneli) i **Projekti**
(nazad na hub). Ostalo vidljivo ali „uskoro" (placeholder u centru).

## Aktivni projekat

Workspace na mount-u učita projekat (`getProject`) i postavi aktivni projekat u
kontekstu (localStorage `codium.activeProjectId`, isto kao F2). Ako projekat ne
postoji → nazad na hub.

## Definicija gotovog (F4)

- [x] Ruta `/codium/workspace/:projectId` prikazuje ljusku.
- [x] Svi regioni vidljivi (toolbar, rail, explorer, editor, right, bottom).
- [x] „Otvori" na kartici vodi u workspace i postavlja aktivni projekat.
- [x] Rail navigacija radi (Tasks/Beleške/Brain aktivni, ostalo placeholder).
- [x] Nazad na hub radi.

## Napomene

- Ne graditi Explorer/Editor/Preview ovde — placeholder regioni.
- Reuse postojeće `ProjectWorkModal` (Tasks/Beleške) i `BrainModal`.
