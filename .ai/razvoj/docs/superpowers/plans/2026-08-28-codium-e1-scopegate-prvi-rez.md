---
id: codium-2281544e-2026-08-28-codium-e1-scopegate-prvi-rez-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: CODIUM E1 — ScopeGate + Audit (prvi rez) Implementation Plan
summary: '> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
  (recommended) or superpowers:executing-plans to implement this plan t'
keywords:
- codium
- scopegate
- audit
- prvi
- rez
- implementation
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-28-codium-e1-scopegate-prvi-rez.md
---

# CODIUM E1 — ScopeGate + Audit (prvi rez) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CODIUM dobija sloj dozvola nad akcijama (`ScopeGate`) i nepromenljiv dnevnik (`audit`), ožičen na jednu stvarnu akciju — poziv online (plaćenog) modela iz chata.

**Architecture:** `ScopeGate` je čista odluka na CORE nivou: prima pravila kroz ubrizganu funkciju i vraća `Decision`, bez ijednog dodira baze. Pravila žive u `codium.db` (poslovni podatak, malo ih je), dnevnik u `codium_ops.db` (append-heavy). Gate se poziva iz `/ask` rute, ne iz domenskog servisa — isti obrazac kao evidencija potrošnje, koja je već tamo, i iz istog razloga: servis ostaje bez zavisnosti na bazu.

**Tech Stack:** Python 3.14, FastAPI, SQLite kroz `core.database`, pytest.

**Spec:** `.ai/izgradnja/codium/11-E1-audit-i-scopegate.md`

## Global Constraints

- Kod na engleskom, komentari i docstring-ovi na srpskom — kao u celom `core/`.
- Migracije su **aditivne**: `codium.db` ide na **v6**, `codium_ops.db` na **ops v2**. Postojeće verzije se ne diraju.
- Nema novih Python zavisnosti.
- Dnevnik je samo `INSERT` i `SELECT`. Repozitorijum ne sme imati `update` ni `delete` metodu.
- Podrazumevano ponašanje za `ai.call_online` je **allow** — gate uvodi kontrolu, ne menja zatečeno ponašanje.
- Verdikt `needs_approval` postoji u modelu, ali ga u ovom rezu ne proizvodi nijedno podrazumevano pravilo za `ai.call_online`; red za odobrenje dolazi u drugom rezu.
- Testovi se pokreću sa `./.venv/Scripts/python.exe -m pytest`, ne sistemskim `python`.
- Svaki test radi nad `tmp_path` bazom; nijedan ne sme da dodirne `data/database/`.

---

### Task 1: ScopeGate — čista odluka

**Files:**
- Create: `core/security/scope_gate.py`
- Test: `tests/test_scope_gate.py`

**Interfaces:**
- Consumes: ništa (nema uvoza iz projekta osim tipova).
- Produces:
  - `ScopeRule(actor: str, action: str, target: str = "*", verdict: str = "deny", note: str = "", id: int | None = None)` — frozen dataclass
  - `Decision(verdict: str, rule_id: int | None, reason: str)` — frozen dataclass
  - `ALLOW = "allow"`, `DENY = "deny"`, `NEEDS_APPROVAL = "needs_approval"`
  - `ScopeGate(rules: Callable[[], list[ScopeRule]])`
  - `ScopeGate.check(*, actor: str, action: str, target: str = "") -> Decision`

- [x] **Step 1: Write the failing test**

Create `tests/test_scope_gate.py`:

```python
# ========== TESTOVI: ScopeGate ==========
from __future__ import annotations

from core.security.scope_gate import ALLOW, DENY, NEEDS_APPROVAL, ScopeGate, ScopeRule


def _gate(*rules: ScopeRule) -> ScopeGate:
    return ScopeGate(lambda: list(rules))


# ---------- covek ----------
def test_human_ne_prolazi_kroz_gate():
    # Covek je taj koji odobrava; pravilo koje bi ga odbilo se ignorise.
    gate = _gate(ScopeRule(actor="*", action="*", target="*", verdict=DENY))
    odluka = gate.check(actor="human", action="file.delete", target="a.py")
    assert odluka.verdict == ALLOW
    assert odluka.rule_id is None


# ---------- podrazumevano po klasi akcije ----------
def test_citanje_je_dozvoljeno_bez_pravila():
    assert _gate().check(actor="agent:builder", action="repo.read").verdict == ALLOW


def test_pisanje_trazi_odobrenje_bez_pravila():
    odluka = _gate().check(actor="agent:builder", action="file.write")
    assert odluka.verdict == NEEDS_APPROVAL


def test_brisanje_je_odbijeno_bez_pravila():
    assert _gate().check(actor="agent:builder", action="file.delete").verdict == DENY


def test_online_poziv_je_dozvoljen_bez_pravila():
    # Namerno: gate uvodi kontrolu, ne menja zateceno ponasanje chata.
    odluka = _gate().check(actor="agent:builder", action="ai.call_online")
    assert odluka.verdict == ALLOW


def test_nepoznat_glagol_je_odbijen():
    assert _gate().check(actor="agent:x", action="nesto.cudno").verdict == DENY


# ---------- specificnost ----------
def test_najspecificniji_target_pobedjuje():
    gate = _gate(
        ScopeRule(actor="agent:builder", action="file.write", target="*",
                  verdict=DENY, id=1),
        ScopeRule(actor="agent:builder", action="file.write",
                  target="project:12/*", verdict=ALLOW, id=2),
    )
    odluka = gate.check(actor="agent:builder", action="file.write",
                        target="project:12/main.py")
    assert odluka.verdict == ALLOW
    assert odluka.rule_id == 2


def test_tacan_akter_pobedjuje_zamenu():
    gate = _gate(
        ScopeRule(actor="*", action="ai.call_online", target="*",
                  verdict=DENY, id=1),
        ScopeRule(actor="agent:builder", action="ai.call_online", target="*",
                  verdict=ALLOW, id=2),
    )
    odluka = gate.check(actor="agent:builder", action="ai.call_online")
    assert odluka.rule_id == 2


def test_zamena_u_akciji_hvata_celu_sekciju():
    gate = _gate(ScopeRule(actor="agent:builder", action="ai.*", target="*",
                           verdict=DENY, id=7))
    odluka = gate.check(actor="agent:builder", action="ai.call_online")
    assert odluka.verdict == DENY
    assert odluka.rule_id == 7


def test_pravilo_drugog_aktera_se_ne_primenjuje():
    gate = _gate(ScopeRule(actor="agent:drugi", action="ai.call_online",
                           target="*", verdict=DENY, id=3))
    odluka = gate.check(actor="agent:builder", action="ai.call_online")
    assert odluka.verdict == ALLOW
    assert odluka.rule_id is None


def test_odluka_nosi_razlog():
    gate = _gate(ScopeRule(actor="agent:builder", action="ai.call_online",
                           target="*", verdict=DENY, note="bez trosenja",
                           id=4))
    odluka = gate.check(actor="agent:builder", action="ai.call_online")
    assert "bez trosenja" in odluka.reason
```

