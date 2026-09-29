---
id: codium-ce1ac450-08-preview-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: F7 — Preview Orchestrator (MVP)
summary: 'Status: **zavrseno (MVP)** (2026-08-18). Prioritet: v0.3. Redosled: rađen
  posle F8.'
keywords:
- preview
- orchestrator
- mvp
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/08-preview.md
---

# F7 — Preview Orchestrator (MVP)

Status: **zavrseno (MVP)** (2026-08-18). Prioritet: v0.3. Redosled: rađen posle F8.

## Cilj

Otvoriti preview projekta kao zaseban Tauri prozor koji učitava spoljni URL
(dev server / staging / live), u izabranoj veličini uređaja i na izabranom
monitoru. Reuse postojeće CORE multi-window infrastrukture (`features/window/`).

MVP granica: **dev server pokreće korisnik ručno** i unosi URL. Auto-detekcija
komande iz `package.json`/`pyproject`, screenshot za karticu i move-to-monitor
uživo dolaze kasnije.

## Urađeno

### Čist sloj (testabilno, bez Tauri)
- `features/codium/previewProfiles.ts`:
  - `PreviewDevice` = desktop | tablet | mobile | custom; standardne veličine
    (1280×800 / 768×1024 / 375×812).
  - `resolvePreviewSize(device, custom)` — custom uz clamp (200..7680).
  - `normalizePreviewUrl(raw)` — dodaje `http://` ako nema šeme; nevalidno → null.
  - `previewWindowLabel(projectId)` — stabilan label prozora po projektu.

### Tauri sloj (no-op van desktop-a)
- `features/codium/previewOrchestrator.ts`:
  - `listPreviewMonitors()` — `availableMonitors()` → {name,x,y,w,h}.
  - `openPreview({projectId,url,size,title,monitorName})` — zatvori prethodni
    prozor istog projekta, otvori nov `WebviewWindow` na URL-u i veličini, uz
    poziciju na izabranom monitoru. Ista funkcija služi i kao „reload".
  - `closePreview(projectId)` — `WebviewWindow.getByLabel(...).close()`.
  - Guard `isTauri()` iz `features/window/windowManager` — sve no-op u browseru.

### GUI
- `features/codium/PreviewModal.tsx` — URL unos (prefill iz projekta:
  preview/staging/live), izbor uređaja, custom dimenzije, izbor monitora (kad ih
  ima >1), prikaz veličine, dugmad Otvori/Reload/Zatvori. Van Tauri-ja: napomena
  da radi samo u desktop aplikaciji. Postavke po projektu u localStorage
  (`codium.preview.<id>`).
- `pages/CodiumPage.tsx` — „Preview" dugme na kartici (bilo `disabled title="Uskoro (F7)"`)
  sada otvara PreviewModal.
- CSS u `styles/codium-hub.css` (sekcija „PREVIEW MODAL (F7)").

### Tauri kapabilnosti
Već postoje u `src-tauri/capabilities/default.json`:
`core:webview:allow-create-webview-window`, `allow-available-monitors`,
`allow-set-size/position`, `allow-close`, `allow-set-focus`. Nema izmene.

## Testovi
- `previewProfiles.test.ts` — 7 (veličine, custom clamp, NaN, URL normalizacija, label).
- `PreviewModal.test.tsx` — 4 (prikaz URL/uređaja, van-Tauri poruka, prazan URL,
  custom polja).

## Provera uživo (browser)
Modal, prebacivanje uređaja (Mobilni → 375×812), i poruka „radi samo u desktop
aplikaciji" potvrđeni u preview-u. **Samo otvaranje Tauri prozora se ne može
proveriti u browseru** — zahteva desktop build (dokumentovana ograda).

## Van opsega (kasnije)
- Auto-detekcija dev komande i pokretanje/gašenje servera iz CODIUM-a.
- Screenshot preview prozora → sačuvaj uz karticu projekta (F2).
- Move-to-monitor uživo (bez ponovnog otvaranja), više preview prozora odjednom.
