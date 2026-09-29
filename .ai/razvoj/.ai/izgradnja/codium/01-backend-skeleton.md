---
id: codium-4dd4d4da-01-backend-skeleton-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: F1 — CODIUM backend domain skeleton
summary: 'Prioritet: v0.1. Status: vidi [00-INDEX.md](00-INDEX.md).'
keywords:
- codium
- backend
- domain
- skeleton
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/01-backend-skeleton.md
edges:
- type: references
  target: codium-66d262ea-00-index-md
  weight: 0.3
---

# F1 — CODIUM backend domain skeleton

Prioritet: v0.1. Status: vidi [00-INDEX.md](00-INDEX.md).

## Cilj

Napraviti backend temelj CODIUM domena po FILMIUM obrascu, ali lakše. Bez GUI-a
u ovoj fazi — samo baza, modeli, servis, router, schema.

## Lokacija

- Kod: `core/domains/codium/`
- Podaci: `data/codium/`
- Sistemski brain (fajlovi, kasnije): `data/codium/system/`

## Obrazac (FILMIUM, redukovano)

```
core/domains/codium/
  manifest.py        (postoji)
  paths.py           CodiumPaths(core_paths)  — kao FilmiumPaths
  models.py          dataclass modeli
  repository.py      SQLite CRUD
  service.py         poslovna logika
  migrations.py      jedan fajl (nabavka stil), NE 31 fajl
apps/api/
  routers/codium.py  API router (transport)
  schemas/codium.py  request/response schema
```

Tok: `GUI → apps/api/routers/codium.py → service → repository → SQLite`.

## Entiteti (v0.1 minimalni set)

Kreće se sa 4 tabele. Ostalo (Goal, Contact, ProjectLink, ProjectAsset) se dodaje
kad zatreba — ne sve odjednom.

### Project
`id, name, slug, type, visibility, status, local_path, project_brain_path,
client_id, repository_url, live_url, staging_url, preview_url, stack, priority,
started_at, deadline_at, last_opened_at, created_at, updated_at`

- `visibility` / `scope`: razdvaja **client** i **private** rad u istoj bazi.
- `client_id`: NULL za privatne projekte.

### Client
`id, name, company_name, type, email, phone, website, notes, created_at, updated_at`

### Task
`id, project_id, title, description, status, priority, due_at, completed_at,
created_at, updated_at`

### Note
`id, project_id, client_id, title, body, source, importance, tags, reminder_at,
status, created_at, updated_at`

- `source`: manual | chat | ai | email | preview | task | roadmap | meeting
- `importance`: low | normal | high | urgent
- `status`: active | done | archived

## Aktivni kontekst

CODIUM zna trenutno aktivan projekat. Kada se pravi Note dok je projekat aktivan:
- auto `project_id`
- ako projekat ima `client_id` → auto `client_id`
- auto datum/vreme, `source` po mestu nastanka

Bez aktivnog projekta → Note ide u globalni CODIUM inbox (`project_id` NULL).

## Dva logička sloja podataka

- **Client/Public Work:** firme, klijenti, rokovi, plaćeni projekti.
- **Private/Personal Lab:** privatne aplikacije, CORE nadogradnje, eksperimenti.

U v0.1 ista SQLite baza, razdvojeni preko `visibility` polja. Fizičko razdvajanje
baza — kasnije, ako zatreba.

## Definicija gotovog (F1)

- [x] `CodiumPaths` pravi `data/codium/` bezbedno.
- [x] `migrations.py` kreira 4 tabele; ponovno pokretanje ne pravi štetu (idempotentno).
- [x] `service.py`: create/list/get/update za Project, Client, Task, Note.
- [x] `routers/codium.py` + `schemas/codium.py` izlažu te operacije.
- [x] Bar jedan test po servisnoj operaciji (pytest kroz `./.venv/Scripts/python.exe`).
- [x] Router registrovan u `apps/api/main.py`.

## Napomene

- Migracije: `nabavka/migrations.py` je uzor (jedan fajl), ne FILMIUM 31-fajl eksplozija.
- Testovi se pokreću kroz venv: `./.venv/Scripts/python.exe -m pytest`.
