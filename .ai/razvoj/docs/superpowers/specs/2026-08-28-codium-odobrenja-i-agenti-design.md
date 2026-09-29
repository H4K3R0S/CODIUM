---
id: codium-7687f8e1-2026-08-28-codium-odobrenja-i-agenti-design-md
type: spec
domain: codium
namespace: global
visibility: global
tier: domain
title: CODIUM — red odobrenja (E1 drugi rez) i agenti (E9)
summary: '**Datum:** 2026-08-28'
keywords:
- codium
- red
- odobrenja
- drugi
- rez
- agenti
- docs
- superpowers
- specs
tags:
- superpowers
- specs
source_path: docs/superpowers/specs/2026-08-28-codium-odobrenja-i-agenti-design.md
edges:
- type: references
  target: core-2281544e-2026-08-28-codium-e1-scopegate-prvi-rez-md
  weight: 0.3
- type: references
  target: codium-30e8c7e3-19-e9-ai-agents-md
  weight: 0.3
---

# CODIUM — red odobrenja (E1 drugi rez) i agenti (E9)

**Datum:** 2026-08-28
**Faze:** E1 (drugi rez) + E9 AI Agents
**Migracije:** `codium v7` (odobrenja), `codium v8` (agenti)
**Prethodno:** [E1 prvi rez](../plans/2026-08-28-codium-e1-scopegate-prvi-rez.md),
[19-E9-ai-agents.md](../../../.ai/izgradnja/codium/19-E9-ai-agents.md)

---

## Zašto oba zajedno

E9 traži da agent koji hoće da promeni stanje stane i pita. Bez reda odobrenja
agent može samo da čita, a petlja koja nikada ne staje ne dokazuje ono zbog čega
kapija postoji. Zato drugi rez E1 ide prvi i tek onda agenti.

Prvi rez E1 je dao odluku (`ScopeGate`) i trag (`codium_audit_log`). Nedostaje
srednji deo: kada kapija kaže `needs_approval`, danas se ništa ne dešava — nema
gde da se ta molba zapiše niti ko da na nju odgovori.

## Ispravke brojeva iz planskih fajlova

Planski fajlovi su pisani pre nego što je išta od E trake napravljeno i njihove
verzije migracija su zastarele.

| Gde | Piše | Tačno je | Razlog |
|---|---|---|---|
| `11-E1` | `codium_approvals` u v6 | **v7** | v6 je već isporučen, sadrži samo `codium_scope_rules` |
| `19-E9` | `codium v11` | **v8** | E2–E8 ne postoje, pa nisu potrošili v7–v10 |
| `19-E9` | zavisi od E1 i E8 | **E1 i AI-2** | E8 (OmniRoute) nije napravljen; modeli već rade kroz `ModelRouter` iz AI-2 |

Fajlovi se ispravljaju u istom potezu, kao što je urađeno za E1 prvi rez.

## Obim koji zavisnosti dozvoljavaju

E9 plan nabraja deset alata. Četiri od njih (`git_log`, `git_diff`,
`read_run_log`, `run_pipeline`) uvijaju servise iz E2 i E3, kojih nema. Prvi rez
E9 nosi **šest alata** — one koji uvijaju kod koji postoji danas.

Ovo nije smanjenje ambicije nego posledica redosleda: alat je tanak omotač oko
postojećeg servisa, pa alat bez servisa ne bi bio omotač nego nova
implementacija u pogrešnoj fazi.

---

## Deo 1 — Red odobrenja (E1 drugi rez)

### Kapija ostaje bez baze

`ScopeGate.check()` i dalje vraća `needs_approval` i ne dodiruje bazu. Upis molbe
je posao pozivaoca kroz zaseban `ApprovalService.request(...)`.

Razlog je isti koji je držao prvi rez čistim: kapija se testira bez ijedne
tabele, a njena odluka ne zavisi od toga da li iko sluša. Servis koji je zvao
kapiju mora umeti da stane — to je njegova odgovornost, ne kapijina.

### Tabela je generična

`codium_approvals` ne zna za agente. Nosi aktera, akciju, cilj, `payload` i
status. Vezu prema agentu drži druga strana — `codium_agent_runs.pending_approval_id`.

Tako E10 automatizacije kasnije koriste isti red bez ijedne izmene šeme. Da red
zna za agente, svaka nova vrsta tražioca tražila bi novu kolonu.

### Šema — migracija v7

