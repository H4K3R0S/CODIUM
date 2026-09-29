---
id: codium-cfe07b7b-13-e3-pipelines-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E3 — Pipelines (sopstveni lokalni runner)
summary: 'Ova faza je izradjena u dva dela umesto kao jedan blok backend+GUI:'
keywords:
- pipelines
- sopstveni
- lokalni
- runner
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/13-E3-pipelines.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E3 — Pipelines (sopstveni lokalni runner)

## Podela na E3a i E3b (2026-08-30)

Ova faza je izradjena u dva dela umesto kao jedan blok backend+GUI:

- **E3a** (zavrsen 2026-08-30) — modeli i parser definicije, migracije
  **`codium v11`** i **`ops v3`** (ne `v6`/`ops v2` kako pise ispod — ti
  brojevi su bili slobodni kad je ovaj fajl pisan, potroseni su medjutim
  ranije istog dana od strane E1/E2), motor sa otkazivanjem i istekom,
  serijski upis loga, `PipelineService` kroz ScopeGate, API sa oporavkom pri
  startu, agentski alati `run_pipeline`/`list_pipeline_runs`.
- **E3b** (zavrsen 2026-09-01) — ekran: stranica, Monaco JSON editor sa
  registrovanom semom, prikaz pokretanja sa logom i ANSI bojama, Overview
  plocica, potvrda pri zatvaranju prozora u toku pokretanja.

Odeljak o tajnama (`${{ secret.alias }}`, maskiranje u logu) nize u ovom
fajlu ceka **E4**, koji donosi prvog potrosaca — ni E3a ni E3b ga ne diraju.

### E3b — odluke iz razgovora koje ovaj fajl gore ne nosi (2026-09-01)

- **Strana zivi samo na `/codium/pipelines`, bez panela u workspace-u** — za
  razliku od E2 (Git panel u docking rasporedu). Pun prikaz pokretanja
  (Monaco + log uzivo) trazi vise prostora nego docking panel nudi.
- **ANSI boje idu kroz sopstveni parser, ne kroz ugradjeni `@xterm/xterm`.**
  Prikaz je read-only; pravi terminalski emulator bi povukao celu zavisnost
  (interakcija, kursor, resize) za nesto sto samo boji tekst.
- **Monaco JSON sema je vezana preko `fileMatch`** na namenskoj in-memory
  putanji modela — `setDiagnosticsOptions` je globalno Monaco stanje, bez
  ogranicenja bi podvlacila greske u svakom `package.json` otvorenom kroz F6.
- **Prikaz loga staje na 2000 redova**, sa trakom za ucitavanje ostatka;
  redovi ostaju u bazi u potpunosti.

Nista od E3b nije provereno kroz pravi pokrenut CORE — automatski skup
(815 vitest, 1598 pytest, dve postojece greske tipova bez novih) je jedini
dokaz. Puna lista provera uzivo je u dev-log unosu `2026-09-01.md`.

**Blok:** razvojna loza · **Zavisi od:** E1, E2 · **Migracija:** codium v6 + ops v2
**Sidebar:** `Pipelines`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

CODIUM sam pokreće nizove komandi nad repozitorijumom (instalacija, lint, testovi,
build), pamti svako pokretanje i čuva pun log. Ovo je najveći deo posla u bloku i
temelj za E4 Deployments, E7 Analytics i E10 Automations.

## Zašto motor ide u Python backend

Odluka korisnika, potvrđena 2026-08-22.

Tauri PTY sloj (T0–T7, `portable-pty`) je interaktivan terminal vezan za otvoren
panel u GUI-ju. Pipeline mora da:

- radi i kada je panel zatvoren ili je aplikacija u drugom domenu,
- ima istoriju pokretanja i trajno sačuvan log,
- bude pokretljiv iz automatizacije (E10), gde GUI uopšte nije u igri.

Zato motor koristi `asyncio.create_subprocess_exec` u backend-u. Prikaz uživo u
pravom terminalskom prozoru je moguć kasnije kao **dodatni sloj nad istim motorom**,
ne kao njegova zamena.

## Definicija pipeline-a

**JSON**, čuva se u bazi kao tekst i validira pri snimanju.

Odluka (2026-08-22): JSON, ne YAML. Python ga čita ugrađenim modulom `json`, pa
faza ne uvodi nijednu novu zavisnost. YAML bi tražio `PyYAML` i pun postupak
registracije alata iz `docs/DEPENDENCIES.md` — trošak koji se ne isplati za
format koji korisnik ionako najčešće uređuje kroz GUI.

