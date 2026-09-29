---
id: codium-970a80a2-2026-08-30-codium-e3b-pipelines-gui-design-md
type: spec
domain: codium
namespace: global
visibility: global
tier: domain
title: E3b — Pipelines (ekran)
summary: '**Datum:** 2026-08-30'
keywords:
- e3b
- pipelines
- ekran
- docs
- superpowers
- specs
tags:
- superpowers
- specs
source_path: docs/superpowers/specs/2026-08-30-codium-e3b-pipelines-gui-design.md
---

# E3b — Pipelines (ekran)

**Datum:** 2026-08-30
**Faza:** E3b (fazni fajl `.ai/izgradnja/codium/13-E3-pipelines.md`)
**Zavisi od:** E3a (motor, baza, API), F6 Monaco, E2 (registar repozitorijuma)

---

## 1. Zašto

E3a je dao motor, bazu i API, ali nijedan čovek ih ne vidi. Pipeline se danas
definiše i pokreće samo kroz `curl`, log se čita kroz `GET` sa `after_seq`, a
sidebar stavka „Pipelines" i dalje stoji kao „uskoro". Overview pločica tvrdi
`3 / 4 running` — brojka koja je tvrdo ukucana i nikad nije bila istinita.

Ova faza zatvara E3: ekran koji definiše, pokreće, prati i otkazuje pokretanja.

## 2. Odnos prema E3a

E3 je namerno podeljen na dva ciklusa (odluka korisnika 2026-08-30). E3a je motor
i API; E3b je ekran. Backend se u ovoj fazi **ne dira** — sve što ekranu treba
već postoji pod `/api/v1/codium/pipelines`:

| Metoda | Putanja |
|---|---|
| GET | `/` (`?repository_id=`) |
| POST | `/` |
| PUT | `/{id}` |
| DELETE | `/{id}` |
| POST | `/{id}/run` |
| GET | `/runs` (`?pipeline_id=&status=&limit=`) |
| GET | `/runs/{run_id}` |
| GET | `/runs/{run_id}/logs` (`?after_seq=`) |
| POST | `/runs/{run_id}/cancel` |

Ako se u toku rada pokaže da ekranu treba nešto što API ne daje, to je nalaz za
zaseban posao, ne tiha dopuna backend-a usred GUI faze.

## 3. Odluke donete pre pisanja

Iz razgovora 2026-08-30.

1. **Samo strana `/codium/pipelines`, bez panela u workspace-u.** Pokretanje
   traje minutima i gleda se s vremena na vreme; nije nešto uz šta se kuca kod.
   Git panel iz E2 jeste bio takav, ovo nije.
2. **Sopstveni ANSI parser**, ne ugrađen `@xterm/xterm`. Paket jeste već
   zavisnost (F5 terminal), ali nosi pun emulator — kursor, istoriju skrolovanja,
   obradu tastature, svoj kanvas. Za prikaz koji se samo čita to je mnogo mašine,
   i teško se testira, jer xterm traži pravi DOM.
3. **Monaco sa registrovanom JSON šemom.** Čovek dobija dopunjavanje imena polja
   i podvučenu grešku pre snimanja. Server ostaje autoritet.
4. **Upozorenje pri zatvaranju prozora dok pokretanje traje**, kroz Tauri
   `onCloseRequested`. Van Tauri-ja no-op. Bez Rust promene.
5. **Prikaz loga staje na poslednjih 2000 redova**, uz traku koja kaže koliko je
   sakriveno i nudi „učitaj sve". Redovi ostaju u bazi; seče se samo prikaz.

## 4. Raspored strane i čisti moduli

Jedna ruta, `/codium/pipelines`, tri kolone koje se sažimaju na užem prozoru.

