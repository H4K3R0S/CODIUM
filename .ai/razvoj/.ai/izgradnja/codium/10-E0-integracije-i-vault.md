---
id: codium-bd38c530-10-e0-integracije-i-vault-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E0 — Integrations sloj + Credential vault
summary: '**Blok:** presečni temelj · **Zavisi od:** ništa · **Migracija:** codium
  v3'
keywords:
- integrations
- sloj
- credential
- vault
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/10-E0-integracije-i-vault.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E0 — Integrations sloj + Credential vault

**Blok:** presečni temelj · **Zavisi od:** ništa · **Migracija:** codium v3
**Vidljivo u GUI-ju:** ne (ekran dolazi u E11)

> **Faza se radi u dva reza.** `E0-mini` ide prvi u celoj traci, jer E8 bez njega
> nema gde da drži OpenRouter ključ. `E0-pun` čeka dok E4 i E5 ne zatraže SSH i
> Docker. Podela je opisana u odeljku „Dva reza" niže.

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Jedno mesto na kome CODIUM zna „sa čime sve ume da razgovara" i gde bezbedno drži
kredencijale za to. Svaka kasnija faza koja traži pristup spolja (GitHub token,
Docker registry, SSH ključ, OpenRouter API ključ) uzima ga odavde i ne bavi se
čuvanjem tajni.

Bez ovoga svaka sledeća faza izmišlja svoj način čuvanja ključeva, i tajne
završe raštrkane po bazi i konfiguracionim fajlovima.

## Osnovni princip

Baza čuva **opis konektora i alias tajne**. Sama tajna nikada ne ulazi u SQLite,
u `config/`, niti u bilo koji fajl pod verzijom. Vrednost živi u OS keychain-u
(na Windows-u: Credential Manager), a domen je dohvata po aliasu u trenutku
upotrebe.

## Backend

### Vault

Nov modul `core/security/secrets.py` — CORE nivo, ne CODIUM, jer će ga koristiti
i drugi domeni.

```
SecretVault
    set(alias: str, value: str) -> None
    get(alias: str) -> str | None
    delete(alias: str) -> None
    exists(alias: str) -> bool
```

Implementacija preko biblioteke `keyring` (servis ime `CORE`, korisničko ime =
alias). Ako keychain nije dostupan, `get` vraća `None` i servis prijavljuje
degradirano stanje — nikada ne pada na čuvanje u fajl.

### Registracija zavisnosti `keyring`

`keyring` je **jedina** nova Python biblioteka u celoj enterprise traci. Registruje
se po sva četiri koraka iz `docs/DEPENDENCIES.md` — ne samo u `requirements.txt`:

1. Unos u `CORE_DEPENDENCIES` (`core/foundation/dependencies.py`):

   ```python
   Dependency(
       key="keyring",
       label="keyring",
       kind=DependencyKind.PYTHON,
       severity=DependencySeverity.IMPORTANT,
       probe="keyring",
       purpose="Bezbedno čuvanje API ključeva i lozinki u OS keychain-u.",
       install_hint="python -m pip install keyring",
       installer=DependencyInstaller.PIP,
   )
   ```

2. `scripts/install/keyring.ps1` (obrazac: postojeći `deep_translator.ps1`), pa
   ime skripte u `INSTALL_SCRIPTS` (`core/foundation/installer.py`).
3. Red u tabeli „Katalog alata" u `docs/DEPENDENCIES.md`.
4. `keyring` u `requirements.txt`.

Bez prvog koraka indikator pored „CORE Online" i INSTALL dugme ne znaju za alat.

> Napomena: `.ai/DEPENDENCIES.json` **nije** registar biblioteka — to je graf
> zavisnosti između modula (ključevi `rules` i `graph`). Registar alata je
> `CORE_DEPENDENCIES` u Python kodu.

### Konektori

`core/domains/codium/integrations/`

- `models.py` — `Connector`, `ConnectorCreate`, `ConnectorUpdate`,
  `ConnectorKind` (enumeracija: `github`, `docker_registry`, `ssh_host`,
  `openrouter`, `smtp`), `ConnectorStatus` (`unconfigured`, `ok`, `error`).
