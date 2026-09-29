---
id: codium-a7794eeb-2026-08-29-codium-ai3-openrouter-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: AI-3 OpenRouter — plan izvođenja
summary: '> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
  (recommended) or superpowers:executing-plans to implement this plan t'
keywords:
- openrouter
- izvođenja
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-29-codium-ai3-openrouter.md
edges:
- type: references
  target: core-1ad03ff9-2026-08-29-codium-openrouter-design-md
  weight: 0.3
---

# AI-3 OpenRouter — plan izvođenja

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenRouter ulazi u CORE ruter modela kao četvrti provajder — jedan ključ za Claude, GPT, Gemini i ostale — sa allow listom umesto deny liste, cenama iz živog kataloga i odobrenjem za online pozive agenta.

**Architecture:** Sloj provajdera (`ChatProvider`), katalog i ruter već postoje iz AI-1 i AI-2. Dodaju se: provajder konektora (da se ključ sačuva), `ChatProvider` nad OpenRouter-om kroz postojeći `openai` SDK sa drugim `base_url`, keširan katalog na disku, allow lista u `core.db`, jedno mesto koje računa `enabled` za oba routera, i provera kapije `ai.call_online` u petlji agenta.

**Tech Stack:** Python 3.14, FastAPI, SQLite (`core.database`), pytest; React + TypeScript + Vite, vitest. Bez novih zavisnosti.

**Spec:** [`docs/superpowers/specs/2026-08-29-codium-openrouter-design.md`](../specs/2026-08-29-codium-openrouter-design.md)

## Global Constraints

- **Nema nove zavisnosti.** OpenRouter ide kroz već instaliran `openai` SDK (`base_url="https://openrouter.ai/api/v1"`); katalog se dohvata `urllib.request`-om iz standardne biblioteke.
- **Vrednost tajne nikad ne izlazi iz `SecretVault`-a.** U bazi stoji samo `secret_alias`. Ključ se ne loguje, ne upisuje u `config_json`, i ne stavlja u poruku greške.
- **Testovi ne dodiruju mrežu.** Svaki HTTP put se ubrizgava kao funkcija ili klijent-fabrika, po uzoru na `core/ai/providers/openai.py`.
- **Komentari i dokumentacija na srpskom, identifikatori na engleskom** — kao u zatečenom kodu.
- **Testovi se pokreću kroz venv:** `./.venv/Scripts/python.exe -m pytest`, ne kroz sistemski `python`.
- **GUI provera tipova:** `npx tsc -b tsconfig.app.json` iz `apps/gui`. Dve greške već postoje pre ovog posla i nisu tvoje: `CoreDockLayout.tsx(42,52) TS2503` i `CodiumWorkspace.tsx(14,3) TS6133`.
- **Postojeće ponašanje ne sme da regresira.** `test_codium_assistant`, `test_api_codium_ai`, `test_api_core_models`, `test_model_visibility_scopes`, `test_chat_providers` moraju proći nepromenjeni.

---

### Task 1: Provajder konektora za OpenRouter

Bez ovoga panel „API ključevi" prikazuje OpenRouter kao nepodržan i ne da ključ da se sačuva — `ConnectorService.supported_kinds()` vraća samo vrste koje imaju provajdera. Zato je ovo prvi posao.

**Files:**
- Create: `core/integrations/providers/openrouter.py`
- Modify: `core/integrations/providers/__init__.py`
- Modify: `apps/api/core_ai_runtime.py`
- Test: `tests/test_openrouter_connector.py`

**Interfaces:**
- Consumes: `ConnectorProbe`, `ConnectorKind` (postojeći)
- Produces: `OpenRouterConnectorProvider(client_factory=None)` sa `kind`, `required_fields()`, `secret_fields()`, `test(config, secret)`

- [ ] **Step 1: Napiši test koji pada**

Create `tests/test_openrouter_connector.py`:

```python
# ========== TESTOVI: provajder konektora OpenRouter ==========
from __future__ import annotations

from core.integrations.models import ConnectorKind
from core.integrations.providers.openrouter import OpenRouterConnectorProvider


class _FakeModels:
    def __init__(self, greska: Exception | None = None) -> None:
        self._greska = greska
        self.pozvan = False

    def list(self):
        self.pozvan = True
        if self._greska is not None:
            raise self._greska
        return {"data": []}


class _FakeClient:
    def __init__(self, api_key: str, base_url: str = "",
                 greska: Exception | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.models = _FakeModels(greska)


def test_vrsta_je_openrouter():
    assert OpenRouterConnectorProvider().kind is ConnectorKind.OPENROUTER


def test_bez_kljuca_proba_pada_bez_poziva():
    pozvano: list[str] = []

    def fabrika(api_key: str):
        pozvano.append(api_key)
        return _FakeClient(api_key)

    proba = OpenRouterConnectorProvider(fabrika).test({}, None)

    assert proba.ok is False
    assert proba.message == "Nema API kljuca."
    assert pozvano == []


def test_uspesna_proba_zove_models_list_na_openrouter_url():
    klijenti: list[_FakeClient] = []

    def fabrika(api_key: str):
        klijent = _FakeClient(api_key, base_url="https://openrouter.ai/api/v1")
        klijenti.append(klijent)
        return klijent

    proba = OpenRouterConnectorProvider(fabrika).test({}, "sk-or-test")

    assert proba.ok is True
    assert proba.message == ""
    assert proba.latency_ms is not None
    assert klijenti[0].api_key == "sk-or-test"
    assert klijenti[0].models.pozvan is True


def test_pad_sdk_a_postaje_uredna_poruka():
    def fabrika(api_key: str):
        return _FakeClient(api_key, greska=RuntimeError("401 unauthorized"))

    proba = OpenRouterConnectorProvider(fabrika).test({}, "sk-or-los")

    assert proba.ok is False
    assert "401 unauthorized" in proba.message


def test_trazi_samo_api_key_i_nijedno_config_polje():
    provajder = OpenRouterConnectorProvider()

    assert provajder.secret_fields() == ["api_key"]
    assert provajder.required_fields() == []
```

- [ ] **Step 2: Pokreni test i potvrdi da pada**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_openrouter_connector.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.integrations.providers.openrouter'`

- [ ] **Step 3: Napiši provajdera**

Create `core/integrations/providers/openrouter.py`:

```python
# ========== PROVAJDER KONEKTORA: OPENROUTER ==========
# Proba konekcije ka OpenRouter-u. OpenRouter je OpenAI-kompatibilan, pa ide
# kroz vec instaliran `openai` SDK sa drugim `base_url` — nova zavisnost se ne
# uvodi. Klijent se ubrizgava (isti obrazac kao core/ai/providers/openai.py) da
# testovi nikad ne dodju do mreze.
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from core.integrations.models import ConnectorKind
from core.integrations.providers.base import ConnectorProbe

# Isti URL koristi i `core/ai/providers/openrouter.py`; drzi se ovde jer je
# konektor prvi koji ga treba, a provajder modela ga uvozi odavde.
BASE_URL = "https://openrouter.ai/api/v1"

ClientFactory = Callable[[str], Any]


class OpenRouterConnectorProvider:
    """Testira OpenRouter konektor pozivom `models.list()`."""

    kind = ConnectorKind.OPENROUTER

    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or self._default_factory

    @staticmethod
    def _default_factory(api_key: str) -> Any:
        import openai

        return openai.OpenAI(api_key=api_key, base_url=BASE_URL)

    # ---------- protokol ----------

    def required_fields(self) -> list[str]:
        return []

    def secret_fields(self) -> list[str]:
        return ["api_key"]

    def test(self, config: dict, secret: str | None) -> ConnectorProbe:
        if not secret:
            return ConnectorProbe(ok=False, message="Nema API kljuca.")

        started = time.perf_counter()
        try:
            klijent = self._client_factory(secret)
            klijent.models.list()
        except Exception as error:  # noqa: BLE001 — SDK puca na svoj nacin
            return ConnectorProbe(ok=False, message=str(error))

        trajanje = int((time.perf_counter() - started) * 1000)
        return ConnectorProbe(ok=True, message="", latency_ms=trajanje)
```

- [ ] **Step 4: Izvezi ga i registruj u runtime-u**

U `core/integrations/providers/__init__.py` dodaj uvoz i `__all__` unos po uzoru na postojeće (`AnthropicConnectorProvider`, `OpenAIConnectorProvider`):

```python
from core.integrations.providers.openrouter import OpenRouterConnectorProvider
```

U `apps/api/core_ai_runtime.py`, uz postojeća dva uvoza konektora:

```python
from core.integrations.providers.openrouter import OpenRouterConnectorProvider
```

i u mapu provajdera koja se predaje `ConnectorService`-u:

```python
_connector_service = ConnectorService(
    _connectors,
    _vault,
    {
        ConnectorKind.ANTHROPIC: AnthropicConnectorProvider(),
        ConnectorKind.OPENAI: OpenAIConnectorProvider(),
        ConnectorKind.OPENROUTER: OpenRouterConnectorProvider(),
    },
)
```

- [ ] **Step 5: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_openrouter_connector.py tests/test_api_core_integrations.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/integrations/providers/openrouter.py core/integrations/providers/__init__.py apps/api/core_ai_runtime.py tests/test_openrouter_connector.py
git commit -m "feat(core-ai): provajder konektora za OpenRouter"
```

---

### Task 2: Katalog OpenRouter modela sa kešom na disku

**Files:**
- Create: `core/ai/openrouter_catalog.py`
- Test: `tests/test_openrouter_catalog.py`

**Interfaces:**
- Produces:
  - `CatalogModel(id, label, context_window, price_in_per_mtok, price_out_per_mtok)`
  - `CatalogSnapshot(models: tuple[CatalogModel, ...], fetched_at: float, stale: bool)`
  - `OpenRouterCatalog(cache_path, fetcher, ttl=CACHE_TTL, now=time.time)` sa `snapshot(force=False) -> CatalogSnapshot`
  - `CatalogUnavailable` (izuzetak)
  - `default_cache_path() -> Path`

- [ ] **Step 1: Napiši test koji pada**

Create `tests/test_openrouter_catalog.py`:

```python
# ========== TESTOVI: katalog OpenRouter modela ==========
from __future__ import annotations

import json

import pytest

from core.ai.openrouter_catalog import (
    CatalogUnavailable,
    OpenRouterCatalog,
)

SIROVO = {
    "data": [
        {
            "id": "anthropic/claude-sonnet-4.5",
            "name": "Anthropic: Claude Sonnet 4.5",
            "context_length": 200000,
            "pricing": {"prompt": "0.000003", "completion": "0.000015"},
        },
        {
            "id": "meta-llama/llama-3-8b:free",
            "name": "Meta: Llama 3 8B (free)",
            "context_length": 8192,
            "pricing": {"prompt": "0", "completion": "0"},
        },
    ],
}


def _katalog(tmp_path, fetcher, *, sada=1000.0, ttl=100.0):
    return OpenRouterCatalog(
        cache_path=tmp_path / "openrouter_models.json",
        fetcher=fetcher,
        ttl=ttl,
        now=lambda: sada,
    )


def test_svez_dohvat_prevodi_cenu_u_dolare_po_milionu(tmp_path):
    katalog = _katalog(tmp_path, lambda: SIROVO)

    snimak = katalog.snapshot()

    assert snimak.stale is False
    prvi = snimak.models[0]
    assert prvi.id == "anthropic/claude-sonnet-4.5"
    assert prvi.label == "Anthropic: Claude Sonnet 4.5"
    assert prvi.context_window == 200000
    assert prvi.price_in_per_mtok == pytest.approx(3.0)
    assert prvi.price_out_per_mtok == pytest.approx(15.0)


def test_besplatan_model_ima_cenu_nula(tmp_path):
    katalog = _katalog(tmp_path, lambda: SIROVO)

    drugi = katalog.snapshot().models[1]

    assert drugi.price_in_per_mtok == 0.0
    assert drugi.price_out_per_mtok == 0.0


def test_kes_unutar_roka_ne_poziva_mrezu(tmp_path):
    pozivi = {"broj": 0}

    def fetcher():
        pozivi["broj"] += 1
        return SIROVO

    katalog = _katalog(tmp_path, fetcher, ttl=100.0)
    katalog.snapshot()
    katalog.snapshot()

    assert pozivi["broj"] == 1


def test_istekao_kes_ponovo_poziva(tmp_path):
    pozivi = {"broj": 0}

    def fetcher():
        pozivi["broj"] += 1
        return SIROVO

    put = tmp_path / "openrouter_models.json"
    prvi = OpenRouterCatalog(cache_path=put, fetcher=fetcher, ttl=10.0,
                             now=lambda: 1000.0)
    prvi.snapshot()
    drugi = OpenRouterCatalog(cache_path=put, fetcher=fetcher, ttl=10.0,
                              now=lambda: 1011.0)
    drugi.snapshot()

    assert pozivi["broj"] == 2