```
apps/gui/src/pages/CodiumPipelines.tsx     strana, drži izbor i sastavlja
apps/gui/src/features/codium/pipelines/
    usePipelines.ts        lista po repozitorijumu, snimanje, brisanje
    useRunPolling.ts       detalj pokretanja + inkrementalni log
    PipelineList.tsx       lista sa ishodom poslednjeg pokretanja
    DefinitionEditor.tsx   Monaco u `json` režimu, „Snimi" i „Pokreni"
    RunHistory.tsx         pokretanja izabranog pipeline-a
    RunDetail.tsx          koraci koji se šire + log
    RunLog.tsx             prikaz loga, granica i traka „starije skriveno"
    ansi.ts                ANSI tekst → komadi sa bojom (čist modul)
    definitionSchema.ts    JSON Schema definicije (čist podatak)
    runBadges.ts           status → tekst i klasa značke (čist modul)
apps/gui/src/styles/codium-pipelines.css
```

Tri modula su čista i nose većinu testova: `ansi.ts`, `definitionSchema.ts`,
`runBadges.ts`. Nijedan ne dodiruje React ni mrežu — isti obrazac koji je
`repoBadges.ts` iz E2 opravdao.

### `ansi.ts`

`parseAnsi(text: string): AnsiChunk[]`, gde je
`AnsiChunk = { text: string; color?: string; bold?: boolean }`.

Pokriva ono što alati stvarno šalju: `\x1b[0m` reset, kodove `30–37` i `90–97`
za boju, `1` za podebljano. **Sve ostalo se tiho guta** — pozicioniranje kursora,
brisanje reda, nepoznati kodovi. Nepoznat niz ne sme da se ispiše kao smeće; on
nestaje. Nezavršen niz na kraju ulaza ne obara parser.

Boja putuje kao ime klase (`ansi-red`), ne kao inline stil, da tema može da je
pregazi.

### `runBadges.ts`

`runBadge(run): { label: string; className: string }` za svih šest statusa
(`queued`, `running`, `success`, `failed`, `cancelled`, `timeout`), plus
`runDuration(run): string` iz `started_at` i `finished_at`.

### Sidebar

Stavka `pipelines` prelazi iz `kind: "soon", phase: "F14"` u
`kind: "route", path: "/codium/pipelines"`.

## 5. Polling i život pokretanja

`useRunPolling(runId)` vraća `{ run, steps, lines, hiddenCount, isPolling, error, showAll }`.

- Na izbor pokretanja: jedan `GET /runs/{id}` i jedan `GET /runs/{id}/logs?after_seq=0`.
- Dok je status `queued` ili `running`: na **500 ms** se dohvataju oboje, a log
  samo od poslednjeg viđenog `seq`. Preko žice ide prirast, ne ceo log.
- Čim status pređe u završni: **još jedan poslednji poziv**, pa se petlja gasi.
  Taj poziv nije višak — poslednja serija loga stiže iz sink-a tek na `flush()`
  pri kraju pokretanja, pa bi bez njega poslednji redovi nedostajali.
- `setTimeout`, ne `setInterval`: spor odgovor ne sme da naslaže zahteve jedan
  preko drugog.
- Čišćenje u `useEffect` gasi tajmer i podiže zastavicu otkazivanja, pa odgovor
  koji stigne posle promene izbora ne upisuje tuđe stanje. Isti obrazac koji
  `CommitHistory` iz E2 već koristi.

### Granica prikaza

`lines` drži poslednjih **2000** redova; `hiddenCount` kaže koliko je ispalo.
Traka iznad loga piše koliko je starijih redova sakriveno i nudi „učitaj sve",
što jednom povuče ceo log od `seq=0` i ukine granicu za to pokretanje.

### Skrol

Automatski skrol radi **samo dok je čovek na dnu**. Čim odskroluje gore, skrol se
ne pomera pod njim; dugme „na dno" ga vraća i ponovo uključuje praćenje. Prikaz
koji otima skrol dok čitaš grešku je gori od prikaza bez skrola.

### Upozorenje pri zatvaranju

Strana broji pokretanja u toku. Dok ih ima, `getCurrentWindow().onCloseRequested`
traži potvrdu sa porukom šta će se prekinuti. Van Tauri-ja no-op, kao
`openAiChatWindow`. Bez Rust promene.

## 6. Uređivač definicije

