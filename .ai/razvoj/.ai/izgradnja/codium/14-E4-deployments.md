---
id: codium-9e822470-14-e4-deployments-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E4 — Deployments
summary: '**Blok:** razvojna loza · **Zavisi od:** E1, E2, E3 · **Migracija:** codium
  v7'
keywords:
- deployments
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/14-E4-deployments.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E4 — Deployments

**Blok:** razvojna loza · **Zavisi od:** E1, E2, E3 · **Migracija:** codium v7
**Sidebar:** `Deployments`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Rezultat uspešnog pipeline pokretanja se isporučuje negde — u folder koji servira
lokalni server, u lokalni Docker, ili kasnije na udaljeni host. Sa istorijom i
mogućnošću povratka na prethodnu verziju.

## Osnovni princip

Deploy **nema svoj build**. Ulaz je uvek uspešan `PipelineRun` iz E3 i artefakt
koji je taj run proizveo. Time je isključeno „radilo je kod mene" — isporučuje se
tačno ono što je prošlo korake.

## Artefakt

Pipeline definicija dobija opciono polje na nivou pokretanja:

```json
{
  "artifact": { "path": "apps/gui/dist" }
}
```

`path` je folder ili fajl, relativan na koren repozitorijuma; proverava se istim
`_safe(rel)` iz `explorer.py` kao i `working_dir` u E3.

Po uspešnom pokretanju runner pakuje tu putanju u `zip` i smešta ga pod
`CodiumPaths.artifacts / <run_id>.zip`. `CodiumPaths` dobija novi atribut
`artifacts` (`data/codium/artifacts`) i ulazi u `ensure_dirs()`.

Zadržavanje: čuva se poslednjih 20 artefakata po pipeline-u.

## Backend

`core/domains/codium/deployments/`

### Provider

`providers/base.py`

```
DeployProvider
    kind: DeployKind
    validate(target: DeployTarget) -> None
    deploy(target, artifact_path, run) -> DeployResult
    rollback(target, previous: Deployment) -> DeployResult
    health(target) -> HealthResult
```

Prvi rez ima dva provajdera:

- `providers/local_folder.py` — raspakuje artefakt u ciljni folder. Prethodni
  sadržaj se ne briše, nego premešta u `<target>/.codium-releases/<timestamp>/`.
  Povratak je premeštanje nazad — zato je jeftin i pouzdan.
- `providers/local_docker.py` — pokreće `docker compose up -d --build` u zadatom
  folderu, ili `docker run` za jednu sliku. Povratak je pokretanje prethodne
  oznake slike.

`providers/ssh_host.py` **nije** deo ove faze. Interfejs i `DeployKind` unos
postoje, pa se dodaje kasnije bez prepravke servisa i ekrana. Kredencijal bi
došao iz E0 konektora tipa `ssh_host`.

### Servis

`DeploymentService`:

- `deploy(target_id, run_id)` — proverava da je run uspešan i da artefakt postoji,
  traži `deploy.execute` od ScopeGate-a, izvršava, upisuje red, beleži u audit.
- `rollback(deployment_id)` — vraća na prethodnu uspešnu isporuku za isti cilj.
- `history(target_id)`, `current(target_id)`.

Isporuka je podrazumevano **`needs_approval`** u ScopeGate-u za sve aktere osim
čoveka. Automatizacija iz E10 sme da je zatraži, ali ne i da je izvrši bez potvrde,
osim ako korisnik izričito napiše pravilo koje to dozvoljava.

## Šema (migracija v7)

```sql
CREATE TABLE codium_deploy_targets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER REFERENCES codium_projects (id) ON DELETE SET NULL,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,            -- local_folder | local_docker | ssh_host
    config_json TEXT NOT NULL DEFAULT '{}',
    connector_id INTEGER REFERENCES codium_connectors (id) ON DELETE SET NULL,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE codium_deployments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id   INTEGER NOT NULL REFERENCES codium_deploy_targets (id) ON DELETE CASCADE,
    run_id      INTEGER REFERENCES codium_pipeline_runs (id) ON DELETE SET NULL,
    commit_sha  TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
        -- pending | running | success | failed | rolled_back
    release_ref TEXT,                     -- folder ili oznaka slike, za povratak
    detail      TEXT NOT NULL DEFAULT '',
    started_at  TEXT,
    finished_at TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_deploys_target ON codium_deployments (target_id, id DESC);
```

## API

`apps/api/routers/codium_deployments.py`, prefiks `/api/v1/codium/deployments`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/targets` | ciljevi isporuke |
| POST | `/targets` | nov cilj (provider validira konfiguraciju) |
| PATCH | `/targets/{id}` | izmena |
| DELETE | `/targets/{id}` | brisanje |
| GET | `/targets/{id}/health` | provera cilja |
| POST | `/` | isporuka (`target_id`, `run_id`) |
| GET | `/` | istorija (`?target_id=`) |
| POST | `/{id}/rollback` | povratak na prethodnu isporuku |

## GUI (radi se posle backend-a bloka)

`pages/CodiumDeployments.tsx`:

- Kartice ciljeva sa trenutno isporučenom verzijom, `commit_sha` i stanjem zdravlja.
- Dugme „Isporuči" nudi samo uspešna pokretanja koja imaju artefakt.
- Istorija isporuka po cilju sa dugmetom „Vrati" na svakoj prethodnoj uspešnoj.
- Kada je potrebna potvrda, kartica prikazuje da isporuka čeka odobrenje i vodi
  na ekran iz E1.

### Overview pločica

Pločica „Deployments" u `CodiumOverview.tsx` postoji i prazna je. Ova faza je
oživljava: broj ciljeva, poslednja isporuka i njen ishod, i upozorenje ako neka
čeka odobrenje.

## Testovi

- `test_local_folder_provider` — nad `tmp_path`: isporuka raspakuje sadržaj,
  prethodna verzija je sačuvana, povratak vraća tačno prethodno stanje.
- `test_deployment_service` — isporuka neuspešnog pokretanja se odbija; isporuka
  bez artefakta se odbija; `needs_approval` pravi stavku u redu i ne izvršava ništa.
- `test_api_codium_deployments` — `rollback` bez prethodne isporuke vraća urednu
  grešku, ne izuzetak.

Docker provider se testira lažnim izvršiocem komandi; testovi ne traže instaliran
Docker.

## Definicija završetka

Cilj se definiše i proverava; artefakt uspešnog pokretanja se isporučuje u lokalni
folder i u lokalni Docker; povratak na prethodnu verziju radi; isporuka traži
odobrenje kada je ne pokreće čovek; testovi domena prolaze.
