---
id: codium-71a0bfe7-2026-08-28-codium-e1-red-odobrenja-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: CODIUM E1 drugi rez — red odobrenja
summary: '> **Za agentne izvođače:** OBAVEZNA POD-VEŠTINA: koristi'
keywords:
- codium
- drugi
- rez
- red
- odobrenja
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-28-codium-e1-red-odobrenja.md
edges:
- type: references
  target: core-7687f8e1-2026-08-28-codium-odobrenja-i-agenti-design-md
  weight: 0.3
---

# CODIUM E1 drugi rez — red odobrenja

> **Za agentne izvođače:** OBAVEZNA POD-VEŠTINA: koristi
> superpowers:subagent-driven-development (preporučeno) ili
> superpowers:executing-plans za izvođenje zadatak po zadatak. Koraci koriste
> `- [ ]` sintaksu za praćenje.

**Cilj:** Kada `ScopeGate` kaže `needs_approval`, molba se upisuje u red, vidi u
GUI-ju i odlučuje — a odluka ostavlja trag u dnevniku.

**Arhitektura:** `ScopeGate` ostaje bez baze i dalje samo vraća verdikt; upis
molbe je posao pozivaoca kroz zaseban `ApprovalRepository`. Tabela
`codium_approvals` je generična (akter, akcija, cilj, payload, status) i ne zna
za agente — vezu prema tražiocu drži tražilac. GUI dobija dve pune strane koje
E1 duguje po svojoj definiciji završetka: `CodiumAccess` (pravila + red čekanja)
i `CodiumAudit` (dnevnik).

**Tehnologije:** Python 3.14, FastAPI, SQLite kroz `core.database`, pytest;
React + TypeScript + Vite, vitest, lucide-react.

**Spec:** [`docs/superpowers/specs/2026-08-28-codium-odobrenja-i-agenti-design.md`](../specs/2026-08-28-codium-odobrenja-i-agenti-design.md)

## Opšta ograničenja

- Migracija je **`codium v7`** (v6 je zauzet pravilima dozvola). Migracije su
  aditivne — nijedna postojeća tabela se ne dira.
- `codium_approvals` ide u **`codium.db`** (poslovni podatak, ide u bekap), ne u
  `codium_ops.db`.
- `ScopeGate` (`core/security/scope_gate.py`) se u ovom planu **ne menja**. Ako
  se čini da mora, stani i pitaj — to znači da je granica pogrešno shvaćena.
- `AuditRepository` i dalje nema `update` ni `delete`. Ne dodaju se.
- Kod i identifikatori na engleskom, komentari i dokumentacija na srpskom, kao u
  postojećim fajlovima domena.
- Testovi se pokreću kroz `./.venv/Scripts/python.exe -m pytest`, ne kroz
  sistemski `python`.
- Provera tipova GUI-ja je `npx tsc -b tsconfig.app.json` u `apps/gui`
  (`--noEmit` nad korenim `tsconfig.json` ne proverava ništa). Dve greške već
  postoje pre ovog rada i nisu tvoje: `CoreDockLayout.tsx(42,52)` i
  `CodiumWorkspace.tsx(14,3)`.
- Poruke commit-a idu kroz `git commit -F- <<'EOF'`, nikad kroz `-m` sa
  navodnicima — bash izvršava sve unutar kosih navodnika.

## Struktura fajlova

| Fajl | Odgovornost |
|---|---|
| `core/domains/codium/migrations.py` | dodaje `CODIUM_MIGRATION_V7` |
| `core/domains/codium/audit/models.py` | dodaje `Approval` dataclass |
| `core/domains/codium/audit/approvals.py` | **nov** — `ApprovalRepository` |
| `core/domains/codium/audit/__init__.py` | izvozi nove simbole |
| `apps/api/codium_security_runtime.py` | dodaje `get_approvals()` |
| `apps/api/schemas/codium_audit.py` | šeme molbi |
| `apps/api/routers/codium_audit.py` | tri nove rute |
| `apps/gui/src/types/codium.ts` | tipovi molbi |
| `apps/gui/src/services/codiumApi.ts` | tri poziva |
| `apps/gui/src/features/codium/approvals.ts` | **nov** — čitanje payload-a za prikaz |
| `apps/gui/src/pages/CodiumAccess.tsx` | **nov** — pravila + red čekanja |
| `apps/gui/src/pages/CodiumAudit.tsx` | **nov** — dnevnik sa filterima |
| `apps/gui/src/styles/codium-access.css` | **nov** — stil obe strane |
| `apps/gui/src/App.tsx` | dve rute |
| `apps/gui/src/components/layout/Sidebar.tsx` | dve stavke iz `soon` u `route` |

---

### Zadatak 1: Migracija v7 — tabela odobrenja

**Fajlovi:**
- Menja: `core/domains/codium/migrations.py` (kraj fajla, uz `CODIUM_MIGRATION_V6`)
- Test: `tests/test_codium_audit_schema.py`

**Interfejsi:**
- Koristi: `DatabaseMigration` iz `core.database`, `initialize_codium_database`
  iz `core.domains.codium.runtime`
- Daje: tabelu `codium_approvals` sa kolonama `id, actor, action, target,
  payload, status, note, requested_at, decided_at`

- [ ] **Korak 1: Napiši testove koji padaju**

Dodaj na kraj `tests/test_codium_audit_schema.py`:

```python
def test_odobrenja_imaju_svoje_kolone(tmp_path):
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    assert _columns(baza, "codium_approvals") == {
        "id", "actor", "action", "target", "payload", "status", "note",
        "requested_at", "decided_at",
    }


def test_status_odobrenja_je_ogranicen(tmp_path):
    # Nepoznat status bi inace tiho prosao, a GUI bi crtao stanje koje
    # ni jedan servis ne poznaje.
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    with core_database_connection(baza) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO codium_approvals (actor, action, status) "
                "VALUES ('agent:x', 'file.write', 'mozda')"
            )


def test_pravila_iz_v6_ostaju_netaknuta(tmp_path):
    # Migracija je aditivna: v6 tabela mora i dalje da postoji.
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    assert "verdict" in _columns(baza, "codium_scope_rules")
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_audit_schema.py -v`
Očekivano: `test_odobrenja_imaju_svoje_kolone` pada sa `sqlite3.OperationalError:
no such table: codium_approvals`.

- [ ] **Korak 3: Dodaj migraciju**

U `core/domains/codium/migrations.py`, ispod definicije `CODIUM_MIGRATION_V6`:

