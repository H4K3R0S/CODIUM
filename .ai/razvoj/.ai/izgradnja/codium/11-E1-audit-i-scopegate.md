---
id: codium-a044c071-11-e1-audit-i-scopegate-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E1 — Audit Logs + ScopeGate (sidebar „Access & Users")
summary: '**Blok:** presečni temelj · **Zavisi od:** AI-2 · **Migracija:** codium
  v6 (pravila) + v7 (odobrenja) + ops v2'
keywords:
- audit
- logs
- scopegate
- sidebar
- access
- users
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/11-E1-audit-i-scopegate.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
- type: references
  target: core-7687f8e1-2026-08-28-codium-odobrenja-i-agenti-design-md
  weight: 0.3
---

# E1 — Audit Logs + ScopeGate (sidebar „Access & Users")

**Blok:** presečni temelj · **Zavisi od:** AI-2 · **Migracija:** codium v6 (pravila) + v7 (odobrenja) + ops v2
**Sidebar:** `Audit Logs` i `Access & Users`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Dve strane iste stvari:

- **ScopeGate** odlučuje **pre** akcije da li akter sme da je izvede.
- **Audit** beleži **posle** akcije šta se desilo, ko je tražio i šta je gate
  odgovorio.

Ovo je odluka korisnika da „Access & Users" ne znači višekorisnički login, nego
dozvole nad akcijama: čovek je jedan, a „korisnici" su AI agenti i automatizacije.

Faza ide rano jer se dozvole i trag ne mogu naknadno ugurati u desetak servisa bez
prepravke svakog od njih.

## Model dozvola

Akter (`Actor`) je jedno od:

- `human` — korisnik, ima sve dozvole,
- `agent:<slug>` — AI agent iz E9,
- `automation:<id>` — pravilo iz E10,
- `system` — pozadinski poslovi CORE-a.

Akcija (`action`) je stabilan string u obliku `<sekcija>.<glagol>`, na primer
`repo.read`, `repo.push`, `file.write`, `file.delete`, `pipeline.run`,
`deploy.execute`, `infra.restart`, `secret.read`, `ai.call_online`.

Cilj (`target`) je putanja ili identifikator resursa, uz podršku za obrazac sa
zvezdicom (`project:12/*`).

Odgovor gate-a je `allow`, `deny` ili `needs_approval`.

## Pravila odlučivanja

1. Najspecifičnije pravilo pobeđuje (duži `target` obrazac ima prednost).
2. Ako pravila nema, primenjuje se podrazumevano ponašanje po klasi akcije:
   čitanje je dozvoljeno, pisanje traži odobrenje, brisanje i sve destruktivno
   se odbija.
3. `human` nikada ne prolazi kroz gate — on je taj koji odobrava.
4. `needs_approval` upisuje stavku u red za odobrenje i vraća pozivaocu status
   „čeka", a ne izuzetak. Servis koji je zvao gate mora umeti da stane.

## Backend

`core/security/scope_gate.py` — CORE nivo, jer će ga koristiti i drugi domeni.

```
ScopeGate
    check(actor: str, action: str, target: str) -> Verdict
    rules() -> list[ScopeRule]
    upsert_rule(rule: ScopeRule) -> ScopeRule
    delete_rule(rule_id: int) -> None
```

`core/domains/codium/audit/`

- `models.py` — `AuditEntry`, `AuditQuery`, `ScopeRule`, `Approval`,
  `Verdict` (enumeracija `allow` / `deny` / `needs_approval`).
- `repository.py` — upis u `codium_audit_log` je isključivo `INSERT`; nema
  `UPDATE` ni `DELETE` metode. Čitanje ide kroz filtriran, straničen upit.
- `service.py` — `AuditService.record(...)`, `AuditService.query(...)`,
  `ApprovalService.pending()`, `.approve(id)`, `.reject(id)`.

Zadržavanje: unosi stariji od godinu dana se sažimaju u dnevni zbir kroz zaseban
posao održavanja. Sirovi unosi se ne brišu ručno iz aplikacije.

## Šema

Tabele se dele između dve baze (pravilo „Dve baze, ne jedna" u
[09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md)):

- `codium_audit_log` → **`codium_ops.db`**, migracija **ops v2**. To je
  append-heavy tabela u koju piše svaka mutacija u sistemu.
- `codium_scope_rules` → **`codium.db`**, migracija **v6**. Pravila su poslovni
  podaci: malo ih je, retko se menjaju, i idu u bekap zajedno sa projektima.
- `codium_approvals` → **`codium.db`**, migracija **v7**. Red za odobrenje je
  dodat kao posebna migracija posle v6 — v6 nosi samo pravila.

`codium_ops.db` više ne uvodi ova faza — nju je uveo `AI-2` (potrošnja,
`ops v1`). Ovde se toj bazi samo dodaje `ops v2`.

### `codium_ops.db` — migracija ops v2

```sql
CREATE TABLE codium_audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor      TEXT NOT NULL,
    action     TEXT NOT NULL,
    target     TEXT NOT NULL DEFAULT '',
    verdict    TEXT NOT NULL,
    outcome    TEXT NOT NULL DEFAULT 'ok',    -- ok | error
    detail     TEXT NOT NULL DEFAULT '',
    project_id INTEGER
);
CREATE INDEX idx_codium_audit_at     ON codium_audit_log (at DESC);
CREATE INDEX idx_codium_audit_actor  ON codium_audit_log (actor, at DESC);
CREATE INDEX idx_codium_audit_action ON codium_audit_log (action, at DESC);
```

### `codium.db` — migracija v6 (samo pravila)

```sql
CREATE TABLE codium_scope_rules (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    actor    TEXT NOT NULL,
    action   TEXT NOT NULL,
    target   TEXT NOT NULL DEFAULT '*',
    verdict  TEXT NOT NULL CHECK (verdict IN ('allow','deny','needs_approval')),
    note     TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `codium.db` — migracija v7 (odobrenja)

```sql
CREATE TABLE codium_approvals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor      TEXT NOT NULL,
    action     TEXT NOT NULL,
    target     TEXT NOT NULL DEFAULT '',
    payload    TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected','expired')),
    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at   TEXT
);
```

## API

`apps/api/routers/codium_audit.py`, prefiks `/api/v1/codium/audit`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/log` | filtriran, straničen dnevnik (`actor`, `action`) |
| GET | `/rules` | pravila dozvola |
| POST | `/rules` | novo pravilo |
| DELETE | `/rules/{id}` | brisanje pravila |
| GET | `/approvals` | stavke koje čekaju odluku |
| POST | `/approvals/{id}/approve` | odobrenje; `409` ako molba više ne čeka |
| POST | `/approvals/{id}/reject` | odbijanje; `409` ako molba više ne čeka |

