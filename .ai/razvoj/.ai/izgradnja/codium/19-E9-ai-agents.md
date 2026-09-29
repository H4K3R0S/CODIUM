---
id: codium-30e8c7e3-19-e9-ai-agents-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E9 — AI Agents
summary: '**Blok:** AI · **Zavisi od:** E1 · **Migracija:** codium v8'
keywords:
- agents
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/19-E9-ai-agents.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E9 — AI Agents

**Blok:** AI · **Zavisi od:** E1 · **Migracija:** codium v8
**Sidebar:** `AI Agents`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Prelazak sa persona na agente. Persona iz F9 je stil odgovaranja — ista petlja
pitanje-odgovor, samo drugi sistemski prompt. Agent ima **alate**, radi u
koracima, i njegovi potezi prolaze kroz ScopeGate iz E1.

Ovo je ono što je ranije nosilo oznaku „F16 CODIUM_SICA".

## Šta postoji

`core/agents/sica/` već postoji kao seme (uključujući `patch_loop.py`). Planska
arhitektura agenata opisana je u `.ai/reference/AGENTS.md`. E9 od tog semena
pravi radnu, ali usku petlju — ne ceo korpus od petnaest agenata odjednom.

**Prvi i jedini agent u ovoj fazi: `ARCHITECT`.** Njegov zadatak je predlog
izmene, ne izvršenje: čita, analizira, piše plan. Time je prva verzija petlje
bezbedna po konstrukciji, a alati koji menjaju stanje se uključuju tek kad petlja
dokaže da radi.

## Model agenta

Agent je zapis, ne klasa po agentu:

- `slug` — stabilan identifikator, ujedno akter u ScopeGate-u (`agent:architect`),
- `name`, `description`,
- `system_prompt` — uloga i granice,
- `model` i `provider` — kroz E8; agent sme da ima drugi model od chata,
- `tools` — spisak dozvoljenih alata,
- `max_steps` — gornja granica koraka u jednoj petlji,
- `enabled`.

Dodavanje agenta je unos u bazu, ne novi Python modul. Novi kod treba samo za
novi **alat**.

## Alati

`core/domains/codium/agents/tools/`

Alat je tanak omotač oko **već postojećeg servisa**, koji pre izvršenja proverava
dozvolu. Ne piše se nova logika rada sa fajlovima:

| Alat | Uvija |
|---|---|
| `read_file`, `list_dir`, `write_file` | `CodiumExplorer` (`core/domains/codium/explorer.py`) |
| `search_code` | Explorer obilazak + pretraga; jedini alat sa nešto novog koda |
| `git_log`, `git_diff` | `RepositoryService` iz E2 |
| `read_run_log` | `PipelineService` iz E3 |
| `write_note`, `create_task` | postojeći `CodiumService` iz F1 |
| `run_pipeline` | `PipelineRunner` iz E3 |

`CodiumExplorer._safe(rel)` već brani izlazak iz korena projekta — nijedan alat ne
piše sopstvenu proveru putanje.

Prvi rez:

| Alat | Akcija u ScopeGate-u | Podrazumevano |
|---|---|---|
| `read_file` | `file.read` | dozvoljeno |
| `list_dir` | `file.read` | dozvoljeno |
| `search_code` | `file.read` | dozvoljeno |
| `git_log`, `git_diff` | `repo.read` | dozvoljeno |
| `read_run_log` | `pipeline.read` | dozvoljeno |
| `write_note` | `note.write` | dozvoljeno |
| `create_task` | `task.write` | dozvoljeno |
| `write_file` | `file.write` | traži odobrenje |
| `run_pipeline` | `pipeline.run` | traži odobrenje |

Alati koji brišu ne postoje u prvom rezu. Kada budu potrebni, ulaze kao
`deny` po pravilu podrazumevanog ponašanja iz E1.

Opisi alata se generišu iz jednog registra i šalju modelu — nema dva mesta gde
se opisuje isti alat.

## Petlja

`core/domains/codium/agents/loop.py`