def test_force_zaobilazi_kes(tmp_path):
    pozivi = {"broj": 0}

    def fetcher():
        pozivi["broj"] += 1
        return SIROVO

    katalog = _katalog(tmp_path, fetcher, ttl=100.0)
    katalog.snapshot()
    katalog.snapshot(force=True)

    assert pozivi["broj"] == 2


def test_pad_mreze_vraca_zastareo_kes(tmp_path):
    put = tmp_path / "openrouter_models.json"
    OpenRouterCatalog(cache_path=put, fetcher=lambda: SIROVO, ttl=10.0,
                      now=lambda: 1000.0).snapshot()

    def puca():
        raise OSError("mreza nedostupna")

    snimak = OpenRouterCatalog(cache_path=put, fetcher=puca, ttl=10.0,
                               now=lambda: 9999.0).snapshot()

    assert snimak.stale is True
    assert snimak.models[0].id == "anthropic/claude-sonnet-4.5"


def test_pad_bez_kesa_dize_gresku(tmp_path):
    def puca():
        raise OSError("mreza nedostupna")

    katalog = _katalog(tmp_path, puca)

    with pytest.raises(CatalogUnavailable):
        katalog.snapshot()


def test_polovan_kes_se_ne_ruse_nego_ponovo_dohvata(tmp_path):
    put = tmp_path / "openrouter_models.json"
    put.write_text("{ ovo nije json", encoding="utf-8")

    snimak = _katalog(tmp_path, lambda: SIROVO).snapshot()

    assert snimak.stale is False
    assert len(snimak.models) == 2


def test_upis_kesa_je_atomican(tmp_path):
    put = tmp_path / "openrouter_models.json"
    _katalog(tmp_path, lambda: SIROVO).snapshot()

    # Posle upisa ne sme ostati nijedan privremeni fajl.
    assert [p.name for p in tmp_path.iterdir()] == [put.name]
    assert json.loads(put.read_text(encoding="utf-8"))["data"]
```

- [ ] **Step 2: Pokreni test i potvrdi da pada**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_openrouter_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.ai.openrouter_catalog'`

- [ ] **Step 3: Napiši modul**

Create `core/ai/openrouter_catalog.py`:

```python
# ========== KATALOG OPENROUTER MODELA ==========
# OpenRouter nudi preko 300 modela i, za razliku od Anthropic-a i OpenAI-ja,
# vraca i CENU u samom katalogu. Zato cena ovog provajdera ne ide u rucnu
# tabelu `pricing.py` nego dolazi iz izvora.
#
# Dohvatanje kosta poziv od 300+ redova, pa se kesira na disk. Pravilo: katalog
# NIKADA ne obara poziv — ako mreza padne a kes postoji, vraca se kes obelezen
# kao zastareo.
from __future__ import annotations

import json
import os
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from core.foundation.paths import core_paths
from core.integrations.providers.openrouter import BASE_URL

# Cene se menjaju retko; dohvatanje na svaki otvor liste je bespotrebno.
CACHE_TTL_SECONDS = 24 * 60 * 60

# Koliko cekamo mrezu pre nego sto odustanemo i posegnemo za kesom.
HTTP_TIMEOUT_SECONDS = 15.0


class CatalogUnavailable(RuntimeError):
    """Katalog se ne moze dohvatiti, a kesa nema."""


@dataclass(frozen=True)
class CatalogModel:
    """Jedan model iz OpenRouter kataloga, u nasim jedinicama."""

    id: str
    label: str
    context_window: int
    # Dolari po MILIONU tokena — jedinica koju `ModelInfo` i `pricing.py` vec
    # koriste. OpenRouter vraca cenu po jednom tokenu, kao tekst.
    price_in_per_mtok: float
    price_out_per_mtok: float


@dataclass(frozen=True)
class CatalogSnapshot:
    """Spisak modela sa podatkom koliko je star."""

    models: tuple[CatalogModel, ...]
    fetched_at: float
    stale: bool


Fetcher = Callable[[], dict]


def default_cache_path() -> Path:
    """Gde kes stoji kad ga niko ne zada (produkcijski put)."""

    return core_paths.data / "cache" / "openrouter_models.json"


def http_fetcher() -> dict:
    """Pravi dohvat sa OpenRouter-a. Standardna biblioteka, bez zavisnosti."""

    zahtev = urllib.request.Request(
        f"{BASE_URL}/models",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(zahtev, timeout=HTTP_TIMEOUT_SECONDS) as odgovor:
        return json.loads(odgovor.read().decode("utf-8"))


def _broj(vrednost: object) -> float:
    """Cena iz kataloga u float. Nepoznat oblik znaci nula, ne pad."""

    try:
        return float(str(vrednost))
    except (TypeError, ValueError):
        return 0.0


class OpenRouterCatalog:
    """Katalog modela sa kesom na disku."""

    def __init__(self, *, cache_path: Path | None = None,
                 fetcher: Fetcher | None = None,
                 ttl: float = CACHE_TTL_SECONDS,
                 now: Callable[[], float] | None = None) -> None:
        self._cache_path = cache_path or default_cache_path()
        self._fetcher = fetcher or http_fetcher
        self._ttl = ttl
        self._now = now or time.time

    # ---------- javno ----------

    def snapshot(self, *, force: bool = False) -> CatalogSnapshot:
        """Modeli iz kesa ako je svez, inace sa mreze.

        `force` preskace kes (ruka na dugmetu „osvezi").
        """

        kes = self._procitaj_kes()
        if not force and kes is not None:
            uzeto_u = float(kes.get("fetched_at", 0.0))
            if self._now() - uzeto_u < self._ttl:
                return CatalogSnapshot(
                    models=self._prevedi(kes.get("data") or []),
                    fetched_at=uzeto_u,
                    stale=False,
                )

        try:
            sirovo = self._fetcher()
        except Exception as error:  # noqa: BLE001 — mreza puca na svoj nacin
            if kes is None:
                raise CatalogUnavailable(str(error)) from error
            # Zastareo spisak je uvek bolji od praznog: korisnik vidi svoje
            # modele i oznaku da podaci nisu sveži.
            return CatalogSnapshot(
                models=self._prevedi(kes.get("data") or []),
                fetched_at=float(kes.get("fetched_at", 0.0)),
                stale=True,
            )

        sada = self._now()
        self._upisi_kes({"fetched_at": sada, "data": sirovo.get("data") or []})
        return CatalogSnapshot(
            models=self._prevedi(sirovo.get("data") or []),
            fetched_at=sada,
            stale=False,
        )

    # ---------- interno ----------

    @staticmethod
    def _prevedi(redovi: list) -> tuple[CatalogModel, ...]:
        modeli: list[CatalogModel] = []
        for red in redovi:
            if not isinstance(red, dict):
                continue
            model_id = str(red.get("id") or "")
            if not model_id:
                continue
            cene = red.get("pricing") or {}
            modeli.append(CatalogModel(
                id=model_id,
                label=str(red.get("name") or model_id),
                context_window=int(red.get("context_length") or 0),
                price_in_per_mtok=_broj(cene.get("prompt")) * 1_000_000,
                price_out_per_mtok=_broj(cene.get("completion")) * 1_000_000,
            ))
        return tuple(modeli)

    def _procitaj_kes(self) -> dict | None:
        """Kes sa diska; polovan ili nepostojeci fajl znaci „nema kesa"."""

        try:
            tekst = self._cache_path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            podaci = json.loads(tekst)
        except json.JSONDecodeError:
            return None
        return podaci if isinstance(podaci, dict) else None

    def _upisi_kes(self, podaci: dict) -> None:
        """Atomican upis: prekinut upis ne sme da ostavi polovan JSON."""

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        privremeni = self._cache_path.with_suffix(".json.tmp")
        try:
            privremeni.write_text(
                json.dumps(podaci, ensure_ascii=False), encoding="utf-8",
            )
            os.replace(privremeni, self._cache_path)
        except OSError:
            # Kes je ubrzanje, ne uslov. Neuspeo upis ne sme da obori poziv.
            privremeni.unlink(missing_ok=True)
```

- [ ] **Step 4: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_openrouter_catalog.py -v`
Expected: PASS (9 testova)

- [ ] **Step 5: Commit**

```bash
git add core/ai/openrouter_catalog.py tests/test_openrouter_catalog.py
git commit -m "feat(core-ai): katalog OpenRouter modela sa kesom na disku"
```

---

### Task 3: Allow lista modela (migracija core_ai v3)

**Files:**
- Modify: `core/integrations/migrations.py`
- Create: `core/ai/allowlist.py`
- Test: `tests/test_model_allowlist.py`

**Interfaces:**
- Consumes: `CatalogModel` iz Task 2
- Produces:
  - `ModelAllowlist(database_path=None)` sa `allowed(provider) -> set[str]`, `set_allowed(provider, model, allowed)`, `is_seeded(provider) -> bool`, `seed(provider, models: Iterable[str])`
  - `seed_selection(models: Sequence[CatalogModel]) -> list[str]`
  - `SEED_MARKER = "__seeded__"`

- [ ] **Step 1: Napiši test koji pada**

Create `tests/test_model_allowlist.py`:

```python
# ========== TESTOVI: allow lista modela ==========
from __future__ import annotations

import pytest

from core.ai.allowlist import SEED_MARKER, ModelAllowlist, seed_selection
from core.ai.openrouter_catalog import CatalogModel
from core.database.runtime import initialize_core_database


@pytest.fixture()
def lista(tmp_path) -> ModelAllowlist:
    database = tmp_path / "core_allow.db"
    initialize_core_database(database)
    return ModelAllowlist(database)


def _model(model_id: str, cena: float = 3.0, kontekst: int = 200000):
    return CatalogModel(id=model_id, label=model_id, context_window=kontekst,
                        price_in_per_mtok=cena, price_out_per_mtok=cena * 5)


def test_prazna_lista_ne_pusta_nijedan_model(lista):
    assert lista.allowed("openrouter") == set()


def test_ukljucen_model_je_dozvoljen(lista):
    lista.set_allowed("openrouter", "anthropic/claude-sonnet-4.5", True)

    assert lista.allowed("openrouter") == {"anthropic/claude-sonnet-4.5"}


def test_iskljucivanje_brise_red(lista):
    lista.set_allowed("openrouter", "openai/gpt-5", True)
    lista.set_allowed("openrouter", "openai/gpt-5", False)

    assert lista.allowed("openrouter") == set()


def test_dvostruko_ukljucivanje_ne_puca(lista):
    lista.set_allowed("openrouter", "openai/gpt-5", True)
    lista.set_allowed("openrouter", "openai/gpt-5", True)

    assert lista.allowed("openrouter") == {"openai/gpt-5"}


def test_marker_se_ne_prikazuje_kao_model(lista):
    lista.seed("openrouter", ["openai/gpt-5"])

    assert lista.is_seeded("openrouter") is True
    assert SEED_MARKER not in lista.allowed("openrouter")


def test_drugo_punjenje_ne_vaskrsava_izbacen_model(lista):
    lista.seed("openrouter", ["openai/gpt-5"])
    lista.set_allowed("openrouter", "openai/gpt-5", False)

    lista.seed("openrouter", ["openai/gpt-5"])

    assert lista.allowed("openrouter") == set()


def test_izbor_uzima_najskuplji_model_po_porodici():
    modeli = [
        _model("anthropic/claude-haiku-4.5", cena=1.0),
        _model("anthropic/claude-opus-5", cena=5.0),
        _model("openai/gpt-5", cena=1.25),
    ]

    assert seed_selection(modeli) == ["anthropic/claude-opus-5", "openai/gpt-5"]


def test_izbor_preskace_besplatne_i_kratak_kontekst():
    modeli = [
        _model("qwen/qwen3-free", cena=0.0),
        _model("google/gemini-flash", cena=0.3, kontekst=32000),
        _model("deepseek/deepseek-chat", cena=0.5),
    ]

    assert seed_selection(modeli) == ["deepseek/deepseek-chat"]


def test_izbor_preskace_nepoznatu_porodicu():
    assert seed_selection([_model("neko/nesto", cena=9.0)]) == []
```

- [ ] **Step 2: Pokreni test i potvrdi da pada**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_model_allowlist.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.ai.allowlist'`

- [ ] **Step 3: Dodaj migraciju core_ai v3**

U `core/integrations/migrations.py`, posle `CORE_AI_MIGRATION_V2`:

```python
# ---------- v3: allow lista (provajderi sa prevelikim katalogom) ----------

CORE_AI_MIGRATION_V3 = DatabaseMigration(
    scope="core_ai",
    version=3,
    name="model_allowlist",
    statements=(
        # ALLOW lista, suprotno od `core_model_visibility`. Deny lista kaze
        # STA SE NE NUDI; allow lista kaze STA UOPSTE POSTOJI. Postoji samo
        # za provajdera koji je trazi (`needs_allowlist = True`), jer njegov
        # katalog ima 300+ modela i deny lista bi znacila 300 iskljucivanja.
        #
        # Bez opsega, namerno: CORE odlucuje koji modeli uopste postoje, a
        # postojeca deny lista po domenu i dalje sme da ih suzi.
        """
        CREATE TABLE core_model_allowlist (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            provider   TEXT NOT NULL,
            model      TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE UNIQUE INDEX idx_core_model_allowlist "
        "ON core_model_allowlist (provider, model)",
    ),
)
```

