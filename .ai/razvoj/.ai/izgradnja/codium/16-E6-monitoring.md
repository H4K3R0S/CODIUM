---
id: codium-22e3d9cd-16-e6-monitoring-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E6 — Monitoring
summary: '**Blok:** operativna loza · **Zavisi od:** E5 · **Migracija:** codium v9
  + ops v3'
keywords:
- monitoring
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/16-E6-monitoring.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E6 — Monitoring

**Blok:** operativna loza · **Zavisi od:** E5 · **Migracija:** codium v9 + ops v3
**Sidebar:** `Monitoring`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Servisi popisani u E5 se mere u pravilnim razmacima, uzorci se čuvaju, a
odstupanja podižu alarm koji stiže u CORE notifikacije. Bez ovoga „Infrastructure"
pokazuje samo trenutak, a ne ponašanje kroz vreme.

## Odnos prema postojećem kodu

`core/system/metrics/system_metrics.py` već meri mašinu (procesor, memorija,
disk). Ta merenja se koriste kao izvor za node-nivo uzorke i **ne pišu se ponovo**.
E6 dodaje merenja po servisu i trajno čuvanje.

## Šta se meri

| Vrsta uzorka | Izvor | Primenjuje se na |
|---|---|---|
| `up` (0/1) | `InfraProvider.status` | svaki servis |
| `latency_ms` | HTTP proba ili otvaranje soketa | servis koji ima port ili URL |
| `cpu_percent`, `memory_mb` | PID procesa, Docker stats | proces i kontejner |
| `host_cpu`, `host_memory`, `host_disk` | `system_metrics.py` | node |

## Backend

`core/domains/codium/monitoring/`

- `models.py` — `Probe`, `MetricSample`, `AlertRule`, `Alert`,
  `AlertState` (`ok`, `firing`, `resolved`).
- `probes.py` — pojedinačne provere. Čist modul koji prima konfiguraciju i vraća
  uzorke; nema pristup bazi. Tipovi: `http` (očekivani status i rok), `tcp`
  (port sluša), `process` (PID živ), `docker` (stanje kontejnera).
- `collector.py` — pozadinski sakupljač. Jedan `asyncio` zadatak koji se budi na
  zadatih 30 sekundi, prolazi kroz uključene servise, izvršava probe uporedo
  (ograničeno na 8 istovremenih) i upisuje uzorke u seriji.
- `alerts.py` — ocena pravila nad poslednjim uzorcima.
- `repository.py`, `service.py`.

Sakupljač se pokreće i gasi kroz postojeći `lifecycle` mehanizam CORE-a
(`core/foundation/lifecycle.py`), da ne bi ostajao živ posle gašenja aplikacije.

### Alarmi

Pravilo: `metric`, `comparison` (`<`, `>`, `==`), `threshold`, `for_samples`
(koliko uzastopnih uzoraka mora da prekrši prag pre paljenja). `for_samples`
postoji da jedan promašen uzorak ne pali alarm.

Kada pravilo pređe u `firing`, šalje se CORE notifikacija i upisuje audit unos.
Kada se vrati, alarm prelazi u `resolved` sa vremenom trajanja. Isti alarm se ne
ponavlja dok traje.

## Šema

Podela na dve baze: `codium_metric_samples` je najbrže rastuća tabela u celom
sistemu i ide u `codium_ops.db` (**ops v3**); pravila i alarmi su poslovni podaci
i idu u `codium.db` (**v9**).

### `codium_ops.db` — migracija ops v3

```sql
-- Bez stranog ključa: `service_id` i `node_id` pokazuju na redove u `codium.db`.
CREATE TABLE codium_metric_samples (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER,
    node_id    INTEGER,
    metric     TEXT NOT NULL,
    value      REAL NOT NULL,
    at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_codium_samples_lookup ON codium_metric_samples (service_id, metric, at DESC);
```

### `codium.db` — migracija v9

```sql
CREATE TABLE codium_alert_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id  INTEGER REFERENCES codium_infra_services (id) ON DELETE CASCADE,
    metric      TEXT NOT NULL,
    comparison  TEXT NOT NULL CHECK (comparison IN ('<','>','==')),
    threshold   REAL NOT NULL,
    for_samples INTEGER NOT NULL DEFAULT 2,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE codium_alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id     INTEGER NOT NULL REFERENCES codium_alert_rules (id) ON DELETE CASCADE,
    state       TEXT NOT NULL DEFAULT 'firing',
    value       REAL,
    started_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);
```

**Zadržavanje je obavezno, ne opciono.** Uzorak na 30 sekundi za deset servisa
znači oko 29.000 redova dnevno. Posao održavanja jednom dnevno: uzorci stariji od
48 sati se sažimaju u petominutne proseke, stariji od 30 dana u dnevne, stariji od
godinu dana se brišu. Bez ovoga baza raste bez granice.

## API

`apps/api/routers/codium_monitoring.py`, prefiks `/api/v1/codium/monitoring`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/overview` | poslednje stanje svih servisa u jednom pozivu |
| GET | `/series` | vremenski red (`?service_id=&metric=&from=&to=&bucket=`) |
| GET | `/rules` | pravila alarma |
| POST | `/rules` | novo pravilo |
| PATCH | `/rules/{id}` | izmena |
| DELETE | `/rules/{id}` | brisanje |
| GET | `/alerts` | aktivni i istorijski alarmi (`?state=`) |
| POST | `/collect` | ručno merenje odmah (za proveru pravila) |

`/series` vraća već sažete kante po `bucket` parametru, da GUI ne dobija hiljade
tačaka za grafikon od 400 piksela.

## GUI (radi se posle backend-a bloka)

`pages/CodiumMonitoring.tsx`:

- Zid pločica: servis, stanje, dostupnost u poslednja 24 sata, mali grafikon.
- Detalj servisa: grafikoni po metrici sa izborom perioda (1 sat, 24 sata, 7 dana).
- Traka aktivnih alarma na vrhu, sa vremenom paljenja.
- Grafikoni po `dataviz` pravilima projekta; bez nove biblioteke ako postojeći
  grafikon u CORE-u pokriva potrebu.

### Overview pločica

Ova faza dodaje na `CodiumOverview.tsx` traku aktivnih alarma — najkorisniju
stvar koju zbirna tabla može da pokaže. Prazna traka znači da je sve u redu.

## Testovi

- `test_probes` — svaki tip probe protiv lažnog izvršioca: uspeh, neuspeh,
  istek roka.
- `test_alerts` — pravilo sa `for_samples: 3` ne pali na dva prekršaja, pali na
  tri; povratak vrednosti u opseg razrešava alarm; isti alarm se ne duplira.
- `test_retention` — sažimanje 48-satnih uzoraka daje očekivan broj kanti i
  očuvane proseke.
- `test_api_codium_monitoring` — `/series` poštuje `bucket` i ne vraća sirove
  uzorke za širok period.

## Definicija završetka

Sakupljač radi u pozadini i staje sa aplikacijom; uzorci se čuvaju i sažimaju;
alarm se pali, šalje notifikaciju i razrešava; `/series` vraća sažete podatke;
testovi domena prolaze.