```python
# ---------- v7: red odobrenja ----------

CODIUM_MIGRATION_V7 = DatabaseMigration(
    scope="codium",
    version=7,
    name="create_approvals",
    statements=(
        # Tabela je namerno genericna: nosi aktera, akciju i payload, a ne zna
        # ko trazi. Vezu drzi trazilac (agent, automatizacija), pa nova vrsta
        # trazioca ne trazi novu kolonu.
        #
        # Status `expired` stoji u skupu ali ga prvi rez ne postavlja — nema
        # roka trajanja molbe. Skup je tu da kasniji posao odrzavanja ne trazi
        # izmenu seme.
        """
        CREATE TABLE codium_approvals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            actor        TEXT NOT NULL,
            action       TEXT NOT NULL,
            target       TEXT NOT NULL DEFAULT '',
            payload      TEXT NOT NULL DEFAULT '',
            status       TEXT NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','approved',
                                           'rejected','expired')),
            note         TEXT NOT NULL DEFAULT '',
            requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            decided_at   TEXT
        )
        """,
        "CREATE INDEX idx_codium_approvals_status "
        "ON codium_approvals (status, requested_at)",
    ),
)
```

I dopiši u listu na kraju fajla:

```python
CODIUM_MIGRATIONS = (
    CODIUM_MIGRATION_V1,
    CODIUM_MIGRATION_V2,
    CODIUM_MIGRATION_V3,
    CODIUM_MIGRATION_V4,
    CODIUM_MIGRATION_V5,
    CODIUM_MIGRATION_V6,
    CODIUM_MIGRATION_V7,
)
```

- [ ] **Korak 4: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_audit_schema.py -v`
Očekivano: svi testovi prolaze.

- [ ] **Korak 5: Commit**

```bash
git add core/domains/codium/migrations.py tests/test_codium_audit_schema.py
git commit -F- <<'EOF'
feat(codium): codium v7 red odobrenja

Tabela je genericna i ne zna ko trazi odobrenje — vezu drzi trazilac.
Tako ista tabela sluzi i agentima i kasnijim automatizacijama.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 2: Model i repozitorijum molbi

**Fajlovi:**
- Menja: `core/domains/codium/audit/models.py`
- Pravi: `core/domains/codium/audit/approvals.py`
- Menja: `core/domains/codium/audit/__init__.py`
- Test: `tests/test_codium_approvals.py` (nov)

**Interfejsi:**
- Koristi: `core_database_connection`, `codium_database_path` (iz
  `core.domains.codium.runtime`), obrazac iz `ScopeRuleRepository`
- Daje:
  - `Approval(actor, action, target="", payload="", status="pending", note="",
    requested_at="", decided_at=None, id=None)` — frozen dataclass
  - `ApprovalRepository(database_path: Path | None = None)` sa
    `request(approval: Approval) -> Approval`,
    `pending() -> list[Approval]`,
    `get(approval_id: int) -> Approval | None`,
    `decide(approval_id: int, status: str, note: str = "") -> Approval | None`

- [ ] **Korak 1: Napiši testove koji padaju**

Nov fajl `tests/test_codium_approvals.py`:

```python
# ========== TESTOVI: red odobrenja ==========
from __future__ import annotations

import pytest

from core.domains.codium.audit import Approval, ApprovalRepository
from core.domains.codium.runtime import initialize_codium_database


@pytest.fixture
def repo(tmp_path) -> ApprovalRepository:
    baza = tmp_path / "codium.db"
    initialize_codium_database(baza)
    return ApprovalRepository(baza)


def test_molba_se_upisuje_kao_pending(repo):
    upisano = repo.request(Approval(
        actor="agent:architect", action="file.write", target="src/api.py",
        payload='{"tool": "write_file"}',
    ))
    assert upisano.id is not None
    assert upisano.status == "pending"
    assert [m.id for m in repo.pending()] == [upisano.id]


def test_odobrena_molba_izlazi_iz_reda(repo):
    molba = repo.request(Approval(actor="agent:x", action="file.write"))
    odluceno = repo.decide(molba.id, "approved")
    assert odluceno.status == "approved"
    assert odluceno.decided_at
    assert repo.pending() == []


def test_vec_odlucena_molba_se_ne_menja_ponovo(repo):
    # Bez ovoga bi odbijen potez mogao naknadno da postane odobren.
    molba = repo.request(Approval(actor="agent:x", action="file.write"))
    repo.decide(molba.id, "rejected", note="ne sada")
    assert repo.decide(molba.id, "approved") is None
    assert repo.get(molba.id).status == "rejected"


def test_odluka_o_nepostojecoj_molbi_vraca_nista(repo):
    assert repo.decide(999, "approved") is None


def test_payload_se_vraca_neizmenjen(repo):
    # Payload nosi pun poziv alata i hash sadrzaja; repozitorijum ga ne tumaci.
    tekst = '{"tool": "write_file", "args": {"rel": "a.py"}, "content_hash": "ab12"}'
    molba = repo.request(Approval(actor="agent:x", action="file.write",
                                  payload=tekst))
    assert repo.get(molba.id).payload == tekst
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_approvals.py -v`
Očekivano: `ImportError: cannot import name 'Approval'`.

- [ ] **Korak 3: Dodaj model**

Na kraj `core/domains/codium/audit/models.py`:

```python
@dataclass(frozen=True)
class Approval:
    """Molba koja ceka ljudsku odluku.

    Namerno ne zna ko je trazi: nosi aktera i pun poziv u `payload`, a vezu
    prema tekucem poslu drzi taj posao. Tako ista tabela sluzi agentima i
    kasnijim automatizacijama.
    """

    actor: str
    action: str
    target: str = ""
    payload: str = ""
    status: str = "pending"
    note: str = ""
    requested_at: str = ""
    decided_at: str | None = None
    id: int | None = None
```

- [ ] **Korak 4: Napiši repozitorijum**

Nov fajl `core/domains/codium/audit/approvals.py`:

```python
# ========== RED ODOBRENJA ==========
# Kapija samo kaze `needs_approval`. Upis molbe je posao pozivaoca, pa je
# ovde — `ScopeGate` i dalje ne dodiruje bazu.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.audit.models import Approval
from core.domains.codium.runtime import codium_database_path

_KOLONE = ("id, actor, action, target, payload, status, note, "
           "requested_at, decided_at")


def _to_approval(row) -> Approval:
    return Approval(id=row[0], actor=row[1], action=row[2], target=row[3],
                    payload=row[4], status=row[5], note=row[6],
                    requested_at=row[7], decided_at=row[8])


class ApprovalRepository:
    """Citanje i odlucivanje o molbama za odobrenje."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def request(self, approval: Approval) -> Approval:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO codium_approvals (actor, action, target, payload) "
                "VALUES (?, ?, ?, ?)",
                (approval.actor, approval.action, approval.target,
                 approval.payload),
            )
            novi_id = cursor.lastrowid
        return self.get(novi_id)

    def pending(self) -> list[Approval]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                f"SELECT {_KOLONE} FROM codium_approvals "
                "WHERE status = 'pending' ORDER BY id DESC"
            ).fetchall()
        return [_to_approval(row) for row in rows]

    def get(self, approval_id: int) -> Approval | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_KOLONE} FROM codium_approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
        return _to_approval(row) if row else None

    def decide(self, approval_id: int, status: str,
               note: str = "") -> Approval | None:
        """Odlucuje o molbi koja jos ceka.

        Uslov `status = 'pending'` je u upitu namerno: vec odlucena molba se ne
        odlucuje ponovo, inace bi odbijen potez mogao naknadno da postane
        odobren. Vraca `None` kada nista nije promenjeno.
        """

        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "UPDATE codium_approvals "
                "SET status = ?, note = ?, decided_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND status = 'pending'",
                (status, note, approval_id),
            )
            promenjeno = cursor.rowcount
        return self.get(approval_id) if promenjeno else None
```