i dopuni torku na kraju fajla:

```python
CORE_AI_MIGRATIONS = (
    CORE_AI_MIGRATION_V1,
    CORE_AI_MIGRATION_V2,
    CORE_AI_MIGRATION_V3,
)
```

- [ ] **Step 4: Napiši allow listu**

Create `core/ai/allowlist.py`:

```python
# ========== ALLOW LISTA MODELA ==========
# Ogledalo `visibility.py`, sa suprotnim znacenjem:
#
#   deny lista  (visibility)  kaze STA SE NE NUDI  — sve ostalo radi
#   allow lista (ovaj modul)  kaze STA UOPSTE POSTOJI — sve ostalo ne radi
#
# Postoji zbog provajdera sa prevelikim katalogom (OpenRouter, 300+ modela),
# gde bi deny lista znacila 300 iskljucivanja da bi ostalo pet modela.
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from core.ai.openrouter_catalog import CatalogModel
from core.database import core_database_connection

# Red koji ne oznacava model nego cinjenicu da je prvo punjenje obavljeno.
# Bez njega bi svaki start vracao modele koje je covek izbacio.
SEED_MARKER = "__seeded__"

# Porodice koje prvo punjenje uzima u obzir. Slug-ovi se menjaju, pa se bira
# PRAVILOM nad zivim katalogom, ne spiskom zamrznutim u kodu.
SEED_FAMILIES = ("anthropic/", "openai/", "google/", "deepseek/", "qwen/")

# Besplatne varijante imaju ostra ogranicenja i nisu dobar podrazumevani izbor.
SEED_MIN_PRICE = 0.0

# Model kraceg konteksta nema smisla kao podrazumevani razvojni sagovornik.
SEED_MIN_CONTEXT = 100_000


def seed_selection(models: Sequence[CatalogModel]) -> list[str]:
    """Po jedan najjaci model iz svake poznate porodice.

    „Najjaci" se meri cenom ulaza: u praksi je najskuplji model porodice i
    njen najsposobniji. Gruba mera, ali jedina koju katalog daje.
    """

    najbolji: dict[str, CatalogModel] = {}
    for model in models:
        porodica = next(
            (f for f in SEED_FAMILIES if model.id.startswith(f)), None,
        )
        if porodica is None:
            continue
        if model.price_in_per_mtok <= SEED_MIN_PRICE:
            continue
        if model.context_window < SEED_MIN_CONTEXT:
            continue
        trenutni = najbolji.get(porodica)
        if trenutni is None or model.price_in_per_mtok > trenutni.price_in_per_mtok:
            najbolji[porodica] = model
    return sorted(model.id for model in najbolji.values())


class ModelAllowlist:
    """Modeli koje je covek izricito pustio, po provajderu."""

    def __init__(self, database_path: Path | None = None) -> None:
        # None znaci core.db.
        self._database_path = database_path

    def allowed(self, provider: str) -> set[str]:
        """Dozvoljeni modeli datog provajdera, bez markera."""

        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                "SELECT model FROM core_model_allowlist WHERE provider = ?",
                (provider,),
            ).fetchall()
        return {row["model"] for row in rows if row["model"] != SEED_MARKER}

    def set_allowed(self, provider: str, model: str, allowed: bool) -> None:
        """Pusta ili sklanja jedan model."""

        with core_database_connection(self._database_path) as connection:
            if allowed:
                connection.execute(
                    "INSERT OR IGNORE INTO core_model_allowlist "
                    "(provider, model) VALUES (?, ?)",
                    (provider, model),
                )
                return
            connection.execute(
                "DELETE FROM core_model_allowlist "
                "WHERE provider = ? AND model = ?",
                (provider, model),
            )

    def is_seeded(self, provider: str) -> bool:
        """Da li je prvo punjenje vec obavljeno."""

        with core_database_connection(self._database_path) as connection:
            red = connection.execute(
                "SELECT 1 FROM core_model_allowlist "
                "WHERE provider = ? AND model = ?",
                (provider, SEED_MARKER),
            ).fetchone()
        return red is not None

    def seed(self, provider: str, models: Iterable[str]) -> None:
        """Prvo punjenje. Ne radi nista ako je vec obavljeno."""

        if self.is_seeded(provider):
            return
        for model in models:
            self.set_allowed(provider, model, True)
        self.set_allowed(provider, SEED_MARKER, True)
```

- [ ] **Step 5: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_model_allowlist.py tests/test_model_visibility_scopes.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/integrations/migrations.py core/ai/allowlist.py tests/test_model_allowlist.py
git commit -m "feat(core-ai): allow lista modela, core_ai v3"
```

---

### Task 4: `ChatProvider` za OpenRouter

**Files:**
- Create: `core/ai/providers/openrouter.py`
- Modify: `core/ai/providers/__init__.py`
- Test: `tests/test_openrouter_provider.py`

**Interfaces:**
- Consumes: `OpenRouterCatalog`, `CatalogModel`, `CatalogUnavailable` (Task 2); `ChatMessage`, `ChatResult`, `ModelInfo`, `ProviderUnavailable` (postojeći)
- Produces: `OpenRouterProvider(vault, *, alias=DEFAULT_ALIAS, catalog, client_factory=None, on_catalog=None)` sa `name="openrouter"`, `is_local=False`, `needs_allowlist=True`, `available()`, `models()`, `chat()`

- [ ] **Step 1: Napiši test koji pada**

Create `tests/test_openrouter_provider.py`:

```python
# ========== TESTOVI: ChatProvider za OpenRouter ==========
from __future__ import annotations

import pytest

from core.ai.openrouter_catalog import CatalogModel, CatalogSnapshot, CatalogUnavailable
from core.ai.providers import ChatProvider
from core.ai.providers.base import ChatMessage, ProviderUnavailable
from core.ai.providers.openrouter import OpenRouterProvider


class _FakeVault:
    def __init__(self, kljuc: str | None) -> None:
        self._kljuc = kljuc

    def get(self, alias: str) -> str | None:
        return self._kljuc if alias else None


class _FakeCatalog:
    def __init__(self, modeli=(), greska: Exception | None = None) -> None:
        self._modeli = modeli
        self._greska = greska
        self.pozvan = 0

    def snapshot(self, *, force: bool = False) -> CatalogSnapshot:
        self.pozvan += 1
        if self._greska is not None:
            raise self._greska
        return CatalogSnapshot(models=tuple(self._modeli), fetched_at=0.0,
                               stale=False)


class _FakeUsage:
    def __init__(self, tekst="zdravo", prompt=11, izlaz=7) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = izlaz
        self._tekst = tekst


class _FakePoruka:
    def __init__(self, tekst: str) -> None:
        self.content = tekst


class _FakeIzbor:
    def __init__(self, tekst: str) -> None:
        self.message = _FakePoruka(tekst)


class _FakeOdgovor:
    def __init__(self, tekst: str) -> None:
        self.choices = [_FakeIzbor(tekst)]
        self.usage = _FakeUsage(tekst)


class _FakeCompletions:
    def __init__(self, zapis: dict) -> None:
        self._zapis = zapis

    def create(self, **kwargs):
        self._zapis.update(kwargs)
        return _FakeOdgovor("zdravo")


class _FakeChat:
    def __init__(self, zapis: dict) -> None:
        self.completions = _FakeCompletions(zapis)


class _FakeClient:
    def __init__(self, api_key: str, base_url: str, zapis: dict) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.chat = _FakeChat(zapis)


MODEL = CatalogModel(id="anthropic/claude-sonnet-4.5",
                     label="Anthropic: Claude Sonnet 4.5",
                     context_window=200000, price_in_per_mtok=3.0,
                     price_out_per_mtok=15.0)


def _provajder(kljuc="sk-or-test", modeli=(MODEL,), greska=None, zapis=None,
               on_catalog=None):
    zapis = {} if zapis is None else zapis

    def fabrika(api_key: str, base_url: str):
        return _FakeClient(api_key, base_url, zapis)

    return OpenRouterProvider(
        _FakeVault(kljuc), alias="openrouter",
        catalog=_FakeCatalog(modeli, greska),
        client_factory=fabrika, on_catalog=on_catalog,
    )


def test_zadovoljava_protokol():
    assert isinstance(_provajder(), ChatProvider)


def test_trazi_allow_listu():
    assert _provajder().needs_allowlist is True


def test_bez_kljuca_nije_dostupan():
    assert _provajder(kljuc=None).available() is False


def test_bez_kljuca_modeli_dizu_gresku():
    with pytest.raises(ProviderUnavailable):
        _provajder(kljuc=None).models()


def test_modeli_nose_cenu_i_kontekst_iz_kataloga():
    modeli = _provajder().models()

    assert len(modeli) == 1
    assert modeli[0].id == "anthropic/claude-sonnet-4.5"
    assert modeli[0].provider == "openrouter"
    assert modeli[0].is_local is False
    assert modeli[0].context_window == 200000
    assert modeli[0].price_in_per_mtok == 3.0
    assert modeli[0].price_out_per_mtok == 15.0


def test_pad_kataloga_postaje_provider_unavailable():
    with pytest.raises(ProviderUnavailable):
        _provajder(greska=CatalogUnavailable("mreza")).models()


def test_uspesan_katalog_javlja_kroz_kuku():
    videno: list = []

    _provajder(on_catalog=videno.extend).models()

    assert [m.id for m in videno] == ["anthropic/claude-sonnet-4.5"]


def test_chat_ide_na_openrouter_url_i_broji_tokene():
    zapis: dict = {}
    provajder = _provajder(zapis=zapis)

    rezultat = provajder.chat(
        [ChatMessage(role="user", content="cao")], "openai/gpt-5",
    )

    assert rezultat.text == "zdravo"
    assert rezultat.model == "openai/gpt-5"
    assert rezultat.provider == "openrouter"
    assert rezultat.prompt_tokens == 11
    assert rezultat.output_tokens == 7
    assert zapis["model"] == "openai/gpt-5"
    assert zapis["messages"] == [{"role": "user", "content": "cao"}]


def test_chat_bez_kljuca_dize_gresku():
    with pytest.raises(ProviderUnavailable):
        _provajder(kljuc=None).chat([ChatMessage(role="user", content="cao")],
                                    "openai/gpt-5")
```

- [ ] **Step 2: Pokreni test i potvrdi da pada**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_openrouter_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.ai.providers.openrouter'`

- [ ] **Step 3: Napiši provajdera**

Create `core/ai/providers/openrouter.py`:

