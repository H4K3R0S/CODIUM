---
id: codium-aeff2a12-2026-08-30-codium-e3a-pipelines-design-md
type: spec
domain: codium
namespace: global
visibility: global
tier: domain
title: E3a — Pipelines (motor, baza i API)
summary: '**Datum:** 2026-08-30'
keywords:
- e3a
- pipelines
- motor
- baza
- api
- docs
- superpowers
- specs
tags:
- superpowers
- specs
source_path: docs/superpowers/specs/2026-08-30-codium-e3a-pipelines-design.md
---

# E3a — Pipelines (motor, baza i API)

**Datum:** 2026-08-30
**Faza:** E3a (fazni fajl `.ai/izgradnja/codium/13-E3-pipelines.md`)
**Zavisi od:** E1 (ScopeGate, dnevnik), E2 (registar repozitorijuma), F5 Explorer (`_safe`)

---

## 1. Zašto

CODIUM danas ne ume da pokrene ništa nad repozitorijumom. Instalacija, lint,
testovi i build rade se u terminalu sa strane, ne ostavljaju trag i ne mogu se
pokrenuti iz automatizacije. Zbog toga E4 Deployments nema šta da izgradi pre
isporuke, E7 Analytics nema nad čim da računa, a E10 Automations nema šta da
okine.

Ova faza donosi motor koji pokreće nizove komandi nad registrovanim
repozitorijumom, pamti svako pokretanje i čuva pun log.

## 2. Podela E3 na dva ciklusa

Odluka korisnika (2026-08-30). Fazni fajl `13-E3-pipelines.md` opisuje motor,
bazu, API, ekran sa Monaco uređivačem, prikaz loga sa ANSI bojama i Overview
pločicu — više posla nego što je cela faza E2 bila.

- **E3a (ovaj dokument):** definicija, motor, baza, API, alati agenta.
  Upotrebljivo kroz API i testove, i odmah otključava E4.
- **E3b (kasnije, svoj spec i svoj plan):** strana `/codium/pipelines`, Monaco
  JSON uređivač sa registrovanom šemom, detalj pokretanja sa logom u bojama,
  Overview pločica, potvrda pri zatvaranju prozora dok pokretanje traje.

Razlog podele: jedan plan od dvadesetak zadataka gubi se u sopstvenoj dužini, a
motor i ekran nemaju zajedničke odluke koje bi morale da se donesu istovremeno.

## 3. Odluke donete pre pisanja

Iz razgovora 2026-08-30; nadjačavaju fazni fajl gde se razilaze.

1. **Tajne izlaze iz dometa.** Fazni fajl traži `${{ secret.alias }}` sa
   maskiranjem u logu, ali vault čuva tajne pod nasumičnim aliasom vezanim za
   konektor, pa „alias" iz primera ne postoji kao pojam koji bi čovek kucao.
   Lokalni pipeline (`npm ci`, lint, testovi, build) ne traži nijednu tajnu; prvi
   stvarni potrošač je E4 Deployments. Oblik reference se bira kad se zna kome
   služi.
2. **Korak se izvršava kroz shell, kao cela linija.** Fazni fajl kaže „kao lista
   argumenata kroz shell", što su dve isključive stvari. Korak pipeline-a jeste
   shell komanda: `npm ci` na Windows-u je `npm.cmd` i bez shell-a se ne
   razrešava, a čovek očekuje da radi i `npm test && npm run build`.
3. **Zadržavanje se sprovodi posle svakog završenog pokretanja**, ne pri startu i
   ne nikad. Jedan `DELETE` sa podupitom, bez rasporeda.
4. **Motor piše kroz ubrizgan sink**, ne pravo u repozitorijum. Serije i tajmer
   žive u sink-u; test motora dobija sink koji skuplja u listu i ne čeka 200 ms.

## 4. Definicija i modeli

```
core/domains/codium/pipelines/
    __init__.py
    models.py           Pipeline, PipelineRun, RunStep, RunLogLine, RunStatus
    definition.py       parsiranje i validacija JSON-a — čist modul
    sinks.py            LogSink protokol + BatchingLogSink
    runner.py           motor
    repository.py       SQL nad codium.db
    log_repository.py   SQL nad codium_ops.db
    service.py          poslovna logika; jedina zove kapiju i dnevnik
```

### Definicija

JSON, čuva se u bazi kao tekst i validira pri snimanju. JSON, ne YAML: Python ga
čita ugrađenim modulom, pa faza ne uvodi nijednu novu zavisnost.

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

`definition.py` nudi `parse(text) -> PipelineDefinition` i diže `DefinitionError`
sa porukom koja kaže koje polje i zašto. Validira: `name` neprazan, `steps`
neprazna lista, svaki korak ima `name` i `run`, `timeout_minutes` pozitivan broj,
`working_dir` ne izlazi iz korena repozitorijuma.

Provera `working_dir` se **ne piše iznova** — uvija se `CodiumExplorer._safe(rel)`
iz `core/domains/codium/explorer.py`, koji tačno to već radi za Explorer. Dve
provere putanje znače dva mesta na kojima se greši.