- [ ] **Korak 5: Izvezi nove simbole**

U `core/domains/codium/audit/__init__.py` dodaj uvoze i imena:

```python
from core.domains.codium.audit.approvals import ApprovalRepository
from core.domains.codium.audit.feed import ActivityFeed, ActivityItem
from core.domains.codium.audit.models import Approval, AuditEntry
from core.domains.codium.audit.repository import AuditRepository, ScopeRuleRepository

__all__ = [
    "ActivityFeed",
    "ActivityItem",
    "Approval",
    "ApprovalRepository",
    "AuditEntry",
    "AuditRepository",
    "ScopeRuleRepository",
]
```

- [ ] **Korak 6: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_codium_approvals.py -v`
Očekivano: svih pet prolazi.

- [ ] **Korak 7: Commit**

```bash
git add core/domains/codium/audit tests/test_codium_approvals.py
git commit -F- <<'EOF'
feat(codium): repozitorijum molbi za odobrenje

Uslov `status = 'pending'` stoji u samom UPDATE upitu: vec odlucena molba
se ne odlucuje ponovo, inace bi odbijen potez mogao naknadno da postane
odobren.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 3: Runtime i rute

**Fajlovi:**
- Menja: `apps/api/codium_security_runtime.py`
- Menja: `apps/api/schemas/codium_audit.py`
- Menja: `apps/api/routers/codium_audit.py`
- Test: `tests/test_api_codium_audit.py`

**Interfejsi:**
- Koristi: `ApprovalRepository`, `Approval` iz Zadatka 2; `AuditRepository` i
  `AuditEntry` koji već postoje
- Daje:
  - `codium_security_runtime.get_approvals() -> ApprovalRepository`
  - `apps.api.routers.codium_audit.get_approvals` (zavisnost koju testovi
    prepisuju kroz `app.dependency_overrides`)
  - rute `GET /api/v1/codium/audit/approvals`,
    `POST /api/v1/codium/audit/approvals/{id}/approve`,
    `POST /api/v1/codium/audit/approvals/{id}/reject`
  - šeme `ApprovalResponse`, `ApprovalsResponse`, `ApprovalDecisionRequest`

- [ ] **Korak 1: Napiši testove koji padaju**

Prvo proširi fixture `client` u `tests/test_api_codium_audit.py` — dodaj uvoz
`get_approvals` u postojeći blok uvoza iz `apps.api.routers.codium_audit`, uvoz
`Approval, ApprovalRepository` u blok iz `core.domains.codium.audit`, i unutar
fixture-a:

```python
    odobrenja = ApprovalRepository(poslovna)
    app.dependency_overrides[get_approvals] = lambda: odobrenja
```

Zatim dodaj na kraj fajla:

```python
# ---------- odobrenja ----------
def test_prazan_red_odobrenja(client):
    resp = client.get("/api/v1/codium/audit/approvals")
    assert resp.status_code == 200
    assert resp.json()["approvals"] == []


def test_molba_se_vidi_u_redu(client, tmp_path):
    ApprovalRepository(tmp_path / "codium.db").request(Approval(
        actor="agent:architect", action="file.write", target="src/api.py",
    ))
    data = client.get("/api/v1/codium/audit/approvals").json()
    assert data["count"] == 1
    assert data["approvals"][0]["target"] == "src/api.py"


def test_odobrenje_menja_status_i_ostavlja_trag(client, tmp_path):
    molba = ApprovalRepository(tmp_path / "codium.db").request(Approval(
        actor="agent:architect", action="file.write", target="src/api.py",
    ))
    resp = client.post(f"/api/v1/codium/audit/approvals/{molba.id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert client.get("/api/v1/codium/audit/approvals").json()["count"] == 0

    # Odobrenje je akcija kao i svaka druga i mora ostaviti trag.
    dnevnik = client.get("/api/v1/codium/audit/log",
                         params={"action": "approval.decide"}).json()
    assert dnevnik["count"] == 1
    assert dnevnik["entries"][0]["actor"] == "human"
    assert dnevnik["entries"][0]["target"] == f"approval:{molba.id}"


def test_odbijanje_pamti_razlog(client, tmp_path):
    molba = ApprovalRepository(tmp_path / "codium.db").request(Approval(
        actor="agent:x", action="file.write",
    ))
    resp = client.post(f"/api/v1/codium/audit/approvals/{molba.id}/reject",
                       json={"note": "ne dira produkciju"})
    assert resp.json()["note"] == "ne dira produkciju"
    assert resp.json()["status"] == "rejected"


def test_odluka_o_vec_odlucenoj_molbi_je_409(client, tmp_path):
    molba = ApprovalRepository(tmp_path / "codium.db").request(Approval(
        actor="agent:x", action="file.write",
    ))
    client.post(f"/api/v1/codium/audit/approvals/{molba.id}/approve")
    ponovo = client.post(f"/api/v1/codium/audit/approvals/{molba.id}/reject")
    assert ponovo.status_code == 409
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_api_codium_audit.py -v`
Očekivano: `ImportError: cannot import name 'get_approvals'`.

- [ ] **Korak 3: Dodaj runtime primerak**

U `apps/api/codium_security_runtime.py`: dopuni uvoz iz
`core.domains.codium.audit` sa `ApprovalRepository`, dodaj `_approvals` u
globalne promenljive, funkciju i red u `reset()`:

```python
def get_approvals() -> ApprovalRepository:
    global _approvals
    if _approvals is None:
        # Molbe su poslovni podatak — poslovna baza, ne ops.
        _approvals = ApprovalRepository(_database_path())
    return _approvals
```

U `reset()` dodaj `_approvals` u `global` red i `_approvals = None`.

- [ ] **Korak 4: Dodaj šeme**

Na kraj `apps/api/schemas/codium_audit.py`:

```python
# ==========          ODOBRENJA          ==========

class ApprovalResponse(BaseModel):
    id: int | None
    actor: str
    action: str
    target: str
    payload: str
    status: str
    note: str
    requested_at: str
    decided_at: str | None

    @classmethod
    def from_domain(cls, approval: Approval) -> "ApprovalResponse":
        return cls(
            id=approval.id, actor=approval.actor, action=approval.action,
            target=approval.target, payload=approval.payload,
            status=approval.status, note=approval.note,
            requested_at=approval.requested_at, decided_at=approval.decided_at,
        )


class ApprovalsResponse(BaseModel):
    count: int
    approvals: list[ApprovalResponse]


class ApprovalDecisionRequest(BaseModel):
    note: str = ""
```