```python
# ========== PROVAJDER: OPENROUTER ==========
# Jedan kljuc za modele vise proizvodjaca. OpenRouter je OpenAI-kompatibilan,
# pa ide kroz vec instaliran `openai` SDK sa drugim `base_url` — bez nove
# zavisnosti.
#
# Za razliku od ostalih, ovaj provajder trazi ALLOW listu: katalog ima preko
# 300 modela, pa bi deny lista znacila 300 iskljucivanja da bi ostalo pet.
from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

from core.ai.openrouter_catalog import CatalogModel, OpenRouterCatalog
from core.ai.providers.base import (
    ChatMessage,
    ChatResult,
    ModelInfo,
    ProviderUnavailable,
)
from core.integrations.providers.openrouter import BASE_URL

# Alias pod kojim vault cuva OpenRouter kljuc kad konektor ne postoji.
DEFAULT_ALIAS = "openrouter"

MAX_TOKENS = 16000

# OpenRouter koristi ova zaglavlja za pripisivanje saobracaja.
APP_URL = "https://github.com/core-os"
APP_TITLE = "CORE"

ClientFactory = Callable[[str, str], Any]
AliasResolver = Callable[[], str]
CatalogHook = Callable[[Sequence[CatalogModel]], None]


class OpenRouterProvider:
    """Modeli kroz OpenRouter, jednim kljucem."""

    name = "openrouter"
    is_local = False
    # Katalog je prevelik za deny listu — vidi `core/ai/allowlist.py`.
    needs_allowlist = True

    def __init__(self, vault: Any, *,
                 alias: str | AliasResolver = DEFAULT_ALIAS,
                 catalog: OpenRouterCatalog | None = None,
                 client_factory: ClientFactory | None = None,
                 on_catalog: CatalogHook | None = None) -> None:
        self._vault = vault
        self._alias = alias
        self._catalog = catalog or OpenRouterCatalog()
        self._client_factory = client_factory or self._default_factory
        self._on_catalog = on_catalog

    @staticmethod
    def _default_factory(api_key: str, base_url: str) -> Any:
        import openai

        return openai.OpenAI(api_key=api_key, base_url=base_url)

    # ---------- interno ----------

    def _alias_sada(self) -> str:
        return self._alias() if callable(self._alias) else self._alias

    def _kljuc(self) -> str | None:
        alias = self._alias_sada()
        return self._vault.get(alias) if alias else None

    def _client(self) -> Any:
        kljuc = self._kljuc()
        if not kljuc:
            raise ProviderUnavailable(
                "Nema API kljuca za OpenRouter — unesi ga u podesavanjima.",
            )
        try:
            return self._client_factory(kljuc, BASE_URL)
        except Exception as error:  # noqa: BLE001 — SDK puca na svoj nacin
            raise ProviderUnavailable(str(error)) from error

    # ---------- protokol ----------

    def available(self) -> bool:
        return bool(self._kljuc())

    def models(self) -> list[ModelInfo]:
        # Katalog je javan, ali prikazivati modele koji ne mogu da odgovore
        # znaci ponuditi izbor koji puca pri prvom kliku.
        if not self._kljuc():
            raise ProviderUnavailable(
                "Nema API kljuca za OpenRouter — unesi ga u podesavanjima.",
            )
        try:
            snimak = self._catalog.snapshot()
        except Exception as error:  # noqa: BLE001 — katalog puca na svoj nacin
            raise ProviderUnavailable(str(error)) from error

        if self._on_catalog is not None:
            # Prvo punjenje allow liste — provajder ne zna sta se s tim radi.
            self._on_catalog(snimak.models)

        return [
            ModelInfo(
                id=model.id,
                label=model.label,
                provider=self.name,
                is_local=False,
                context_window=model.context_window,
                price_in_per_mtok=model.price_in_per_mtok,
                price_out_per_mtok=model.price_out_per_mtok,
            )
            for model in snimak.models
        ]

    def chat(self, messages: list[ChatMessage], model: str,
             **options: object) -> ChatResult:
        klijent = self._client()
        started = time.perf_counter()

        try:
            odgovor = klijent.chat.completions.create(
                model=model,
                messages=[{"role": m.role, "content": m.content}
                          for m in messages],
                max_tokens=MAX_TOKENS,
                extra_headers={"HTTP-Referer": APP_URL, "X-Title": APP_TITLE},
            )
        except Exception as error:  # noqa: BLE001
            raise ProviderUnavailable(str(error)) from error

        izbori = getattr(odgovor, "choices", []) or []
        sadrzaj = getattr(izbori[0].message, "content", "") if izbori else ""
        upotreba = getattr(odgovor, "usage", None)

        return ChatResult(
            text=sadrzaj or "",
            model=model,
            provider=self.name,
            prompt_tokens=int(getattr(upotreba, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(upotreba, "completion_tokens", 0) or 0),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
```

- [ ] **Step 4: Izvezi ga**

U `core/ai/providers/__init__.py` dodaj, po uzoru na postojeće:

```python
from core.ai.providers.openrouter import OpenRouterProvider
```

i dopiši `"OpenRouterProvider"` u `__all__`.

- [ ] **Step 5: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_openrouter_provider.py tests/test_chat_providers.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/ai/providers/openrouter.py core/ai/providers/__init__.py tests/test_openrouter_provider.py
git commit -m "feat(core-ai): ChatProvider za OpenRouter kroz openai SDK"
```

---

### Task 5: Jedno mesto koje računa `enabled`

Danas i `routers/core_models.py` i `routers/codium_ai.py` imaju svoju kopiju funkcije `_red`. Allow lista bi bila treća stvar koju obe kopije moraju da znaju — otud premeštaj u jedan modul pre nego što se doda.

**Files:**
- Create: `core/ai/selection.py`
- Test: `tests/test_model_selection.py`

**Interfaces:**
- Consumes: `ModelVisibilityRepository`, `GLOBAL_SCOPE` (postojeći); `ModelAllowlist` (Task 3); `ModelInfo` (postojeći)
- Produces:
  - `Decision(enabled: bool, disabled_globally: bool)`
  - `ModelSelection(visibility, allowlist, allowlist_providers: set[str])` sa `decide_all(models: Sequence[ModelInfo], scope: str) -> list[tuple[ModelInfo, Decision]]`
  - `allowlist_providers(providers: Sequence[object]) -> set[str]`

- [ ] **Step 1: Napiši test koji pada**

Create `tests/test_model_selection.py`:

```python
# ========== TESTOVI: odluka da li se model nudi ==========
from __future__ import annotations

import pytest

from core.ai.allowlist import ModelAllowlist
from core.ai.providers.base import ModelInfo
from core.ai.selection import ModelSelection, allowlist_providers
from core.ai.visibility import GLOBAL_SCOPE, ModelVisibilityRepository
from core.database.runtime import initialize_core_database


class _Obican:
    name = "ollama"


class _SaListom:
    name = "openrouter"
    needs_allowlist = True


@pytest.fixture()
def izbor(tmp_path):
    database = tmp_path / "core_izbor.db"
    initialize_core_database(database)
    return ModelSelection(
        ModelVisibilityRepository(database),
        ModelAllowlist(database),
        {"openrouter"},
    ), ModelVisibilityRepository(database), ModelAllowlist(database)


def _model(provider: str, model_id: str, *, placeholder: bool = False):
    return ModelInfo(id=model_id, label=model_id, provider=provider,
                     is_local=provider == "ollama", is_placeholder=placeholder)


def test_prepoznaje_provajdere_sa_allow_listom():
    assert allowlist_providers([_Obican(), _SaListom()]) == {"openrouter"}


def test_obican_provajder_je_podrazumevano_ukljucen(izbor):
    selection, _, _ = izbor

    odluke = selection.decide_all([_model("ollama", "qwen2.5:7b")], GLOBAL_SCOPE)

    assert odluke[0][1].enabled is True
    assert odluke[0][1].disabled_globally is False


def test_obican_provajder_postuje_deny_listu(izbor):
    selection, vidljivost, _ = izbor
    vidljivost.set_model_enabled("ollama", "qwen2.5:7b", False)

    odluke = selection.decide_all([_model("ollama", "qwen2.5:7b")], GLOBAL_SCOPE)

    assert odluke[0][1].enabled is False


def test_provajder_sa_allow_listom_podrazumevano_nije_ukljucen(izbor):
    selection, _, _ = izbor

    odluke = selection.decide_all([_model("openrouter", "openai/gpt-5")],
                                  GLOBAL_SCOPE)

    assert odluke[0][1].enabled is False


def test_pusten_model_je_ukljucen(izbor):
    selection, _, lista = izbor
    lista.set_allowed("openrouter", "openai/gpt-5", True)

    odluke = selection.decide_all([_model("openrouter", "openai/gpt-5")],
                                  GLOBAL_SCOPE)

    assert odluke[0][1].enabled is True


def test_domen_ne_moze_da_vrati_ono_sto_core_nije_pustio(izbor):
    selection, _, _ = izbor

    odluke = selection.decide_all([_model("openrouter", "openai/gpt-5")],
                                  "codium")

    assert odluke[0][1].enabled is False
    assert odluke[0][1].disabled_globally is True


def test_domen_sme_da_suzi_pusten_model(izbor):
    selection, vidljivost, lista = izbor
    lista.set_allowed("openrouter", "openai/gpt-5", True)
    vidljivost.set_model_enabled("openrouter", "openai/gpt-5", False,
                                 scope="codium")

    odluke = selection.decide_all([_model("openrouter", "openai/gpt-5")],
                                  "codium")

    assert odluke[0][1].enabled is False
    assert odluke[0][1].disabled_globally is False


def test_red_cuvar_nikada_nije_ukljucen(izbor):
    selection, _, _ = izbor

    odluke = selection.decide_all(
        [_model("openrouter", "openrouter:nedostupan", placeholder=True)],
        GLOBAL_SCOPE,
    )

    assert odluke[0][1].enabled is False
    assert odluke[0][1].disabled_globally is False
```

- [ ] **Step 2: Pokreni test i potvrdi da pada**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_model_selection.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.ai.selection'`

- [ ] **Step 3: Napiši modul**

Create `core/ai/selection.py`:

```python
# ========== ODLUKA: DA LI SE MODEL NUDI ==========
# Jedno mesto koje spaja dva pravila vidljivosti, jer ih dva routera
# (`core_models.py` i `codium_ai.py`) racunaju identicno:
#
#   1. allow lista — samo za provajdera koji je trazi (OpenRouter)
#   2. deny lista  — globalna, pa domenska
#
# Setovi se citaju JEDNOM po pozivu (`decide_all`), a ne po modelu: katalog sa
# 300 redova bi inace znacio 600 upita nad bazom po otvaranju izbornika.
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from core.ai.allowlist import ModelAllowlist
from core.ai.providers.base import ModelInfo
from core.ai.visibility import GLOBAL_SCOPE, ModelVisibilityRepository


@dataclass(frozen=True)
class Decision:
    """Sta GUI treba da zna o jednom modelu."""

    enabled: bool
    # Model koji CORE nije pustio; domen ga ne moze vratiti, pa ga
    # podesavanja domena prikazuju zakljucanog i objasnjavaju zasto.
    disabled_globally: bool


def allowlist_providers(providers: Sequence[object]) -> set[str]:
    """Imena provajdera koji traze allow listu umesto deny liste."""

    return {
        str(getattr(p, "name", ""))
        for p in providers
        if getattr(p, "needs_allowlist", False)
    }


class ModelSelection:
    """Racuna `enabled` i `disabled_globally` za spisak modela."""

    def __init__(self, visibility: ModelVisibilityRepository,
                 allowlist: ModelAllowlist,
                 allowlist_provider_names: set[str]) -> None:
        self._visibility = visibility
        self._allowlist = allowlist
        self._sa_listom = allowlist_provider_names

    def decide_all(self, models: Sequence[ModelInfo],
                   scope: str) -> list[tuple[ModelInfo, Decision]]:
        globalno_iskljuceni = self._visibility.disabled_models(GLOBAL_SCOPE)
        u_domenu_iskljuceni = (
            set() if scope == GLOBAL_SCOPE
            else self._visibility.disabled_models(scope)
        )
        pusteni = {
            ime: self._allowlist.allowed(ime) for ime in self._sa_listom
        }

        odluke: list[tuple[ModelInfo, Decision]] = []
        for model in models:
            odluke.append((model, self._jedan(
                model, scope, globalno_iskljuceni, u_domenu_iskljuceni, pusteni,
            )))
        return odluke

    # ---------- interno ----------

    @staticmethod
    def _jedan(model: ModelInfo, scope: str,
               globalno_iskljuceni: set[tuple[str, str]],
               u_domenu_iskljuceni: set[tuple[str, str]],
               pusteni: dict[str, set[str]]) -> Decision:
        # Red-cuvar nije model: ne moze se ni ukljuciti ni iskljuciti.
        if model.is_placeholder:
            return Decision(enabled=False, disabled_globally=False)

        kljuc = (model.provider, model.id)
        if model.provider in pusteni:
            core_dozvoljava = model.id in pusteni[model.provider]
        else:
            core_dozvoljava = kljuc not in globalno_iskljuceni

        if scope == GLOBAL_SCOPE:
            # U globalnom opsegu se odlucuje, pa nema „zakljucano odozgo".
            return Decision(enabled=core_dozvoljava, disabled_globally=False)

        u_domenu = kljuc not in u_domenu_iskljuceni
        return Decision(enabled=core_dozvoljava and u_domenu,
                        disabled_globally=not core_dozvoljava)
```

- [ ] **Step 4: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_model_selection.py -v`
Expected: PASS (9 testova)

- [ ] **Step 5: Commit**

```bash
git add core/ai/selection.py tests/test_model_selection.py
git commit -m "feat(core-ai): jedno mesto koje racuna vidljivost modela"
```

---

### Task 6: Routeri koriste `ModelSelection`, dobijaju `only_enabled`, i pišu u allow listu

**Files:**
- Modify: `apps/api/schemas/core_models.py`
- Modify: `apps/api/routers/core_models.py`
- Modify: `apps/api/routers/codium_ai.py`
- Modify: `apps/api/core_ai_runtime.py`
- Test: `tests/test_api_core_models.py`, `tests/test_api_codium_ai.py`

**Interfaces:**
- Consumes: `ModelSelection`, `allowlist_providers`, `Decision` (Task 5); `ModelAllowlist` (Task 3)
- Produces: `core_ai_runtime.get_allowlist() -> ModelAllowlist`; obe rute `/models` primaju `?only_enabled=`; `ModelInfoSchema` dobija polje `needs_allowlist: bool`

- [ ] **Step 1: Napiši testove koji padaju**

Dopuni `tests/test_api_core_models.py` — dodaj na kraj fajla:

```python
class _FakeOpenRouter:
    name = "openrouter"
    is_local = False
    needs_allowlist = True

    def available(self) -> bool:
        return True

    def models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="openai/gpt-5", label="OpenAI: GPT-5",
                      provider="openrouter", is_local=False,
                      price_in_per_mtok=1.25, price_out_per_mtok=10.0),
        ]

    def chat(self, messages, model, **options) -> ChatResult:
        raise NotImplementedError


