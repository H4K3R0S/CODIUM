---
id: codium-8c75f889-07-notes-agenda-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: F8 — Notes / agenda / kalendar
summary: 'Status: **zavrseno** (2026-08-18). Prioritet: v0.2.'
keywords:
- notes
- agenda
- kalendar
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/07-notes-agenda.md
---

# F8 — Notes / agenda / kalendar

Status: **zavrseno** (2026-08-18). Prioritet: v0.2.

## Cilj

Objediniti rokove i podsetnike koji već postoje u bazi (F1) u jedan pregled:
- Task `due_at`
- Beleška `reminder_at` (samo aktivne)
- Projekat `deadline_at` (preskoči završene/arhivirane)

Bez nove migracije — sve tri kolone već postoje iz F1.

## Urađeno

### Backend
- `models.AgendaItem` — jedinstvena stavka (kind task|note|project, ref_id, title,
  at, overdue, project_id, client_id, status, priority). Nije red u bazi, izvodi se.
- `service.list_agenda(days_ahead=14, include_overdue=True, project_id=None, now=None)` —
  spaja tri izvora, filtrira na prozor [sada, sada+days_ahead] (+ probijeni rokovi ako
  `include_overdue`), sortira rastuće po vremenu. `now` parametar za determinističke testove.
- `service._parse_iso` — tolerantno parsira ISO (pun timestamp, 'Z' sufiks, offset,
  goli datum → ponoć UTC); naivno se tretira kao UTC.
- API `GET /api/v1/codium/agenda?days_ahead&include_overdue&project_id` (clamp 0..365).
- Schema `AgendaItemResponse` + `AgendaResponse`.

### Frontend
- `types/codium.ts` — `AgendaItem`, `AgendaKind`, `AgendaResponse`.
- `services/codiumApi.getAgenda({daysAhead, includeOverdue, projectId})`.
- `features/codium/AgendaPanel.tsx` — dva prikaza:
  - **Lista**: grupisano po hitnosti (Probijen rok / Danas / Narednih 7 dana / Kasnije),
    bedž broja u kašnjenju, ikone po tipu.
  - **Mesec**: kalendar grid (pon-prvi), tačka + broj stavki po danu, crvena za kašnjenje,
    klik na dan otvara listu tog dana. Navigacija prethodni/sledeći mesec.
- Ugrađen na CODIUM hub (`pages/CodiumPage.tsx`) iznad sekcija projekata.
- CSS u `styles/codium-hub.css` (sekcija „AGENDA I ROKOVI (F8)").

## Testovi
- `tests/test_codium_service.py` — 5 agenda testova (spoj, prozor, overdue+toggle,
  preskače done task, filter po projektu).
- `tests/test_api_codium.py` — 3 agenda testa (prazno, upcoming+overdue, exclude_overdue).
- `AgendaPanel.test.tsx` — 4 (prazno, lista+broj kašnjenja, prebacivanje na mesec, projectId).

## Van opsega (kasnije)
- Podsetnik notifikacije (system tray / push).
- Google/Outlook kalendar sync — kroz CORE `integrations/`.
- Prikaz agende i na CORE glavnom dashboardu (sada samo CODIUM hub).