- `providers/base.py` — protokol koji svaki tip konektora ispunjava:

  ```
  ConnectorProvider
      kind: ConnectorKind
      required_fields() -> tuple[str, ...]   # koja polja forma traži
      secret_fields() -> tuple[str, ...]     # koja od njih idu u vault
      test(config: dict, secrets: dict) -> ConnectorProbe
  ```

  `ConnectorProbe` nosi `ok: bool`, `message: str`, `latency_ms: int | None`.
- `providers/local.py` — trivijalni provideri koji ne traže mrežu
  (`ssh_host` u prvom rezu proverava samo da ključ postoji i da je host razrešiv).
- `repository.py` — CRUD nad `codium_connectors`.
- `service.py` — `ConnectorService`: kreiranje (tajna ide u vault, u bazu ide
  alias), izmena, brisanje (briše i tajnu iz vault-a), `test_connection(id)`.

### Šema (migracija v3)

```sql
CREATE TABLE codium_connectors (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL,
    config_json  TEXT NOT NULL DEFAULT '{}',   -- ne-tajna podešavanja
    secret_alias TEXT,                          -- ključ u vault-u, ne vrednost
    status       TEXT NOT NULL DEFAULT 'unconfigured',
    last_tested_at TEXT,
    last_error   TEXT,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_codium_connectors_name ON codium_connectors (name);
```

### API

`apps/api/routers/codium_integrations.py`, prefiks `/api/v1/codium/integrations`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/kinds` | spisak podržanih tipova + koja polja traže |
| GET | `/` | lista konektora (bez tajni) |
| POST | `/` | novi konektor; tajna ide u vault |
| PATCH | `/{id}` | izmena; prazna tajna znači „ne diraj postojeću" |
| DELETE | `/{id}` | briše konektor i njegovu tajnu |
| POST | `/{id}/test` | pokreće `test()` provajdera |

Odgovori **nikada** ne vraćaju vrednost tajne, samo `has_secret: bool`.

## Dva reza

### E0-mini — radi se prvi u celoj traci

Obim: `SecretVault` u celini, `Connector` model, repozitorijum, servis, i **samo
jedan** tip konektora — `openrouter`. Migracija v3 pravi tabelu u punom obliku
(kolone se ne dodaju kasnije), ali provajder postoji jedan.

Toliko je dovoljno da E8 ima gde da drži API ključ. Procena: mali posao, oko
dva do tri fajla plus migracija.

### E0-pun — radi se posle E8

Dodaje provajdere `github`, `docker_registry`, `ssh_host`, `smtp`, njihove
`test()` implementacije i pun `GET /kinds` odgovor. Nema nove migracije — tabela
već stoji od v3.

## GUI

Nema ekrana ni u jednom rezu. Ekran je E11. Ovde se samo dodaju tipovi u
`types/codium.ts` i pozivi u `codiumApi.ts`, da E11 kasnije bude tanak.

## Zadatak pripreme (radi se uz ovu fazu)

U `apps/gui/src/components/layout/Sidebar.tsx` zameniti badge oznake faza
F13–F17 E-kodovima, prema tabeli u `09-ENTERPRISE-OVERVIEW.md`. Stavke ostaju
`kind: "soon"` dok ekran ne stigne.

## Testovi

- `test_secret_vault` — lažni keyring backend: upis, čitanje, brisanje,
  ponašanje kad keychain nije dostupan.
- `test_codium_connectors` — kreiranje upisuje alias a ne vrednost; brisanje
  konektora briše i tajnu; `test_connection` sa lažnim provajderom vraća `ok` i
  upisuje `last_tested_at`.
- `test_api_codium_integrations` — odgovor ne sadrži tajnu ni pod kojim ključem.

## Definicija završetka

Konektor se može napraviti, izmeniti, testirati i obrisati preko API-ja; tajna
nije pronalaziva u `codium.db` ni u jednom fajlu repozitorijuma; testovi domena
prolaze.
