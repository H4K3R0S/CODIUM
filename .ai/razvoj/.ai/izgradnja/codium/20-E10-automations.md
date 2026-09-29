---
id: codium-a58fb1ae-20-e10-automations-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E10 — Automations
summary: '**Blok:** AI · **Zavisi od:** E2–E6, E9 · **Migracija:** codium v12'
keywords:
- e10
- automations
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/20-E10-automations.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E10 — Automations

**Blok:** AI · **Zavisi od:** E2–E6, E9 · **Migracija:** codium v12
**Sidebar:** `Automations`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Povezati događaje koje podsistemi već proizvode sa akcijama koje već umeju da
izvrše. Bez ovoga svaki lanac (commit, pa testovi, pa isporuka, pa dev-log) ostaje
ručan.

Faza je namerno poslednja u AI bloku: ona ne donosi nove sposobnosti, nego spaja
postojeće. Automatizacija nad podsistemom koji nije stabilan samo umnožava kvarove.

## Model pravila

Pravilo ima tri dela: **kada**, **ako**, **onda**.

```
when:  pipeline.run.finished
if:    status == "failed" AND pipeline_id == 3
then:  notify + agent_analyze(agent="architect")
```

### Događaji

| Događaj | Izvor | Nosi |
|---|---|---|
| `repo.commit.detected` | E2, provera na 60 s | repo, grana, sha, autor |
| `repo.branch.changed` | E2 | repo, stara i nova grana |
| `pipeline.run.finished` | E3 | run, status, izlazni kod, trajanje |
| `deployment.finished` | E4 | isporuka, cilj, status |
| `service.state.changed` | E5 | servis, staro i novo stanje |
| `alert.fired`, `alert.resolved` | E6 | pravilo, servis, vrednost |
| `schedule.tick` | E10 | cron izraz |

Događaji se objavljuju kroz jednostavan sinhroni razglas u procesu
(`core/domains/codium/automations/bus.py`). Nema reda poruka, nema spoljne
infrastrukture — jedan proces, jedan pretplatnik po pravilu.

### Uslovi

Mali izraz nad poljima događaja: poređenja (`==`, `!=`, `<`, `>`), `AND`, `OR`,
`contains`. Parsira se u `conditions.py` u stablo i **izvršava se sopstvenim
prolaskom kroz to stablo**. Nikada `eval`. Ovo je pravilo bezbednosti, ne stila.

### Akcije

| Akcija | Radi | Dozvola |
|---|---|---|
| `notify` | CORE notifikacija | dozvoljeno |
| `write_note` | beleška na projektu | dozvoljeno |
| `write_dev_log` | unos u `.ai/dev-log/` | dozvoljeno |
| `create_task` | task na projektu | dozvoljeno |
| `run_pipeline` | pokreće pipeline iz E3 | traži odobrenje |
| `deploy` | isporuka iz E4 | traži odobrenje |
| `restart_service` | E5 | traži odobrenje |
| `agent_analyze` | pokreće agenta iz E9 nad kontekstom događaja | traži odobrenje ako agent troši online model |

Akter je `automation:<id>`, pa sve prolazi kroz ScopeGate iz E1 i ostavlja trag u
audit-u. Automatizacija nema više prava od agenta.

### Zaštita od petlje

Tri obavezne mere, jer pravilo koje pali samo sebe je najlakši način da se sistem
zaglavi:

1. Događaj koji je proizvela akcija nosi oznaku porekla; pravilo se ne pali na
   sopstvenu posledicu.
2. Ograničenje učestalosti po pravilu: najviše N okidanja u prozoru (podrazumevano
   5 na 10 minuta). Prekoračenje gasi pravilo i šalje notifikaciju.
3. Dubina lanca je ograničena na 3; dalje se ne prosleđuje.

## Šema (migracija v12)

```sql
CREATE TABLE codium_automation_rules (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    event         TEXT NOT NULL,
    condition_expr TEXT NOT NULL DEFAULT '',
    actions_json  TEXT NOT NULL DEFAULT '[]',
    project_id    INTEGER REFERENCES codium_projects (id) ON DELETE CASCADE,
    enabled       INTEGER NOT NULL DEFAULT 1,
    rate_limit_n  INTEGER NOT NULL DEFAULT 5,
    rate_limit_seconds INTEGER NOT NULL DEFAULT 600,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE codium_automation_runs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id  INTEGER NOT NULL REFERENCES codium_automation_rules (id) ON DELETE CASCADE,
    event_json TEXT NOT NULL DEFAULT '{}',
    matched  INTEGER NOT NULL DEFAULT 1,
    status   TEXT NOT NULL DEFAULT 'done',
        -- done | skipped | waiting_approval | failed | rate_limited
    detail   TEXT NOT NULL DEFAULT '',
    at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_automation_runs ON codium_automation_runs (rule_id, at DESC);
```

## API

`apps/api/routers/codium_automations.py`, prefiks `/api/v1/codium/automations`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/events` | dostupni događaji i njihova polja |
| GET | `/actions` | dostupne akcije i tražene dozvole |
| GET | `/` | pravila |
| POST | `/` | novo pravilo (validira izraz i akcije) |
| PATCH | `/{id}` | izmena, uključujući uključivanje i gašenje |
| DELETE | `/{id}` | brisanje |
| POST | `/{id}/test` | proba nad izmišljenim događajem; **ne izvršava akcije** |
| GET | `/runs` | istorija okidanja (`?rule_id=`) |

`POST /{id}/test` postoji da se pravilo proveri bez posledica. Vraća da li bi se
upalilo i šta bi uradilo.

## GUI (radi se posle backend-a bloka)

`pages/CodiumAutomations.tsx`:

- Lista pravila, prekidač uključeno/isključeno, vreme poslednjeg okidanja.
- Uređivač u tri koraka: izbor događaja, sastavljanje uslova nad njegovim
  poljima, izbor akcija. Uz svaku akciju odmah piše da li traži odobrenje.
- Dugme „Probaj" prikazuje ishod nad izmišljenim događajem.
- Istorija okidanja sa razlogom kada je preskočeno ili prekoračilo ograničenje.

## Testovi

- `test_condition_parser` — tačno parsiranje i ocena; izraz sa pozivom funkcije
  se odbija pri parsiranju (dokaz da se ne koristi `eval`).
- `test_automation_bus` — događaj stiže samo do pravila koja ga slušaju.
- `test_automation_loop_guard` — pravilo koje pali samo sebe se zaustavlja;
  prekoračena učestalost gasi pravilo i upisuje `rate_limited`; dubina lanca
  se poštuje.
- `test_automation_scope` — `deploy` iz automatizacije bez pravila ne izvršava
  ništa i pravi stavku u redu za odobrenje.
- `test_api_codium_automations` — `test` ne izvršava akcije.

## Definicija završetka

Pravilo se sastavlja, proba bez posledica, pali na pravi događaj i izvršava
dozvoljene akcije; opasne akcije traže odobrenje; zaštita od petlje radi; testovi
domena prolaze.