```json
{
  "name": "test-i-build",
  "timeout_minutes": 20,
  "env": { "CI": "1" },
  "steps": [
    { "name": "instalacija", "run": "npm ci" },
    { "name": "lint", "run": "npm run lint", "continue_on_error": true },
    { "name": "testovi", "run": "npm test" },
    { "name": "build", "run": "npm run build", "working_dir": "apps/gui" }
  ]
}
```

Monaco ima ugrađenu podršku za JSON sa proverom šeme, pa uređivač u GUI-ju dobija
dopunjavanje i podvučene greške besplatno — dovoljno je registrovati JSON šemu
definicije.

Pravila:

- `run` se izvršava kao lista argumenata kroz shell repozitorijuma; `working_dir`
  je uvek relativan na koren repozitorijuma i ne sme da izađe iz njega. **Provera
  se ne piše iznova** — koristi se `_safe(rel)` iz
  `core/domains/codium/explorer.py`, koji tačno to već radi za Explorer.
- Koraci idu redom. Neuspeh prekida pokretanje osim ako korak nosi
  `continue_on_error: true`.
- `timeout_minutes` važi za celo pokretanje; istek gasi stablo procesa.
- `env` se spaja sa okruženjem procesa; vrednosti mogu da referišu tajnu iz E0
  zapisom `${{ secret.alias }}`, koja se razrešava tek u trenutku pokretanja i
  **nikada** se ne upisuje u log (zamenjuje se sa `***`).

## Backend

`core/domains/codium/pipelines/`

- `models.py` — `Pipeline`, `PipelineRun`, `RunStep`, `RunLogLine`,
  `RunStatus` (`queued`, `running`, `success`, `failed`, `cancelled`, `timeout`).
- `definition.py` — parsiranje i validacija JSON definicije. Čist modul, bez
  ulaza/izlaza; najlakši deo za testiranje.
- `runner.py` — motor. Jedan `PipelineRunner` po procesu API-ja:

  ```
  PipelineRunner
      start(pipeline_id, trigger) -> PipelineRun     # ne blokira
      cancel(run_id) -> None
      is_running(run_id) -> bool
  ```

  Pokretanje ide kao `asyncio.Task`. Po koraku se pravi podproces sa `cwd` na
  korenu repozitorijuma, `stdout` i `stderr` se čitaju red po red i upisuju u
  `codium_run_logs` sa rastućim `seq`. Upis u bazu ide u serijama (do 50 redova
  ili 200 ms), da hiljadu redova loga ne znači hiljadu transakcija.
- `repository.py`, `service.py` — CRUD nad definicijama i pokretanjima, upit
  logova od zadatog `seq`.

Otkazivanje i istek gase **celo stablo procesa**, ne samo direktno dete. Na
Windows-u to znači `taskkill /T`, na ostalim sistemima grupa procesa.

Pri startu API-ja svako pokretanje zatečeno u stanju `running` prelazi u
`failed` sa napomenom da je aplikacija restartovana. Bez toga zaostala pokretanja
zauvek vise u „radi".

### Prihvaćeno ograničenje: zatvaranje aplikacije prekida pokretanje

Runner živi u procesu FastAPI backend-a. Gaseći CORE, gasiš i pokretanje koje
traje. Ovo se **prihvata** u prvom rezu — odvojen proces koji preživljava
aplikaciju je zaseban posao i ne vredi ga uzimati sada.

Obaveze koje iz toga slede:

- GUI pri zatvaranju prozora proverava da li neko pokretanje traje i, ako traje,
  traži potvrdu sa jasnom porukom šta će se prekinuti.
- Pokretanje prekinuto gašenjem dobija status `failed` sa razlogom
  „aplikacija zatvorena", da se u istoriji razlikuje od pravog pada.

### ScopeGate i audit

`pipeline.run` prolazi kroz gate pre pokretanja. Pokretanje koje traži tajnu
dodatno traži `secret.read` za taj alias. Početak, kraj i izlazni kod svakog
pokretanja idu u audit.

## Šema

Podela na dve baze po pravilu iz [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md):
definicije, pokretanja i koraci su poslovni podaci i idu u `codium.db` (**v6**);
`codium_run_logs` je append-heavy i ide u `codium_ops.db` (**ops v2**).

### `codium.db` — migracija v6