Dopuni uvoz na vrhu fajla: `from core.domains.codium.audit import ActivityItem,
Approval, AuditEntry`.

- [ ] **Korak 5: Dodaj rute**

Na kraj `apps/api/routers/codium_audit.py`, uz dopunjene uvoze
(`ApprovalRepository` iz `core.domains.codium.audit`, `AuditEntry` iz istog
paketa, `HTTPException` iz `fastapi`, i nove šeme):

```python
def get_approvals() -> ApprovalRepository:
    return codium_security_runtime.get_approvals()


# ==========          ODOBRENJA          ==========

@router.get("/approvals", response_model=ApprovalsResponse)
def list_approvals(
    approvals: ApprovalRepository = Depends(get_approvals),
) -> ApprovalsResponse:
    """Molbe koje čekaju odluku, najnovija prva."""

    ceka = approvals.pending()
    return ApprovalsResponse(
        count=len(ceka),
        approvals=[ApprovalResponse.from_domain(a) for a in ceka],
    )


def _decide(approval_id: int, status: str, note: str,
            approvals: ApprovalRepository,
            audit: AuditRepository) -> ApprovalResponse:
    """Zajedničko telo za odobri i odbij — razlikuje ih samo status."""

    odluceno = approvals.decide(approval_id, status, note)
    if odluceno is None:
        # Molba ne postoji ili je vec odlucena. Oba su sukob sa stanjem, ne
        # greska poziva: klijent je gledao zastareo spisak.
        raise HTTPException(status_code=409,
                            detail="Molba ne čeka odluku.")

    audit.record(AuditEntry(
        actor="human", action="approval.decide",
        target=f"approval:{approval_id}", verdict="allow",
        outcome="ok", detail=f"{status}: {odluceno.action} {odluceno.target}",
    ))
    return ApprovalResponse.from_domain(odluceno)


@router.post("/approvals/{approval_id}/approve",
             response_model=ApprovalResponse)
def approve(
    approval_id: int,
    payload: ApprovalDecisionRequest | None = None,
    approvals: ApprovalRepository = Depends(get_approvals),
    audit: AuditRepository = Depends(get_audit),
) -> ApprovalResponse:
    """Odobrava tačno taj potez. Sledeći isti potez pita ponovo."""

    return _decide(approval_id, "approved",
                   payload.note if payload else "", approvals, audit)


@router.post("/approvals/{approval_id}/reject",
             response_model=ApprovalResponse)
def reject(
    approval_id: int,
    payload: ApprovalDecisionRequest | None = None,
    approvals: ApprovalRepository = Depends(get_approvals),
    audit: AuditRepository = Depends(get_audit),
) -> ApprovalResponse:
    """Odbija potez uz razlog koji ostaje zapisan."""

    return _decide(approval_id, "rejected",
                   payload.note if payload else "", approvals, audit)
```

- [ ] **Korak 6: Pokreni testove i potvrdi da prolaze**

Pokreni: `./.venv/Scripts/python.exe -m pytest tests/test_api_codium_audit.py tests/test_codium_security_runtime.py -v`
Očekivano: svi prolaze, uključujući postojeći
`test_dnevnik_nema_rutu_koja_menja_unos`.

- [ ] **Korak 7: Pokreni ceo paket**

Pokreni: `./.venv/Scripts/python.exe -m pytest -q`
Očekivano: nula padova. Prethodno stanje je 1317 testova.

- [ ] **Korak 8: Commit**

```bash
git add apps/api tests/test_api_codium_audit.py
git commit -F- <<'EOF'
feat(api): rute reda odobrenja uz trag u dnevniku

Odluka o molbi je akcija kao i svaka druga, pa upisuje unos u dnevnik.
Odluka o vec odlucenoj molbi vraca 409: klijent je gledao zastareo
spisak, sto je sukob sa stanjem a ne greska poziva.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 4: GUI — tipovi, pozivi i čitanje payload-a

**Fajlovi:**
- Menja: `apps/gui/src/types/codium.ts`
- Menja: `apps/gui/src/services/codiumApi.ts`
- Pravi: `apps/gui/src/features/codium/approvals.ts`
- Test: `apps/gui/src/features/codium/approvals.test.ts` (nov)

**Interfejsi:**
- Koristi: `getJson`, `postJson` iz `./httpClient`; obrazac postojeće
  `getActivity`
- Daje:
  - tipovi `Approval`, `ApprovalsResponse`, `ScopeRule`, `ScopeRulesResponse`,
    `AuditEntry`, `AuditLogResponse`
  - `getApprovals()`, `approveRequest(id, note?)`, `rejectRequest(id, note?)`,
    `getScopeRules()`, `addScopeRule(rule)`, `deleteScopeRule(id)`,
    `getAuditLog(params)`
  - `describePayload(payload: string): PayloadLine[]`

- [ ] **Korak 1: Napiši test koji pada**

Nov fajl `apps/gui/src/features/codium/approvals.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { describePayload } from "./approvals";

describe("prikaz payload-a molbe", () => {
  it("razlaze poziv alata u redove", () => {
    const linije = describePayload(
      '{"tool":"write_file","args":{"rel":"src/api.py"},"content_hash":"ab12"}',
    );
    expect(linije).toEqual([
      { label: "Alat", value: "write_file" },
      { label: "rel", value: "src/api.py" },
      { label: "Otisak sadržaja", value: "ab12" },
    ]);
  });

  it("prazan payload ne daje nijedan red", () => {
    expect(describePayload("")).toEqual([]);
  });

  it("neispravan JSON se prikazuje kao sirov tekst, ne ruši stranu", () => {
    // Payload dolazi iz baze; strana koja pukne na njemu sakrila bi
    // upravo ono sto covek treba da vidi pre odluke.
    expect(describePayload("nije json")).toEqual([
      { label: "Sadržaj", value: "nije json" },
    ]);
  });
});
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

Pokreni (u `apps/gui`): `npx vitest run src/features/codium/approvals.test.ts`
Očekivano: `Failed to resolve import "./approvals"`.

- [ ] **Korak 3: Napiši modul**

Nov fajl `apps/gui/src/features/codium/approvals.ts`:

```ts
// ==========          PRIKAZ MOLBE ZA ODOBRENJE          ==========
// Cist modul bez ijednog uvoza — prevod payload-a u redove koje covek cita
// pre nego sto klikne Odobri.

export type PayloadLine = { label: string; value: string };

/**
 * Razlaže payload molbe u redove za prikaz.
 *
 * Payload dolazi iz baze i ne mora biti ispravan JSON. Neispravan se pokazuje
 * kao sirov tekst: strana koja bi pukla sakrila bi upravo ono što treba
 * videti pre odluke.
 */
export function describePayload(payload: string): PayloadLine[] {
  const tekst = payload.trim();
  if (!tekst) {
    return [];
  }

  let podaci: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(tekst);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return [{ label: "Sadržaj", value: tekst }];
    }
    podaci = parsed as Record<string, unknown>;
  } catch {
    return [{ label: "Sadržaj", value: tekst }];
  }

  const linije: PayloadLine[] = [];
  if (typeof podaci.tool === "string") {
    linije.push({ label: "Alat", value: podaci.tool });
  }

  const args = podaci.args;
  if (typeof args === "object" && args !== null && !Array.isArray(args)) {
    for (const [ime, vrednost] of Object.entries(args)) {
      linije.push({ label: ime, value: String(vrednost) });
    }
  }

  if (typeof podaci.content_hash === "string") {
    linije.push({ label: "Otisak sadržaja", value: podaci.content_hash });
  }

  return linije.length > 0 ? linije : [{ label: "Sadržaj", value: tekst }];
}
```

- [ ] **Korak 4: Pokreni test i potvrdi da prolazi**

Pokreni (u `apps/gui`): `npx vitest run src/features/codium/approvals.test.ts`
Očekivano: 3 testa prolaze.

- [ ] **Korak 5: Dodaj tipove**

Na kraj `apps/gui/src/types/codium.ts`:

```ts
// ==========          DOZVOLE, MOLBE I DNEVNIK          ==========

export type ScopeVerdict = "allow" | "deny" | "needs_approval";

export type ScopeRule = {
  id: number | null;
  actor: string;
  action: string;
  target: string;
  verdict: ScopeVerdict;
  note: string;
};

export type ScopeRulesResponse = { count: number; rules: ScopeRule[] };

export type ScopeRuleRequest = {
  actor: string;
  action: string;
  target: string;
  verdict: ScopeVerdict;
  note: string;
};

export type Approval = {
  id: number | null;
  actor: string;
  action: string;
  target: string;
  payload: string;
  status: string;
  note: string;
  requested_at: string;
  decided_at: string | null;
};

export type ApprovalsResponse = { count: number; approvals: Approval[] };

export type AuditEntry = {
  id: number | null;
  at: string;
  actor: string;
  action: string;
  target: string;
  verdict: string;
  outcome: string;
  detail: string;
  project_id: number | null;
};

export type AuditLogResponse = { count: number; entries: AuditEntry[] };
```

- [ ] **Korak 6: Dodaj pozive**

Na kraj `apps/gui/src/services/codiumApi.ts` (i dopuni blok uvoza tipova sa
`Approval`, `ApprovalsResponse`, `AuditLogResponse`, `ScopeRule`,
`ScopeRuleRequest`, `ScopeRulesResponse`):

```ts
// ==========          DOZVOLE I ODOBRENJA          ==========

export function getScopeRules(): Promise<ScopeRulesResponse> {
  return getJson("/api/v1/codium/audit/rules");
}

export function addScopeRule(rule: ScopeRuleRequest): Promise<ScopeRule> {
  return postJson("/api/v1/codium/audit/rules", rule);
}

export function deleteScopeRule(ruleId: number): Promise<{ ok: boolean }> {
  return deleteRequest(`/api/v1/codium/audit/rules/${ruleId}`);
}

export function getApprovals(): Promise<ApprovalsResponse> {
  return getJson("/api/v1/codium/audit/approvals");
}

export function approveRequest(id: number, note = ""): Promise<Approval> {
  return postJson(`/api/v1/codium/audit/approvals/${id}/approve`, { note });
}

export function rejectRequest(id: number, note = ""): Promise<Approval> {
  return postJson(`/api/v1/codium/audit/approvals/${id}/reject`, { note });
}

// ==========          DNEVNIK          ==========

export function getAuditLog(
  params: { actor?: string; action?: string; limit?: number; offset?: number } = {},
): Promise<AuditLogResponse> {
  const upit = new URLSearchParams();
  if (params.actor) upit.set("actor", params.actor);
  if (params.action) upit.set("action", params.action);
  upit.set("limit", String(params.limit ?? 50));
  upit.set("offset", String(params.offset ?? 0));
  return getJson(`/api/v1/codium/audit/log?${upit.toString()}`);
}
```

- [ ] **Korak 7: Provera tipova**

Pokreni (u `apps/gui`): `npx tsc -b tsconfig.app.json`
Očekivano: samo dve zatečene greške (`CoreDockLayout.tsx(42,52)`,
`CodiumWorkspace.tsx(14,3)`), nijedna nova.

- [ ] **Korak 8: Commit**

```bash
git add apps/gui/src/types apps/gui/src/services apps/gui/src/features/codium
git commit -F- <<'EOF'
feat(gui): tipovi i pozivi za dozvole, odobrenja i dnevnik

Neispravan payload se prikazuje kao sirov tekst umesto da rusi stranu:
covek pre odluke mora da vidi upravo taj sadrzaj.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 5: Strana „Access & Users"

**Fajlovi:**
- Pravi: `apps/gui/src/pages/CodiumAccess.tsx`
- Pravi: `apps/gui/src/styles/codium-access.css`
- Test: `apps/gui/src/pages/CodiumAccess.test.tsx` (nov)

**Interfejsi:**
- Koristi: `getScopeRules`, `addScopeRule`, `deleteScopeRule`, `getApprovals`,
  `approveRequest`, `rejectRequest` iz Zadatka 4; `describePayload` iz Zadatka 4
- Daje: podrazumevani izvoz `CodiumAccess` (React komponenta bez props-a)

Pogledaj `apps/gui/src/pages/CodiumSettingsPage.tsx` za obrazac strane domena
(zaglavlje, učitavanje, stanje greške) i prati ga.

- [ ] **Korak 1: Napiši test koji pada**

Nov fajl `apps/gui/src/pages/CodiumAccess.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CodiumAccess from "./CodiumAccess";
import * as api from "../services/codiumApi";

vi.mock("../services/codiumApi");

const MOLBA = {
  id: 7, actor: "agent:architect", action: "file.write", target: "src/api.py",
  payload: '{"tool":"write_file","args":{"rel":"src/api.py"}}',
  status: "pending", note: "", requested_at: "2026-08-29 10:00:00",
  decided_at: null,
};

beforeEach(() => {
  vi.mocked(api.getScopeRules).mockResolvedValue({ count: 0, rules: [] });
  vi.mocked(api.getApprovals).mockResolvedValue({
    count: 1, approvals: [MOLBA],
  });
  vi.mocked(api.approveRequest).mockResolvedValue({
    ...MOLBA, status: "approved",
  });
});

function prikazi() {
  return render(
    <MemoryRouter>
      <CodiumAccess />
    </MemoryRouter>,
  );
}

