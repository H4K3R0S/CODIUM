---
id: codium-c3289ed2-06-editor-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: F6 — CODIUM Editor (Monaco)
summary: 'Prioritet: odmrznuto (posle F5). Status: vidi [00-INDEX.md](00-INDEX.md).'
keywords:
- codium
- editor
- monaco
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/06-editor.md
edges:
- type: references
  target: codium-66d262ea-00-index-md
  weight: 0.3
---

# F6 — CODIUM Editor (Monaco)

Prioritet: odmrznuto (posle F5). Status: vidi [00-INDEX.md](00-INDEX.md).

## Cilj

Uređivanje fajlova u editor regionu workspace-a (F4). Monaco editor sa više
tabova, dirty stanjem i Save.

## Backend

Dodato `explorer.write_file(rel, content)` + `PUT /projects/{id}/files/content`
(unutar korena, bez izlaska). Ostalo iz F5 (list/read/create/rename/delete).

## GUI

- Zavisnosti: `@monaco-editor/react` + `monaco-editor` (npm).
- Offline setup: [lib/monacoSetup.ts](../../../apps/gui/src/lib/monacoSetup.ts) —
  `loader.config({ monaco })` (lokalni monaco, ne CDN). Language worker fajlovi se
  NE uvoze (monaco „exports" mapa + Vite ih teško resolve-uju) — koristi se prazan
  blob worker: editovanje i isticanje sintakse rade na glavnoj niti, IntelliSense
  isključen (dovoljno za v0.x). Uvezeno u `main.tsx`.
- [features/codium/CodeEditorPanel.tsx](../../../apps/gui/src/features/codium/CodeEditorPanel.tsx):
  multi-tab (otvoren fajl = tab), dirty tačka, Save (Ctrl+S) + Save all, zatvaranje
  taba uz potvrdu ako je dirty, jezik po ekstenziji, binarno/preveliko = read-only.
- Napomena o layout-u: u flex/grid kontejneru `automaticLayout` ume da promaši prvu
  meru → ručni `editor.layout()` u `onMount` (rAF + timeout).

## Definicija gotovog (F6)

- [x] Monaco radi lokalno (bez CDN), učitava sadržaj fajla.
- [x] Multi-tab: otvaranje više fajlova, prebacivanje, zatvaranje.
- [x] Dirty stanje + Save (Ctrl+S) + Save all pišu kroz API.
- [x] Jezik po ekstenziji; binarno/preveliko read-only.
- [x] Ugrađena pretraga (Monaco Ctrl+F).

## Napomene

- IntelliSense/dijagnostika (TS/JSON worker) — kasnije, ako zatreba (traži
  rešavanje monaco worker bundlinga; za sada nebitno).
- Autokorekcija lakim modelima (llama3.2/qwen2.5) — poseban zadatak (F9 AI).