`DefinitionEditor` montira Monaco u `json` režimu.

**Šema se registruje ograničeno.** `monaco.languages.json.jsonDefaults.setDiagnosticsOptions`
je **globalan** za celu aplikaciju, a F6 editor otvara `.json` fajlove kroz isti
Monaco. Zato šema ide sa `fileMatch` na namenski URI modela
(`inmemory://codium/pipeline-definition.json`), koji uređivač zadaje svom modelu
preko `path`. Bez toga bi šema pipeline-a podvlačila greške u `package.json`-u
koji čovek otvori u Explorer-u.

`definitionSchema.ts` je običan objekat: `name` i `steps` obavezni, `steps`
neprazan niz, korak traži `name` i `run`, `timeout_minutes` pozitivan ceo broj,
`env` mapa `string→string`, `working_dir` i `continue_on_error` opcioni.

Server ostaje autoritet: „Snimi" šalje tekst kakav jeste, a 400 sa porukom iz
`DefinitionError` se prikazuje iznad uređivača. Šema skraćuje petlju, ne
zamenjuje proveru.

## 7. Overview pločica

Pločica „Pipelines" danas piše tvrdo ukucano `3 / 4` sa oznakom „uskoro". Prelazi
na stvarno stanje: broj pipeline-a, koliko ih trenutno radi, i ishod poslednjeg
pokretanja. Klik vodi na stranu.

Pad poziva ostavlja nule i ne obara Overview — isto pravilo koje pločica
repozitorijuma iz E2 već poštuje.

## 8. Tipovi i API klijent

`types/codium.ts` dobija `Pipeline`, `PipelineRun`, `RunStep`, `RunLogLine` i
omotače odgovora (`PipelinesResponse`, `RunsResponse`, `RunDetailResponse`,
`RunLogsResponse`, `CancelResponse`), plus `PipelineCreateRequest` i
`PipelineUpdateRequest`.

`services/codiumApi.ts` dobija devet poziva, po jedan za svaku rutu iz E3a.
Vrednosti u upitu idu kroz `encodeURIComponent`, kao u E2.

## 9. Testovi

- `ansi.test.ts` — običan tekst bez nizova; boja pa reset; podebljano; svetle
  varijante; nepoznat niz nestaje umesto da se ispiše; nezavršen niz na kraju ne
  obara parser.
- `definitionSchema.test.ts` — ista tabela slučajeva koju `test_pipeline_definition.py`
  već proverava, kroz validator šeme. Šema koja dozvoljava ono što server odbija
  je gora od nikakve, jer laže pre snimanja.
- `runBadges.test.ts` — svih šest statusa i računanje trajanja.
- `useRunPolling.test.ts` — petlja se gasi na završni status, sa još jednim
  pozivom posle njega; `after_seq` raste; promena izbora ne upisuje stari odgovor.
- `CodiumPipelines.test.tsx` — prazan registar; lista sa ishodom; izbor pipeline-a
  dohvata istoriju; „Pokreni" zove API; neispravna definicija pokazuje poruku sa
  servera.

## 10. Definicija završetka

Pipeline se definiše i snima kroz Monaco sa podvučenim greškama, pokreće se sa
strane, log stiže inkrementalno dok radi, boje se vide, pokretanje se otkazuje;
sidebar stavka vodi na rutu; Overview pločica pokazuje stvarno stanje; zatvaranje
prozora dok pokretanje traje traži potvrdu; testovi prolaze i `tsc` ne dobija
nove greške.

## 11. Van dometa svesno

- Bilo kakva izmena backend-a. E3a je zatvoren.
- Panel u workspace-u.
- Okidači osim ručnog — E10 Automations.
- Uređivanje definicije bilo gde osim na ovoj strani.
- Prikaz uživo u pravom terminalskom prozoru.
- Dve postojeće `tsc` greške (`CoreDockLayout.tsx` TS2503, `CodiumWorkspace.tsx`
  TS6133) prethode ovoj grani i ne popravljaju se ovde; merilo je da nema **novih**.