describe("strana Access & Users", () => {
  it("prikazuje molbu koja ceka odluku", async () => {
    prikazi();
    expect(await screen.findByText("agent:architect")).toBeInTheDocument();
    expect(screen.getByText("file.write")).toBeInTheDocument();
  });

  it("odobrenje sklanja molbu iz reda", async () => {
    prikazi();
    await screen.findByText("agent:architect");
    vi.mocked(api.getApprovals).mockResolvedValue({ count: 0, approvals: [] });

    await userEvent.click(screen.getByRole("button", { name: /Odobri/ }));

    await waitFor(() => {
      expect(api.approveRequest).toHaveBeenCalledWith(7, "");
    });
    await waitFor(() => {
      expect(screen.queryByText("agent:architect")).not.toBeInTheDocument();
    });
  });

  it("prazan red kaze da nema sta da se odlucuje", async () => {
    vi.mocked(api.getApprovals).mockResolvedValue({ count: 0, approvals: [] });
    prikazi();
    expect(
      await screen.findByText("Nema molbi koje čekaju odluku."),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

Pokreni (u `apps/gui`): `npx vitest run src/pages/CodiumAccess.test.tsx`
Očekivano: `Failed to resolve import "./CodiumAccess"`.

- [ ] **Korak 3: Napiši stranu**

Nov fajl `apps/gui/src/pages/CodiumAccess.tsx`:

```tsx
// ==========          ACCESS & USERS          ==========
// Dve stvari na jednoj strani: sta akteri smeju (pravila) i sta upravo ceka
// ljudsku odluku (red odobrenja). Red stoji gore jer je hitniji — pravilo se
// pise jednom, a molba blokira posao dok stoji.
import { Check, ShieldBan, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { describePayload } from "../features/codium/approvals";
import { relativeTime } from "../features/codium/activity";
import {
  addScopeRule,
  approveRequest,
  deleteScopeRule,
  getApprovals,
  getScopeRules,
  rejectRequest,
} from "../services/codiumApi";
import type { Approval, ScopeRule, ScopeVerdict } from "../types/codium";
import "../styles/codium-access.css";

const PRAZAN_OBRAZAC = {
  actor: "",
  action: "",
  target: "*",
  verdict: "deny" as ScopeVerdict,
  note: "",
};

export default function CodiumAccess() {
  const [rules, setRules] = useState<ScopeRule[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [error, setError] = useState("");
  const [obrazac, setObrazac] = useState(PRAZAN_OBRAZAC);
  const [razlozi, setRazlozi] = useState<Record<number, string>>({});

  const ucitaj = useCallback(async () => {
    try {
      const [pravila, molbe] = await Promise.all([
        getScopeRules(),
        getApprovals(),
      ]);
      setRules(pravila.rules);
      setApprovals(molbe.approvals);
      setError("");
    } catch {
      // Greska je traka iznad sadrzaja, ne prazna strana: vec ucitana
      // pravila ostaju vidljiva.
      setError("Učitavanje nije uspelo.");
    }
  }, []);

  useEffect(() => {
    void ucitaj();
  }, [ucitaj]);

  const odluci = async (id: number, odobri: boolean) => {
    try {
      if (odobri) {
        await approveRequest(id, "");
      } else {
        await rejectRequest(id, razlozi[id] ?? "");
      }
      await ucitaj();
    } catch {
      setError("Odluka nije prošla — možda je molba već odlučena.");
      await ucitaj();
    }
  };

  const dodajPravilo = async () => {
    if (!obrazac.actor.trim() || !obrazac.action.trim()) {
      return;
    }
    await addScopeRule(obrazac);
    setObrazac(PRAZAN_OBRAZAC);
    await ucitaj();
  };

  return (
    <div className="cacc-page">
      <header className="cacc-head">
        <p className="cacc-eyebrow">CODIUM · Sistem</p>
        <h1>Access &amp; Users</h1>
        <p className="cacc-sub">
          Ko sme šta. „Korisnici" su agenti i automatizacije — čovek odobrava.
        </p>
      </header>

      {error && <p className="cacc-error">{error}</p>}

      <section className="cacc-panel">
        <h2>Čeka odobrenje</h2>
        {approvals.length === 0 ? (
          <p className="cacc-empty">Nema molbi koje čekaju odluku.</p>
        ) : (
          <ul className="cacc-approvals">
            {approvals.map((molba) => (
              <li className="cacc-approval" key={molba.id}>
                <div className="cacc-approval-head">
                  <ShieldBan aria-hidden="true" size={15} />
                  <span className="cacc-actor">{molba.actor}</span>
                  <span className="cacc-action">{molba.action}</span>
                  <span className="cacc-target">{molba.target}</span>
                  <span className="cacc-when">
                    {relativeTime(molba.requested_at)}
                  </span>
                </div>

                <dl className="cacc-approval-payload">
                  {describePayload(molba.payload).map((linija) => (
                    <div key={linija.label}>
                      <dt>{linija.label}</dt>
                      <dd>{linija.value}</dd>
                    </div>
                  ))}
                </dl>

                <div className="cacc-actions">
                  <input
                    aria-label={`Razlog za molbu ${molba.id}`}
                    onChange={(e) =>
                      setRazlozi((prev) => ({
                        ...prev,
                        [molba.id as number]: e.target.value,
                      }))
                    }
                    placeholder="Razlog odbijanja"
                    value={razlozi[molba.id as number] ?? ""}
                  />
                  <button
                    className="cacc-approve"
                    onClick={() => void odluci(molba.id as number, true)}
                    type="button"
                  >
                    <Check aria-hidden="true" size={14} /> Odobri
                  </button>
                  <button
                    className="cacc-reject"
                    onClick={() => void odluci(molba.id as number, false)}
                    type="button"
                  >
                    <X aria-hidden="true" size={14} /> Odbij
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="cacc-panel">
        <h2>Pravila dozvola</h2>
        {rules.length === 0 ? (
          <p className="cacc-empty">
            Nema pravila — važi podrazumevano ponašanje po glagolu akcije.
          </p>
        ) : (
          <table className="cacc-table">
            <thead>
              <tr>
                <th>Akter</th>
                <th>Akcija</th>
                <th>Cilj</th>
                <th>Odgovor</th>
                <th>Napomena</th>
                <th aria-label="Brisanje" />
              </tr>
            </thead>
            <tbody>
              {rules.map((pravilo) => (
                <tr key={pravilo.id}>
                  <td>{pravilo.actor}</td>
                  <td>{pravilo.action}</td>
                  <td>{pravilo.target}</td>
                  <td className={`cacc-verdict v-${pravilo.verdict}`}>
                    {pravilo.verdict}
                  </td>
                  <td>{pravilo.note}</td>
                  <td>
                    <button
                      aria-label={`Obriši pravilo ${pravilo.id}`}
                      onClick={() => {
                        void deleteScopeRule(pravilo.id as number).then(ucitaj);
                      }}
                      type="button"
                    >
                      <Trash2 aria-hidden="true" size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="cacc-form">
          <input
            aria-label="Akter pravila"
            onChange={(e) => setObrazac({ ...obrazac, actor: e.target.value })}
            placeholder="agent:architect"
            value={obrazac.actor}
          />
          <input
            aria-label="Akcija pravila"
            onChange={(e) => setObrazac({ ...obrazac, action: e.target.value })}
            placeholder="file.write"
            value={obrazac.action}
          />
          <input
            aria-label="Cilj pravila"
            onChange={(e) => setObrazac({ ...obrazac, target: e.target.value })}
            value={obrazac.target}
          />
          <select
            aria-label="Odgovor pravila"
            onChange={(e) =>
              setObrazac({ ...obrazac, verdict: e.target.value as ScopeVerdict })
            }
            value={obrazac.verdict}
          >
            <option value="allow">allow</option>
            <option value="needs_approval">needs_approval</option>
            <option value="deny">deny</option>
          </select>
          <input
            aria-label="Napomena pravila"
            onChange={(e) => setObrazac({ ...obrazac, note: e.target.value })}
            placeholder="zašto"
            value={obrazac.note}
          />
          <button onClick={() => void dodajPravilo()} type="button">
            Dodaj pravilo
          </button>
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Korak 4: Napiši stil**

Nov fajl `apps/gui/src/styles/codium-access.css`. Prati ton
`codium-dashboard.css`: oštre ivice (`border-radius: 0`), tamna podloga,
tanke linije. Klase: `.cacc-page`, `.cacc-head`, `.cacc-panel`,
`.cacc-approval`, `.cacc-approval-payload`, `.cacc-actions`, `.cacc-table`,
`.cacc-form`, `.cacc-error`.

Verdikt dobija boju istim pravilom koje već važi na kontrolnoj tabli:
`allow` neutralno, `needs_approval` žuto, `deny` crveno — odbijanje nije kvar i
ne sme da izgleda kao greška.

- [ ] **Korak 5: Pokreni test i potvrdi da prolazi**

Pokreni (u `apps/gui`): `npx vitest run src/pages/CodiumAccess.test.tsx`
Očekivano: 3 testa prolaze.

- [ ] **Korak 6: Commit**

```bash
git add apps/gui/src/pages/CodiumAccess.tsx apps/gui/src/pages/CodiumAccess.test.tsx apps/gui/src/styles/codium-access.css
git commit -F- <<'EOF'
feat(gui): strana Access & Users sa redom odobrenja

Red cekanja stoji iznad tabele pravila jer je hitniji: pravilo se pise
jednom, a molba blokira posao dok stoji.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 6: Strana „Audit Logs"

**Fajlovi:**
- Pravi: `apps/gui/src/pages/CodiumAudit.tsx`
- Menja: `apps/gui/src/styles/codium-access.css`
- Test: `apps/gui/src/pages/CodiumAudit.test.tsx` (nov)

**Interfejsi:**
- Koristi: `getAuditLog` iz Zadatka 4; `relativeTime` iz
  `features/codium/activity`
- Daje: podrazumevani izvoz `CodiumAudit`

- [ ] **Korak 1: Napiši test koji pada**

Nov fajl `apps/gui/src/pages/CodiumAudit.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CodiumAudit from "./CodiumAudit";
import * as api from "../services/codiumApi";

vi.mock("../services/codiumApi");

const UNOS = {
  id: 1, at: "2026-08-29 10:00:00", actor: "agent:architect",
  action: "file.write", target: "src/api.py", verdict: "deny",
  outcome: "blocked", detail: "pravilo domena", project_id: null,
};

beforeEach(() => {
  vi.mocked(api.getAuditLog).mockResolvedValue({ count: 1, entries: [UNOS] });
});

function prikazi() {
  return render(
    <MemoryRouter>
      <CodiumAudit />
    </MemoryRouter>,
  );
}

describe("strana Audit Logs", () => {
  it("prikazuje unos dnevnika", async () => {
    prikazi();
    expect(await screen.findByText("file.write")).toBeInTheDocument();
    expect(screen.getByText("agent:architect")).toBeInTheDocument();
  });

  it("filter po akteru salje parametar", async () => {
    prikazi();
    await screen.findByText("file.write");

    await userEvent.type(screen.getByLabelText("Akter"), "agent:x");
    await userEvent.click(screen.getByRole("button", { name: "Primeni" }));

    await waitFor(() => {
      expect(api.getAuditLog).toHaveBeenLastCalledWith(
        expect.objectContaining({ actor: "agent:x" }),
      );
    });
  });

  it("prazan dnevnik ne izgleda kao greska", async () => {
    vi.mocked(api.getAuditLog).mockResolvedValue({ count: 0, entries: [] });
    prikazi();
    expect(
      await screen.findByText("Dnevnik je prazan."),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

Pokreni (u `apps/gui`): `npx vitest run src/pages/CodiumAudit.test.tsx`
Očekivano: `Failed to resolve import "./CodiumAudit"`.

- [ ] **Korak 3: Napiši stranu**

Nov fajl `apps/gui/src/pages/CodiumAudit.tsx`:

```tsx
// ==========          AUDIT LOGS          ==========
// Dnevnik se cita unazad u nizu, pa „Ucitaj jos" dopisuje redove umesto da
// ih zameni — zamena bi gubila mesto na kome si stao.
import { useCallback, useEffect, useState } from "react";

import { relativeTime } from "../features/codium/activity";
import { getAuditLog } from "../services/codiumApi";
import type { AuditEntry } from "../types/codium";
import "../styles/codium-access.css";

const STRANICA = 50;

export default function CodiumAudit() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [error, setError] = useState("");
  const [imaJos, setImaJos] = useState(false);
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");

  const ucitaj = useCallback(
    async (offset: number, dopuni: boolean) => {
      try {
        const data = await getAuditLog({
          actor: actor.trim() || undefined,
          action: action.trim() || undefined,
          limit: STRANICA,
          offset,
        });
        setEntries((prev) =>
          dopuni ? [...prev, ...data.entries] : data.entries,
        );
        setImaJos(data.entries.length === STRANICA);
        setError("");
      } catch {
        setError("Učitavanje dnevnika nije uspelo.");
      }
    },
    [actor, action],
  );

  useEffect(() => {
    void ucitaj(0, false);
    // Namerno bez `ucitaj` u zavisnostima: filteri se primenjuju dugmetom,
    // a ne kucanjem — inace bi svaki pritisak tastera zvao server.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="cacc-page">
      <header className="cacc-head">
        <p className="cacc-eyebrow">CODIUM · Sistem</p>
        <h1>Audit Logs</h1>
        <p className="cacc-sub">
          Šta je traženo, šta je kapija odgovorila i kako se završilo.
        </p>
      </header>

      {error && <p className="cacc-error">{error}</p>}

      <div className="cadt-filters">
        <label htmlFor="cadt-actor">Akter</label>
        <input
          id="cadt-actor"
          onChange={(e) => setActor(e.target.value)}
          placeholder="agent:architect"
          value={actor}
        />
        <label htmlFor="cadt-action">Akcija</label>
        <input
          id="cadt-action"
          onChange={(e) => setAction(e.target.value)}
          placeholder="file.write"
          value={action}
        />
        <button onClick={() => void ucitaj(0, false)} type="button">
          Primeni
        </button>
      </div>

      {entries.length === 0 ? (
        <p className="cacc-empty">Dnevnik je prazan.</p>
      ) : (
        <table className="cacc-table cadt-table">
          <thead>
            <tr>
              <th>Kada</th>
              <th>Akter</th>
              <th>Akcija</th>
              <th>Cilj</th>
              <th>Odgovor</th>
              <th>Ishod</th>
              <th>Detalj</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((unos) => (
              <tr key={unos.id}>
                <td>{relativeTime(unos.at)}</td>
                <td>{unos.actor}</td>
                <td>{unos.action}</td>
                <td>{unos.target}</td>
                <td className={`cacc-verdict v-${unos.verdict}`}>
                  {unos.verdict}
                </td>
                <td>{unos.outcome}</td>
                <td>{unos.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {imaJos && (
        <button
          className="cadt-more"
          onClick={() => void ucitaj(entries.length, true)}
          type="button"
        >
          Učitaj još
        </button>
      )}
    </div>
  );
}
```

Dopuni `apps/gui/src/styles/codium-access.css` klasama `.cadt-filters`,
`.cadt-table` i `.cadt-more` u istom tonu kao ostatak fajla.

- [ ] **Korak 4: Pokreni test i potvrdi da prolazi**

Pokreni (u `apps/gui`): `npx vitest run src/pages/CodiumAudit.test.tsx`
Očekivano: 3 testa prolaze.

- [ ] **Korak 5: Commit**

```bash
git add apps/gui/src/pages/CodiumAudit.tsx apps/gui/src/pages/CodiumAudit.test.tsx apps/gui/src/styles/codium-access.css
git commit -F- <<'EOF'
feat(gui): strana Audit Logs sa filterima i dopunjavanjem

Ucitavanje dopisuje redove umesto da ih zamenjuje: dnevnik se cita
unazad u nizu, pa bi zamena gubila mesto na kome si stao.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Zadatak 7: Rute, sidebar i ispravke planskih fajlova

**Fajlovi:**
- Menja: `apps/gui/src/App.tsx`
- Menja: `apps/gui/src/components/layout/Sidebar.tsx:287-288`
- Menja: `.ai/izgradnja/codium/11-E1-audit-i-scopegate.md`
- Menja: `.ai/izgradnja/codium/00-INDEX.md`

**Interfejsi:**
- Koristi: `CodiumAccess` i `CodiumAudit` iz Zadataka 5 i 6

- [ ] **Korak 1: Dodaj rute**

U `apps/gui/src/App.tsx`, uz uvoze ostalih CODIUM strana i odmah posle rute
`/codium/settings`:

```tsx
        <Route
          path="/codium/access"
          element={<CodiumAccess />}
        />

        <Route
          path="/codium/audit"
          element={<CodiumAudit />}
        />
```

- [ ] **Korak 2: Otključaj stavke u sidebar-u**

U `apps/gui/src/components/layout/Sidebar.tsx`, sekcija `SYSTEM`, zameni dve
`soon` stavke:

```tsx
        { id: "access-users", label: "Access & Users", icon: Users, kind: "route", path: "/codium/access" },
        { id: "audit-logs", label: "Audit Logs", icon: ScrollText, kind: "route", path: "/codium/audit" },
```

- [ ] **Korak 3: Pokreni ceo GUI paket i proveru tipova**

Pokreni (u `apps/gui`): `npx vitest run` pa `npx tsc -b tsconfig.app.json`
Očekivano: svi testovi prolaze; `tsc` prijavljuje samo dve zatečene greške.

- [ ] **Korak 4: Ispravi planske fajlove**

U `.ai/izgradnja/codium/11-E1-audit-i-scopegate.md`:
- zaglavlje: `Migracija: codium v6 + ops v2` → `codium v6 (pravila) + v7
  (odobrenja) + ops v2`,
- u odeljku „Šema", `codium_approvals` premesti pod naslov migracije **v7** sa
  napomenom da v6 nosi samo pravila,
- u tabeli API-ja dodaj da `/approvals/{id}/approve|reject` vraćaju `409` kada
  molba više ne čeka.

U `.ai/izgradnja/codium/00-INDEX.md`, red za E1 u tabeli statusa: `plan zapisan`
→ `zavrseno`, datum `2026-08-29`, a kolonu baze uskladi sa gornjim.

- [ ] **Korak 5: Provera uživo**

Pokreni API i GUI, pa u browseru:

1. Otvori `#/codium/access` — strana se otvara, red čekanja prazan.
2. Napravi pravilo: akter `agent:proba`, akcija `file.write`, verdikt
   `needs_approval`.
3. Kroz `curl` upiši molbu direktno u red:
   `curl -s -X POST localhost:8000/api/v1/codium/audit/rules -H "Content-Type: application/json" -d '{"actor":"agent:proba","action":"file.write","verdict":"needs_approval"}'`
   pa proveri da se pravilo vidi u tabeli.
4. Otvori `#/codium/audit` — dnevnik prikazuje ranije unose sa bojom po verdiktu.
5. Obriši probno pravilo da tabela ostane prazna kao pre provere.

Zapiši šta si video. Ako se nešto ne poklapa sa očekivanim, to je nalaz — ne
prećuti ga.

- [ ] **Korak 6: Commit**

```bash
git add apps/gui/src/App.tsx apps/gui/src/components/layout/Sidebar.tsx .ai/izgradnja/codium
git commit -F- <<'EOF'
feat(gui): Access & Users i Audit Logs prestaju da budu „uskoro"

Dve sidebar stavke koje su stajale kao najava sada vode na prave strane,
cime je E1 zaokruzen po svojoj definiciji zavrsetka.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Definicija završetka

- `codium_approvals` postoji, status je ograničen šemom, v6 tabele netaknute.
- Molba se upisuje, vidi u redu, i odlučuje tačno jednom; druga odluka vraća 409.
- Svaka odluka ostavlja unos u dnevniku kao `human` + `approval.decide`.
- `#/codium/access` prikazuje red čekanja i tabelu pravila; `#/codium/audit`
  prikazuje filtriran dnevnik.
- Ceo pytest paket i ceo vitest paket prolaze; `npx tsc -b tsconfig.app.json`
  ne prijavljuje nijednu novu grešku.