`RunStatus`: `queued`, `running`, `success`, `failed`, `cancelled`, `timeout`.
Status koraka dodatno poznaje `skipped`.

`env` je običan rečnik stringova koji se spaja sa okruženjem procesa. `${{ ... }}`
se ne parsira i ne razrešava u ovoj fazi.

## 5. Motor

```
PipelineRunner(runs: RunStore, sink: LogSink, clock=time.monotonic)
    start(pipeline, definition, run_id) -> None   # ne blokira; asyncio.Task
    cancel(run_id) -> bool
    is_running(run_id) -> bool
```

`RunStore` je uzak protokol nad statusima pokretanja i koraka; `LogSink` ima
jednu metodu, `write(run_id, step_idx, stream, lines)`. Serije — do 50 redova ili
200 ms — žive u `sinks.BatchingLogSink`, ne u motoru. Tako test motora dobija
sink koji skuplja u listu, a test serija lažan sat; nijedan ne čeka stvarnih
200 ms i nijedan ne dodiruje SQLite.

### Po koraku

`asyncio.create_subprocess_shell(korak.run, cwd=<koren repozitorijuma>/<working_dir>,
env=<okruženje procesa + definicija>, stdout=PIPE, stderr=PIPE)`.

`stdout` i `stderr` se čitaju **istovremeno**, svaki svojim zadatkom, a redovi
nose oznaku toka. `seq` je monoton **po pokretanju**, ne po koraku — inače se dva
toka ne mogu poređati u jedan prikaz.

### Gašenje gasi stablo, ne samo dete

`create_subprocess_shell` na Windows-u pravi `cmd.exe`, koji pravi `npm`, koji
pravi `node`. Gašenje samo deteta ostavlja unuke da rade. Zato se koristi isti
obrazac koji `core/domains/codium/dev_server.py` već ima: `taskkill /F /T /PID` na
Windows-u, grupa procesa na ostalim sistemima.

### Redosled, prekid, istek

Koraci idu redom. Ne-nulti izlazni kod prekida pokretanje osim ako korak nosi
`continue_on_error: true`. Korak koji je preskočen posle prekida dobija status
`skipped`, ne ostaje `queued` — inače se u istoriji ne razlikuje „nije stigao na
red" od „nikad nije ni krenuo".

`timeout_minutes` važi za **celo pokretanje**, ne po koraku: `asyncio.wait_for`
nad celim zadatkom, pa gašenje stabla, pa status `timeout`.

### Oporavak pri startu

U `core_lifespan` (`apps/api/main.py`) svako pokretanje zatečeno u stanju
`running` prelazi u `failed`, sa `detail` = „aplikacija zatvorena". Bez toga
zaostala pokretanja zauvek vise u „radi".

### Prihvaćeno ograničenje

Runner živi u procesu FastAPI backend-a, pa gašenje CORE-a prekida pokretanje
koje traje. Ovo se prihvata u prvom rezu; odvojen proces koji preživljava
aplikaciju je zaseban posao. Potvrda pri zatvaranju prozora pripada E3b.

## 6. Baza

### `codium.db` — migracija `CODIUM_MIGRATION_V11`

```sql
CREATE TABLE codium_pipelines (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL
                  REFERENCES codium_repositories (id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    definition    TEXT NOT NULL,
    enabled       INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE codium_pipeline_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL
                REFERENCES codium_pipelines (id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'queued',
    trigger     TEXT NOT NULL DEFAULT 'manual',
    commit_sha  TEXT,
    branch      TEXT,
    exit_code   INTEGER,
    detail      TEXT NOT NULL DEFAULT '',
    started_at  TEXT,
    finished_at TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_runs_pipeline ON codium_pipeline_runs (pipeline_id, id DESC);

CREATE TABLE codium_run_steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL
                REFERENCES codium_pipeline_runs (id) ON DELETE CASCADE,
    idx         INTEGER NOT NULL,
    name        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued',
    exit_code   INTEGER,
    started_at  TEXT,
    finished_at TEXT
);
CREATE INDEX idx_codium_run_steps_run ON codium_run_steps (run_id, idx);
```

`detail` je dodat u odnosu na fazni fajl: „aplikacija zatvorena" i „istek" moraju
negde da stanu, inače se u istoriji ne razlikuju od običnog pada.

Uz tabele, ista migracija upisuje dva pravila kapije:

- `agent:*` / `pipeline.run` / `*` → `needs_approval` — agent pokreće tuđe
  komande, čovek odobrava.
- `agent:*` / `pipeline.write` / `*` → `deny` — definiciju piše čovek.

Glagol `run` i inače pada na `NEEDS_APPROVAL` u `_DEFAULTS`, ali izričito pravilo
nosi razlog u dnevniku umesto „podrazumevano za `run`". `_DEFAULTS` se ne dira.

### `codium_ops.db` — migracija `CODIUM_OPS_MIGRATION_V3`

