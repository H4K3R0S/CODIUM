---
id: codium-580b9d17-02-project-hub-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: F2 — CODIUM Project Hub GUI
summary: 'Prioritet: v0.1. Status: vidi [00-INDEX.md](00-INDEX.md).'
keywords:
- codium
- project
- hub
- gui
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/02-project-hub.md
edges:
- type: references
  target: codium-66d262ea-00-index-md
  weight: 0.3
---

# F2 — CODIUM Project Hub GUI

Prioritet: v0.1. Status: vidi [00-INDEX.md](00-INDEX.md).

## Cilj

Prvi ekran CODIUM-a. Pregled svih projekata, slično FILMIUM home stranici, ali za
razvoj. CODIUM landing prestaje da bude placeholder.

## Lokacija

- `apps/gui/src/features/codium/` (prati `features/filmium/` obrazac)
- GUI zove backend preko service/hook sloja (kao filmium), nikad direktno bazu.

## Glavni prikaz — kartice projekata

Svaka kartica:
- screenshot / preview slika (fallback: design reference ili prazna)
- naziv projekta
- client / private oznaka
- status
- najbliži rok
- tehnologije (stack)
- poslednji rad (`last_opened_at`)
- dugmad: Otvori, Preview, Dev-log, Tasks

## Sekcije

- Aktivni projekti
- Klijentski projekti
- Privatni projekti
- Nedavno otvarano
- Rokovi ove nedelje
- Ideje / eksperimenti

## Filteri

All · Client · Private · Active · Paused · Finished · Web · Python · Tauri · React · AI

## CODIUM sidebar (dugmad)

Projekti · Explorer · Editor · Preview · Terminal · Git · AI Chat · Tasks · Beleške ·
Kalendar · Settings

U v0.1 aktivno samo: **Projekti, Tasks, Beleške, Settings**. Ostalo je vidljivo ali
vodi na "uskoro" dok se ne izgrade faze F4+.

## Screenshot projekta

Kartica čuva screenshot. Izvori (redom): manual upload → screenshot preview prozora →
poslednji live preview → design reference fallback. Fajlovi u `data/codium/` preko
`CodiumPaths` (assets folder).

## Add / Open projekat

- **Add Project:** unos naziva, tipa, visibility (client/private), local_path,
  opciono client. Upisuje Project red preko F1 servisa.
- **Open Project:** postavlja aktivni projekat u kontekstu (bitno za auto-vezivanje
  beleški iz F1).

## Definicija gotovog (F2)

- [x] Landing prikazuje kartice iz baze (ne mock podaci).
- [x] Add/Open projekat radi kroz F1 API.
- [x] Filteri i bar 3 sekcije rade (Nedavno / Aktivni / Klijentski / Privatni).
- [x] Client/private vizuelno razdvojeni (badge + zasebne sekcije).
- [x] Aktivan projekat se pamti u kontekstu (localStorage `codium.activeProjectId`).

## Napomene

- Vizuelni jezik i layout: prati postojeći filmium home + `codium.css` temu.
- Ne graditi editor/preview ovde — to su F4/F6.