```
AgentLoop.run(agent, task, context) -> AgentRun
```

Korak: model dobija zadatak, istoriju i opise alata; vraća ili poziv alata ili
konačan odgovor. Poziv alata se izvršava, rezultat se dodaje u istoriju, sledeći
korak. Petlja staje na konačnom odgovoru, na `max_steps`, na grešci alata koja se
ponovi dva puta, ili na odbijanju ScopeGate-a.

Svaki korak se upisuje u `codium_agent_steps` — petlja mora biti čitljiva unazad.
Agent koji radi nevidljivo je agent kome se ne može verovati.

Kada alat vrati `needs_approval`, petlja se **pauzira** i zapisuje stanje. Posle
odobrenja u E1 nastavlja od istog koraka; posle odbijanja se završava sa
obrazloženjem.

## Šema (migracija v11)

```sql
CREATE TABLE codium_agents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    system_prompt TEXT NOT NULL DEFAULT '',
    model         TEXT NOT NULL DEFAULT '',
    provider      TEXT NOT NULL DEFAULT '',
    tools_json    TEXT NOT NULL DEFAULT '[]',
    max_steps     INTEGER NOT NULL DEFAULT 12,
    enabled       INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE codium_agent_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id   INTEGER NOT NULL REFERENCES codium_agents (id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES codium_projects (id) ON DELETE SET NULL,
    task       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'running',
        -- running | waiting_approval | done | failed | cancelled
    result     TEXT NOT NULL DEFAULT '',
    steps_used INTEGER NOT NULL DEFAULT 0,
    cost_usd   REAL NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);

CREATE TABLE codium_agent_steps (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id   INTEGER NOT NULL REFERENCES codium_agent_runs (id) ON DELETE CASCADE,
    idx      INTEGER NOT NULL,
    kind     TEXT NOT NULL,          -- thought | tool_call | tool_result | answer
    tool     TEXT,
    payload  TEXT NOT NULL DEFAULT '',
    at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_agent_steps_run ON codium_agent_steps (run_id, idx);
```

## API

`apps/api/routers/codium_agents.py`, prefiks `/api/v1/codium/agents`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/` | agenti |
| POST | `/` | nov agent |
| PATCH | `/{id}` | izmena (uključujući spisak alata) |
| DELETE | `/{id}` | brisanje |
| GET | `/tools` | registar alata i njihove tražene dozvole |
| POST | `/{id}/run` | pokretanje; vraća `run_id` odmah |
| GET | `/runs/{run_id}` | stanje + koraci |
| POST | `/runs/{run_id}/cancel` | prekid |

## GUI (radi se posle backend-a bloka)

`pages/CodiumAgents.tsx`:

- Lista agenata sa modelom i brojem dozvoljenih alata.
- Uređivač: sistemski prompt, model iz E8 kataloga, čekiranje alata; uz svaki
  alat piše koju dozvolu traži i šta je trenutno pravilo za tog agenta.
- Pokretanje: polje za zadatak, pa prikaz koraka uživo (polling, kao E3).
- Korak koji čeka odobrenje se ističe i vodi na ekran iz E1.

## Testovi

- `test_agent_tools` — svaki alat traži tačnu dozvolu; alat bez dozvole ne
  izvršava ništa i vraća `needs_approval` ili odbijanje.
- `test_agent_loop` — lažni model koji vraća unapred određen niz poteza:
  petlja poziva alate redom, staje na konačnom odgovoru, poštuje `max_steps`,
  prekida se posle dve iste greške alata.
- `test_agent_pause_resume` — `needs_approval` pauzira petlju; posle odobrenja
  nastavlja od istog koraka; posle odbijanja se završava.
- `test_api_codium_agents` — koraci se čitaju inkrementalno.

Nijedan test ne poziva pravi model.

## Definicija završetka

`ARCHITECT` agent se definiše, pokreće, koristi alate za čitanje i vraća plan;
svaki korak je zapisan; alat koji menja stanje traži odobrenje i petlja ga
poštuje; testovi domena prolaze.