```sql
-- Bez stranog ključa: `run_id` pokazuje na red u drugoj bazi.
CREATE TABLE codium_run_logs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id   INTEGER NOT NULL,
    step_idx INTEGER NOT NULL,
    seq      INTEGER NOT NULL,
    stream   TEXT NOT NULL DEFAULT 'stdout',
    line     TEXT NOT NULL,
    at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_run_logs_seq ON codium_run_logs (run_id, seq);
```

### Zadržavanje

Posle svakog završenog pokretanja servis briše redove loga pokretanjima izvan
poslednjih 50 za taj pipeline. Zaglavlje i koraci ostaju; briše se samo
`codium_run_logs`. `codium_ops.db` je odvojena baš zato što brzo raste —
ostaviti je bez granice znači izneveriti razlog razdvajanja.

## 7. API

`apps/api/schemas/codium_pipelines.py` — Pydantic ulaz i izlaz.

`apps/api/codium_pipelines_runtime.py` — po uzoru na
`codium_repositories_runtime.py`, uz jednu bitnu razliku: `PipelineRunner` je
**jedan primerak po procesu**, jer pokretanja koja traju žive u njemu.

`apps/api/routers/codium_pipelines.py`, prefiks `/api/v1/codium/pipelines`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/` | pipeline-i (`?repository_id=`) |
| POST | `/` | nov, validira definiciju pri upisu |
| PUT | `/{id}` | izmena definicije |
| DELETE | `/{id}` | brisanje |
| POST | `/{id}/run` | pokretanje, vraća `run_id` odmah |
| GET | `/runs` | istorija (`?pipeline_id=&status=&limit=`) |
| GET | `/runs/{run_id}` | zaglavlje plus koraci |
| GET | `/runs/{run_id}/logs` | `?after_seq=` — inkrementalno |
| POST | `/runs/{run_id}/cancel` | otkazivanje |

Preslikavanje grešaka: `DefinitionError` → 400, `PipelineNotFound` /
`RunNotFound` → 404, pokretanje pipeline-a čiji je repozitorijum nestao sa diska
→ **409** (to je stanje sveta, ne kvar).

Live log je polling `logs?after_seq=` na 500 ms dok je status `running`. Bez
WebSocket-a, u skladu sa pravilom CORE-a.

Rute nose `actor="human"`; čovek zaobilazi kapiju.

## 8. Alati agenta

Dva nova `ToolSpec`-a u `core/domains/codium/agents/tools/builtin.py`:

| Alat | Argumenti | Akcija |
|---|---|---|
| `run_pipeline` | `name` | `pipeline.run` |
| `list_pipeline_runs` | `name`, `limit` | `pipeline.read` |

`run_pipeline` vraća `run_id` i početni status, **ne čeka kraj** — petlja agenta
ne sme da visi dvadeset minuta. Ishod se čita kroz `list_pipeline_runs`, koji
pada na `read` i prolazi bez odobrenja.

Kao i git alati iz E2, oba rade nad prvim registrovanim repozitorijumom projekta
i vraćaju rečenicu umesto izuzetka kad pipeline ne postoji.

## 9. Testovi

- `test_pipeline_definition` — ispravna definicija; nedostajuće polje; prazna
  lista koraka; `working_dir` koji izlazi iz korena.
- `test_pipeline_runner` — dva koraka `python -c ...` daju `success` i rastući
  `seq`; ne-nulti kod prekida; `continue_on_error` ne prekida; preskočen korak
  nosi `skipped`; otkazivanje daje `cancelled`; istek daje `timeout`. Lažan sink,
  lažan sat.
- `test_pipeline_log_sink` — serija se šalje na 50 redova i na istek prozora;
  nijedan red se ne gubi pri zatvaranju.
- `test_pipeline_recovery` — pokretanje u `running` posle restarta prelazi u
  `failed` sa razlogom u `detail`.
- `test_pipeline_retention` — 51. pokretanje briše log prvog, a zaglavlje ostaje.
- `test_api_codium_pipelines` — `after_seq` vraća samo nove redove; neispravna
  definicija daje 400; `pipeline.run` bez dozvole ne pokreće ništa i ostavlja
  trag u dnevniku.
- `test_codium_agent_tools` — dopuna za oba nova alata.

## 10. Definicija završetka

Pipeline se definiše, snima, pokreće i otkazuje kroz API; log se čita
inkrementalno tokom rada; preskočeni koraci se razlikuju od nepokrenutih;
zaostala pokretanja se čiste pri startu; zadržavanje drži `codium_ops.db` u
granici; agent ima `run_pipeline` i `list_pipeline_runs`; testovi domena prolaze.

## 11. Van dometa svesno

- Tajne u definiciji i maskiranje u logu — ulaze sa E4, kad postoji potrošač.
- Ekran, Monaco uređivač sa JSON šemom, log u bojama, Overview pločica — E3b.
- Okidači osim ručnog i API-ja — E10 Automations.
- Pokretanje koje preživljava gašenje aplikacije.
- Prikaz uživo u pravom terminalskom prozoru: moguć kasnije kao dodatni sloj nad
  istim motorom, ne kao njegova zamena.
