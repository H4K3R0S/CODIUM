---
id: codium-d048df85-15-e5-infrastructure-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E5 — Infrastructure
summary: '**Blok:** operativna loza · **Zavisi od:** E0, E1 · **Migracija:** codium
  v8'
keywords:
- infrastructure
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/15-E5-infrastructure.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E5 — Infrastructure

**Blok:** operativna loza · **Zavisi od:** E0, E1 · **Migracija:** codium v8
**Sidebar:** `Infrastructure`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Popis svega što negde radi i što CODIUM ume da upali, ugasi i proveri: lokalne
dev servere, Docker kontejnere, baze, pozadinske procese, kasnije i udaljene
hostove. E6 Monitoring meri ove iste stavke; E10 Automations ih pokreće.

## Odnos prema postojećem kodu

`core/domains/codium/dev_server.py` već zna da pokrene i zaustavi dev server
projekta (F7 Preview). Ta logika se **ne duplira** — postaje prvi provider
(`local_process`), a `dev_server.py` ostaje njen pozivalac ili se u nju uvija.
Ovo je jedina tačka gde faza dira postojeći modul; izmena mora ostaviti F7
Preview u punoj funkciji.

## Model

Dva nivoa:

- **Node** — mesto gde nešto radi. U prvom rezu postoji jedan ugrađen node
  `localhost`. Kasnije se dodaju udaljeni hostovi kroz E0 konektor `ssh_host`.
- **Service** — jedna stvar koja radi na node-u: proces, kontejner, baza, port.

Razdvajanje postoji da bi kasnije dodavanje udaljene mašine bilo dodavanje reda,
a ne prepravka modela.

## Backend

`core/domains/codium/infrastructure/`

### Provider

`providers/base.py`

```
InfraProvider
    kind: ServiceKind
    discover(node) -> list[DiscoveredService]
    status(service) -> ServiceState        # running | stopped | unknown | error
    start(service) -> None
    stop(service) -> None
    restart(service) -> None
    logs(service, lines) -> list[str]
```

Provajderi prvog reza:

- `providers/local_process.py` — dev serveri i pozadinski procesi. Preuzima
  logiku iz `dev_server.py`. Stanje se utvrđuje po PID-u i po tome da li port
  sluša.
- `providers/local_docker.py` — `docker ps`, `start`, `stop`, `restart`, `logs`
  preko `docker` CLI-ja. `discover` popunjava listu iz zatečenih kontejnera.
- `providers/port_probe.py` — najprostiji: „nešto sluša na ovom portu". Za baze
  i tuđe servise koje CODIUM ne pokreće, samo prati.

`providers/ssh_host.py` nije u ovoj fazi.

### Servis

`InfrastructureService`:

- `nodes()`, `services(node_id=None, project_id=None)`,
- `discover(node_id)` — pita svaki provider i predlaže nađene servise za upis;
  korisnik potvrđuje šta se dodaje u registar (ne upisuje se automatski sve),
- `start` / `stop` / `restart` — svaki prolazi kroz ScopeGate
  (`infra.start`, `infra.stop`, `infra.restart`) i piše u audit. `stop` i
  `restart` su podrazumevano `needs_approval` za ne-ljudske aktere,
- `logs(service_id, lines)`.

## Šema (migracija v8)

```sql
CREATE TABLE codium_infra_nodes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'local',   -- local | ssh
    connector_id INTEGER REFERENCES codium_connectors (id) ON DELETE SET NULL,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE codium_infra_services (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id     INTEGER NOT NULL REFERENCES codium_infra_nodes (id) ON DELETE CASCADE,
    project_id  INTEGER REFERENCES codium_projects (id) ON DELETE SET NULL,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,     -- local_process | local_docker | port_probe
    config_json TEXT NOT NULL DEFAULT '{}',   -- komanda, cwd, port, ime kontejnera
    auto_start  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_infra_services_node ON codium_infra_services (node_id);
```

Trenutno stanje servisa se **ne** upisuje u bazu. Ono se čita uživo od
provajdera i kešira u memoriji 5 sekundi. Istorija stanja je posao E6, u
zasebnoj tabeli uzoraka.

## API

`apps/api/routers/codium_infrastructure.py`, prefiks
`/api/v1/codium/infrastructure`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/nodes` | node-ovi |
| POST | `/nodes` | nov node |
| GET | `/services` | servisi sa uživo stanjem (`?node_id=&project_id=`) |
| POST | `/services` | ručni upis servisa |
| PATCH | `/services/{id}` | izmena |
| DELETE | `/services/{id}` | uklanjanje iz registra |
| POST | `/nodes/{id}/discover` | predlog nađenih servisa (ne upisuje) |
| POST | `/services/{id}/start` | pokretanje |
| POST | `/services/{id}/stop` | zaustavljanje |
| POST | `/services/{id}/restart` | ponovno pokretanje |
| GET | `/services/{id}/logs` | poslednjih N redova |

## GUI (radi se posle backend-a bloka)

`pages/CodiumInfrastructure.tsx`:

- Grupisano po node-u, kartica po servisu: ime, tip, stanje (boja), port, projekat.
- Dugmad Pokreni / Zaustavi / Restartuj, sa potvrdom za zaustavljanje.
- „Pronađi servise" otvara listu predloga sa čekiranjem šta upisati.
- Klik na servis otvara poslednjih 200 redova loga.

## Testovi

- `test_local_process_provider` — pokretanje trivijalnog procesa, stanje prelazi
  u `running`, zaustavljanje ga gasi zajedno sa decom.
- `test_infra_discover` — lažni Docker izvršilac vraća dva kontejnera; `discover`
  ih predlaže a **ne** upisuje u bazu.
- `test_infra_scope` — `stop` iz agentskog aktera bez pravila ne gasi ništa i
  ostavlja stavku u redu za odobrenje.
- Regresija: postojeći F7 Preview testovi moraju i dalje prolaziti posle uvijanja
  `dev_server.py`.

## Definicija završetka

Servisi se popisuju, prikazuju uživo stanje i pokreću se, zaustavljaju i
restartuju kroz gate; Docker i lokalni procesi rade; F7 Preview nije regresirao;
testovi domena prolaze.
