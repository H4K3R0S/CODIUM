---
id: codium-3d1b3b0a-05-explorer-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: F5 — CODIUM Explorer (file tree)
summary: 'Prioritet: odmrznuto (posle F4). Status: vidi [00-INDEX.md](00-INDEX.md).'
keywords:
- codium
- explorer
- file
- tree
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/05-explorer.md
edges:
- type: references
  target: codium-66d262ea-00-index-md
  weight: 0.3
---

# F5 — CODIUM Explorer (file tree)

Prioritet: odmrznuto (posle F4). Status: vidi [00-INDEX.md](00-INDEX.md).

## Cilj

File tree projekta u Explorer regionu workspace-a (F4). Nov skener — **ne postoji
generički CORE System Layer za fajlove**, pa se gradi namenski servis, ograničen na
koren projekta (`Project.local_path`).

## Backend — nov skener

`core/domains/codium/explorer.py` — `CodiumExplorer(root)`:
- `list_dir(rel)` — jedan nivo (lazy), folderi prvi pa fajlovi, alfabetski
- `read_file(rel)` — tekst (cap veličine, odbij binarno) — koristi i F6 editor
- `create_file(rel)`, `create_dir(rel)`, `rename(rel, novo_ime)`, `delete(rel)`
- Bezbednost: sve putanje se resolve-uju unutar `root`; izlazak (`..`) → greška
- Default ignore: `node_modules, .venv, venv, dist, build, target, .git,
  __pycache__, .mypy_cache, .pytest_cache, .idea, .vscode, .cache, cache`

## API

`/api/v1/codium/projects/{id}/files`:
- `GET  ?path=` — listing direktorijuma
- `GET  /content?path=` — sadržaj fajla (read-only; za F6)
- `POST` — kreiraj (`{path, kind: file|dir}`)
- `PATCH` — preimenuj (`{path, new_name}`)
- `DELETE ?path=` — obriši (potvrda u GUI-ju)

Projekat bez `local_path` → 400 (nema šta da se skenira).

## GUI

Explorer region (F4 placeholder → stvarni tree): lazy expand foldera, ikone,
kontekst akcije (New File/Folder, Rename, Delete uz potvrdu, Refresh), pretraga po
imenu, Collapse all. Klik na fajl → (F6 editor; za sada prikaz sadržaja).

## Definicija gotovog (F5)

- [x] Skener lista koren projekta (lazy, ignore lista).
- [x] Bezbednost: nema izlaska iz korena projekta.
- [x] Create/Rename/Delete rade kroz API.
- [x] GUI Explorer prikazuje tree, expand/refresh, akcije uz potvrdu za Delete.
- [x] Klik na fajl prikazuje sadržaj (most ka F6).

## Napomene

- Ignore lista podrazumevana; kasnije po projektu konfigurabilna.
- Binarni/veliki fajlovi: listaj ali ne učitavaj sadržaj (cap).