```sql
CREATE TABLE codium_approvals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    actor        TEXT NOT NULL,
    action       TEXT NOT NULL,
    target       TEXT NOT NULL DEFAULT '',
    payload      TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','approved','rejected','expired')),
    note         TEXT NOT NULL DEFAULT '',
    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at   TEXT
);
CREATE INDEX idx_codium_approvals_status ON codium_approvals (status, requested_at);
```

`payload` je JSON sa punim pozivom alata: ime alata, argumenti, i `content_hash`
kada potez piše sadržaj.

Status `expired` stoji u `CHECK` skupu, ali ga prvi rez ne postavlja — nema roka
trajanja molbe. Skup je tu da kasniji posao održavanja ne traži izmenu šeme.

### Šta odobrenje znači

Odobrenje važi za **tačno taj potez** i ništa više. Sledeći `file.write`, makar i
na isti fajl, pita ponovo. Trajna dozvola se piše ručno kao pravilo u
`codium_scope_rules`; „odobri i zapamti" ne postoji kao čekboks jer bi jedan klik
iz umora trajno otvarao kapiju, a to se ne bi videlo nigde osim u tabeli pravila.

Kada potez piše sadržaj, `payload` nosi SHA-256 tog sadržaja. Pri nastavku se
hash proverava ponovo: ako se ne poklapa, potez pada uz obrazloženje. Bez te
provere „Odobri" znači „veruj agentu na reč" — tačno ono što kapija treba da
spreči.

### Servis

`core/domains/codium/audit/approvals.py`

```
ApprovalRepository
    request(approval) -> Approval        # INSERT, status 'pending'
    pending() -> list[Approval]
    get(approval_id) -> Approval | None
    decide(approval_id, status, note) -> Approval | None
```

`decide` menja samo red koji je `pending`. Već odlučena molba se ne odlučuje
ponovo — inače bi odbijeni potez mogao naknadno da postane odobren.

### API

Dodaje se u postojeći `apps/api/routers/codium_audit.py`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/approvals` | molbe koje čekaju odluku |
| POST | `/approvals/{id}/approve` | odobrenje |
| POST | `/approvals/{id}/reject` | odbijanje uz razlog |

Svaka odluka upisuje unos u dnevnik: akter `human`, akcija `approval.decide`,
cilj `approval:<id>`. Odobrenje je akcija kao i svaka druga i mora ostaviti trag.

### GUI

- `pages/CodiumAccess.tsx` — tabela pravila (akter × akcija × cilj → odgovor) sa
  dodavanjem i brisanjem, plus panel „Čeka odobrenje" sa punim prikazom poteza
  koji se odobrava i dugmadima Odobri / Odbij.
- `pages/CodiumAudit.tsx` — dnevnik sa filterima po akteru i akciji, učitavanje u
  stranicama, boja po odgovoru kapije uz isto pravilo kao na kontrolnoj tabli:
  odbijeno nije greška i ne sme da izgleda kao kvar.

Time je E1 zaokružen po svojoj definiciji završetka.

---

## Deo 2 — Agenti (E9)

### Šta agent jeste

Persona iz F9 je stil odgovaranja: ista petlja pitanje-odgovor, drugi sistemski
prompt. Agent ima **alate**, radi u koracima, i svaki njegov potez prolazi kroz
kapiju.

Agent je zapis u bazi, ne klasa po agentu. Dodavanje agenta je unos u tabelu; nov
Python kod treba samo za nov **alat**.

Prvi i jedini agent ove faze je `ARCHITECT`: čita, analizira, predlaže plan. Alat
koji menja stanje mu je dostupan, ali traži odobrenje — petlja je bezbedna po
konstrukciji, a ne po disciplini.

### Struktura

```
core/domains/codium/agents/
    models.py         Agent, AgentRun, AgentStep, ToolResult
    repository.py     AgentRepository, RunRepository
    tools/registry.py ToolSpec + registar
    tools/builtin.py  šest alata
    loop.py           AgentLoop — čista petlja, sve injektovano
    runner.py         daemon nit oko petlje
```

### Registar alata je jedan izvor

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str      # ide modelu
    args: dict[str, str]  # ime -> opis, ide modelu
    action: str           # ide kapiji, npr. "file.write"
    run: Callable[..., ToolResult]
```

Iz istog zapisa se generiše i opis koji model čita i akcija koju kapija proverava.
Nema mesta gde alat modelu kaže jedno, a kapiji prijavi drugo.

### Alati prvog reza