- [x] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_scope_gate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.security.scope_gate'`

- [x] **Step 3: Write minimal implementation**

Create `core/security/scope_gate.py`:

```python
# ========== SCOPE GATE ==========
# Odlucuje PRE akcije da li akter sme da je izvede. CORE nivo, jer ce ga
# koristiti i drugi domeni, ne samo CODIUM.
#
# Gate ne zna za bazu: pravila prima kroz ubrizganu funkciju. Tako se ista
# odluka testira bez ijednog reda u SQLite-u, a pozivalac bira odakle pravila
# dolaze (baza, konfiguracija, test).
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

ALLOW = "allow"
DENY = "deny"
NEEDS_APPROVAL = "needs_approval"

# Podrazumevano ponasanje po glagolu akcije, kad nijedno pravilo ne pogadja.
#
# `call_online` je namerno `allow`: gate uvodi kontrolu nad postojecim chatom,
# a ne obara ga u trenutku spajanja. Ko hoce zabranu, upise pravilo.
_DEFAULTS: dict[str, str] = {
    "read": ALLOW,
    "list": ALLOW,
    "call_online": ALLOW,
    "write": NEEDS_APPROVAL,
    "push": NEEDS_APPROVAL,
    "run": NEEDS_APPROVAL,
    "execute": NEEDS_APPROVAL,
    "delete": DENY,
    "restart": DENY,
}

# Nepoznat glagol se odbija. Tiho dozvoljavanje nepoznate akcije je rupa koja
# se primeti tek kad nesto ode naopako.
_FALLBACK = DENY

# Akter koji ne prolazi kroz gate — on je taj koji odobrava.
HUMAN = "human"


@dataclass(frozen=True)
class ScopeRule:
    """Jedno pravilo dozvole."""

    actor: str
    action: str
    target: str = "*"
    verdict: str = DENY
    note: str = ""
    id: int | None = None


@dataclass(frozen=True)
class Decision:
    """Odgovor gate-a, sa tragom odakle je odluka dosla."""

    verdict: str
    rule_id: int | None
    reason: str


def _matches(pattern: str, value: str) -> bool:
    """Poklapanje sa zvezdicom na kraju obrasca (`project:12/*`)."""
    if pattern in ("", "*"):
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def _specificity(pattern: str) -> int:
    """Koliko je obrazac odredjen — duzi tacan deo znaci precizniji obrazac."""
    if pattern in ("", "*"):
        return 0
    if pattern.endswith("*"):
        return len(pattern) - 1
    # Tacan pogodak je uvek precizniji od bilo kog obrasca sa zvezdicom.
    return len(pattern) + 1


class ScopeGate:
    """Odlucuje da li akter sme da izvede akciju nad ciljem."""

    def __init__(self, rules: Callable[[], list[ScopeRule]]) -> None:
        self._rules = rules

    def check(self, *, actor: str, action: str, target: str = "") -> Decision:
        if actor == HUMAN:
            return Decision(ALLOW, None, "covek ne prolazi kroz gate")

        pogodjena = [
            rule for rule in self._rules()
            if _matches(rule.actor, actor)
            and _matches(rule.action, action)
            and _matches(rule.target, target)
        ]
        if pogodjena:
            # Najspecificnije pravilo pobedjuje; cilj je najjaci kriterijum,
            # pa akter, pa akcija.
            najbolje = max(
                pogodjena,
                key=lambda r: (_specificity(r.target), _specificity(r.actor),
                               _specificity(r.action)),
            )
            razlog = najbolje.note or f"pravilo {najbolje.actor} {najbolje.action}"
            return Decision(najbolje.verdict, najbolje.id, razlog)

        glagol = action.rsplit(".", 1)[-1]
        verdikt = _DEFAULTS.get(glagol, _FALLBACK)
        return Decision(verdikt, None, f"podrazumevano za `{glagol}`")
```

- [x] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_scope_gate.py -q`
Expected: PASS (12 testova)

- [x] **Step 5: Commit**

```bash
git add core/security/scope_gate.py tests/test_scope_gate.py
git commit -m "feat(core-security): ScopeGate odlucuje pre akcije, bez dodira baze"
```

---

### Task 2: Migracije — pravila (codium v6) i dnevnik (ops v2)

**Files:**
- Modify: `core/domains/codium/migrations.py` (dodati `CODIUM_MIGRATION_V6`, upisati ga u `CODIUM_MIGRATIONS`)
- Modify: `core/domains/codium/ops_migrations.py` (dodati `CODIUM_OPS_MIGRATION_V2`, upisati ga u `CODIUM_OPS_MIGRATIONS`)
- Test: `tests/test_codium_audit_schema.py`

**Interfaces:**
- Consumes: `DatabaseMigration` iz `core.database`, `initialize_codium_database` / `initialize_codium_ops_database` iz `core.domains.codium.runtime`.
- Produces: tabele `codium_scope_rules` (codium.db) i `codium_audit_log` (codium_ops.db).

- [x] **Step 1: Write the failing test**

Create `tests/test_codium_audit_schema.py`:

```python
# ========== TESTOVI: sema pravila i dnevnika ==========
from __future__ import annotations

from core.database import core_database_connection
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)


def _columns(path, table: str) -> set[str]:
    with core_database_connection(path) as connection:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_pravila_imaju_svoje_kolone(tmp_path):
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    assert _columns(baza, "codium_scope_rules") == {
        "id", "actor", "action", "target", "verdict", "note", "created_at",
    }


def test_verdikt_je_ogranicen_na_tri_vrednosti(tmp_path):
    import sqlite3

    import pytest

    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    with core_database_connection(baza) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO codium_scope_rules (actor, action, target, verdict) "
                "VALUES ('agent:x', 'file.write', '*', 'mozda')"
            )


def test_dnevnik_ima_svoje_kolone(tmp_path):
    baza = tmp_path / "codium_ops.db"
    initialize_codium_ops_database(baza)
    assert _columns(baza, "codium_audit_log") == {
        "id", "at", "actor", "action", "target", "verdict", "outcome",
        "detail", "project_id",
    }


def test_ops_v1_tabela_ostaje_netaknuta(tmp_path):
    # Migracija je aditivna: potrosnja iz `ops v1` mora i dalje da postoji.
    baza = tmp_path / "codium_ops.db"
    initialize_codium_ops_database(baza)
    assert "cost_usd" in _columns(baza, "codium_ai_usage")
```

- [x] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_audit_schema.py -q`
Expected: FAIL — `sqlite3.OperationalError: no such table: codium_scope_rules`

- [x] **Step 3: Write minimal implementation**

U `core/domains/codium/migrations.py`, pre reda `CODIUM_MIGRATIONS = (`:

```python
# ---------- v6: pravila dozvola (ScopeGate) ----------

CODIUM_MIGRATION_V6 = DatabaseMigration(
    scope="codium",
    version=6,
    name="create_scope_rules",
    statements=(
        # Pravila su poslovni podatak: malo ih je, retko se menjaju, i idu u
        # bekap zajedno sa projektima. Zato stoje ovde, a ne u ops bazi.
        #
        # CHECK nad verdiktom je namerno u semi: pogresna vrednost bi inace
        # tiho prosla i gate bi je vratio kao nepoznat verdikt.
        """
        CREATE TABLE codium_scope_rules (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            actor      TEXT NOT NULL,
            action     TEXT NOT NULL,
            target     TEXT NOT NULL DEFAULT '*',
            verdict    TEXT NOT NULL
                       CHECK (verdict IN ('allow','deny','needs_approval')),
            note       TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX idx_codium_scope_rules_actor "
        "ON codium_scope_rules (actor, action)",
    ),
)
```

I proširiti torku:

```python
CODIUM_MIGRATIONS = (
    CODIUM_MIGRATION_V1,
    CODIUM_MIGRATION_V2,
    CODIUM_MIGRATION_V3,
    CODIUM_MIGRATION_V4,
    CODIUM_MIGRATION_V5,
    CODIUM_MIGRATION_V6,
)
```

U `core/domains/codium/ops_migrations.py`, pre reda `CODIUM_OPS_MIGRATIONS = (`:

```python
# ---------- v2: dnevnik akcija (audit) ----------

CODIUM_OPS_MIGRATION_V2 = DatabaseMigration(
    scope="codium_ops",
    version=2,
    name="create_audit_log",
    statements=(
        # Append-heavy: u ovu tabelu pise svaka provera dozvole. Zato je ovde,
        # uz potrosnju, a ne u poslovnoj bazi.
        #
        # `at` je CURRENT_TIMESTAMP, dakle UTC — isto kao `codium_ai_usage`.
        """
        CREATE TABLE codium_audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actor      TEXT NOT NULL,
            action     TEXT NOT NULL,
            target     TEXT NOT NULL DEFAULT '',
            verdict    TEXT NOT NULL,
            outcome    TEXT NOT NULL DEFAULT 'ok',
            detail     TEXT NOT NULL DEFAULT '',
            project_id INTEGER
        )
        """,
        "CREATE INDEX idx_codium_audit_at ON codium_audit_log (at DESC)",
        "CREATE INDEX idx_codium_audit_actor "
        "ON codium_audit_log (actor, at DESC)",
        "CREATE INDEX idx_codium_audit_action "
        "ON codium_audit_log (action, at DESC)",
    ),
)
```

I proširiti torku:

```python
CODIUM_OPS_MIGRATIONS = (
    CODIUM_OPS_MIGRATION_V1,
    CODIUM_OPS_MIGRATION_V2,
)
```

- [x] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_audit_schema.py -q`
Expected: PASS (4 testa)

- [x] **Step 5: Commit**

```bash
git add core/domains/codium/migrations.py core/domains/codium/ops_migrations.py tests/test_codium_audit_schema.py
git commit -m "feat(codium): codium v6 pravila dozvola i ops v2 dnevnik akcija"
```

---

### Task 3: Repozitorijumi — pravila i dnevnik

**Files:**
- Create: `core/domains/codium/audit/__init__.py`
- Create: `core/domains/codium/audit/models.py`
- Create: `core/domains/codium/audit/repository.py`
- Test: `tests/test_codium_audit_repository.py`

**Interfaces:**
- Consumes: `ScopeRule` iz `core.security.scope_gate` (Task 1); tabele iz Task 2; `core_database_connection` iz `core.database`; `codium_database_path` / `codium_ops_database_path` iz `core.domains.codium.runtime`.
- Produces:
  - `AuditEntry(actor: str, action: str, verdict: str, target: str = "", outcome: str = "ok", detail: str = "", project_id: int | None = None, at: str = "", id: int | None = None)`
  - `ScopeRuleRepository(database_path: Path | None = None)` sa `list() -> list[ScopeRule]`, `add(rule: ScopeRule) -> ScopeRule`, `delete(rule_id: int) -> None`
  - `AuditRepository(database_path: Path | None = None)` sa `record(entry: AuditEntry) -> None`, `query(*, actor: str | None = None, action: str | None = None, limit: int = 100, offset: int = 0) -> list[AuditEntry]`

- [x] **Step 1: Write the failing test**

Create `tests/test_codium_audit_repository.py`:

```python
# ========== TESTOVI: repozitorijumi pravila i dnevnika ==========
from __future__ import annotations

import pytest

from core.domains.codium.audit import AuditEntry, AuditRepository, ScopeRuleRepository
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)
from core.security.scope_gate import DENY, ScopeRule


@pytest.fixture
def pravila(tmp_path) -> ScopeRuleRepository:
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    return ScopeRuleRepository(baza)


@pytest.fixture
def dnevnik(tmp_path) -> AuditRepository:
    baza = tmp_path / "codium_ops.db"
    initialize_codium_ops_database(baza)
    return AuditRepository(baza)


# ---------- pravila ----------
def test_dodato_pravilo_se_cita_nazad(pravila):
    pravila.add(ScopeRule(actor="agent:builder", action="ai.call_online",
                          target="*", verdict=DENY, note="bez trosenja"))
    svi = pravila.list()
    assert len(svi) == 1
    assert svi[0].actor == "agent:builder"
    assert svi[0].verdict == DENY
    assert svi[0].id is not None


def test_add_vraca_pravilo_sa_dodeljenim_id(pravila):
    upisano = pravila.add(ScopeRule(actor="agent:x", action="file.write",
                                    verdict=DENY))
    assert upisano.id is not None
    assert upisano.actor == "agent:x"


def test_obrisano_pravilo_nestaje(pravila):
    upisano = pravila.add(ScopeRule(actor="agent:x", action="file.write",
                                    verdict=DENY))
    pravila.delete(upisano.id)
    assert pravila.list() == []


# ---------- dnevnik ----------
def test_upisan_unos_se_cita_nazad(dnevnik):
    dnevnik.record(AuditEntry(actor="agent:builder", action="ai.call_online",
                              target="claude-sonnet-5", verdict="deny",
                              outcome="blocked", detail="pravilo domena"))
    unosi = dnevnik.query()
    assert len(unosi) == 1
    assert unosi[0].action == "ai.call_online"
    assert unosi[0].outcome == "blocked"
    assert unosi[0].at != ""


def test_dnevnik_nema_izmenu_ni_brisanje():
    # Nepromenljivost je poenta dnevnika: metoda koja ne postoji ne moze da se
    # pozove ni greskom, ni iz rute koju neko kasnije doda.
    assert not hasattr(AuditRepository, "update")
    assert not hasattr(AuditRepository, "delete")


def test_upit_filtrira_po_akteru(dnevnik):
    dnevnik.record(AuditEntry(actor="agent:a", action="ai.call_online",
                              verdict="allow"))
    dnevnik.record(AuditEntry(actor="agent:b", action="ai.call_online",
                              verdict="allow"))
    assert [u.actor for u in dnevnik.query(actor="agent:b")] == ["agent:b"]


def test_upit_filtrira_po_akciji(dnevnik):
    dnevnik.record(AuditEntry(actor="agent:a", action="ai.call_online",
                              verdict="allow"))
    dnevnik.record(AuditEntry(actor="agent:a", action="file.write",
                              verdict="deny"))
    assert [u.action for u in dnevnik.query(action="file.write")] == ["file.write"]


def test_upit_stranicira_i_vraca_najnovije_prvo(dnevnik):
    for redni in range(5):
        dnevnik.record(AuditEntry(actor="agent:a", action="ai.call_online",
                                  verdict="allow", detail=str(redni)))
    prva_strana = dnevnik.query(limit=2)
    druga_strana = dnevnik.query(limit=2, offset=2)
    assert len(prva_strana) == 2 and len(druga_strana) == 2
    # Najnovije prvo: poslednji upisan ima najveci id.
    assert prva_strana[0].id > druga_strana[0].id
```

- [x] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_audit_repository.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.domains.codium.audit'`

- [x] **Step 3: Write minimal implementation**

Create `core/domains/codium/audit/models.py`:

```python
# ========== MODELI DNEVNIKA ==========
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuditEntry:
    """Jedan upis u dnevnik: ko je sta trazio i sta je gate odgovorio.

    `outcome` je ishod same akcije (`ok` / `blocked` / `error`), dok je
    `verdict` odgovor gate-a. Nisu isto: dozvoljena akcija moze da pukne.
    """

    actor: str
    action: str
    verdict: str
    target: str = ""
    outcome: str = "ok"
    detail: str = ""
    project_id: int | None = None
    at: str = ""
    id: int | None = None
```

Create `core/domains/codium/audit/repository.py`:

```python
# ========== REPOZITORIJUMI: pravila dozvola i dnevnik ==========
# Pravila stoje u poslovnoj `codium.db`, dnevnik u operativnoj
# `codium_ops.db` — dve baze, jer im se rast i bekap razlikuju.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.audit.models import AuditEntry
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)
from core.security.scope_gate import ScopeRule


# ==========          PRAVILA DOZVOLA          ==========

class ScopeRuleRepository:
    """Citanje i upis pravila koja hrane `ScopeGate`."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def list(self) -> list[ScopeRule]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                "SELECT id, actor, action, target, verdict, note "
                "FROM codium_scope_rules ORDER BY id"
            ).fetchall()
        return [
            ScopeRule(id=row[0], actor=row[1], action=row[2], target=row[3],
                      verdict=row[4], note=row[5])
            for row in rows
        ]

    def add(self, rule: ScopeRule) -> ScopeRule:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO codium_scope_rules (actor, action, target, "
                "verdict, note) VALUES (?, ?, ?, ?, ?)",
                (rule.actor, rule.action, rule.target, rule.verdict, rule.note),
            )
            novi_id = cursor.lastrowid
        # Frozen dataclass: novi primerak, ne izmena postojeceg.
        return ScopeRule(id=novi_id, actor=rule.actor, action=rule.action,
                         target=rule.target, verdict=rule.verdict,
                         note=rule.note)

    def delete(self, rule_id: int) -> None:
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                "DELETE FROM codium_scope_rules WHERE id = ?", (rule_id,)
            )


# ==========          DNEVNIK          ==========

class AuditRepository:
    """Upis i citanje dnevnika akcija.

    Namerno nema `update` ni `delete`: dnevnik koji se moze prepraviti nije
    dnevnik. Zadrzavanje starih unosa je posao odrzavanja, ne aplikacije.
    """

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_ops_database_path()

    def record(self, entry: AuditEntry) -> None:
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO codium_audit_log (
                    actor, action, target, verdict, outcome, detail, project_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (entry.actor, entry.action, entry.target, entry.verdict,
                 entry.outcome, entry.detail, entry.project_id),
            )

    def query(self, *, actor: str | None = None, action: str | None = None,
              limit: int = 100, offset: int = 0) -> list[AuditEntry]:
        uslovi: list[str] = []
        parametri: list[object] = []
        if actor is not None:
            uslovi.append("actor = ?")
            parametri.append(actor)
        if action is not None:
            uslovi.append("action = ?")
            parametri.append(action)

        where = f" WHERE {' AND '.join(uslovi)}" if uslovi else ""
        parametri.extend([limit, offset])

        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                "SELECT id, at, actor, action, target, verdict, outcome, "
                f"detail, project_id FROM codium_audit_log{where} "
                "ORDER BY id DESC LIMIT ? OFFSET ?",
                tuple(parametri),
            ).fetchall()

        return [
            AuditEntry(id=row[0], at=row[1], actor=row[2], action=row[3],
                       target=row[4], verdict=row[5], outcome=row[6],
                       detail=row[7], project_id=row[8])
            for row in rows
        ]
```

Create `core/domains/codium/audit/__init__.py`:

```python
# ========== CODIUM AUDIT ==========
# Dozvole (pravila za `ScopeGate`) i nepromenljiv dnevnik akcija.
from core.domains.codium.audit.models import AuditEntry
from core.domains.codium.audit.repository import AuditRepository, ScopeRuleRepository

__all__ = [
    "AuditEntry",
    "AuditRepository",
    "ScopeRuleRepository",
]
```

- [x] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_audit_repository.py -q`
Expected: PASS (8 testova)

- [x] **Step 5: Commit**

```bash
git add core/domains/codium/audit tests/test_codium_audit_repository.py
git commit -m "feat(codium): repozitorijumi pravila dozvola i dnevnika bez izmene"
```

---

### Task 4: `CodiumAssistant.resolve` — koji model bi bio pozvan

**Files:**
- Modify: `core/domains/codium/assistant/assistant_service.py` (dodati metodu `resolve`)
- Test: `tests/test_codium_assistant.py` (dopuna postojećeg fajla)

**Interfaces:**
- Consumes: postojeći `ModelRouter.resolve(*, project_id, persona, override_provider, override_model) -> ResolvedModel`.
- Produces: `CodiumAssistant.resolve(*, project_id: int | None, persona_id: str, model: str | None = None, provider: str | None = None) -> ResolvedModel`. Ruta iz Task 5 je koristi da sazna provajdera **pre** poziva.

- [x] **Step 1: Write the failing test**

Dopisati na kraj `tests/test_codium_assistant.py`:

```python
def test_resolve_vraca_model_bez_poziva_provajdera():
    """Ruta mora da zna koji bi model bio pozvan PRE nego sto ga pozove.

    Bez ovoga bi gate ili gadjao pogresnog provajdera, ili bi resolvovanje
    bilo napisano dvaput — pa bi se dve kopije s vremenom razisle.
    """
    from types import SimpleNamespace

    from core.ai.model_router import ModelRouter

    class Provajder:
        name = "ollama"
        is_local = True

        def chat(self, messages, model):        # pragma: no cover
            raise AssertionError("resolve ne sme da zove provajdera")

    router = ModelRouter(
        providers={"ollama": Provajder()},
        pref_lookup=lambda project_id, persona: None,
        default_lookup=lambda: ("ollama", "qwen2.5"),
    )
    assistant = CodiumAssistant(
        router,
        project_lookup=lambda _: None,
        # Ugradjeni spisak persona se ovde ne testira — stub drzi test na
        # jednoj stvari: da `resolve` vrati odluku bez poziva provajdera.
        personas=lambda persona_id: SimpleNamespace(id=persona_id, system=""),
    )

    resolved = assistant.resolve(project_id=None, persona_id="global")

    assert resolved.provider_name == "ollama"
    assert resolved.model == "qwen2.5"
```

- [x] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_assistant.py -k resolve -q`
Expected: FAIL — `AttributeError: 'CodiumAssistant' object has no attribute 'resolve'`

- [x] **Step 3: Write minimal implementation**

U `core/domains/codium/assistant/assistant_service.py`, iznad metode `ask`:

```python
    def resolve(
        self,
        *,
        project_id: int | None,
        persona_id: str,
        model: str | None = None,
        provider: str | None = None,
    ) -> ResolvedModel:
        """Koji bi model bio pozvan, bez pozivanja.

        Ruta ovim saznaje provajdera pre nego sto pusti poziv, pa dozvola moze
        da se proveri unapred. Ista odluka se posle prosledjuje `ask`-u kao
        override, da se ne resolvuje dvaput i da se dve odluke ne raziđu.
        """
        active = self._personas(persona_id)
        return self._router.resolve(
            project_id=project_id,
            persona=active.id,
            override_provider=provider,
            override_model=model,
        )
```

Uz to dodati uvoz tipa na vrh fajla (uz postojeći uvoz `ModelRouter`):

```python
from core.ai.model_router import ModelRouter, ResolvedModel
```

- [x] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_assistant.py -q`
Expected: PASS (svi postojeći + novi)

- [x] **Step 5: Commit**

```bash
git add core/domains/codium/assistant/assistant_service.py tests/test_codium_assistant.py
git commit -m "feat(codium): asistent ume da kaze koji bi model pozvao, bez poziva"
```

---

### Task 5: Runtime — gate i dnevnik kao zavisnosti rute

**Files:**
- Create: `apps/api/codium_security_runtime.py`
- Test: `tests/test_codium_security_runtime.py`

**Interfaces:**
- Consumes: `ScopeGate`, `ScopeRuleRepository`, `AuditRepository` iz Task 1 i 3.
- Produces:
  - `get_scope_rules() -> ScopeRuleRepository`
  - `get_scope_gate() -> ScopeGate`
  - `get_audit() -> AuditRepository`
  - `reset() -> None` (za testove)

- [x] **Step 1: Write the failing test**

Create `tests/test_codium_security_runtime.py`:

```python
# ========== TESTOVI: runtime bezbednosnog sloja CODIUM-a ==========
from __future__ import annotations

from apps.api import codium_security_runtime
from core.security.scope_gate import ScopeGate


def test_gate_cita_pravila_lenjo(tmp_path, monkeypatch):
    """Gate sme da se napravi i kad baze jos nema.

    Pravila se citaju u trenutku provere, ne u trenutku pravljenja gate-a —
    inace bi svaki restart trazio da baza vec postoji, a pravilo dodato u toku
    rada ne bi vazilo do sledeceg pokretanja.
    """
    monkeypatch.setattr(
        codium_security_runtime, "_database_path",
        lambda: tmp_path / "nema.db",
    )
    codium_security_runtime.reset()

    gate = codium_security_runtime.get_scope_gate()

    assert isinstance(gate, ScopeGate)


def test_isti_primerak_kroz_ponovni_poziv(tmp_path, monkeypatch):
    monkeypatch.setattr(
        codium_security_runtime, "_database_path",
        lambda: tmp_path / "codium.db",
    )
    codium_security_runtime.reset()

    assert codium_security_runtime.get_audit() is codium_security_runtime.get_audit()
```

- [x] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_security_runtime.py -q`
Expected: FAIL — `ImportError: cannot import name 'codium_security_runtime'`

- [x] **Step 3: Write minimal implementation**

Create `apps/api/codium_security_runtime.py`:

```python
# ========== RUNTIME: dozvole i dnevnik CODIUM-a ==========
# Rute traze gate i dnevnik kroz `Depends`, pa im ovde stoji jedan primerak.
# Testovi ga menjaju kroz `app.dependency_overrides`, ne kroz ovaj modul.
from __future__ import annotations

from pathlib import Path

from core.domains.codium.audit import AuditRepository, ScopeRuleRepository
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)
from core.security.scope_gate import ScopeGate

_rules: ScopeRuleRepository | None = None
_audit: AuditRepository | None = None
_gate: ScopeGate | None = None


def _database_path() -> Path:
    """Poslovna baza (pravila). Izdvojeno da test moze da je zameni."""
    return codium_database_path()


def _ops_database_path() -> Path:
    """Operativna baza (dnevnik)."""
    return codium_ops_database_path()


def get_scope_rules() -> ScopeRuleRepository:
    global _rules
    if _rules is None:
        _rules = ScopeRuleRepository(_database_path())
    return _rules


def get_audit() -> AuditRepository:
    global _audit
    if _audit is None:
        _audit = AuditRepository(_ops_database_path())
    return _audit


def get_scope_gate() -> ScopeGate:
    global _gate
    if _gate is None:
        # Pravila se citaju u trenutku provere, ne sada: pravilo dodato u toku
        # rada mora da vazi odmah, bez restarta.
        _gate = ScopeGate(lambda: get_scope_rules().list())
    return _gate


def reset() -> None:
    """Zaboravi napravljene primerke (koristi se u testovima)."""
    global _rules, _audit, _gate
    _rules = None
    _audit = None
    _gate = None
```

- [x] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_security_runtime.py -q`
Expected: PASS (2 testa)

- [x] **Step 5: Commit**

```bash
git add apps/api/codium_security_runtime.py tests/test_codium_security_runtime.py
git commit -m "feat(api): runtime za ScopeGate i dnevnik CODIUM-a"
```

---

### Task 6: `/ask` pita gate pre online poziva i ostavlja trag

**Files:**
- Modify: `apps/api/routers/codium_ai.py` (ruta `ask_assistant`, plus dve nove `Depends` funkcije)
- Modify: `apps/api/schemas/codium_ai.py` (`AssistantAskRequest` dobija `actor`)
- Test: `tests/test_api_codium_ai.py` (dopuna postojećeg fajla)

**Interfaces:**
- Consumes: `CodiumAssistant.resolve` (Task 4), `ScopeGate.check` (Task 1), `AuditRepository.record` + `AuditEntry` (Task 3), `codium_security_runtime.get_scope_gate` / `get_audit` (Task 5), postojeći `get_providers()` koji vraća listu provajdera sa poljima `name` i `is_local`.
- Produces: ništa što kasniji zadaci koriste (ovo je poslednji zadatak reza).

- [x] **Step 1: Write the failing test**

Dopisati na kraj `tests/test_api_codium_ai.py`:

```python
# ========== DOZVOLE: online poziv prolazi kroz gate ==========

def test_odbijen_online_poziv_ne_zove_model_i_ostavlja_trag(tmp_path):
    """Pravilo domena zaustavlja placeni poziv pre nego sto se desi."""
    from apps.api.routers import codium_ai
    from core.domains.codium.audit import AuditRepository
    from core.domains.codium.runtime import initialize_codium_ops_database
    from core.security.scope_gate import DENY, ScopeGate, ScopeRule

    ops = tmp_path / "codium_ops.db"
    initialize_codium_ops_database(ops)
    dnevnik = AuditRepository(ops)

    gate = ScopeGate(lambda: [
        ScopeRule(actor="agent:builder", action="ai.call_online", target="*",
                  verdict=DENY, note="bez trosenja", id=1),
    ])

    class Resolved:
        provider_name = "anthropic"
        model = "claude-sonnet-5"
        source = "override"

    class Servis:
        def resolve(self, **_):
            return Resolved()

        def ask(self, **_):                       # pragma: no cover
            raise AssertionError("odbijen poziv ne sme da stigne do modela")

    class Provajder:
        name = "anthropic"
        is_local = False

    app.dependency_overrides[codium_ai.get_service] = lambda: Servis()
    app.dependency_overrides[codium_ai.get_providers] = lambda: [Provajder()]
    app.dependency_overrides[codium_ai.get_scope_gate] = lambda: gate
    app.dependency_overrides[codium_ai.get_audit] = lambda: dnevnik
    try:
        with TestClient(app) as tc:
            resp = tc.post("/api/v1/codium/ai/ask", json={
                "project_id": None, "persona": "global",
                "message": "zdravo", "history": [],
                "model": "claude-sonnet-5", "provider": "anthropic",
                "actor": "agent:builder",
            })
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_fallback"] is True
    assert "bez trosenja" in data["reply"]

    unosi = dnevnik.query()
    assert len(unosi) == 1
    assert unosi[0].verdict == "deny"
    assert unosi[0].outcome == "blocked"
    assert unosi[0].target == "claude-sonnet-5"


def test_lokalni_model_ne_prolazi_kroz_gate(tmp_path):
    """Lokalni poziv nista ne kosta i ne izlazi iz masine — gate ga ne dira."""
    from apps.api.routers import codium_ai
    from core.domains.codium.audit import AuditRepository
    from core.domains.codium.runtime import initialize_codium_ops_database
    from core.security.scope_gate import DENY, ScopeGate, ScopeRule

    ops = tmp_path / "codium_ops.db"
    initialize_codium_ops_database(ops)
    dnevnik = AuditRepository(ops)

    # Pravilo koje bi odbilo SVE — lokalni poziv ipak prolazi.
    gate = ScopeGate(lambda: [
        ScopeRule(actor="*", action="*", target="*", verdict=DENY, id=1),
    ])

    class Resolved:
        provider_name = "ollama"
        model = "qwen2.5"
        source = "registry"

    class Odgovor:
        reply = "zdravo"
        sources: list[str] = []
        persona = "global"
        model = "qwen2.5"
        provider = "ollama"
        source = "registry"
        is_fallback = False
        prompt_tokens = 1
        output_tokens = 1
        duration_ms = 5
        cost_usd = 0.0

    class Servis:
        def resolve(self, **_):
            return Resolved()

        def ask(self, **_):
            return Odgovor()

    class Provajder:
        name = "ollama"
        is_local = True

    app.dependency_overrides[codium_ai.get_service] = lambda: Servis()
    app.dependency_overrides[codium_ai.get_providers] = lambda: [Provajder()]
    app.dependency_overrides[codium_ai.get_scope_gate] = lambda: gate
    app.dependency_overrides[codium_ai.get_audit] = lambda: dnevnik
    try:
        with TestClient(app) as tc:
            resp = tc.post("/api/v1/codium/ai/ask", json={
                "project_id": None, "persona": "global",
                "message": "zdravo", "history": [],
                "actor": "agent:builder",
            })
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["is_fallback"] is False
    assert dnevnik.query() == []


def test_covek_prolazi_i_dozvoljen_poziv_ostavlja_trag(tmp_path):
    from apps.api.routers import codium_ai
    from core.domains.codium.audit import AuditRepository
    from core.domains.codium.runtime import initialize_codium_ops_database
    from core.security.scope_gate import DENY, ScopeGate, ScopeRule

    ops = tmp_path / "codium_ops.db"
    initialize_codium_ops_database(ops)
    dnevnik = AuditRepository(ops)

    gate = ScopeGate(lambda: [
        ScopeRule(actor="*", action="ai.call_online", target="*",
                  verdict=DENY, id=1),
    ])

    class Resolved:
        provider_name = "anthropic"
        model = "claude-sonnet-5"
        source = "override"

    class Odgovor:
        reply = "odgovor"
        sources: list[str] = []
        persona = "global"
        model = "claude-sonnet-5"
        provider = "anthropic"
        source = "override"
        is_fallback = False
        prompt_tokens = 10
        output_tokens = 20
        duration_ms = 900
        cost_usd = 0.001

    class Servis:
        def resolve(self, **_):
            return Resolved()

        def ask(self, **_):
            return Odgovor()

    class Provajder:
        name = "anthropic"
        is_local = False

    app.dependency_overrides[codium_ai.get_service] = lambda: Servis()
    app.dependency_overrides[codium_ai.get_providers] = lambda: [Provajder()]
    app.dependency_overrides[codium_ai.get_scope_gate] = lambda: gate
    app.dependency_overrides[codium_ai.get_audit] = lambda: dnevnik
    try:
        with TestClient(app) as tc:
            # Bez `actor` polja — podrazumevano je covek.
            resp = tc.post("/api/v1/codium/ai/ask", json={
                "project_id": None, "persona": "global",
                "message": "zdravo", "history": [],
            })
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["is_fallback"] is False

    unosi = dnevnik.query()
    assert len(unosi) == 1
    assert unosi[0].verdict == "allow"
    assert unosi[0].outcome == "ok"
```

**Napomena za izvršioca:** `app`, `TestClient` i uvozi na vrhu `tests/test_api_codium_ai.py` već postoje — ne dupliraj ih. Ako se u tom fajlu `app.dependency_overrides` čisti drugačije (npr. `pop` po ključu), prati zatečeni obrazac umesto `clear()`.

- [x] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_api_codium_ai.py -q`
Expected: FAIL — `AttributeError: module 'apps.api.routers.codium_ai' has no attribute 'get_scope_gate'`

- [x] **Step 3: Write minimal implementation**

U `apps/api/schemas/codium_ai.py`, u klasu `AssistantAskRequest` dodati polje:

```python
    # Ko trazi odgovor. Podrazumevano covek — on ne prolazi kroz gate.
    # Agenti i automatizacije se predstavljaju kao `agent:<slug>` /
    # `automation:<id>` i za njih vaze pravila dozvola.
    actor: str = "human"
```

U `apps/api/routers/codium_ai.py`, uz postojeće uvoze:

```python
from apps.api import codium_security_runtime
from core.domains.codium.audit import AuditEntry, AuditRepository
from core.security.scope_gate import ALLOW, ScopeGate
```

Uz postojeće `Depends` funkcije:

```python
def get_scope_gate() -> ScopeGate:
    return codium_security_runtime.get_scope_gate()


def get_audit() -> AuditRepository:
    return codium_security_runtime.get_audit()
```

Zameniti telo rute `ask_assistant` ovim (postojeći deo sa `usage.record` i `return` ostaje na kraju, netaknut):

```python
@router.post("/ask", response_model=AssistantAnswerResponse)
def ask_assistant(
    payload: AssistantAskRequest,
    service: CodiumAssistant = Depends(get_service),
    usage: UsageRecorder = Depends(get_usage_recorder),
    providers: list = Depends(get_providers),
    gate: ScopeGate = Depends(get_scope_gate),
    audit: AuditRepository = Depends(get_audit),
) -> AssistantAnswerResponse:
    """Odgovor asistenta na srpskom, po izabranoj personi i kontekstu projekta.

    Ako lokalni model (Ollama) nije dostupan, vraća se fallback (is_fallback=true).

    Poziv online modela prolazi kroz `ScopeGate`: pravilo domena sme da ga
    zaustavi pre nego što se potroši novac. Provera i upis u dnevnik su posao
    rute, ne domenskog servisa — isto kao evidencija potrošnje ispod.
    """

    # Prazan string iz zahteva (npr. provider="") ne sme da stigne do rutera —
    # override_provider="" probija podrazumevani izbor umesto da ga ignoriše.
    model = payload.model.strip() if payload.model and payload.model.strip() else None
    provider = payload.provider.strip() if payload.provider and payload.provider.strip() else None

    # Koji bi model bio pozvan — pre nego što se pozove.
    resolved = service.resolve(
        project_id=payload.project_id,
        persona_id=payload.persona,
        model=model,
        provider=provider,
    )
    lokalni = {p.name: p.is_local for p in providers}
    # Nepoznat provajder se tretira kao online: pretpostavka na stranu opreza.
    je_online = not lokalni.get(resolved.provider_name, False)

    if je_online:
        odluka = gate.check(actor=payload.actor, action="ai.call_online",
                            target=resolved.model)
        if odluka.verdict != ALLOW:
            audit.record(AuditEntry(
                actor=payload.actor, action="ai.call_online",
                target=resolved.model, verdict=odluka.verdict,
                outcome="blocked", detail=odluka.reason,
                project_id=payload.project_id,
            ))
            # Odbijanje je uredan odgovor u chatu, ne HTTP greška: korisnik
            # treba da pročita razlog na mestu gde je i pitao.
            return AssistantAnswerResponse(
                reply=f"Pravilo domena ne dozvoljava online model "
                      f"{resolved.model}: {odluka.reason}",
                persona=payload.persona,
                model=resolved.model,
                provider=resolved.provider_name,
                source=resolved.source,
                is_fallback=True,
                sources=[],
                prompt_tokens=0,
                output_tokens=0,
                duration_ms=0,
                cost_usd=0.0,
            )
        audit.record(AuditEntry(
            actor=payload.actor, action="ai.call_online",
            target=resolved.model, verdict=odluka.verdict, outcome="ok",
            detail=odluka.reason, project_id=payload.project_id,
        ))

    result = service.ask(
        project_id=payload.project_id,
        persona_id=payload.persona,
        message=payload.message,
        history=[ChatTurn(author=t.author, text=t.text) for t in payload.history],
        # Odluka je već doneta gore — prosleđuje se, da se ne resolvuje dvaput.
        model=resolved.model,
        provider=resolved.provider_name,
    )
```

**Napomena za izvršioca:** odbijen odgovor se pravi direktno, ne kroz `from_domain` — nema domenskog `AssistantAnswer` objekta jer poziv nikad nije ni krenuo. Polja `AssistantAnswerResponse` su tačno ona navedena gore, uključujući obavezno `sources`.

- [x] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_api_codium_ai.py -q`
Expected: PASS (postojeći + 3 nova)

- [x] **Step 5: Run the whole suite**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, bez ijedne regresije (polazna vrednost: 1272 testa)

- [x] **Step 6: Commit**

```bash
git add apps/api/routers/codium_ai.py apps/api/schemas/codium_ai.py tests/test_api_codium_ai.py
git commit -m "feat(codium): online poziv modela prolazi kroz ScopeGate i ostavlja trag"
```

---

## Definicija završetka reza

- `scope_gate.check(...)` može da pozove bilo koji servis; odluka ne dodiruje bazu.
- Odbijen online poziv ne stiže do modela, vraća uredan odgovor u chat i ostavlja trag.
- Dozvoljen online poziv ostavlja trag.
- Lokalni poziv ne prolazi kroz gate i ne puni dnevnik.
- Dnevnik nema način da se izmeni ili obriše iz aplikacije.
- Ceo pytest zelen.

## Šta svesno NIJE u ovom rezu

- Red za odobrenje (`needs_approval` → `codium_approvals`) i rute odobravanja.
- Rute `/api/v1/codium/audit/*` (dnevnik, pravila) — dolaze uz GUI.
- Strane `CodiumAccess` i `CodiumAudit`.
- Ožičavanje ostalih akcija (`file.write`, `repo.push`, `pipeline.run`, `deploy.execute`) — svaka ide uz svoju E fazu.