@pytest.fixture
def allowlist(tmp_path) -> ModelAllowlist:
    database = tmp_path / "core_modeli_allow.db"
    initialize_core_database(database)
    return ModelAllowlist(database)


@pytest.fixture
def client_or(visibility, allowlist) -> Iterator[TestClient]:
    app.dependency_overrides[core_models.get_providers] = (
        lambda: [_FakeProvider(), _FakeOpenRouter()]
    )
    app.dependency_overrides[core_models.get_visibility] = lambda: visibility
    app.dependency_overrides[core_models.get_allowlist] = lambda: allowlist
    tc = TestClient(app)
    try:
        yield tc
    finally:
        tc.close()
        app.dependency_overrides.clear()


def test_openrouter_model_podrazumevano_nije_ukljucen(client_or):
    odgovor = client_or.get("/api/v1/core/ai/models")

    redovi = {m["id"]: m for m in odgovor.json()["models"]}
    assert redovi["openai/gpt-5"]["enabled"] is False
    assert redovi["qwen2.5:7b"]["enabled"] is True


def test_ukljucivanje_openrouter_modela_pise_u_allow_listu(client_or, allowlist):
    client_or.put("/api/v1/core/ai/models/enabled", json={
        "provider": "openrouter", "model": "openai/gpt-5",
        "enabled": True, "scope": "global",
    })

    assert allowlist.allowed("openrouter") == {"openai/gpt-5"}


def test_iskljucivanje_openrouter_modela_brise_iz_allow_liste(client_or, allowlist):
    allowlist.set_allowed("openrouter", "openai/gpt-5", True)

    client_or.put("/api/v1/core/ai/models/enabled", json={
        "provider": "openrouter", "model": "openai/gpt-5",
        "enabled": False, "scope": "global",
    })

    assert allowlist.allowed("openrouter") == set()


def test_only_enabled_izbacuje_ono_sto_se_ne_nudi(client_or):
    odgovor = client_or.get("/api/v1/core/ai/models?only_enabled=true")

    ids = [m["id"] for m in odgovor.json()["models"]]
    assert "openai/gpt-5" not in ids
    assert "qwen2.5:7b" in ids


def test_odgovor_kaze_koji_provajder_trazi_allow_listu(client_or):
    redovi = {m["id"]: m for m in client_or.get("/api/v1/core/ai/models").json()["models"]}

    assert redovi["openai/gpt-5"]["needs_allowlist"] is True
    assert redovi["qwen2.5:7b"]["needs_allowlist"] is False
```

Dopuni uvoze na vrhu istog fajla:

```python
from core.ai.allowlist import ModelAllowlist
```

- [ ] **Step 2: Pokreni testove i potvrdi da padaju**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_api_core_models.py -v`
Expected: FAIL — `AttributeError: module 'apps.api.routers.core_models' has no attribute 'get_allowlist'`

- [ ] **Step 3: Dodaj polje u šemu**

U `apps/api/schemas/core_models.py`, u `ModelInfoSchema`:

```python
    # Provajder cija se lista vodi ALLOW listom (OpenRouter, 300+ modela).
    # GUI ga po ovome izdvaja u zasebnu sekciju sa pretragom, umesto da mu
    # 300 redova ubaci u obican izbornik.
    needs_allowlist: bool = False
```

i u `from_domain`:

```python
    @classmethod
    def from_domain(cls, item: ModelInfo, enabled: bool = True,
                    disabled_globally: bool = False,
                    needs_allowlist: bool = False) -> "ModelInfoSchema":
```

sa `needs_allowlist=needs_allowlist,` u telu poziva `cls(...)`.

- [ ] **Step 4: Dodaj allow listu u runtime**

U `apps/api/core_ai_runtime.py`, uz `_visibility`:

```python
from core.ai.allowlist import ModelAllowlist

_allowlist = ModelAllowlist()


def get_allowlist() -> ModelAllowlist:
    return _allowlist
```

- [ ] **Step 5: Prevedi `core_models.py` na `ModelSelection`**

U `apps/api/routers/core_models.py` zameni uvoze i obe funkcije:

```python
from core.ai.allowlist import ModelAllowlist
from core.ai.selection import ModelSelection, allowlist_providers


def get_allowlist() -> ModelAllowlist:
    return core_ai_runtime.get_allowlist()


@router.get("", response_model=ModelsResponse)
def list_models(
    scope: str = GLOBAL_SCOPE,
    only_enabled: bool = False,
    providers: list = Depends(get_providers),
    visibility: ModelVisibilityRepository = Depends(get_visibility),
    allowlist: ModelAllowlist = Depends(get_allowlist),
) -> ModelsResponse:
    """Svi modeli, sa odlukom za trazeni opseg.

    Isključeni ostaju u odgovoru — podešavanja moraju da ih vide da bi se
    mogli vratiti. `only_enabled=true` je za chat izbornik: katalogu sa 300+
    modela ne treba da putuje ceo da bi se prikazalo pet.
    """

    sa_listom = allowlist_providers(providers)
    selection = ModelSelection(visibility, allowlist, sa_listom)
    odluke = selection.decide_all(ModelCatalog(providers).list(), scope)

    modeli = [
        ModelInfoSchema.from_domain(
            model, enabled=odluka.enabled,
            disabled_globally=odluka.disabled_globally,
            needs_allowlist=model.provider in sa_listom,
        )
        for model, odluka in odluke
        # Red-cuvar prezivi `only_enabled`: on je poruka zasto modeli
        # nedostaju, a ne model koji se nudi.
        if not only_enabled or odluka.enabled or model.is_placeholder
    ]
    return ModelsResponse(models=modeli)


@router.put("/enabled", response_model=ModelEnabledResponse)
def set_model_enabled(
    payload: ModelEnabledRequest,
    providers: list = Depends(get_providers),
    visibility: ModelVisibilityRepository = Depends(get_visibility),
    allowlist: ModelAllowlist = Depends(get_allowlist),
) -> ModelEnabledResponse:
    """Uključuje ili isključuje model u traženom opsegu.

    Opseg odlučuje u koju listu ide upis: allow lista je globalna, pa se u
    opsegu `global` za provajdera koji je traži piše u nju, a u opsegu domena
    i dalje radi deny lista. Tako domen sme da suzi izbor, ali ne i da pusti
    model koji CORE nije pustio.
    """

    if (payload.scope == GLOBAL_SCOPE
            and payload.provider in allowlist_providers(providers)):
        allowlist.set_allowed(payload.provider, payload.model, payload.enabled)
    else:
        visibility.set_model_enabled(payload.provider, payload.model,
                                     payload.enabled, scope=payload.scope)
    return ModelEnabledResponse(provider=payload.provider, model=payload.model,
                                enabled=payload.enabled, scope=payload.scope)
```

- [ ] **Step 6: Prevedi `codium_ai.py` na isti modul**

U `apps/api/routers/codium_ai.py` dodaj uvoze:

```python
from core.ai.allowlist import ModelAllowlist
from core.ai.selection import ModelSelection, allowlist_providers
```

dodaj zavisnost:

```python
def get_allowlist() -> ModelAllowlist:
    return core_ai_runtime.get_allowlist()
```

(uvoz `core_ai_runtime` već postoji u tom fajlu kroz `codium_assistant_runtime`; ako ga nema, dodaj `from apps.api import core_ai_runtime`.)

i zameni telo `list_models`:

```python
@router.get("/models", response_model=ModelsResponse)
def list_models(
    only_enabled: bool = False,
    providers: list = Depends(get_providers),
    repository: CodiumRepository = Depends(get_repository),
    globalna: ModelVisibilityRepository = Depends(get_global_visibility),
    allowlist: ModelAllowlist = Depends(get_allowlist),
) -> ModelsResponse:
    """Modeli iz svih provajdera. Nedostupan provajder daje red sa razlogom.

    Isključeni modeli OSTAJU u odgovoru — podešavanja moraju da ih vide da bi
    se mogli vratiti. `only_enabled=true` je za chat izbornik.

    Vidljivost ima tri sloja i sva tri računa `ModelSelection`: allow lista za
    provajdera koji je traži, pa globalna deny lista, pa domenska.
    """

    sa_listom = allowlist_providers(providers)
    selection = ModelSelection(globalna, allowlist, sa_listom)
    odluke = selection.decide_all(ModelCatalog(providers).list(), _OPSEG)

    modeli = [
        ModelInfoSchema.from_domain(
            model, enabled=odluka.enabled,
            disabled_globally=odluka.disabled_globally,
            needs_allowlist=model.provider in sa_listom,
        )
        for model, odluka in odluke
        if not only_enabled or odluka.enabled or model.is_placeholder
    ]
    return ModelsResponse(models=modeli)
```

- [ ] **Step 7: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_api_core_models.py tests/test_api_codium_ai.py tests/test_model_visibility_scopes.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add apps/api/schemas/core_models.py apps/api/routers/core_models.py apps/api/routers/codium_ai.py apps/api/core_ai_runtime.py tests/test_api_core_models.py
git commit -m "feat(api): allow lista i only_enabled u katalogu modela"
```

---

### Task 7: Cene iz kataloga kao drugi izvor

**Files:**
- Modify: `core/ai/pricing.py`
- Modify: `apps/api/core_ai_runtime.py`
- Test: `tests/test_ai_usage.py`

**Interfaces:**
- Produces: `set_extra_price_source(fn: Callable[[str], tuple[float, float] | None] | None) -> None`
- `price_for` i `cost_usd` zadržavaju postojeći potpis

- [ ] **Step 1: Napiši testove koji padaju**

Dopuni `tests/test_ai_usage.py` — dodaj na kraj fajla:

```python
from core.ai.pricing import cost_usd, price_for, set_extra_price_source


def test_rucna_tabela_ima_prednost_nad_dodatnim_izvorom():
    set_extra_price_source(lambda model_id: (99.0, 99.0))
    try:
        assert price_for("claude-opus-5") == (5.0, 25.0)
    finally:
        set_extra_price_source(None)


def test_dodatni_izvor_daje_cenu_nepoznatom_modelu():
    set_extra_price_source(
        lambda model_id: (1.25, 10.0) if model_id == "openai/gpt-5" else None,
    )
    try:
        assert price_for("openai/gpt-5") == (1.25, 10.0)
        assert cost_usd("openai/gpt-5", 1_000_000, 1_000_000) == 11.25
    finally:
        set_extra_price_source(None)


def test_bez_dodatnog_izvora_nepoznat_model_kosta_nula():
    set_extra_price_source(None)

    assert price_for("openai/gpt-5") is None
    assert cost_usd("openai/gpt-5", 1_000_000, 1_000_000) == 0.0
```

- [ ] **Step 2: Pokreni testove i potvrdi da padaju**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ai_usage.py -v`
Expected: FAIL — `ImportError: cannot import name 'set_extra_price_source'`

- [ ] **Step 3: Dodaj drugi izvor u `pricing.py`**

U `core/ai/pricing.py`, ispod `_UVODNE`:

```python
# Drugi izvor cena, za provajdera cija ih lista donosi sama (OpenRouter).
# Rucna tabela ostaje PRVA: za direktan Anthropic ili OpenAI poziv ona je
# tacnija od OpenRouter-ove marze.
#
# Modul-nivo namerno: `usage.py` i ostali zovu `price_for` kao slobodnu
# funkciju, pa bi provlacenje izvora kroz sve pozivaoce bilo veca izmena od
# same funkcije. Postavlja se jednom, u `core_ai_runtime`.
_DODATNI_IZVOR: "Callable[[str], tuple[float, float] | None] | None" = None


def set_extra_price_source(
    izvor: "Callable[[str], tuple[float, float] | None] | None",
) -> None:
    """Postavlja (ili sklanja) drugi izvor cena."""

    global _DODATNI_IZVOR
    _DODATNI_IZVOR = izvor
```

Dodaj uvoz na vrh fajla:

```python
from collections.abc import Callable
```

i zameni telo `price_for`:

```python
def price_for(model_id: str, *,
              na_dan: date | None = None) -> tuple[float, float] | None:
    """Cena ulaza i izlaza po milionu tokena, ili None za nepoznat model."""

    if model_id not in _CENE:
        # Nepoznat rucnoj tabeli — pitaj katalog, ako ga ima.
        return None if _DODATNI_IZVOR is None else _DODATNI_IZVOR(model_id)

    uvodna = _UVODNE.get(model_id)
    if uvodna is not None:
        vrednost, vazi_do = uvodna
        if (na_dan or date.today()) <= vazi_do:
            return vrednost

    return _CENE[model_id]
```

- [ ] **Step 4: Poveži katalog kao izvor u runtime-u**

U `apps/api/core_ai_runtime.py`, posle definicije OpenRouter provajdera (Task 8 dodaje samu definiciju; ako je još nema, ovaj korak ide zajedno sa njom):