| Alat | Uvija | Akcija | Podrazumevano |
|---|---|---|---|
| `read_file` | `CodiumExplorer.read_file` | `file.read` | dozvoljeno |
| `list_dir` | `CodiumExplorer.list_dir` | `file.read` | dozvoljeno |
| `search_code` | obilazak Explorer-a + pretraga | `file.read` | dozvoljeno |
| `write_note` | `CodiumService.create_note` | `note.write` | dozvoljeno |
| `create_task` | `CodiumService.create_task` | `task.write` | dozvoljeno |
| `write_file` | `CodiumExplorer.write_file` | `file.write` | traži odobrenje |

`search_code` je jedini alat sa nešto novog koda: obilazak stabla kroz Explorer,
traženje niza po linijama, ograničen broj pogodaka i preskakanje binarnih fajlova.

Zaštita putanje se **ne piše ponovo**. `CodiumExplorer._safe(rel)` već brani
izlazak iz korena projekta, i nijedan alat ne sme da nosi sopstvenu proveru —
dve provere znače dva mesta gde se greši.

Alati koji brišu ne postoje u prvom rezu.

### Kako model traži alat

Provajderski protokol (`ChatProvider.chat`) prima poruke i vraća tekst; o alatima
ne zna ništa. Prvi rez ga **ne menja**.

Opisi alata idu u sistemski prompt, a model odgovara ili konačnim tekstom ili
blokom oblika:

```json
{"tool": "read_file", "args": {"rel": "src/api.py"}}
```

Petlja parsira strogo. Neispravan JSON nije pad nego rezultat koraka koji se
vraća modelu kao greška; model dobija priliku da se popravi, a pravilo o dve iste
greške zaredom hvata onaj koji ne ume.

Prednost: radi sa sva tri provajdera odmah, uključujući lokalne Ollama modele,
bez izmene protokola. Nativni tool-calling (Anthropic i OpenAI) je kasnija
nadogradnja **sloja ispod petlje** — petlja se ne menja.

### Petlja

```
AgentLoop.run(agent, task, context) -> AgentRun
```

Korak: model dobija zadatak, istoriju i opise alata. Vraća poziv alata ili
konačan odgovor. Poziv se proverava na kapiji, pa izvršava, pa se rezultat
dodaje u istoriju.

Petlja staje na:

- konačnom odgovoru modela (`done`),
- `max_steps` (`failed`, uz obrazloženje),
- dve iste greške alata zaredom (`failed`),
- odgovoru kapije `deny` (`failed`, uz zapisan verdikt),
- odgovoru kapije `needs_approval` (`waiting_approval`).

Svaki korak se upisuje u `codium_agent_steps` pre nego što se pređe na sledeći.
Agent koji radi nevidljivo je agent kome se ne može verovati.

### Izvršavanje i pauza

`POST /{id}/run` upisuje red u `codium_agent_runs`, diže **daemon nit** i odmah
vraća `run_id`. To je obrazac koji projekat već koristi (`streaming.py`,
`installer.py`, `disk_monitor.py`) — nema reda poslova i ne uvodi se.

Nit vrti korake i svaki upisuje u bazu. GUI poziva `GET /runs/{id}` u intervalu.

Kada kapija vrati `needs_approval`, nit upiše molbu u `codium_approvals`, postavi
run na `waiting_approval` sa `pending_approval_id`, i **umre**. Nastavak posle
odobrenja je **nova nit** koja čita korake iz baze i nastavlja od istog mesta.

Stanje živi u bazi, ne u memoriji niti. Zato restart API-ja ne gubi run, a pauza
ne traži nikakav mehanizam držanja niti u snu.

Odbijena molba završava run kao `cancelled`, sa razlogom zapisanim kao poslednji
korak.

### Šema — migracija v8

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
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id            INTEGER NOT NULL
                        REFERENCES codium_agents (id) ON DELETE CASCADE,
    project_id          INTEGER
                        REFERENCES codium_projects (id) ON DELETE SET NULL,
    task                TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running','waiting_approval',
                                          'done','failed','cancelled')),
    result              TEXT NOT NULL DEFAULT '',
    steps_used          INTEGER NOT NULL DEFAULT 0,
    cost_usd            REAL NOT NULL DEFAULT 0,
    pending_approval_id INTEGER,
    started_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at         TEXT
);
CREATE INDEX idx_codium_agent_runs_agent ON codium_agent_runs (agent_id, id DESC);