```sql
CREATE TABLE codium_pipelines (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL REFERENCES codium_repositories (id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    definition    TEXT NOT NULL,          -- JSON
    enabled       INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE codium_pipeline_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL REFERENCES codium_pipelines (id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'queued',
    trigger     TEXT NOT NULL DEFAULT 'manual',  -- manual | automation | api
    commit_sha  TEXT,
    branch      TEXT,
    exit_code   INTEGER,
    started_at  TEXT,
    finished_at TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_runs_pipeline ON codium_pipeline_runs (pipeline_id, id DESC);

CREATE TABLE codium_run_steps (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL REFERENCES codium_pipeline_runs (id) ON DELETE CASCADE,
    idx        INTEGER NOT NULL,
    name       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'queued',
    exit_code  INTEGER,
    started_at TEXT,
    finished_at TEXT
);

```

### `codium_ops.db` — migracija ops v2

```sql
-- Bez stranog ključa: `run_id` pokazuje na red u drugoj bazi. Čišćenje logova
-- posle brisanja pokretanja radi posao održavanja, ne kaskada.
CREATE TABLE codium_run_logs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  INTEGER NOT NULL,
    step_idx INTEGER NOT NULL,
    seq     INTEGER NOT NULL,
    stream  TEXT NOT NULL DEFAULT 'stdout',   -- stdout | stderr
    line    TEXT NOT NULL,
    at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_run_logs_seq ON codium_run_logs (run_id, seq);
```

Zadržavanje: pun log se čuva za poslednjih 50 pokretanja po pipeline-u; starijima
ostaje samo zaglavlje sa statusom i trajanjem.

## API

`apps/api/routers/codium_pipelines.py`, prefiks `/api/v1/codium/pipelines`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/` | pipeline-i (`?repository_id=`) |
| POST | `/` | nov (validira JSON definiciju pri upisu) |
| PUT | `/{id}` | izmena definicije |
| DELETE | `/{id}` | brisanje |
| POST | `/{id}/run` | pokretanje; vraća `run_id` odmah |
| GET | `/runs` | istorija (`?pipeline_id=&status=&limit=`) |
| GET | `/runs/{run_id}` | zaglavlje + koraci |
| GET | `/runs/{run_id}/logs` | `?after_seq=` — inkrementalno |
| POST | `/runs/{run_id}/cancel` | otkazivanje |

Live log se dobija polling-om `logs?after_seq=` na 500 ms dok je status
`running`. Bez WebSocket-a, u skladu sa pravilom CORE-a.

## GUI (radi se posle backend-a bloka)

`pages/CodiumPipelines.tsx`:

- Lista pipeline-a po repozitorijumu, sa ishodom poslednjeg pokretanja.
- Uređivač definicije — Monaco u `json` režimu sa registrovanom šemom; greške se
  podvlače u uređivaču, bez posebnog polja za poruku.
- Detalj pokretanja: koraci kao lista koja se širi, log sa automatskim skrolom i
  ANSI bojama (`@xterm/xterm` je već zavisnost projekta; koristi se samo parser boja).
- Dugme „Otkaži" dok pokretanje traje.

### Overview pločica

`apps/gui/src/pages/CodiumOverview.tsx` već ima pločicu „Pipelines" koja ništa ne
prikazuje. Ova faza je oživljava: ishod i vreme poslednjeg pokretanja, broj
pokretanja koja trenutno rade, i klik koji vodi na ekran. Bez toga Overview
tvrdi da sekcija postoji a ne pokazuje ništa.

## Testovi

- `test_pipeline_definition` — validna JSON definicija, nedostajuće polje, `working_dir` koji
  pokušava da izađe iz repozitorijuma, razrešavanje `${{ secret.alias }}`.
- `test_pipeline_runner` — pokretanje sa dva trivijalna koraka (`python -c ...`)
  daje `success` i ispravan redosled `seq`; korak koji vraća ne-nulti kod prekida
  pokretanje; `continue_on_error` ga ne prekida; otkazivanje postavlja `cancelled`;
  istek postavlja `timeout`.
- `test_pipeline_secrets` — vrednost tajne se ne pojavljuje ni u jednom redu loga.
- `test_pipeline_recovery` — pokretanje u stanju `running` posle restarta prelazi
  u `failed`.
- `test_api_codium_pipelines` — `after_seq` vraća samo nove redove.

## Definicija završetka

Pipeline se definiše, snima, pokreće i otkazuje; log se čita inkrementalno tokom
rada; tajne ne cure u log; zaostala pokretanja se čiste pri startu; testovi domena
prolaze.
