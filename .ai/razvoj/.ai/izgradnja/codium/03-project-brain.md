---
id: codium-058228c1-03-project-brain-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: F3 — CODIUM Project Brain
summary: 'Prioritet: v0.1. Status: vidi [00-INDEX.md](00-INDEX.md).'
keywords:
- codium
- project
- brain
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/03-project-brain.md
edges:
- type: references
  target: codium-66d262ea-00-index-md
  weight: 0.3
---

# F3 — CODIUM Project Brain

Prioritet: v0.1. Status: vidi [00-INDEX.md](00-INDEX.md).

## Cilj

Svaki projekat dobija folder sa instrukcijama i istorijom rada. Projektni ekvivalent
`.ai/` foldera. Danas ga čita Claude/Codex; kasnije lokalni CODIUM agent. Zato format
mora biti stabilan i jednostavan.

## Lokacija

Podržati oba:
- Lokalni repo projekta: `<project>/.codium/`
- CODIUM registry (za projekte bez repo-a): `data/codium/projects/<project-id>/brain/`

`Project.project_brain_path` (iz F1) pokazuje na aktivnu lokaciju.

## Struktura foldera

```
.codium/
  project.md          naziv, opis, stack, putanja, repo, live/staging, vlasnik, klijent, status
  instructions.md     pravila za AI: kako čitati, šta ne dirati, stil koda, bitni fajlovi, komande
  architecture.md     struktura app, moduli, granice, backend/frontend, baza/API/integracije
  goals.md            ciljevi projekta
  tasks.md            taskovi (ogledalo Task tabele iz baze, čitljivo)
  decisions.md        donete odluke (decision log)
  testing.md          kako pokrenuti testove, šta je prolaz, šta ako padne
  security.md         secret handling, input validation, auth, dependency rizik
  known-issues.md     poznati problemi / rizici
  handoff.md          stanje za sledeću sesiju/executora
  dev-log/
    INDEX.md
    entries/YYYY-MM-DD.md
  design/             reference slike, tokeni, screenshotovi, UI odluke
  context/            dodatni kontekst
  assets/             projektni asseti
```

## Generisanje foldera

CODIUM servis (backend) generiše `.codium/` skelet:
- popuni `project.md` iz Project reda (F1)
- ostali fajlovi = template sa naslovima sekcija
- ako folder već postoji, ne prepisuje — samo dopunjava što fali

## Dev-log format

Svaka veća izmena = unos u `dev-log/entries/YYYY-MM-DD.md`:
- cilj
- urađeno
- testovi / provera
- sledeće
- napomene
- executor / model

## Prikaz u GUI-u

- Dugme "Dev-log" na kartici projekta (F2) otvara `dev-log/INDEX.md`.
- Prikaz `instructions.md` i `project.md` u project panelu (read-only u v0.1).

## Definicija gotovog (F3)

- [x] Servis generiše `.codium/` skelet za projekat (oba mesta podržana).
- [x] `project.md` se popunjava iz baze.
- [x] Postojeći folder se ne prepisuje.
- [x] Dev-log unos se može kreirati i pročitati.
- [x] GUI prikazuje project brain (read-only).

## Napomene

- Format namerno prost (Markdown), da ga i lokalni model kasnije lako čita.
- Ovo je most ka F11 (AI Development Protocol) — protokol će čitati ovaj folder.