CREATE TABLE codium_agent_steps (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  INTEGER NOT NULL
            REFERENCES codium_agent_runs (id) ON DELETE CASCADE,
    idx     INTEGER NOT NULL,
    kind    TEXT NOT NULL,   -- thought | tool_call | tool_result | answer
    tool    TEXT,
    payload TEXT NOT NULL DEFAULT '',
    at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_agent_steps_run ON codium_agent_steps (run_id, idx);
```

Migracija upisuje i `ARCHITECT` kao početni red u `codium_agents`.

Prazni `model` i `provider` znače „koristi ono što bi chat koristio" — poziv ide
kroz `ModelRouter.resolve()` iz AI-2. Agent sme da ima svoj model, ali ne mora, i
prazna vrednost nije greška nego nasleđivanje.

`cost_usd` na run-u je zbir troška koraka. Svaki poziv modela ionako upisuje red
kroz `UsageRecorder`; petlja sabira te vrednosti da bi cena celog zadatka bila
vidljiva bez ukrštanja dve tabele u GUI-ju.

`CHECK` nad statusom je namerno u šemi: pogrešna vrednost bi inače tiho prošla i
GUI bi crtao run u stanju koje petlja ne poznaje.

### API

`apps/api/routers/codium_agents.py`, prefiks `/api/v1/codium/agents`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/` | agenti |
| POST | `/` | nov agent |
| PATCH | `/{id}` | izmena, uključujući spisak alata |
| DELETE | `/{id}` | brisanje |
| GET | `/tools` | registar alata i dozvola koje traže |
| POST | `/{id}/run` | pokretanje; vraća `run_id` odmah |
| GET | `/runs` | poslednji run-ovi (za kontrolnu tablu) |
| GET | `/runs/{run_id}` | stanje i koraci, `since_idx` za dopunu |
| POST | `/runs/{run_id}/cancel` | prekid |

`GET /runs/{run_id}` prima `since_idx` da poll ne prenosi iste korake u krug.

### GUI

- `pages/CodiumAgents.tsx` — lista agenata sa modelom i brojem alata; uređivač sa
  sistemskim promptom, izborom modela iz kataloga i čekiranjem alata, gde uz svaki
  alat piše koju dozvolu traži i kakvo je trenutno pravilo za tog aktera;
  pokretanje sa zadatkom i prikazom koraka kroz poll.
- Korak koji čeka odobrenje se ističe i vodi na panel odobrenja u `CodiumAccess`.
- **AI Agents panel na kontrolnoj tabli prestaje da bude mock** i čita
  `GET /runs` — to je bio povod za ceo ovaj korak.

---

## Testiranje

Nijedan test ne poziva pravi model. Lažni model vraća unapred određen niz poteza.

- `test_codium_approvals` — molba se upisuje kao `pending`; `decide` menja samo
  `pending` red; već odlučena molba se ne menja ponovo.
- `test_agent_tools` — svaki alat traži tačno onu dozvolu koju registar navodi;
  odbijen alat ne izvršava ništa; alat ne piše sopstvenu proveru putanje.
- `test_agent_loop` — petlja poziva alate redom, staje na konačnom odgovoru,
  poštuje `max_steps`, prekida se posle dve iste greške alata, i upisuje svaki
  korak.
- `test_agent_pause_resume` — `needs_approval` pauzira run i upisuje molbu; posle
  odobrenja nastavlja od istog koraka; posle odbijanja završava kao `cancelled`;
  sadržaj promenjen između molbe i nastavka obara potez zbog hash-a.
- `test_api_codium_agents` — koraci se čitaju inkrementalno kroz `since_idx`.

## Definicija završetka

Molba za odobrenje se pravi, vidi u GUI-ju i odlučuje, a odluka ostavlja trag u
dnevniku. `ARCHITECT` se pokreće, koristi alate za čitanje i vraća plan; svaki
korak je zapisan i vidljiv; `write_file` traži odobrenje, pauzira run, i posle
odluke nastavlja ili završava. AI Agents panel na kontrolnoj tabli prikazuje
prave run-ove.

## Šta ostaje za kasnije

- Nativni tool-calling za Anthropic i OpenAI (sloj ispod petlje).
- Alati nad E2 i E3 (`git_log`, `git_diff`, `read_run_log`, `run_pipeline`) kad te
  faze postoje.
- Alati koji brišu — ulaze kao `deny` po podrazumevanom pravilu iz E1.
- Sažimanje unosa dnevnika starijih od godinu dana u dnevni zbir.