```python
from core.ai.pricing import set_extra_price_source

_openrouter_catalog = OpenRouterCatalog()


def _cena_iz_kataloga(model_id: str) -> tuple[float, float] | None:
    """Cena OpenRouter modela iz keširanog kataloga.

    Katalog koji ne odgovara znaci „nepoznata cena", ne pad: trosak se tada
    upisuje kao nula, a poziv se svejedno evidentira.
    """

    try:
        snimak = _openrouter_catalog.snapshot()
    except Exception:  # noqa: BLE001 — katalog puca na svoj nacin
        return None
    for model in snimak.models:
        if model.id == model_id:
            return (model.price_in_per_mtok, model.price_out_per_mtok)
    return None


set_extra_price_source(_cena_iz_kataloga)
```

- [ ] **Step 5: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ai_usage.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/ai/pricing.py apps/api/core_ai_runtime.py tests/test_ai_usage.py
git commit -m "feat(core-ai): cene OpenRouter modela iz kataloga"
```

---

### Task 8: OpenRouter provajder u runtime-u, sa punjenjem allow liste

**Files:**
- Modify: `apps/api/core_ai_runtime.py`
- Test: `tests/test_core_ai_runtime_openrouter.py`

**Interfaces:**
- Consumes: `OpenRouterProvider` (Task 4), `OpenRouterCatalog` (Task 2), `ModelAllowlist` + `seed_selection` (Task 3)
- Produces: `get_chat_providers()` vraća četiri provajdera; `seed_allowlist(models)` kuka

- [ ] **Step 1: Napiši test koji pada**

Create `tests/test_core_ai_runtime_openrouter.py`:

```python
# ========== TESTOVI: OpenRouter u runtime-u ==========
from __future__ import annotations

from apps.api import core_ai_runtime


def test_openrouter_je_medju_chat_provajderima():
    imena = [p.name for p in core_ai_runtime.get_chat_providers()]

    assert "openrouter" in imena


def test_openrouter_trazi_allow_listu():
    provajder = next(p for p in core_ai_runtime.get_chat_providers()
                     if p.name == "openrouter")

    assert getattr(provajder, "needs_allowlist", False) is True


def test_punjenje_allow_liste_bira_po_pravilu(tmp_path, monkeypatch):
    from core.ai.allowlist import ModelAllowlist
    from core.ai.openrouter_catalog import CatalogModel
    from core.database.runtime import initialize_core_database

    database = tmp_path / "core_seed.db"
    initialize_core_database(database)
    lista = ModelAllowlist(database)
    monkeypatch.setattr(core_ai_runtime, "_allowlist", lista)

    core_ai_runtime.seed_allowlist([
        CatalogModel(id="openai/gpt-5", label="GPT-5", context_window=400000,
                     price_in_per_mtok=1.25, price_out_per_mtok=10.0),
        CatalogModel(id="neko/nesto", label="Nesto", context_window=200000,
                     price_in_per_mtok=9.0, price_out_per_mtok=9.0),
    ])

    assert lista.allowed("openrouter") == {"openai/gpt-5"}
```

- [ ] **Step 2: Pokreni test i potvrdi da pada**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_core_ai_runtime_openrouter.py -v`
Expected: FAIL — `AssertionError: 'openrouter' not in [...]` i `AttributeError: seed_allowlist`

- [ ] **Step 3: Poveži provajdera**

U `apps/api/core_ai_runtime.py`, uz ostale uvoze provajdera:

```python
from collections.abc import Sequence

from core.ai.allowlist import ModelAllowlist, seed_selection
from core.ai.openrouter_catalog import CatalogModel, OpenRouterCatalog
from core.ai.providers import (
    AnthropicProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
)
```

posle `_openai_provider`:

```python
def seed_allowlist(models: Sequence[CatalogModel]) -> None:
    """Prvo punjenje allow liste, pri prvom uspesnom dohvatu kataloga.

    Prazna allow lista znaci prazan OpenRouter u chatu — tacno, ali
    neupotrebljivo na prvom startu. Izbor ide PRAVILOM nad zivim katalogom
    (`seed_selection`), ne spiskom slug-ova zamrznutim u kodu, jer se slug-ovi
    menjaju. Marker u samoj listi cuva da izbacen model ne vaskrsne.
    """

    try:
        _allowlist.seed("openrouter", seed_selection(models))
    except Exception:  # noqa: BLE001 — baza jos ne postoji na prvom startu
        return


_openrouter_provider = OpenRouterProvider(
    _vault,
    alias=lambda: _alias_za(ConnectorKind.OPENROUTER),
    catalog=_openrouter_catalog,
    on_catalog=seed_allowlist,
)
```

i dopuni spisak:

```python
def get_chat_providers() -> list:
    """Provajderi modela za katalog i ruter — isti za sve domene."""

    return [_ollama_provider, _anthropic_provider, _openai_provider,
            _openrouter_provider]
```

**Napomena o redosledu u fajlu:** `_openrouter_catalog` i `set_extra_price_source` iz Task 7 moraju stajati **pre** `_openrouter_provider`, jer ga on koristi.

- [ ] **Step 4: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_core_ai_runtime_openrouter.py tests/test_api_core_models.py tests/test_api_codium_ai.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/core_ai_runtime.py tests/test_core_ai_runtime_openrouter.py
git commit -m "feat(api): OpenRouter provajder u runtime-u, prvo punjenje allow liste"
```

---

### Task 9: Kapija `ai.call_online` u petlji agenta

Agent troši novac na online poziv, pa mu treba odobrenje. Provera ide u `loop.py`, gde agent i bira model — **ne** u `core/ai`, jer ruter modela ne sme da zna za CODIUM kapiju.

**Files:**
- Modify: `core/domains/codium/agents/loop.py`
- Modify: `core/domains/codium/migrations.py`
- Modify: `apps/api/codium_agents_runtime.py`
- Test: `tests/test_codium_agent_online_gate.py`

**Interfaces:**
- Consumes: `ScopeGate`, `ApprovalRepository`, `RunRepository` (postojeći)
- Produces: `AgentLoop(..., resolve_model: Callable[[], tuple[str, str, bool]] | None = None)`; molba sa payload-om `{"kind": "model", "provider": …, "model": …}`

- [ ] **Step 1: Napiši testove koji padaju**

Create `tests/test_codium_agent_online_gate.py`:

```python
# ========== TESTOVI: odobrenje za online poziv agenta ==========
from __future__ import annotations

import json

import pytest

from core.domains.codium.agents import AgentRepository, AgentRun, RunRepository
from core.domains.codium.agents.loop import AgentLoop
from core.domains.codium.agents.tools import build_tools
from core.domains.codium.audit import (
    ApprovalRepository,
    AuditRepository,
    ScopeRuleRepository,
)
from core.domains.codium.explorer import CodiumExplorer
from core.domains.codium.runtime import (
    initialize_codium_database,
    initialize_codium_ops_database,
)
from core.security.scope_gate import ScopeGate, ScopeRule


@pytest.fixture
def okruzenje(tmp_path):
    poslovna = tmp_path / "codium.db"
    ops = tmp_path / "codium_ops.db"
    initialize_codium_database(poslovna)
    initialize_codium_ops_database(ops)

    koren = tmp_path / "projekat"
    koren.mkdir()

    return {
        "poslovna": poslovna,
        "koren": koren,
        "runs": RunRepository(poslovna),
        "agenti": AgentRepository(poslovna),
        "pravila": ScopeRuleRepository(poslovna),
        "odobrenja": ApprovalRepository(poslovna),
        "dnevnik": AuditRepository(ops),
    }


def _petlja(okruzenje, *, resolve_model, odgovori=("Gotov sam.",)) -> AgentLoop:
    iterator = iter(odgovori)
    return AgentLoop(
        runs=okruzenje["runs"],
        tools=build_tools(CodiumExplorer(okruzenje["koren"]), None, None),
        gate=ScopeGate(lambda: okruzenje["pravila"].list()),
        approvals=okruzenje["odobrenja"],
        audit=okruzenje["dnevnik"],
        chat=lambda poruke: next(iterator, "Gotov sam."),
        resolve_model=resolve_model,
    )


def _pokreni(okruzenje, *, resolve_model, odgovori=("Gotov sam.",)):
    agent = okruzenje["agenti"].by_slug("architect")
    run = okruzenje["runs"].start(AgentRun(agent_id=agent.id, task="uradi"))
    petlja = _petlja(okruzenje, resolve_model=resolve_model, odgovori=odgovori)
    return petlja, agent, petlja.run(agent, run)


def _trazi_odobrenje(okruzenje) -> None:
    okruzenje["pravila"].add(ScopeRule(
        actor="agent:*", action="ai.call_online", target="*",
        verdict="needs_approval", note="online poziv trosi novac",
    ))


def test_lokalni_model_ne_pita_kapiju(okruzenje):
    _trazi_odobrenje(okruzenje)

    _, _, run = _pokreni(
        okruzenje, resolve_model=lambda: ("ollama", "qwen2.5:7b", True),
    )

    assert run.status == "done"


def test_online_model_pauzira_posao_i_trazi_odobrenje(okruzenje):
    _trazi_odobrenje(okruzenje)

    _, _, run = _pokreni(
        okruzenje, resolve_model=lambda: ("openrouter", "openai/gpt-5", False),
    )

    assert run.status == "waiting_approval"
    assert run.pending_approval_id is not None

    molba = okruzenje["odobrenja"].get(run.pending_approval_id)
    assert molba.action == "ai.call_online"
    assert molba.target == "openrouter/openai/gpt-5"
    assert json.loads(molba.payload) == {
        "kind": "model", "provider": "openrouter", "model": "openai/gpt-5",
    }


def test_pauza_ne_ulazi_u_transkript_kao_poruka(okruzenje):
    """Korak pauze je `note`, ne `tool_result`.

    `tool_result` bi u `_poruke` postao poruka korisnika, pa bi model dobio
    „Ceka odobrenje..." kao da mu je to neko rekao.
    """

    _trazi_odobrenje(okruzenje)

    _, _, run = _pokreni(
        okruzenje, resolve_model=lambda: ("openrouter", "openai/gpt-5", False),
    )

    assert [s.kind for s in okruzenje["runs"].steps(run.id)] == ["note"]


def test_odobren_online_poziv_nastavlja_posao(okruzenje):
    _trazi_odobrenje(okruzenje)
    petlja, agent, pauziran = _pokreni(
        okruzenje, resolve_model=lambda: ("openrouter", "openai/gpt-5", False),
    )

    okruzenje["odobrenja"].decide(pauziran.pending_approval_id, "approved",
                                  "moze")
    run = petlja.resume(agent, pauziran)

    assert run.status == "done"
    assert run.result == "Gotov sam."


def test_odobrenje_ostavlja_trag_u_dnevniku(okruzenje):
    _trazi_odobrenje(okruzenje)
    petlja, agent, pauziran = _pokreni(
        okruzenje, resolve_model=lambda: ("openrouter", "openai/gpt-5", False),
    )

    okruzenje["odobrenja"].decide(pauziran.pending_approval_id, "approved", "")
    petlja.resume(agent, pauziran)

    akcije = [(u.action, u.verdict) for u in okruzenje["dnevnik"].query()]
    assert ("ai.call_online", "needs_approval") in akcije
    assert ("ai.call_online", "approved") in akcije


def test_odbijen_online_poziv_prekida_posao(okruzenje):
    _trazi_odobrenje(okruzenje)
    petlja, agent, pauziran = _pokreni(
        okruzenje, resolve_model=lambda: ("openrouter", "openai/gpt-5", False),
    )

    okruzenje["odobrenja"].decide(pauziran.pending_approval_id, "rejected",
                                  "preskupo")
    run = petlja.resume(agent, pauziran)

    assert run.status == "cancelled"
    assert "preskupo" in run.result


def test_deny_pravilo_obara_posao_bez_molbe(okruzenje):
    okruzenje["pravila"].add(ScopeRule(
        actor="agent:*", action="ai.call_online", target="*",
        verdict="deny", note="bez interneta",
    ))

    _, _, run = _pokreni(
        okruzenje, resolve_model=lambda: ("openrouter", "openai/gpt-5", False),
    )

    assert run.status == "failed"
    assert "bez interneta" in run.result
    assert okruzenje["odobrenja"].pending() == []


def test_bez_resolve_model_petlja_radi_kao_pre(okruzenje):
    _trazi_odobrenje(okruzenje)

    _, _, run = _pokreni(okruzenje, resolve_model=None)

    assert run.status == "done"
```

- [ ] **Step 2: Pokreni testove i potvrdi da padaju**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_online_gate.py -v`
Expected: FAIL — `TypeError: AgentLoop.__init__() got an unexpected keyword argument 'resolve_model'`

- [ ] **Step 3: Dodaj proveru u petlju**

U `core/domains/codium/agents/loop.py`:

Dopuni tip i konstruktor:

```python
# Ko odgovara: (provajder, model, da li je lokalan). Ubrizgano, jer petlja ne
# sme da zna kako se model bira — to je posao rutera.
ModelResolver = Callable[[], tuple[str, str, bool]]

# Akcija kapije za online poziv. Lokalni model ne pita nista — ne trosi novac.
ONLINE_ACTION = "ai.call_online"
```

```python
    def __init__(self, *, runs: RunRepository, tools: ToolRegistry,
                 gate: ScopeGate, approvals: ApprovalRepository,
                 audit: AuditRepository, chat: Chat,
                 resolve_model: ModelResolver | None = None) -> None:
        self._runs = runs
        self._tools = tools
        self._gate = gate
        self._approvals = approvals
        self._audit = audit
        self._chat = chat
        self._resolve_model = resolve_model
```

Zameni `run`:

```python
    def run(self, agent: Agent, run: AgentRun) -> AgentRun:
        prepreka = self._proveri_online(agent, run)
        if prepreka is not None:
            return prepreka
        return self._vrti(agent, run, koraka=0, poslednja_greska="",
                          ponovljeno=0)
```

Dodaj metodu (uz ostale pomoćne, ispod `_zatrazi_odobrenje`):

```python
    def _proveri_online(self, agent: Agent, run: AgentRun) -> AgentRun | None:
        """Pita kapiju sme li ovaj posao da koristi online model.

        Pita se JEDNOM po poslu, ne po koraku: covek odobrava da ovaj posao
        radi na placenom modelu, a ne svaku pojedinacnu poruku. Bez
        `resolve_model` (stariji pozivaoci i testovi) provera se preskace.
        """

        if self._resolve_model is None:
            return None
        try:
            provajder, model, lokalan = self._resolve_model()
        except Exception:  # noqa: BLE001 — ruter puca na svoj nacin
            # Nepoznat model se ponasa kao lokalan: kapija nema sta da meri,
            # a poziv ce svakako pasti na svom mestu, sa svojom porukom.
            return None
        if lokalan:
            return None

        cilj = f"{provajder}/{model}"
        odluka = self._gate.check(actor=f"agent:{agent.slug}",
                                  action=ONLINE_ACTION, target=cilj)

        if odluka.verdict == ALLOW:
            return None

        if odluka.verdict == NEEDS_APPROVAL:
            molba = self._approvals.request(Approval(
                actor=f"agent:{agent.slug}", action=ONLINE_ACTION, target=cilj,
                payload=json.dumps({"kind": "model", "provider": provajder,
                                    "model": model}, ensure_ascii=False),
            ))
            self._audit.record(AuditEntry(
                actor=f"agent:{agent.slug}", action=ONLINE_ACTION,
                verdict=NEEDS_APPROVAL, target=cilj, outcome="pending",
                detail=f"molba {molba.id}", project_id=run.project_id,
            ))
            # Vrsta koraka je `note`, ne `tool_result`: pauza pred prvi poziv
            # nije rezultat alata i ne sme da udje u transkript kao poruka
            # korisnika (`_poruke` je namerno ne prepoznaje).
            self._korak(run.id, "note", "",
                        f"Ceka odobrenje coveka za online model {cilj} "
                        f"(molba {molba.id}).")
            pauziran = self._runs.wait_for_approval(run.id, molba.id)
            return pauziran if pauziran is not None else self._runs.get(run.id)

        # `deny` i svaki nepoznat verdikt obaraju posao. Tiho placanje onoga
        # sto kapija nije izricito dozvolila je rupa.
        self._audit.record(AuditEntry(
            actor=f"agent:{agent.slug}", action=ONLINE_ACTION,
            verdict=odluka.verdict, target=cilj, outcome="blocked",
            detail=odluka.reason, project_id=run.project_id,
        ))
        self._korak(run.id, "note", "",
                    f"Online model odbijen: {odluka.reason}")
        return self._runs.finish(
            run.id, status="failed",
            result=f"Kapija je odbila online model `{cilj}`: {odluka.reason}",
            steps_used=self._broj_poteza(run.id),
        )
```

Dodaj granu u `resume`, odmah posle reda `payload = self._procitaj_payload(molba.payload)`:

```python
        if payload.get("kind") == "model":
            # Molba za online model nema alat da se izvrsi — odobrenje samo
            # pusta posao da krene.
            cilj = f"{payload.get('provider', '')}/{payload.get('model', '')}"
            if molba.status != "approved":
                razlog = molba.note or "bez obrazlozenja"
                self._korak(run.id, "note", "",
                            f"Online model odbijen: {razlog}")
                return self._runs.finish(
                    run.id, status="cancelled",
                    result=f"Covek je odbio online model `{cilj}`: {razlog}",
                    steps_used=self._broj_poteza(run.id),
                )
            self._audit.record(AuditEntry(
                actor=f"agent:{agent.slug}", action=ONLINE_ACTION,
                verdict="approved", target=cilj, outcome="ok",
                detail=f"odobreno molbom {molba.id}",
                project_id=run.project_id,
            ))
            nastavljen = self._runs.resume(run.id)
            if nastavljen is None:
                return self._runs.get(run.id)
            return self._vrti(agent, nastavljen,
                              koraka=self._broj_poteza(run.id),
                              poslednja_greska="", ponovljeno=0)
```

- [ ] **Step 4: Dodaj podrazumevano pravilo (migracija codium v9)**

U `core/domains/codium/migrations.py`, posle `CODIUM_MIGRATION_V8`:

```python
# ---------- v9: agent za online model trazi odobrenje ----------

CODIUM_MIGRATION_V9 = DatabaseMigration(
    scope="codium",
    version=9,
    name="agent_online_needs_approval",
    statements=(
        # Podrazumevani glagol `call_online` je u `ScopeGate` namerno `allow`
        # (gate ne sme da obori postojeci chat u trenutku spajanja). Za agenta
        # to ne vazi: on trosi novac bez coveka za tastaturom, pa mu treba
        # izricito pravilo. Covek i dalje prolazi — `human` zaobilazi kapiju.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'ai.call_online', '*', 'needs_approval',
                'online poziv trosi novac — covek odobrava')
        """,
    ),
)
```

i dopuni torku `CODIUM_MIGRATIONS` sa `CODIUM_MIGRATION_V9`.

- [ ] **Step 5: Poveži resolver u runtime-u**

U `apps/api/codium_agents_runtime.py`, u funkciji koja pravi `AgentLoop` (traži `AgentLoop(` u fajlu), dodaj argument:

```python
    def resolve_model() -> tuple[str, str, bool]:
        """Cime bi ovaj posao odgovorio, i da li je to lokalan model."""

        resolved = router.resolve(
            project_id=run.project_id, persona=f"agent:{agent.slug}",
            override_provider=agent.provider or None,
            override_model=agent.model or None,
        )
        provajder = next(
            (p for p in codium_assistant_runtime.get_providers()
             if p.name == resolved.provider_name), None,
        )
        lokalan = bool(getattr(provajder, "is_local", False))
        return (resolved.provider_name, resolved.model, lokalan)
```

i predaj ga: `AgentLoop(..., resolve_model=resolve_model)`.

- [ ] **Step 6: Pokreni testove**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_codium_agent_online_gate.py tests/test_codium_agent_loop.py tests/test_api_codium_agents.py tests/test_codium_approvals.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add core/domains/codium/agents/loop.py core/domains/codium/migrations.py apps/api/codium_agents_runtime.py tests/test_codium_agent_online_gate.py
git commit -m "feat(codium): agent trazi odobrenje za online model, codium v9"
```

---

### Task 10: GUI — molba za online model se čita

Bez ovoga red odobrenja pokazuje sirov JSON, pa čovek odobrava nešto što ne razume.

**Files:**
- Modify: `apps/gui/src/features/codium/approvals.ts`
- Test: `apps/gui/src/features/codium/approvals.test.ts`

**Interfaces:**
- Produces: `describePayload` prepoznaje `{"kind":"model", …}`

- [ ] **Step 1: Napiši test koji pada**

Dodaj u `apps/gui/src/features/codium/approvals.test.ts`:

```typescript
describe("molba za online model", () => {
  it("prikazuje provajdera i model umesto sirovog JSON-a", () => {
    const linije = describePayload(
      JSON.stringify({ kind: "model", provider: "openrouter", model: "openai/gpt-5" }),
    );

    expect(linije).toEqual([
      { label: "Provajder", value: "openrouter" },
      { label: "Model", value: "openai/gpt-5" },
    ]);
  });

  it("nepotpuna molba za model ne pada", () => {
    const linije = describePayload(JSON.stringify({ kind: "model" }));

    expect(linije).toEqual([
      { label: "Provajder", value: "—" },
      { label: "Model", value: "—" },
    ]);
  });
});
```

- [ ] **Step 2: Pokreni test i potvrdi da pada**

Run (iz `apps/gui`): `npx vitest run src/features/codium/approvals.test.ts`
Expected: FAIL — vraća `[{ label: "Sadržaj", value: "..." }]`

- [ ] **Step 3: Dopuni `describePayload`**

U `apps/gui/src/features/codium/approvals.ts`, odmah posle parsiranja `podaci`:

```typescript
  // Molba za online model nema alat ni argumente — nosi samo čime bi se
  // odgovorilo. Bez ove grane bi se prikazala kao sirov JSON.
  if (podaci.kind === "model") {
    const tekst = (vrednost: unknown): string =>
      typeof vrednost === "string" && vrednost !== "" ? vrednost : "—";
    return [
      { label: "Provajder", value: tekst(podaci.provider) },
      { label: "Model", value: tekst(podaci.model) },
    ];
  }
```

- [ ] **Step 4: Pokreni testove**

Run (iz `apps/gui`): `npx vitest run src/features/codium/approvals.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/gui/src/features/codium/approvals.ts apps/gui/src/features/codium/approvals.test.ts
git commit -m "feat(gui): molba za online model se cita u redu odobrenja"
```

---

### Task 11: GUI — sekcija „OpenRouter katalog" u podešavanjima

**Files:**
- Create: `apps/gui/src/features/settings/openrouterCatalog.ts`
- Create: `apps/gui/src/features/settings/openrouterCatalog.test.ts`
- Modify: `apps/gui/src/features/settings/ModelsPanel.tsx`
- Modify: `apps/gui/src/styles/settings.css`

**Interfaces:**
- Consumes: `CatalogModel` tip iz `features/codium/modelPicker.ts`
- Produces: `searchCatalog(models, query, limit) -> { shown, hidden }`, `formatPrice(model) -> string`

- [ ] **Step 1: Napiši test koji pada**

Create `apps/gui/src/features/settings/openrouterCatalog.test.ts`:

```typescript
import { describe, expect, it } from "vitest";

import { formatPrice, searchCatalog } from "./openrouterCatalog";
import type { CatalogModel } from "../codium/modelPicker";

function model(id: string, cena = 1.25, izlaz = 10): CatalogModel {
  return {
    id,
    label: id,
    provider: "openrouter",
    is_local: false,
    context_window: 200000,
    price_in_per_mtok: cena,
    price_out_per_mtok: izlaz,
    size_gb: null,
    oversized: false,
    available: true,
    unavailable_reason: "",
    enabled: false,
    is_placeholder: false,
    disabled_globally: false,
    needs_allowlist: true,
  };
}

describe("pretraga OpenRouter kataloga", () => {
  it("prazan upit vraca sve do granice", () => {
    const rezultat = searchCatalog([model("a"), model("b")], "", 50);

    expect(rezultat.shown.map((m) => m.id)).toEqual(["a", "b"]);
    expect(rezultat.hidden).toBe(0);
  });

  it("trazi po id-u bez obzira na velicinu slova", () => {
    const rezultat = searchCatalog(
      [model("openai/gpt-5"), model("anthropic/claude-opus-5")], "CLAUDE", 50,
    );

    expect(rezultat.shown.map((m) => m.id)).toEqual(["anthropic/claude-opus-5"]);
  });

  it("odseca na granicu i javlja koliko je ostalo", () => {
    const modeli = [model("a"), model("b"), model("c")];

    const rezultat = searchCatalog(modeli, "", 2);

    expect(rezultat.shown).toHaveLength(2);
    expect(rezultat.hidden).toBe(1);
  });

  it("ukljuceni modeli idu prvi", () => {
    const iskljucen = model("a");
    const ukljucen = { ...model("b"), enabled: true };

    const rezultat = searchCatalog([iskljucen, ukljucen], "", 50);

    expect(rezultat.shown.map((m) => m.id)).toEqual(["b", "a"]);
  });

  it("cena se pise po milionu tokena", () => {
    expect(formatPrice(model("a", 1.25, 10))).toBe("$1.25 / $10.00 po Mtok");
  });

  it("besplatan model to i kaze", () => {
    expect(formatPrice(model("a", 0, 0))).toBe("besplatno");
  });
});
```

- [ ] **Step 2: Pokreni test i potvrdi da pada**

Run (iz `apps/gui`): `npx vitest run src/features/settings/openrouterCatalog.test.ts`
Expected: FAIL — `Failed to resolve import "./openrouterCatalog"`

- [ ] **Step 3: Napiši čist modul**

Create `apps/gui/src/features/settings/openrouterCatalog.ts`:

```typescript
// ==========          OPENROUTER KATALOG (čist modul)          ==========
// Pretraga i odsecanje kataloga od 300+ modela. Bez React-a i bez fetch-a, da
// se logika testira bez renderovanja — isti obrazac kao `modelPicker.ts`.