Dnevnik nema endpoint za izmenu ni brisanje. To je namerno.

> **Napomena (izvršeno stanje, 2026-08-28):** `PUT /rules/{id}` (izmena
> pravila) nije napravljen. `ScopeRuleRepository` nosi samo `list`/`add`/
> `delete` — izmena pravila u redu ne postoji ni u repozitorijumu ni u API-ju.
> Ko god treba da promeni pravilo, obriše ga i doda novo. Filter po periodu
> (`from`/`to`) na `/log` takođe nije napravljen — dnevnik filtrira samo po
> `actor` i `action`. Ovo je odluka, ne propust: obim je zatvoren u
> [2026-08-28-codium-odobrenja-i-agenti-design.md](../../../docs/superpowers/specs/2026-08-28-codium-odobrenja-i-agenti-design.md)
> (Deo 1), koji je tačan opis onoga što je izgrađeno. Ako neka od ove dve
> stavke zatreba, to je nov posao, ne dovršetak ovog.

## GUI (radi se posle backend-a bloka)

- `pages/CodiumAccess.tsx` — tabela pravila (akter × akcija × cilj → odgovor)
  sa dodavanjem i brisanjem (bez uređivanja u redu — vidi napomenu iznad),
  plus panel „Čeka odobrenje" sa punim prikazom poteza koji se odobrava i
  dugmadima Odobri / Odbij.
- `pages/CodiumAudit.tsx` — dnevnik sa filterima po akteru i akciji (bez
  filtera po periodu — vidi napomenu iznad), učitavanje u stranicama, boja po
  odgovoru gate-a.

## Testovi

- `test_scope_gate` — specifičnost pravila, podrazumevano ponašanje po klasi
  akcije, `human` zaobilazi gate, `needs_approval` pravi stavku u redu.
- `test_codium_audit` — repository nema `update`/`delete`; upit filtrira i
  stranicira; sažimanje starih unosa čuva zbir.
- `test_api_codium_audit` — ne postoji ruta koja menja postojeći unos dnevnika.

## Definicija završetka

Servis proizvoljne faze može da pozove `scope_gate.check(...)` i `audit.record(...)`;
odbijena destruktivna akcija ostavlja trag; red za odobrenje radi kroz API;
testovi domena prolaze.