import type { CatalogModel } from "../codium/modelPicker";

export type CatalogSearch = {
  /** Redovi koji se prikazuju. */
  shown: CatalogModel[];
  /** Koliko pogodaka je odsečeno granicom. */
  hidden: number;
};

/** Koliko redova ide u DOM. 300 redova nije spisak nego kazna. */
export const DEFAULT_LIMIT = 50;

/**
 * Pretraga po id-u i nazivu, sa uključenima na vrhu.
 *
 * Uključeni idu prvi jer su ono što korisnik zapravo koristi — ostatak
 * kataloga je tu da bi se nešto novo našlo, ne da bi se svaki put prelistalo.
 */
export function searchCatalog(models: CatalogModel[], query: string,
                              limit: number = DEFAULT_LIMIT): CatalogSearch {
  const igla = query.trim().toLowerCase();
  const pogodjeni = igla === ""
    ? [...models]
    : models.filter(
        (m) =>
          m.id.toLowerCase().includes(igla) ||
          m.label.toLowerCase().includes(igla),
      );

  pogodjeni.sort((a, b) => {
    if (a.enabled !== b.enabled) {
      return a.enabled ? -1 : 1;
    }
    return a.id.localeCompare(b.id);
  });

  return {
    shown: pogodjeni.slice(0, limit),
    hidden: Math.max(0, pogodjeni.length - limit),
  };
}

/** Cena po milionu tokena, ulaz pa izlaz. */
export function formatPrice(model: CatalogModel): string {
  if (model.price_in_per_mtok === 0 && model.price_out_per_mtok === 0) {
    return "besplatno";
  }
  const ulaz = model.price_in_per_mtok.toFixed(2);
  const izlaz = model.price_out_per_mtok.toFixed(2);
  return `$${ulaz} / $${izlaz} po Mtok`;
}
```

- [ ] **Step 4: Pokreni test**

Run (iz `apps/gui`): `npx vitest run src/features/settings/openrouterCatalog.test.ts`
Expected: PASS (6 testova)

- [ ] **Step 5: Ožiči sekciju u `ModelsPanel.tsx`**

Provajder sa allow listom se izdvaja iz obične liste — inače bi 300 redova
palo u grupu „Online". Dodaj uvoze:

```typescript
import { DEFAULT_LIMIT, formatPrice, searchCatalog } from "./openrouterCatalog";
```

Ispod `const [opseg, setOpseg] = useState("global");` dodaj stanje pretrage:

```typescript
  const [upit, setUpit] = useState("");
```

Iznad `return (` dodaj podelu kataloga:

```typescript
  // Provajder sa allow listom ima 300+ modela i ide u svoju sekciju sa
  // pretragom; ostali idu u obicne grupe „Lokalno" / „Online".
  const obicni = modeli.filter((m) => !m.needs_allowlist);
  const izKataloga = modeli.filter((m) => m.needs_allowlist);
  const pretraga = searchCatalog(izKataloga, upit, DEFAULT_LIMIT);
  const cuvar = izKataloga.find((m) => m.is_placeholder);
```

Zameni `groupModels(modeli)` sa `groupModels(obicni)`, a `modeli.length === 0`
uslov sa `obicni.length === 0 && izKataloga.length === 0`.

Ispod bloka sa grupama, pre zatvaranja `</section>`, dodaj sekciju:

```tsx
      {izKataloga.length > 0 && (
        <div className="cset-group">
          <h3 className="cset-group-title">OpenRouter katalog</h3>
          <p className="cset-panel-sub">
            Ovaj provajder ima preko 300 modela, pa se u chatu nudi samo ono
            što ovde uključiš.
          </p>

          {cuvar !== undefined ? (
            // Bez ključa katalog ne postoji — red-čuvar nosi razlog.
            <p className="cset-empty">{cuvar.unavailable_reason}</p>
          ) : (
            <>
              <input
                className="set-orc-search"
                aria-label="Pretraga OpenRouter kataloga"
                placeholder="Pretraga po nazivu modela…"
                value={upit}
                onChange={(event) => setUpit(event.target.value)}
              />

              <ul className="cset-list">
                {pretraga.shown.map((model) => (
                  <li
                    key={`${model.provider}:${model.id}`}
                    className="cset-item set-orc-row"
                  >
                    <div className="cset-item-main">
                      <span className="cset-item-title">{model.id}</span>
                      <span className="cset-item-meta set-orc-meta">
                        {formatPrice(model)} ·{" "}
                        {Math.round(model.context_window / 1000)}k konteksta
                      </span>
                    </div>

                    {model.disabled_globally ? (
                      // Allow lista je globalna: u opsegu domena prekidac bi
                      // pisao u DENY listu, a model bi i dalje bio nepusten.
                      // Obecanje koje ruter ne ispunjava.
                      <span className="cset-item-note">
                        pušta se u CORE podešavanjima
                      </span>
                    ) : (
                      <button
                        type="button"
                        role="switch"
                        aria-checked={model.enabled}
                        aria-label={`Model ${model.id} u chatu`}
                        className={`cset-switch ${model.enabled ? "on" : ""}`}
                        onClick={() => void prebaci(model)}
                      >
                        <span className="cset-switch-knob" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>

              {pretraga.hidden > 0 && (
                <p className="set-orc-more">
                  Još {pretraga.hidden} modela — suzi pretragu.
                </p>
              )}
              {pretraga.shown.length === 0 && (
                <p className="cset-empty">Nijedan model se ne poklapa.</p>
              )}
            </>
          )}
        </div>
      )}
```

Stilovi u `apps/gui/src/styles/settings.css` — bez novih boja, jer su crvena,
žuta i zelena rezervisane za značenje, a ovo je spisak:

```css
/* ---------- OpenRouter katalog (300+ modela, pa pretraga) ---------- */

.set-orc-search {
  width: 100%;
  margin: 8px 0 12px;
  padding: 8px 10px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  color: #e2e8f0;
  background: rgba(8, 13, 27, 0.62);
  font: inherit;
}

.set-orc-search:focus {
  border-color: rgba(var(--domain-accent-rgb, 125, 211, 252), 0.45);
  outline: none;
}

/* Id modela je dugačak (`anthropic/claude-…`) i ne sme da razvuče red. */
.set-orc-row .cset-item-title {
  overflow: hidden;
  word-break: break-all;
}

.set-orc-meta {
  font-variant-numeric: tabular-nums;
}

.set-orc-more {
  margin: 10px 0 0;
  color: #8b95a8;
  font-size: 0.78rem;
}
```

- [ ] **Step 6: Prebaci chat izbornik na `only_enabled`**

U `apps/gui/src/services/codiumApi.ts` zameni:

```typescript
/** Katalog modela (lokalni + online) dostupnih asistentu.
 *
 * `onlyEnabled` je za chat izbornik: katalog sa 300+ modela ne treba da
 * putuje ceo da bi se prikazalo pet. Podešavanja ga zovu bez toga, jer
 * moraju da vide i isključene da bi mogli da ih vrate.
 */
export function listAssistantModels(
  onlyEnabled = false,
): Promise<{ models: CatalogModel[] }> {
  const upit = onlyEnabled ? "?only_enabled=true" : "";
  return getJson<{ models: CatalogModel[] }>(
    `/api/v1/codium/ai/models${upit}`,
  );
}
```

U `apps/gui/src/features/codium/useAssistantChat.ts:72` zameni poziv:

```typescript
      const { models: list } = await listAssistantModels(true);
```

U `apps/gui/src/features/codium/modelPicker.ts` dopuni tip `CatalogModel`:

```typescript
  // Provajder čija se lista vodi allow listom (OpenRouter). Podešavanja ga
  // izdvajaju u zasebnu sekciju sa pretragom.
  needs_allowlist: boolean;
```

i u `apps/gui/src/services/coreApi.ts` dodaj isti parametar `listCoreModels`-u:

```typescript
/** Svi modeli sa odlukom za traženi opseg. */
export function listCoreModels(
  scope = "global",
  onlyEnabled = false,
): Promise<{ models: CatalogModel[] }> {
  const upit = onlyEnabled ? "&only_enabled=true" : "";
  return getJson<{ models: CatalogModel[] }>(
    `/api/v1/core/ai/models?scope=${encodeURIComponent(scope)}${upit}`,
  );
}
```

**Napomena:** dodavanje obaveznog polja u `CatalogModel` obara svaki test koji
gradi taj objekat ručno. Pokreni `npx vitest run` i dopuni `needs_allowlist:
false` gde prevodilac prijavi — to je posao ovog koraka, ne sledećeg.

- [ ] **Step 7: Pokreni proveru tipova i sve GUI testove**

Run (iz `apps/gui`): `npx tsc -b tsconfig.app.json`
Expected: samo dve zatečene greške iz „Global Constraints"

Run (iz `apps/gui`): `npx vitest run`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add apps/gui/src/features/settings/openrouterCatalog.ts apps/gui/src/features/settings/openrouterCatalog.test.ts apps/gui/src/features/settings/ModelsPanel.tsx apps/gui/src/styles/settings.css apps/gui/src/services/codiumApi.ts apps/gui/src/services/coreApi.ts apps/gui/src/features/codium/modelPicker.ts apps/gui/src/features/codium/useAssistantChat.ts
git commit -m "feat(gui): sekcija OpenRouter kataloga u podesavanjima modela"
```

---

### Task 12: Provera uživo i ispravka podrazumevanog modela

Testovi dokazuju da naš kod radi. Ovaj korak dokazuje da OpenRouter radi.

**Files:**
- Modify: `config/models_config.json`
- Modify: `.ai/izgradnja/codium/00-INDEX.md`

- [ ] **Step 1: Pokreni ceo paket testova**

Run: `./.venv/Scripts/python.exe -m pytest`
Expected: PASS, bez ijednog pada

Run (iz `apps/gui`): `npx vitest run` i `npx tsc -b tsconfig.app.json`
Expected: PASS; tsc samo dve zatečene greške

- [ ] **Step 2: Zatraži od korisnika da unese ključ**

Ključ se **ne unosi umesto korisnika.** Zamoli ga da ga sam nalepi u
**Podešavanja → API ključevi → OpenRouter**, pa da javi kad je sačuvan.

- [ ] **Step 3: Prođi kroz proveru iz spec-a, tačku po tačku**

1. Konektor sačuvan, proba konekcije prolazi.
2. Katalog stigao; drugi otvor ne poziva mrežu (proveri vreme izmene
   `data/cache/openrouter_models.json`).
3. Allow lista se napunila sama; pogledaj šta je izabrala.
4. Model odgovara u chatu.
5. Potrošnja upisana: `SELECT provider, model, prompt_tokens, output_tokens,
   cost_usd FROM codium_ai_usage ORDER BY id DESC LIMIT 3;` nad
   `codium_ops.db` — trošak mora biti veći od nule.
6. Isključi model u podešavanjima; nestaje iz chat izbornika, a u
   podešavanjima ostaje i može da se vrati.
7. Postavi agentu online model i pokreni posao; posao staje na
   „Čeka odobrenje", a red odobrenja pokazuje provajdera i model (ne JSON).
8. Ako je unet i Anthropic ključ, isti prolaz za njega — time se zatvara AI-2.

- [ ] **Step 4: Ispravi podrazumevani model**

`config/models_config.json` danas ima `"developer_model": "anthropic/claude-3.5-sonnet"` — slug koji više ne stoji. Zameni ga slug-om iz **živog kataloga** (onim koji je allow lista izabrala za `anthropic/`), i ostavi `provider` i `endpoint` kakvi jesu.

- [ ] **Step 5: Upiši status faze**

U `.ai/izgradnja/codium/00-INDEX.md`, u tabeli enterprise trake:

- red `AI-3` → `**zavrseno**`, datum današnji,
- red `AI-2` → `**zavrseno**` ako je i Anthropic prošao proveru; inače ostaje kako jeste, uz kratku napomenu šta još čeka.

- [ ] **Step 6: Commit**

```bash
git add config/models_config.json .ai/izgradnja/codium/00-INDEX.md
git commit -m "chore(codium): AI-3 potvrdjen uzivo, tacan podrazumevani model"
```

---

## Napomena o ključu

Ključ je u razgovoru poslat kao čist tekst i time zapisan u transkript na disku. Posle provere ga treba poništiti na openrouter.ai i napraviti nov. Nova vrednost ide isključivo kroz **Podešavanja → API ključevi**; nijedan korak ovog plana ne upisuje ključ u fajl, u bazu, ni u poruku greške.
