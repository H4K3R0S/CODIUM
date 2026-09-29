---
id: codium-d6179b67-2026-08-24-codium-faza1-lokalni-modeli-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: 'CODIUM Faza 1 — Lokalni modeli: plan implementacije'
summary: '> **Za agentske radnike:** OBAVEZNA POD-VEŠTINA: koristi'
keywords:
- codium
- faza
- lokalni
- modeli
- implementacije
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-24-codium-faza1-lokalni-modeli.md
edges:
- type: references
  target: core-abe7bfd0-2026-08-24-codium-ai-provajderi-design-md
  weight: 0.3
---

# CODIUM Faza 1 — Lokalni modeli: plan implementacije

> **Za agentske radnike:** OBAVEZNA POD-VEŠTINA: koristi
> `superpowers:subagent-driven-development` (preporučeno) ili
> `superpowers:executing-plans` da odradiš plan zadatak po zadatak. Koraci
> koriste `- [ ]` sintaksu za praćenje.

**Cilj:** AI chat okvir u CODIUM-u dobija izbor lokalnog modela — lista se puni
iz Ollama, izbor se pamti po projektu i personi.

**Arhitektura:** Nov sloj `core/ai/providers/` sa protokolom `ChatProvider` iza
kog stoji `OllamaProvider` (omotač nad postojećim `OllamaClient`). `ModelCatalog`
spaja izvore modela, `ModelRouter` bira model po redosledu override → zapamćeno →
podrazumevano. `CodiumAssistant` prestaje da zove Ollama direktno i ide kroz
ruter.

**Tehnologije:** Python 3.14, FastAPI, SQLite, pytest; React + TypeScript,
Vitest.

**Spec:** [`docs/superpowers/specs/2026-08-24-codium-ai-provajderi-design.md`](../specs/2026-08-24-codium-ai-provajderi-design.md)

## Globalna ograničenja

- **Nema novih zavisnosti u ovoj fazi.** Ni Python, ni npm. `keyring` i
  `anthropic` dolaze u Fazi 2.
- **`core/ai/core_router.py` se ne dira.** To je klasifikator namere, ne ruter
  modela.
- **`core/ai/vram_guard.py` se ne dira.** To je mutex za jedan GPU, ne provera
  veličine modela.
- **`OllamaClient.generate()` se ne dira.** Koriste ga `CoreRouter` i FILMIUM
  `CuratorService`. Nove metode se dodaju pored njega.
- **`POST /api/v1/codium/ai/ask` bez polja `model` mora da se ponaša tačno kao
  pre.** F9 ne sme da regresira.
- Testovi se pokreću kroz venv: `./.venv/Scripts/python.exe -m pytest`, ne kroz
  sistemski python.
- Komentari i poruke u kodu na srpskom, po obrascu postojećih fajlova
  (`# ========== NASLOV ==========`).
- Budžet VRAM-a je 8 GB (jedan GPU). Model veći od toga se **označava**, nikada
  ne odbija.

---

## Struktura fajlova

| Fajl | Odgovornost |
|---|---|
| `core/ai/providers/__init__.py` | reeksport javnih imena sloja |
| `core/ai/providers/base.py` | tipovi (`ChatMessage`, `ModelInfo`, `ChatResult`) i protokol `ChatProvider` |
| `core/ai/providers/ollama.py` | `OllamaProvider` — jedini provajder u ovoj fazi |
| `core/ai/ollama_client.py` | *(izmena)* dodaje `tags()` i `chat()` |
| `core/ai/catalog.py` | `ModelCatalog` — spaja izvore modela |
| `core/ai/model_router.py` | `ModelRouter` — bira model; ne zna za HTTP ni za bazu |
| `core/domains/codium/models.py` | *(izmena)* `ModelPref` dataclass |
| `core/domains/codium/migrations.py` | *(izmena)* migracija v3 |
| `core/domains/codium/repository.py` | *(izmena)* čitanje i upis postavke modela |
| `core/domains/codium/assistant/assistant_service.py` | *(izmena)* ide kroz ruter umesto direktno na Ollama |
| `apps/api/codium_assistant_runtime.py` | *(izmena)* sastavlja provajdere, ruter i asistenta |
| `apps/api/schemas/codium_ai.py` | *(izmena)* šeme za modele i postavke |
| `apps/api/routers/codium_ai.py` | *(izmena)* tri nove rute |
| `apps/gui/src/features/codium/modelPicker.ts` | čist modul: grupisanje i sortiranje kataloga |
| `apps/gui/src/features/codium/AiAssistant.tsx` | *(izmena)* dropdown modela |
| `apps/gui/src/services/codiumApi.ts` | *(izmena)* pozivi novih ruta |

---

### Task 1: Protokol provajdera i zajednički tipovi

**Fajlovi:**
- Create: `core/ai/providers/__init__.py`
- Create: `core/ai/providers/base.py`
- Test: `tests/test_chat_providers.py`

**Interfejsi:**
- Consumes: ništa.
- Produces: `ChatMessage(role, content)`, `ModelInfo(...)`,
  `ChatResult(text, model, provider, prompt_tokens, output_tokens, duration_ms)`,
  `ProviderUnavailable`, `ChatProvider` protokol. Svaki naredni zadatak koristi
  tačno ova imena.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_chat_providers.py`:

```python
# ========== TESTOVI: sloj provajdera modela ==========
from __future__ import annotations

from core.ai.providers import (
    ChatMessage,
    ChatProvider,
    ChatResult,
    ModelInfo,
    ProviderUnavailable,
)


class _FakeProvider:
    name = "fake"
    is_local = True

    def available(self) -> bool:
        return True

    def models(self) -> list[ModelInfo]:
        return [ModelInfo(id="m1", label="M1", provider="fake", is_local=True)]

    def chat(self, messages, model, **options) -> ChatResult:
        return ChatResult(text="zdravo", model=model, provider="fake")


def test_fake_provider_zadovoljava_protokol():
    assert isinstance(_FakeProvider(), ChatProvider)


def test_model_info_ima_podrazumevane_vrednosti():
    info = ModelInfo(id="m1", label="M1", provider="fake", is_local=True)
    assert info.available is True
    assert info.unavailable_reason == ""
    assert info.size_gb is None
    assert info.oversized is False
    assert info.price_in_per_mtok == 0.0


def test_chat_result_ima_nulte_tokene_po_podrazumevanom():
    result = ChatResult(text="a", model="m1", provider="fake")
    assert result.prompt_tokens == 0
    assert result.output_tokens == 0
    assert result.duration_ms == 0


def test_chat_message_nosi_ulogu_i_sadrzaj():
    message = ChatMessage(role="user", content="pitanje")
    assert (message.role, message.content) == ("user", "pitanje")


def test_provider_unavailable_je_runtime_error():
    assert issubclass(ProviderUnavailable, RuntimeError)
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_chat_providers.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: No module named 'core.ai.providers'`.

- [ ] **Korak 3: Napiši `core/ai/providers/base.py`**

```python
# ========== PROTOKOL PROVAJDERA MODELA ==========
# Jedan ulaz za sve modele: lokalne (Ollama) i online (kasnije faze). Tipovi su
# naši, ne SDK-ovi, jer sloj apstrahuje više provajdera; konverzija u oblik koji
# pojedini SDK očekuje dešava se unutar tog provajdera i nigde drugde.
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ProviderUnavailable(RuntimeError):
    """Provajder ne odgovara (servis ugašen, mreža, ključ nedostaje)."""


# ========== TIPOVI ==========

@dataclass(frozen=True)
class ChatMessage:
    """Jedna poruka razgovora. `role` je 'system', 'user' ili 'assistant'."""

    role: str
    content: str


@dataclass(frozen=True)
class ModelInfo:
    """Opis jednog modela za prikaz u izborniku."""

    id: str
    label: str
    provider: str
    is_local: bool
    context_window: int = 0
    # Cena po milionu tokena; nula za lokalne modele.
    price_in_per_mtok: float = 0.0
    price_out_per_mtok: float = 0.0
    # Veličina na disku u GB (Ollama); približna mera potrebe za VRAM-om.
    size_gb: float | None = None
    # Veći od budžeta VRAM-a — sme da se izabere, ali nosi upozorenje.
    oversized: bool = False
    available: bool = True
    unavailable_reason: str = ""


@dataclass(frozen=True)
class ChatResult:
    """Odgovor modela sa merenjima poziva."""

    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


# ========== PROTOKOL ==========

@runtime_checkable
class ChatProvider(Protocol):
    """Ugovor koji svaki provajder modela ispunjava."""

    name: str
    is_local: bool

    def available(self) -> bool:
        """Da li provajder trenutno odgovara."""

    def models(self) -> list[ModelInfo]:
        """Modeli koje provajder nudi. Diže ProviderUnavailable ako ne može."""

    def chat(self, messages: list[ChatMessage], model: str,
             **options: object) -> ChatResult:
        """Jedan ne-stream poziv modela."""
```

- [ ] **Korak 4: Napiši `core/ai/providers/__init__.py`**

```python
# ========== SLOJ PROVAJDERA MODELA ==========
from core.ai.providers.base import (
    ChatMessage,
    ChatProvider,
    ChatResult,
    ModelInfo,
    ProviderUnavailable,
)

__all__ = [
    "ChatMessage",
    "ChatProvider",
    "ChatResult",
    "ModelInfo",
    "ProviderUnavailable",
]
```

- [ ] **Korak 5: Pokreni test i potvrdi da prolazi**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_chat_providers.py -v
```

Očekivano: 5 passed.

- [ ] **Korak 6: Commit**

```bash
git add core/ai/providers tests/test_chat_providers.py
git commit -m "feat(core-ai): protokol ChatProvider i zajednicki tipovi"
```

---

### Task 2: `OllamaClient` dobija `tags()` i `chat()`

**Fajlovi:**
- Modify: `core/ai/ollama_client.py`
- Test: `tests/test_ollama_client.py`

**Interfejsi:**
- Consumes: ništa iz Task 1.
- Produces: `OllamaClient.tags() -> list[dict]`,
  `OllamaClient.chat(model, messages, *, system=None) -> dict`, i novi ctor
  argument `get_transport`. Task 3 zove obe metode.

`generate()` ostaje netaknut — koriste ga `CoreRouter` i FILMIUM `CuratorService`.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_ollama_client.py`:

```python
# ========== TESTOVI: Ollama klijent (tags + chat) ==========
from __future__ import annotations

import json

import pytest

from core.ai.ollama_client import OllamaClient, OllamaUnavailable


def _client(*, get_body: str = "{}", post_body: str = "{}"):
    def get_transport(url: str, timeout: float) -> str:
        get_transport.url = url
        return get_body

    def post_transport(url: str, body: bytes, timeout: float) -> str:
        post_transport.url = url
        post_transport.payload = json.loads(body.decode("utf-8"))
        return post_body

    client = OllamaClient(
        endpoint="http://localhost:11434",
        transport=post_transport,
        get_transport=get_transport,
    )
    return client, get_transport, post_transport


def test_tags_vraca_listu_modela():
    body = json.dumps({"models": [{"model": "qwen2.5:7b", "size": 4_700_000_000}]})
    client, get_transport, _ = _client(get_body=body)

    models = client.tags()

    assert get_transport.url == "http://localhost:11434/api/tags"
    assert models[0]["model"] == "qwen2.5:7b"


def test_tags_bez_kljuca_models_vraca_prazno():
    client, _, _ = _client(get_body=json.dumps({"greska": "nema"}))
    assert client.tags() == []


def test_tags_na_neispravan_json_die_ollama_unavailable():
    client, _, _ = _client(get_body="nije json")
    with pytest.raises(OllamaUnavailable):
        client.tags()


def test_chat_salje_poruke_na_api_chat():
    body = json.dumps({
        "message": {"role": "assistant", "content": "Zdravo."},
        "prompt_eval_count": 12,
        "eval_count": 5,
    })
    client, _, post_transport = _client(post_body=body)

    data = client.chat("qwen2.5:7b", [{"role": "user", "content": "Cao"}])

    assert post_transport.url == "http://localhost:11434/api/chat"
    assert post_transport.payload["stream"] is False
    assert post_transport.payload["messages"] == [{"role": "user", "content": "Cao"}]
    assert data["message"]["content"] == "Zdravo."
    assert data["prompt_eval_count"] == 12


def test_chat_stavlja_system_na_pocetak_poruka():
    client, _, post_transport = _client(
        post_body=json.dumps({"message": {"content": "ok"}}),
    )

    client.chat("m", [{"role": "user", "content": "a"}], system="Ti si CORE.")

    assert post_transport.payload["messages"][0] == {
        "role": "system", "content": "Ti si CORE.",
    }


def test_chat_na_neispravan_json_die_ollama_unavailable():
    client, _, _ = _client(post_body="{{{")
    with pytest.raises(OllamaUnavailable):
        client.chat("m", [{"role": "user", "content": "a"}])
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_ollama_client.py -v
```

Očekivano: FAIL sa `TypeError: OllamaClient.__init__() got an unexpected keyword argument 'get_transport'`.

- [ ] **Korak 3: Dopuni `core/ai/ollama_client.py`**

Ispod postojeće `Transport` deklaracije dodaj tip i podrazumevani GET transport:

```python
# GET transport: (url, timeout) -> odgovor kao tekst.
GetTransport = Callable[[str, float], str]


def _default_get_transport(url: str, timeout: float) -> str:
    try:
        with urlopen(url, timeout=timeout) as response:  # noqa: S310 — lokalni host
            return response.read().decode("utf-8")
    except (URLError, OSError) as error:
        raise OllamaUnavailable(str(error)) from error
```

U `__init__` dodaj argument (postojeći pozivi rade nepromenjeno jer je opcion):

```python
    def __init__(self, endpoint: str = "http://localhost:11434",
                 transport: Transport | None = None,
                 timeout: float = 60.0,
                 get_transport: GetTransport | None = None) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._transport = transport or _default_transport
        self._get_transport = get_transport or _default_get_transport
        self._timeout = timeout
```

Na kraj klase dodaj dve metode:

```python
    def tags(self) -> list[dict]:
        """Lokalno instalirani modeli (`GET /api/tags`)."""

        raw = self._get_transport(f"{self._endpoint}/api/tags", self._timeout)
        data = self._decode(raw)
        models = data.get("models", [])
        return models if isinstance(models, list) else []

    def chat(self, model: str, messages: list[dict], *,
             system: str | None = None) -> dict:
        """Ne-stream poziv `/api/chat`. Vraća ceo dekodiran odgovor.

        Za razliku od `generate`, ovaj put nosi listu poruka i u odgovoru
        `prompt_eval_count` / `eval_count` — brojanje tokena bez dodatnog posla.
        """

        payload_messages = list(messages)
        if system is not None:
            payload_messages.insert(0, {"role": "system", "content": system})

        raw = self._transport(
            f"{self._endpoint}/api/chat",
            json.dumps({
                "model": model,
                "messages": payload_messages,
                "stream": False,
            }).encode("utf-8"),
            self._timeout,
        )
        return self._decode(raw)

    @staticmethod
    def _decode(raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise OllamaUnavailable(f"Neispravan odgovor Ollama: {error}") from error
        if not isinstance(data, dict):
            raise OllamaUnavailable("Ollama nije vratio JSON objekat.")
        return data
```

- [ ] **Korak 4: Pokreni testove i potvrdi da prolaze**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_ollama_client.py tests/test_api_core_ai.py -v
```

Očekivano: 6 novih passed, postojeći `test_api_core_ai.py` i dalje passed.

- [ ] **Korak 5: Commit**

```bash
git add core/ai/ollama_client.py tests/test_ollama_client.py
git commit -m "feat(core-ai): OllamaClient dobija tags() i chat() uz netaknut generate()"
```

---

### Task 3: `OllamaProvider`

**Fajlovi:**
- Create: `core/ai/providers/ollama.py`
- Modify: `core/ai/providers/__init__.py`
- Test: `tests/test_chat_providers.py` (dopuna)

**Interfejsi:**
- Consumes: `ChatMessage`, `ChatResult`, `ModelInfo`, `ProviderUnavailable`
  (Task 1); `OllamaClient.tags()`, `OllamaClient.chat()` (Task 2).
- Produces: `OllamaProvider(client)` sa `name = "ollama"`, `is_local = True`, i
  konstanta `VRAM_BUDGET_GB = 8.0`. Task 4 i Task 6 ga koriste.

- [ ] **Korak 1: Dopiši testove koji padaju**

Na kraj `tests/test_chat_providers.py` dodaj:

```python
# ---------- OllamaProvider ----------

import json  # noqa: E402

from core.ai.ollama_client import OllamaClient  # noqa: E402
from core.ai.providers.ollama import VRAM_BUDGET_GB, OllamaProvider  # noqa: E402


def _ollama(*, get_body: str = "{}", post_body: str = "{}") -> OllamaProvider:
    client = OllamaClient(
        transport=lambda url, body, timeout: post_body,
        get_transport=lambda url, timeout: get_body,
    )
    return OllamaProvider(client)


def test_ollama_provider_mapira_tags_u_model_info():
    body = json.dumps({"models": [
        {"model": "qwen2.5:7b", "size": 4_700_000_000},
    ]})

    info = _ollama(get_body=body).models()[0]

    assert info.id == "qwen2.5:7b"
    assert info.provider == "ollama"
    assert info.is_local is True
    assert info.size_gb == 4.7
    assert info.oversized is False
    assert info.price_in_per_mtok == 0.0


def test_ollama_provider_oznacava_model_veci_od_budzeta():
    body = json.dumps({"models": [
        {"model": "veliki:70b", "size": 40_000_000_000},
    ]})

    info = _ollama(get_body=body).models()[0]

    assert info.size_gb > VRAM_BUDGET_GB
    assert info.oversized is True
    # Oznaka, ne zabrana — model ostaje dostupan za izbor.
    assert info.available is True


def test_ollama_provider_bez_servisa_die_provider_unavailable():
    def pukni(url, timeout):
        raise OllamaUnavailable("veza odbijena")

    provider = OllamaProvider(OllamaClient(get_transport=pukni))

    assert provider.available() is False
    with pytest.raises(ProviderUnavailable):
        provider.models()


def test_ollama_provider_chat_cita_tekst_i_tokene():
    body = json.dumps({
        "message": {"role": "assistant", "content": "  Odgovor.  "},
        "prompt_eval_count": 20,
        "eval_count": 7,
    })

    result = _ollama(post_body=body).chat(
        [ChatMessage(role="user", content="pitanje")], "qwen2.5:7b",
    )

    assert result.text == "  Odgovor.  "
    assert result.model == "qwen2.5:7b"
    assert result.provider == "ollama"
    assert result.prompt_tokens == 20
    assert result.output_tokens == 7
    assert result.duration_ms >= 0
```

Na vrh fajla dodaj uvoze koje ovi testovi traže:

```python
import pytest

from core.ai.ollama_client import OllamaUnavailable
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_chat_providers.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: No module named 'core.ai.providers.ollama'`.

- [ ] **Korak 3: Napiši `core/ai/providers/ollama.py`**

```python
# ========== PROVAJDER: OLLAMA (lokalni modeli) ==========
# Omotač nad postojećim OllamaClient-om. Ne zamenjuje ga — `generate()` i dalje
# koriste CoreRouter i FILMIUM Kurator; ovde se koriste `tags()` i `chat()`.
from __future__ import annotations

import time

from core.ai.ollama_client import OllamaClient, OllamaUnavailable
from core.ai.providers.base import (
    ChatMessage,
    ChatResult,
    ModelInfo,
    ProviderUnavailable,
)

# Budžet VRAM-a mašine: jedan GPU sa 8 GB (isti razlog zbog kog postoji
# vram_guard mutex). Model veći od ovoga se OZNAČAVA, nikad ne odbija —
# `size` iz /api/tags je veličina na disku, samo približna mera potrebe za
# VRAM-om, pa bi tvrdo odbijanje odbilo i modele koji bi radili.
VRAM_BUDGET_GB = 8.0

_BYTES_PER_GB = 1_000_000_000


class OllamaProvider:
    """Lokalni modeli kroz Ollama."""

    name = "ollama"
    is_local = True

    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    def available(self) -> bool:
        try:
            self._client.tags()
        except OllamaUnavailable:
            return False
        return True

    def models(self) -> list[ModelInfo]:
        try:
            raw = self._client.tags()
        except OllamaUnavailable as error:
            raise ProviderUnavailable(str(error)) from error
        return [self._to_info(item) for item in raw if isinstance(item, dict)]

    def chat(self, messages: list[ChatMessage], model: str,
             **options: object) -> ChatResult:
        started = time.perf_counter()
        payload = [{"role": m.role, "content": m.content} for m in messages]

        try:
            data = self._client.chat(model, payload)
        except OllamaUnavailable as error:
            raise ProviderUnavailable(str(error)) from error

        message = data.get("message")
        text = str(message.get("content", "")) if isinstance(message, dict) else ""
        return ChatResult(
            text=text,
            model=model,
            provider=self.name,
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            output_tokens=int(data.get("eval_count") or 0),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ---------- interno ----------

    @classmethod
    def _to_info(cls, item: dict) -> ModelInfo:
        model_id = str(item.get("model") or item.get("name") or "")
        raw_size = item.get("size")
        size_gb = (
            round(raw_size / _BYTES_PER_GB, 1)
            if isinstance(raw_size, int | float) and raw_size > 0
            else None
        )
        return ModelInfo(
            id=model_id,
            label=model_id,
            provider=cls.name,
            is_local=True,
            size_gb=size_gb,
            oversized=size_gb is not None and size_gb > VRAM_BUDGET_GB,
        )
```

- [ ] **Korak 4: Dopuni `core/ai/providers/__init__.py`**

```python
from core.ai.providers.ollama import VRAM_BUDGET_GB, OllamaProvider
```

i dodaj `"OllamaProvider"` i `"VRAM_BUDGET_GB"` u `__all__`.

- [ ] **Korak 5: Pokreni testove i potvrdi da prolaze**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_chat_providers.py -v
```

Očekivano: 9 passed.

- [ ] **Korak 6: Commit**

```bash
git add core/ai/providers tests/test_chat_providers.py
git commit -m "feat(core-ai): OllamaProvider nad tags() i chat()"
```

---

### Task 4: `ModelCatalog`

**Fajlovi:**
- Create: `core/ai/catalog.py`
- Test: `tests/test_model_catalog.py`

**Interfejsi:**
- Consumes: `ChatProvider`, `ModelInfo`, `ProviderUnavailable` (Task 1).
- Produces: `ModelCatalog(providers: list[ChatProvider])` sa
  `list() -> list[ModelInfo]`. Task 8 ga zove iz rute `/models`.

Ključno ponašanje: kad provajder ne odgovara, njegovi modeli se **ne znaju**, pa
katalog vraća jedan red-obaveštenje sa `available=False` i razlogom. Korisnik
treba da vidi da Ollama ne radi, a ne da mu lista tiho ostane prazna.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_model_catalog.py`:

```python
# ========== TESTOVI: katalog modela ==========
from __future__ import annotations

from core.ai.catalog import ModelCatalog
from core.ai.providers import ModelInfo, ProviderUnavailable


class _Ok:
    name = "ok"
    is_local = True

    def available(self) -> bool:
        return True

    def models(self) -> list[ModelInfo]:
        return [ModelInfo(id="a", label="A", provider="ok", is_local=True)]

    def chat(self, messages, model, **options):
        raise NotImplementedError


class _Pukao:
    name = "pukao"
    is_local = False

    def available(self) -> bool:
        return False

    def models(self) -> list[ModelInfo]:
        raise ProviderUnavailable("servis ne odgovara")

    def chat(self, messages, model, **options):
        raise NotImplementedError


def test_katalog_spaja_modele_svih_provajdera():
    items = ModelCatalog([_Ok()]).list()
    assert [i.id for i in items] == ["a"]


def test_nedostupan_provajder_daje_red_sa_razlogom_a_ne_prazno():
    items = ModelCatalog([_Pukao()]).list()

    assert len(items) == 1
    assert items[0].available is False
    assert items[0].provider == "pukao"
    assert "servis ne odgovara" in items[0].unavailable_reason


def test_nedostupan_provajder_ne_obara_dostupnog():
    items = ModelCatalog([_Ok(), _Pukao()]).list()

    assert [i.available for i in items] == [True, False]


def test_prazan_spisak_provajdera_daje_prazan_katalog():
    assert ModelCatalog([]).list() == []
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_model_catalog.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: No module named 'core.ai.catalog'`.

- [ ] **Korak 3: Napiši `core/ai/catalog.py`**

```python
# ========== KATALOG MODELA ==========
# Spaja modele iz svih registrovanih provajdera u jednu listu za izbornik.
# Pravilo: katalog nikada ne obara poziv. Provajder koji ne odgovara ne nestaje
# iz liste — dobija jedan red sa available=False i razlogom, da korisnik vidi
# ZAŠTO mu modeli nedostaju.
from __future__ import annotations

from core.ai.providers.base import ChatProvider, ModelInfo, ProviderUnavailable


class ModelCatalog:
    """Jedinstven spisak modela iz svih izvora."""

    def __init__(self, providers: list[ChatProvider]) -> None:
        self._providers = providers

    def list(self) -> list[ModelInfo]:
        result: list[ModelInfo] = []
        for provider in self._providers:
            try:
                result.extend(provider.models())
            except ProviderUnavailable as error:
                result.append(self._nedostupan(provider, str(error)))
        return result

    @staticmethod
    def _nedostupan(provider: ChatProvider, reason: str) -> ModelInfo:
        return ModelInfo(
            id=f"{provider.name}:nedostupan",
            label=f"{provider.name} nije dostupan",
            provider=provider.name,
            is_local=provider.is_local,
            available=False,
            unavailable_reason=reason,
        )
```

- [ ] **Korak 4: Pokreni test i potvrdi da prolazi**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_model_catalog.py -v
```

Očekivano: 4 passed.

- [ ] **Korak 5: Commit**

```bash
git add core/ai/catalog.py tests/test_model_catalog.py
git commit -m "feat(core-ai): ModelCatalog spaja izvore i cuva razlog nedostupnosti"
```

---

### Task 5: Migracija v3 i postavka modela u bazi

**Fajlovi:**
- Modify: `core/domains/codium/models.py`
- Modify: `core/domains/codium/migrations.py`
- Modify: `core/domains/codium/repository.py`
- Test: `tests/test_codium_model_prefs.py`

**Interfejsi:**
- Consumes: ništa iz prethodnih zadataka.
- Produces: `ModelPref(id, project_id, persona, model, provider, updated_at)`,
  `CodiumRepository.get_model_pref(project_id, persona) -> ModelPref | None`,
  `CodiumRepository.set_model_pref(project_id, persona, model, provider) -> ModelPref`.
  Task 6 i Task 8 ih koriste.

**Pažnja — SQLite i NULL u UNIQUE indeksu:** `project_id` sme da bude `NULL`
(chat bez izabranog projekta). U SQLite-u su dve `NULL` vrednosti **različite**
za potrebe UNIQUE indeksa, pa bi običan `UNIQUE (project_id, persona)` dozvolio
neograničeno mnogo redova za isti par (`NULL`, `"architect"`). Zato indeks ide
preko izraza: `COALESCE(project_id, 0)`.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_codium_model_prefs.py`:

```python
# ========== TESTOVI: postavka modela po projektu i personi ==========
from __future__ import annotations

import pytest

from core.domains.codium import CodiumRepository, initialize_codium_database


@pytest.fixture()
def repository(tmp_path):
    database = tmp_path / "codium_prefs.db"
    initialize_codium_database(database)
    return CodiumRepository(database)


def test_bez_upisa_nema_postavke(repository):
    assert repository.get_model_pref(None, "architect") is None


def test_upis_i_citanje_postavke(repository):
    repository.set_model_pref(None, "architect", "qwen2.5:7b", "ollama")

    pref = repository.get_model_pref(None, "architect")

    assert pref is not None
    assert pref.model == "qwen2.5:7b"
    assert pref.provider == "ollama"
    assert pref.project_id is None


def test_ponovni_upis_menja_a_ne_duplira(repository):
    repository.set_model_pref(None, "architect", "prvi:7b", "ollama")
    repository.set_model_pref(None, "architect", "drugi:7b", "ollama")

    pref = repository.get_model_pref(None, "architect")

    assert pref.model == "drugi:7b"
    assert repository.count_model_prefs() == 1


def test_razlicite_persone_imaju_svoje_postavke(repository):
    repository.set_model_pref(None, "architect", "a:7b", "ollama")
    repository.set_model_pref(None, "builder", "b:7b", "ollama")

    assert repository.get_model_pref(None, "architect").model == "a:7b"
    assert repository.get_model_pref(None, "builder").model == "b:7b"


def test_projekat_i_globalna_postavka_su_odvojeni(repository):
    repository.set_model_pref(None, "architect", "globalni:7b", "ollama")
    repository.set_model_pref(7, "architect", "projektni:7b", "ollama")

    assert repository.get_model_pref(None, "architect").model == "globalni:7b"
    assert repository.get_model_pref(7, "architect").model == "projektni:7b"
    assert repository.count_model_prefs() == 2
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_model_prefs.py -v
```

Očekivano: FAIL sa `AttributeError: 'CodiumRepository' object has no attribute 'get_model_pref'`.

- [ ] **Korak 3: Dodaj `ModelPref` u `core/domains/codium/models.py`**

Na kraj fajla, uz ostale dataclass-e:

```python
@dataclass(frozen=True)
class ModelPref:
    """Zapamćen izbor modela za par (projekat, persona)."""

    id: int
    project_id: int | None
    persona: str
    model: str
    provider: str
    updated_at: str
```

- [ ] **Korak 4: Dodaj migraciju v3 u `core/domains/codium/migrations.py`**

Ispod `CODIUM_MIGRATION_V2`:

```python
# ---------- v3: zapamćen izbor modela (Faza 1 AI provajdera) ----------

CODIUM_MIGRATION_V3 = DatabaseMigration(
    scope="codium",
    version=3,
    name="create_model_prefs",
    statements=(
        """
        CREATE TABLE codium_model_prefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES codium_projects (id) ON DELETE CASCADE,
            persona TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL,
            provider TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # COALESCE u indeksu: u SQLite-u su dve NULL vrednosti RAZLIČITE za
        # UNIQUE, pa bi obican UNIQUE (project_id, persona) dozvolio vise
        # redova za isti par (NULL, 'architect').
        "CREATE UNIQUE INDEX idx_codium_model_prefs "
        "ON codium_model_prefs (COALESCE(project_id, 0), persona)",
    ),
)
```

I zameni poslednji red fajla:

```python
CODIUM_MIGRATIONS = (
    CODIUM_MIGRATION_V1,
    CODIUM_MIGRATION_V2,
    CODIUM_MIGRATION_V3,
)
```

- [ ] **Korak 5: Dodaj metode u `core/domains/codium/repository.py`**

Uvezi `ModelPref` u postojeći blok uvoza iz `core.domains.codium.models`, pa na
kraj klase dodaj:

```python
    # ==========          POSTAVKA MODELA          ==========

    def get_model_pref(self, project_id: int | None,
                       persona: str) -> ModelPref | None:
        """Zapamćen model za par (projekat, persona); None ako ga nema."""

        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT * FROM codium_model_prefs
                WHERE COALESCE(project_id, 0) = COALESCE(?, 0) AND persona = ?
                """,
                (project_id, persona),
            ).fetchone()
        return self._row_to_model_pref(row) if row is not None else None

    def set_model_pref(self, project_id: int | None, persona: str,
                       model: str, provider: str) -> ModelPref:
        """Upisuje ili menja postavku. Par (projekat, persona) je jedinstven."""

        with core_database_connection(self._database_path) as connection:
            existing = connection.execute(
                """
                SELECT id FROM codium_model_prefs
                WHERE COALESCE(project_id, 0) = COALESCE(?, 0) AND persona = ?
                """,
                (project_id, persona),
            ).fetchone()

            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO codium_model_prefs (
                        project_id, persona, model, provider
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (project_id, persona, model, provider),
                )
                pref_id = cursor.lastrowid
                if pref_id is None:
                    raise RuntimeError("SQLite nije vratio ID postavke modela.")
            else:
                pref_id = existing["id"]
                connection.execute(
                    """
                    UPDATE codium_model_prefs
                    SET model = ?, provider = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (model, provider, pref_id),
                )

            row = connection.execute(
                "SELECT * FROM codium_model_prefs WHERE id = ?",
                (pref_id,),
            ).fetchone()
        return self._row_to_model_pref(row)

    def count_model_prefs(self) -> int:
        """Broj upisanih postavki (koristi se u testovima i dijagnostici)."""

        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM codium_model_prefs",
            ).fetchone()
        return int(row["n"])
```

Uz ostale `_row_to_*` statičke metode dodaj:

```python
    @staticmethod
    def _row_to_model_pref(row: sqlite3.Row) -> ModelPref:
        return ModelPref(
            id=row["id"],
            project_id=row["project_id"],
            persona=row["persona"],
            model=row["model"],
            provider=row["provider"],
            updated_at=row["updated_at"],
        )
```

- [ ] **Korak 6: Pokreni testove i potvrdi da prolaze**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_model_prefs.py tests/test_codium_service.py tests/test_api_codium.py -v
```

Očekivano: 5 novih passed; postojeći CODIUM testovi bez regresije.

- [ ] **Korak 7: Commit**

```bash
git add core/domains/codium tests/test_codium_model_prefs.py
git commit -m "feat(codium): migracija v3 - zapamcen izbor modela po projektu i personi"
```

---

### Task 6: `ModelRouter`

**Fajlovi:**
- Create: `core/ai/model_router.py`
- Test: `tests/test_model_router.py`

**Interfejsi:**
- Consumes: `ChatProvider`, `ChatMessage`, `ChatResult`, `ProviderUnavailable`
  (Task 1).
- Produces: `ResolvedModel(provider_name, model, source)` i `ModelRouter` sa
  `resolve(*, project_id=None, persona="", override_provider=None,
  override_model=None) -> ResolvedModel` i
  `chat(messages, resolved, **options) -> ChatResult`. Task 7 ga koristi.

Ruter namerno **ne zna** za `ModelRegistry` ni za bazu. Postavku i podrazumevani
model dobija kao ubrizgane funkcije, pa je testabilan bez ijednog od ta dva.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_model_router.py`:

```python
# ========== TESTOVI: biranje modela ==========
from __future__ import annotations

import pytest

from core.ai.model_router import ModelRouter, ResolvedModel
from core.ai.providers import ChatMessage, ChatResult, ProviderUnavailable


class _Provider:
    name = "ollama"
    is_local = True

    def __init__(self) -> None:
        self.pozvan_sa: tuple | None = None

    def available(self) -> bool:
        return True

    def models(self):
        return []

    def chat(self, messages, model, **options) -> ChatResult:
        self.pozvan_sa = (messages, model)
        return ChatResult(text="ok", model=model, provider=self.name)


def _router(pref=None, default=("ollama", "podrazumevani:7b")):
    provider = _Provider()
    router = ModelRouter(
        providers={"ollama": provider},
        pref_lookup=lambda project_id, persona: pref,
        default_lookup=lambda: default,
    )
    return router, provider


def test_override_pobedjuje_sve():
    router, _ = _router(pref=("ollama", "zapamceni:7b"))

    resolved = router.resolve(
        project_id=1, persona="architect",
        override_provider="ollama", override_model="izabrani:7b",
    )

    assert resolved == ResolvedModel("ollama", "izabrani:7b", "override")


def test_bez_override_a_koristi_zapamcenu_postavku():
    router, _ = _router(pref=("ollama", "zapamceni:7b"))

    resolved = router.resolve(project_id=1, persona="architect")

    assert resolved == ResolvedModel("ollama", "zapamceni:7b", "pref")


def test_bez_postavke_pada_na_podrazumevani():
    router, _ = _router(pref=None)

    resolved = router.resolve(project_id=1, persona="architect")

    assert resolved == ResolvedModel("ollama", "podrazumevani:7b", "registry")


def test_prazan_override_model_se_ignorise():
    router, _ = _router(pref=("ollama", "zapamceni:7b"))

    resolved = router.resolve(persona="architect", override_model="")

    assert resolved.source == "pref"


def test_override_bez_provajdera_uzima_provajdera_podrazumevanog():
    router, _ = _router(default=("ollama", "podrazumevani:7b"))

    resolved = router.resolve(persona="architect", override_model="izabrani:7b")

    assert resolved == ResolvedModel("ollama", "izabrani:7b", "override")


def test_chat_prosledjuje_pozivu_izabrani_model():
    router, provider = _router()

    result = router.chat(
        [ChatMessage(role="user", content="a")],
        ResolvedModel("ollama", "izabrani:7b", "override"),
    )

    assert provider.pozvan_sa[1] == "izabrani:7b"
    assert result.text == "ok"


def test_nepoznat_provajder_die_provider_unavailable():
    router, _ = _router()

    with pytest.raises(ProviderUnavailable, match="nepostoji"):
        router.chat([], ResolvedModel("nepostoji", "m", "override"))
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_model_router.py -v
```

Očekivano: FAIL sa `ModuleNotFoundError: No module named 'core.ai.model_router'`.

- [ ] **Korak 3: Napiši `core/ai/model_router.py`**

```python
# ========== RUTER MODELA ==========
# Bira KOJIM modelom se odgovara. Nije isto što i core_router.py — taj
# klasifikuje nameru korisnika u JSON intent i sa izborom modela nema veze.
#
# Ruter ne zna za ModelRegistry ni za bazu: postavku i podrazumevani model
# dobija kao ubrizgane funkcije, pa se testira bez ijednog od ta dva.
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.ai.providers.base import (
    ChatMessage,
    ChatProvider,
    ChatResult,
    ProviderUnavailable,
)

# pref_lookup(project_id, persona) -> (provajder, model) | None
PrefLookup = Callable[[int | None, str], tuple[str, str] | None]
# default_lookup() -> (provajder, model)
DefaultLookup = Callable[[], tuple[str, str]]


@dataclass(frozen=True)
class ResolvedModel:
    """Odluka rutera: čime se odgovara i odakle je odluka došla."""

    provider_name: str
    model: str
    source: str  # "override" | "pref" | "registry"


class ModelRouter:
    """Redosled odlučivanja: override, pa zapamćeno, pa podrazumevano."""

    def __init__(self, providers: dict[str, ChatProvider],
                 pref_lookup: PrefLookup,
                 default_lookup: DefaultLookup) -> None:
        self._providers = providers
        self._pref_lookup = pref_lookup
        self._default_lookup = default_lookup

    def resolve(self, *, project_id: int | None = None, persona: str = "",
                override_provider: str | None = None,
                override_model: str | None = None) -> ResolvedModel:
        default_provider, default_model = self._default_lookup()

        # 1. Izričit izbor korisnika u chatu uvek pobeđuje.
        if override_model:
            return ResolvedModel(
                override_provider or default_provider,
                override_model,
                "override",
            )

        # 2. Zapamćena postavka za taj projekat i tu personu.
        pref = self._pref_lookup(project_id, persona)
        if pref is not None:
            return ResolvedModel(pref[0], pref[1], "pref")

        # 3. Podrazumevano po domenu i ulozi (postojeće ponašanje).
        return ResolvedModel(default_provider, default_model, "registry")

    def chat(self, messages: list[ChatMessage], resolved: ResolvedModel,
             **options: object) -> ChatResult:
        provider = self._providers.get(resolved.provider_name)
        if provider is None:
            raise ProviderUnavailable(
                f"Nepoznat provajder: {resolved.provider_name}",
            )
        return provider.chat(messages, resolved.model, **options)
```

- [ ] **Korak 4: Pokreni test i potvrdi da prolazi**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_model_router.py -v
```

Očekivano: 7 passed.

- [ ] **Korak 5: Commit**

```bash
git add core/ai/model_router.py tests/test_model_router.py
git commit -m "feat(core-ai): ModelRouter - override, zapamceno, podrazumevano"
```

---

### Task 7: `CodiumAssistant` ide kroz ruter

**Fajlovi:**
- Modify: `core/domains/codium/assistant/assistant_service.py`
- Modify: `apps/api/codium_assistant_runtime.py`
- Test: `tests/test_codium_assistant.py` (prepravka postojećeg)

**Interfejsi:**
- Consumes: `ChatMessage`, `ChatResult`, `ProviderUnavailable` (Task 1);
  `ModelRouter`, `ResolvedModel` (Task 6); `CodiumRepository.get_model_pref`
  (Task 5); `OllamaProvider` (Task 3).
- Produces: `CodiumAssistant(router, project_lookup)` sa
  `ask(*, project_id, persona_id, message, history=None, model=None,
  provider=None) -> AssistantAnswer`, gde `AssistantAnswer` dobija nova polja
  `provider: str` i `source: str`. Task 8 ih vraća kroz API.

Ovo je jedina invazivna izmena u postojećem F9 kodu. `CodiumAssistant` prestaje
da prima `ModelRegistry` i `generate` — traženje podrazumevanog lokalnog modela
seli se u runtime, gde mu je i mesto, jer je CODIUM-specifično.

- [ ] **Korak 1: Prepravi testove tako da padnu**

U `tests/test_codium_assistant.py` zameni pomoćnu funkciju `_assistant` i uvoze.
Novi vrh fajla:

```python
# ========== TESTOVI: CODIUM Asistent (chat po personi) ==========
from __future__ import annotations

from types import SimpleNamespace

from core.ai.model_router import ModelRouter, ResolvedModel
from core.ai.providers import ChatResult, ProviderUnavailable
from core.domains.codium.assistant import (
    ChatTurn,
    CodiumAssistant,
    DEFAULT_PERSONA,
    PERSONAS,
    persona,
    persona_ids,
)

_DEFAULT = ("ollama", "llama3.2:latest")


def _project(name="Sajt", slug="sajt", stack="React", status="active"):
    return SimpleNamespace(name=name, slug=slug, stack=stack, status=status)


class _Provider:
    """Hvata poslednji poziv i vraća zadati odgovor (ili diže grešku)."""

    name = "ollama"
    is_local = True

    def __init__(self, reply="Predlog arhitekture.", raise_error=False) -> None:
        self.reply = reply
        self.raise_error = raise_error
        self.messages: list = []
        self.model = ""

    def available(self) -> bool:
        return not self.raise_error

    def models(self):
        return []

    def chat(self, messages, model, **options) -> ChatResult:
        if self.raise_error:
            raise ProviderUnavailable("Ollama nije pokrenut")
        self.messages = list(messages)
        self.model = model
        return ChatResult(text=self.reply, model=model, provider=self.name,
                          prompt_tokens=3, output_tokens=4)


def _assistant(provider=None, *, pref=None, lookup=lambda _pid: None):
    provider = provider or _Provider()
    router = ModelRouter(
        providers={"ollama": provider},
        pref_lookup=lambda project_id, persona: pref,
        default_lookup=lambda: _DEFAULT,
    )
    return CodiumAssistant(router, lookup), provider
```

Zameni postojeće testove servisa ovima (testovi persona ostaju nepromenjeni):

```python
# ---------- servis ----------

def test_ask_salje_personin_system_prompt_kao_prvu_poruku():
    assistant, provider = _assistant()

    assistant.ask(project_id=None, persona_id="architect", message="Kako?")

    assert provider.messages[0].role == "system"
    assert "srpskom" in provider.messages[0].content


def test_ask_salje_korisnicku_poruku_kao_poslednju():
    assistant, provider = _assistant()

    assistant.ask(project_id=None, persona_id="architect", message="Kako?")

    assert provider.messages[-1].role == "user"
    assert provider.messages[-1].content == "Kako?"


def test_ask_prenosi_istoriju_kao_zasebne_poruke():
    assistant, provider = _assistant()

    assistant.ask(
        project_id=None, persona_id="architect", message="Nastavi",
        history=[ChatTurn(author="me", text="Prvo"),
                 ChatTurn(author="assistant", text="Drugo")],
    )

    uloge = [m.role for m in provider.messages]
    assert uloge == ["system", "user", "assistant", "user"]


def test_ask_dodaje_kontekst_projekta_u_system_poruku():
    assistant, provider = _assistant(lookup=lambda _pid: _project())

    assistant.ask(project_id=1, persona_id="architect", message="Kako?")

    assert "Sajt" in provider.messages[0].content
    assert "React" in provider.messages[0].content


def test_ask_bez_izbora_koristi_podrazumevani_model():
    assistant, provider = _assistant()

    answer = assistant.ask(project_id=None, persona_id="architect", message="a")

    assert provider.model == "llama3.2:latest"
    assert answer.model == "llama3.2:latest"
    assert answer.source == "registry"


def test_ask_postuje_izricit_izbor_modela():
    assistant, provider = _assistant()

    answer = assistant.ask(project_id=None, persona_id="architect",
                           message="a", model="qwen2.5:7b")

    assert provider.model == "qwen2.5:7b"
    assert answer.source == "override"


def test_ask_koristi_zapamcenu_postavku():
    assistant, provider = _assistant(pref=("ollama", "zapamceni:7b"))

    answer = assistant.ask(project_id=1, persona_id="architect", message="a")

    assert provider.model == "zapamceni:7b"
    assert answer.source == "pref"


def test_ask_bez_provajdera_vraca_fallback_bez_pada():
    assistant, _ = _assistant(_Provider(raise_error=True))

    answer = assistant.ask(project_id=None, persona_id="architect", message="a")

    assert answer.is_fallback is True
    assert "Ollama" in answer.reply


def test_ask_secka_belinu_odgovora():
    assistant, _ = _assistant(_Provider(reply="  Odgovor.  "))

    answer = assistant.ask(project_id=None, persona_id="architect", message="a")

    assert answer.reply == "Odgovor."


def test_nepoznata_persona_pada_na_podrazumevanu():
    assistant, _ = _assistant()

    answer = assistant.ask(project_id=None, persona_id="nepostoji", message="a")

    assert answer.persona == DEFAULT_PERSONA
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_assistant.py -v
```

Očekivano: FAIL sa `TypeError: CodiumAssistant.__init__() takes 4 positional arguments but 3 were given`.

- [ ] **Korak 3: Prepravi `core/domains/codium/assistant/assistant_service.py`**

Zameni vrh fajla (uvozi i konstante) ovim:

```python
# ========== CODIUM ASISTENT (chat servis) ==========
# Kognitivni sloj CODIUM domena: razgovor sa modelom kroz ModelRouter. Persona
# (chat mod) bira sistemski prompt; kratak kontekst projekta (ime/stack/status)
# ide u istu sistemsku poruku. Ako provajder nije dostupan, vraća se uredan
# fallback (bez pada). Servis ne zna koji je provajder u igri — to je posao
# rutera.
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.ai.model_router import ModelRouter
from core.ai.providers import ChatMessage, ProviderUnavailable
from core.domains.codium.assistant.personas import persona

# project_lookup(project_id) -> Project | None (dataclass sa name/slug/stack/status)
ProjectLookup = Callable[[int], Any]

# Koliko poslednjih poruka istorije ide u razgovor (da ostane sažeto).
_HISTORY_LIMIT = 8
```

Zameni `AssistantAnswer` dataclass:

```python
@dataclass
class AssistantAnswer:
    reply: str
    persona: str
    model: str
    provider: str = ""
    # Odakle je došla odluka o modelu: "override" | "pref" | "registry".
    source: str = ""
    is_fallback: bool = False
    sources: list[str] = field(default_factory=list)
```

Zameni telo klase `CodiumAssistant` (sve od `def __init__` do kraja fajla):

```python
class CodiumAssistant:
    """Razgovor sa asistentom po personi, sa kontekstom projekta."""

    def __init__(self, router: ModelRouter,
                 project_lookup: ProjectLookup) -> None:
        self._router = router
        self._project_lookup = project_lookup

    def ask(
        self,
        *,
        project_id: int | None,
        persona_id: str,
        message: str,
        history: list[ChatTurn] | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> AssistantAnswer:
        active = persona(persona_id)
        resolved = self._router.resolve(
            project_id=project_id,
            persona=active.id,
            override_provider=provider,
            override_model=model,
        )
        messages = self._build_messages(
            project_id, history or [], message, active.system,
        )

        try:
            result = self._router.chat(messages, resolved)
        except ProviderUnavailable:
            return AssistantAnswer(
                reply=(
                    "Model trenutno nije dostupan (Ollama nije pokrenut). "
                    "Pokreni Ollama pa pokušaj ponovo."
                ),
                persona=active.id,
                model=resolved.model,
                provider=resolved.provider_name,
                source=resolved.source,
                is_fallback=True,
            )

        return AssistantAnswer(
            reply=result.text.strip(),
            persona=active.id,
            model=resolved.model,
            provider=resolved.provider_name,
            source=resolved.source,
        )

    # ---------- interno ----------

    def _build_messages(
        self,
        project_id: int | None,
        history: list[ChatTurn],
        message: str,
        system: str,
    ) -> list[ChatMessage]:
        """Sistemska poruka (persona + kontekst), pa istorija, pa novo pitanje."""

        context = self._project_context(project_id)
        if context:
            system = f"{system}\n\nKontekst projekta: {context}"

        messages = [ChatMessage(role="system", content=system)]
        for turn in history[-_HISTORY_LIMIT:]:
            messages.append(ChatMessage(
                role="user" if turn.author == "me" else "assistant",
                content=turn.text,
            ))
        messages.append(ChatMessage(role="user", content=message))
        return messages

    def _project_context(self, project_id: int | None) -> str:
        if project_id is None:
            return ""
        project = self._project_lookup(project_id)
        if project is None:
            return ""
        bits = [f"{project.name} ({project.slug})"]
        stack = getattr(project, "stack", "") or ""
        if stack:
            bits.append(f"stack: {stack}")
        status = getattr(project, "status", "")
        status_value = getattr(status, "value", status)
        if status_value:
            bits.append(f"status: {status_value}")
        return ", ".join(bits)
```

`ChatTurn` dataclass ostaje nepromenjen.

- [ ] **Korak 4: Prepravi `apps/api/codium_assistant_runtime.py`**

Ceo fajl:

```python
# ========== CODIUM ASISTENT RUNTIME (chat za API) ==========
# Sastavlja provajdere, ruter i asistenta. Ovde živi CODIUM-specifično traženje
# podrazumevanog lokalnog modela (Codium.assistant_model, pa CORE.model) — ruter
# je generički i o registru ne zna ništa.
from __future__ import annotations

from apps.api import core_ai_runtime
from core.ai import OllamaClient
from core.ai.model_registry import ModelNotConfiguredError
from core.ai.model_router import ModelRouter
from core.ai.providers import OllamaProvider
from core.domains.codium.assistant import CodiumAssistant
from core.domains.codium.repository import CodiumRepository

# Redosled traženja podrazumevanog lokalnog modela za asistenta.
_LOCAL_ROLES: tuple[tuple[str, str], ...] = (
    ("Codium", "assistant_model"),
    ("CORE", "model"),
)
# Poslednja linija odbrane ako registar nema nijednu lokalnu ulogu.
_FALLBACK = ("ollama", "llama3.2:latest")

_registry = core_ai_runtime.get_registry()
_repository = CodiumRepository()


def _endpoint() -> str:
    try:
        return _registry.binding("CORE", "model").endpoint
    except Exception:  # noqa: BLE001
        return "http://localhost:11434"


def _default_model() -> tuple[str, str]:
    """Prvi lokalni model iz registra; inače siguran fallback."""

    for domain, role in _LOCAL_ROLES:
        try:
            binding = _registry.binding(domain, role)
        except ModelNotConfiguredError:
            continue
        if binding.is_local:
            return (binding.provider, binding.model)
    return _FALLBACK


def _pref(project_id: int | None, persona: str) -> tuple[str, str] | None:
    pref = _repository.get_model_pref(project_id, persona)
    return (pref.provider, pref.model) if pref is not None else None


_provider = OllamaProvider(OllamaClient(endpoint=_endpoint(), timeout=60.0))
_router = ModelRouter(
    providers={_provider.name: _provider},
    pref_lookup=_pref,
    default_lookup=_default_model,
)
_service = CodiumAssistant(_router, _repository.get_project)


def get_service() -> CodiumAssistant:
    return _service


def get_providers() -> list:
    """Provajderi za katalog modela (ruta /models)."""

    return [_provider]


def get_repository() -> CodiumRepository:
    return _repository
```

- [ ] **Korak 5: Prepravi `client` fixture u `tests/test_api_codium_ai.py`**

Postojeći fixture pravi asistenta direktno — `CodiumAssistant(ModelRegistry(...),
fake_generate, lambda _pid: None)` — pa ga izmena ctor-a obara. Zameni vrh fajla
(od uvoza do kraja fixture-a) ovim; sami testovi ispod ostaju nepromenjeni:

```python
# ========== TESTOVI: API CODIUM Asistent ==========
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers.codium_ai import get_service
from core.ai.model_router import ModelRouter
from core.ai.providers import ChatResult, ModelInfo
from core.domains.codium.assistant import CodiumAssistant


class _FakeProvider:
    name = "ollama"
    is_local = True

    def available(self) -> bool:
        return True

    def models(self) -> list[ModelInfo]:
        return [ModelInfo(id="llama3.2:latest", label="llama3.2:latest",
                          provider="ollama", is_local=True, size_gb=2.0)]

    def chat(self, messages, model, **options) -> ChatResult:
        return ChatResult(text="Evo predloga.", model=model, provider=self.name)


@pytest.fixture
def client() -> Iterator[TestClient]:
    provider = _FakeProvider()
    router = ModelRouter(
        providers={"ollama": provider},
        pref_lookup=lambda project_id, persona: None,
        default_lookup=lambda: ("ollama", "llama3.2:latest"),
    )
    service = CodiumAssistant(router, lambda _pid: None)

    app.dependency_overrides[get_service] = lambda: service
    tc = TestClient(app)
    try:
        yield tc
    finally:
        tc.close()
        app.dependency_overrides.pop(get_service, None)
```

- [ ] **Korak 6: Pokreni testove i potvrdi da prolaze**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_assistant.py tests/test_api_codium_ai.py -v
```

Očekivano: svi passed. Ponašanje `/ask` bez polja `model` mora ostati isto —
postojeći testovi u `test_api_codium_ai.py` to i proveravaju i ne smeju se menjati.

- [ ] **Korak 7: Commit**

```bash
git add core/domains/codium/assistant apps/api/codium_assistant_runtime.py tests/test_codium_assistant.py tests/test_api_codium_ai.py
git commit -m "refactor(codium): asistent ide kroz ModelRouter umesto direktno na Ollama"
```

---

### Task 8: API rute za katalog i postavku

**Fajlovi:**
- Modify: `apps/api/schemas/codium_ai.py`
- Modify: `apps/api/routers/codium_ai.py`
- Test: `tests/test_api_codium_ai.py` (dopuna)

**Interfejsi:**
- Consumes: `ModelCatalog` (Task 4), `CodiumRepository.get_model_pref` /
  `set_model_pref` (Task 5), `CodiumAssistant.ask(..., model, provider)`
  (Task 7), runtime funkcije `get_providers()` i `get_repository()` (Task 7).
- Produces: `GET /api/v1/codium/ai/models`, `GET /api/v1/codium/ai/prefs`,
  `PUT /api/v1/codium/ai/prefs`, i dopunjen `POST /api/v1/codium/ai/ask`.
  Task 10 ih zove iz GUI-ja.

- [ ] **Korak 1: Dopiši testove koji padaju**

Na kraj `tests/test_api_codium_ai.py` dodaj:

```python
# ---------- katalog modela ----------

def test_models_vraca_listu_sa_oznakom_lokalnog(client):
    response = client.get("/api/v1/codium/ai/models")

    assert response.status_code == 200
    body = response.json()
    assert "models" in body
    for item in body["models"]:
        assert item["provider"] != ""
        assert isinstance(item["is_local"], bool)


# ---------- postavka modela ----------

def test_prefs_bez_upisa_vraca_prazno(client):
    response = client.get("/api/v1/codium/ai/prefs", params={"persona": "architect"})

    assert response.status_code == 200
    assert response.json()["pref"] is None


def test_put_prefs_pamti_izbor(client):
    saved = client.put("/api/v1/codium/ai/prefs", json={
        "project_id": None,
        "persona": "architect",
        "model": "qwen2.5:7b",
        "provider": "ollama",
    })

    assert saved.status_code == 200
    assert saved.json()["pref"]["model"] == "qwen2.5:7b"

    read = client.get("/api/v1/codium/ai/prefs", params={"persona": "architect"})
    assert read.json()["pref"]["model"] == "qwen2.5:7b"


def test_ask_prima_opcioni_model(client):
    response = client.post("/api/v1/codium/ai/ask", json={
        "project_id": None,
        "persona": "architect",
        "message": "Kako da pocnem?",
        "history": [],
        "model": "qwen2.5:7b",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "qwen2.5:7b"
    assert body["source"] == "override"


def test_ask_bez_modela_i_dalje_radi(client):
    response = client.post("/api/v1/codium/ai/ask", json={
        "project_id": None,
        "persona": "architect",
        "message": "Kako da pocnem?",
        "history": [],
    })

    assert response.status_code == 200
    assert response.json()["model"] != ""
```

Fixture `client` iz Task 7 mora da zameni i dve nove zavisnosti, inače
`/models` udara u pravu Ollama instalaciju a `/prefs` u pravu bazu. Dopuni ga:

```python
from apps.api.routers.codium_ai import get_providers, get_repository, get_service
from core.domains.codium import CodiumRepository, initialize_codium_database


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    provider = _FakeProvider()
    router = ModelRouter(
        providers={"ollama": provider},
        pref_lookup=lambda project_id, persona: None,
        default_lookup=lambda: ("ollama", "llama3.2:latest"),
    )
    service = CodiumAssistant(router, lambda _pid: None)

    database = tmp_path / "codium_api.db"
    initialize_codium_database(database)
    repository = CodiumRepository(database)

    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_providers] = lambda: [provider]
    app.dependency_overrides[get_repository] = lambda: repository
    tc = TestClient(app)
    try:
        yield tc
    finally:
        tc.close()
        app.dependency_overrides.clear()
```

- [ ] **Korak 2: Pokreni testove i potvrdi da padaju**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api_codium_ai.py -v
```

Očekivano: FAIL sa `404 Not Found` na `/models` i `/prefs`.

- [ ] **Korak 3: Dopuni `apps/api/schemas/codium_ai.py`**

Dodaj polja u postojeće šeme:

```python
class AssistantAskRequest(BaseModel):
    project_id: int | None = None
    persona: str = "architect"
    message: str = Field(..., min_length=1)
    history: list[ChatTurnSchema] = Field(default_factory=list)
    # Izričit izbor korisnika; prazno znači "odluči po postavci pa registru".
    model: str | None = None
    provider: str | None = None
```

```python
class AssistantAnswerResponse(BaseModel):
    reply: str
    persona: str
    model: str
    provider: str
    source: str
    is_fallback: bool
    sources: list[str]

    @classmethod
    def from_domain(cls, result: AssistantAnswer) -> "AssistantAnswerResponse":
        return cls(
            reply=result.reply,
            persona=result.persona,
            model=result.model,
            provider=result.provider,
            source=result.source,
            is_fallback=result.is_fallback,
            sources=list(result.sources),
        )
```

Na kraj fajla dodaj nove šeme:

```python
class ModelInfoSchema(BaseModel):
    id: str
    label: str
    provider: str
    is_local: bool
    context_window: int
    price_in_per_mtok: float
    price_out_per_mtok: float
    size_gb: float | None
    oversized: bool
    available: bool
    unavailable_reason: str

    @classmethod
    def from_domain(cls, item: ModelInfo) -> "ModelInfoSchema":
        return cls(
            id=item.id,
            label=item.label,
            provider=item.provider,
            is_local=item.is_local,
            context_window=item.context_window,
            price_in_per_mtok=item.price_in_per_mtok,
            price_out_per_mtok=item.price_out_per_mtok,
            size_gb=item.size_gb,
            oversized=item.oversized,
            available=item.available,
            unavailable_reason=item.unavailable_reason,
        )


class ModelsResponse(BaseModel):
    models: list[ModelInfoSchema]


class ModelPrefSchema(BaseModel):
    project_id: int | None
    persona: str
    model: str
    provider: str

    @classmethod
    def from_domain(cls, item: ModelPref) -> "ModelPrefSchema":
        return cls(
            project_id=item.project_id,
            persona=item.persona,
            model=item.model,
            provider=item.provider,
        )


class ModelPrefResponse(BaseModel):
    pref: ModelPrefSchema | None


class ModelPrefRequest(BaseModel):
    project_id: int | None = None
    persona: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
```

Dopuni uvoz na vrhu fajla:

```python
from core.ai.providers import ModelInfo
from core.domains.codium.models import ModelPref
```

- [ ] **Korak 4: Dopuni `apps/api/routers/codium_ai.py`**

Dopuni uvoze:

```python
from apps.api.schemas.codium_ai import (
    AssistantAnswerResponse,
    AssistantAskRequest,
    ModelInfoSchema,
    ModelPrefRequest,
    ModelPrefResponse,
    ModelPrefSchema,
    ModelsResponse,
    PersonasResponse,
    PersonaSchema,
)
from core.ai.catalog import ModelCatalog
```

Dopuni poziv `service.ask` u `ask_assistant` dvama poljima:

```python
    result = service.ask(
        project_id=payload.project_id,
        persona_id=payload.persona,
        message=payload.message,
        history=[ChatTurn(author=t.author, text=t.text) for t in payload.history],
        model=payload.model,
        provider=payload.provider,
    )
```

Na kraj fajla dodaj tri rute:

Uz postojeći `get_service`, dodaj još dve zavisnosti. Moraju ići kroz `Depends`,
a ne kao direktan poziv runtime modula — inače testovi ne mogu da ih zamene, pa
bi `/models` udarao u pravu Ollama instalaciju, a `/prefs` u pravu bazu:

```python
def get_providers() -> list:
    return codium_assistant_runtime.get_providers()


def get_repository() -> CodiumRepository:
    return codium_assistant_runtime.get_repository()
```

Uz to uvezi `from core.domains.codium.repository import CodiumRepository`.

Na kraj fajla dodaj tri rute:

```python
# ==========          KATALOG MODELA          ==========

@router.get("/models", response_model=ModelsResponse)
def list_models(providers: list = Depends(get_providers)) -> ModelsResponse:
    """Modeli iz svih provajdera. Nedostupan provajder daje red sa razlogom."""

    return ModelsResponse(
        models=[
            ModelInfoSchema.from_domain(m) for m in ModelCatalog(providers).list()
        ],
    )


# ==========          POSTAVKA MODELA          ==========

@router.get("/prefs", response_model=ModelPrefResponse)
def read_model_pref(
    persona: str,
    project_id: int | None = None,
    repository: CodiumRepository = Depends(get_repository),
) -> ModelPrefResponse:
    """Zapamćen model za par (projekat, persona)."""

    pref = repository.get_model_pref(project_id, persona)
    return ModelPrefResponse(
        pref=ModelPrefSchema.from_domain(pref) if pref is not None else None,
    )


@router.put("/prefs", response_model=ModelPrefResponse)
def write_model_pref(
    payload: ModelPrefRequest,
    repository: CodiumRepository = Depends(get_repository),
) -> ModelPrefResponse:
    """Pamti izbor modela za par (projekat, persona)."""

    pref = repository.set_model_pref(
        payload.project_id, payload.persona, payload.model, payload.provider,
    )
    return ModelPrefResponse(pref=ModelPrefSchema.from_domain(pref))
```

- [ ] **Korak 5: Pokreni testove i potvrdi da prolaze**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api_codium_ai.py -v
```

Očekivano: svi passed, uključujući pet novih.

- [ ] **Korak 6: Pokreni ceo Python paket**

```bash
./.venv/Scripts/python.exe -m pytest -q
```

Očekivano: nula neuspeha. Broj testova veći od 1000 za oko 30.

- [ ] **Korak 7: Commit**

```bash
git add apps/api tests/test_api_codium_ai.py
git commit -m "feat(api): rute za katalog modela i zapamcen izbor u CODIUM chatu"
```

---

### Task 9: GUI čist modul `modelPicker.ts`

**Fajlovi:**
- Create: `apps/gui/src/features/codium/modelPicker.ts`
- Test: `apps/gui/src/features/codium/modelPicker.test.ts`

**Interfejsi:**
- Consumes: ništa — modul nema uvoza.
- Produces: `type CatalogModel` (jedini opis oblika koji ruta `/models` vraća —
  polja se poklapaju sa `ModelInfoSchema` iz Task 8), `type ModelGroup`,
  `groupModels(models) -> ModelGroup[]`, `formatModelLabel(model) -> string`.
  Task 10 uvozi sve četiri.

Modul je čist — bez React-a i bez `fetch`-a — pa se testira bez renderovanja.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `apps/gui/src/features/codium/modelPicker.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { formatModelLabel, groupModels, type CatalogModel } from "./modelPicker";

function model(over: Partial<CatalogModel> = {}): CatalogModel {
  return {
    id: "qwen2.5:7b",
    label: "qwen2.5:7b",
    provider: "ollama",
    is_local: true,
    context_window: 0,
    price_in_per_mtok: 0,
    price_out_per_mtok: 0,
    size_gb: 4.7,
    oversized: false,
    available: true,
    unavailable_reason: "",
    ...over,
  };
}

describe("groupModels", () => {
  it("stavlja lokalne modele u grupu Lokalno", () => {
    const groups = groupModels([model()]);

    expect(groups).toHaveLength(1);
    expect(groups[0].title).toBe("Lokalno");
    expect(groups[0].models[0].id).toBe("qwen2.5:7b");
  });

  it("razdvaja lokalne i online u dve grupe, lokalni prvi", () => {
    const groups = groupModels([
      model({ id: "claude", is_local: false, provider: "anthropic" }),
      model(),
    ]);

    expect(groups.map((g) => g.title)).toEqual(["Lokalno", "Online"]);
  });

  it("dostupne modele stavlja iznad nedostupnih", () => {
    const groups = groupModels([
      model({ id: "pao", available: false }),
      model({ id: "radi" }),
    ]);

    expect(groups[0].models.map((m) => m.id)).toEqual(["radi", "pao"]);
  });

  it("dostupne modele sortira po nazivu", () => {
    const groups = groupModels([model({ id: "b", label: "b" }), model({ id: "a", label: "a" })]);

    expect(groups[0].models.map((m) => m.id)).toEqual(["a", "b"]);
  });

  it("prazan ulaz daje prazan spisak grupa", () => {
    expect(groupModels([])).toEqual([]);
  });
});

describe("formatModelLabel", () => {
  it("dodaje velicinu lokalnom modelu", () => {
    expect(formatModelLabel(model())).toBe("qwen2.5:7b (4.7 GB)");
  });

  it("upozorava na model veci od budzeta", () => {
    const label = formatModelLabel(model({ size_gb: 40, oversized: true }));

    expect(label).toContain("40 GB");
    expect(label).toContain("veći od VRAM-a");
  });

  it("prikazuje cenu online modela", () => {
    const label = formatModelLabel(
      model({ id: "claude", is_local: false, size_gb: null, price_in_per_mtok: 5 }),
    );

    expect(label).toContain("$5");
  });

  it("nedostupan model nosi razlog", () => {
    const label = formatModelLabel(
      model({ available: false, unavailable_reason: "veza odbijena" }),
    );

    expect(label).toContain("veza odbijena");
  });
});
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

```bash
npm --prefix apps/gui run test -- modelPicker
```

Očekivano: FAIL sa `Failed to resolve import "./modelPicker"`.

- [ ] **Korak 3: Napiši `apps/gui/src/features/codium/modelPicker.ts`**

```ts
// ==========          IZBORNIK MODELA (čist modul)          ==========
// Grupisanje i sortiranje kataloga za dropdown. Bez React-a i bez fetch-a, da
// se logika testira bez renderovanja.

export type CatalogModel = {
  id: string;
  label: string;
  provider: string;
  is_local: boolean;
  context_window: number;
  price_in_per_mtok: number;
  price_out_per_mtok: number;
  size_gb: number | null;
  oversized: boolean;
  available: boolean;
  unavailable_reason: string;
};

export type ModelGroup = {
  title: string;
  models: CatalogModel[];
};

/** Dostupni prvi, pa po nazivu. Nedostupni ostaju u listi — vide se sivi. */
function sortModels(models: CatalogModel[]): CatalogModel[] {
  return [...models].sort((a, b) => {
    if (a.available !== b.available) {
      return a.available ? -1 : 1;
    }
    return a.label.localeCompare(b.label);
  });
}

/** Deli katalog na „Lokalno" i „Online". Prazna grupa se ne prikazuje. */
export function groupModels(models: CatalogModel[]): ModelGroup[] {
  const local = models.filter((m) => m.is_local);
  const online = models.filter((m) => !m.is_local);

  const groups: ModelGroup[] = [];
  if (local.length > 0) {
    groups.push({ title: "Lokalno", models: sortModels(local) });
  }
  if (online.length > 0) {
    groups.push({ title: "Online", models: sortModels(online) });
  }
  return groups;
}

/** Natpis u dropdown-u: naziv plus veličina ili cena, plus razlog ako ne radi. */
export function formatModelLabel(model: CatalogModel): string {
  const parts: string[] = [];

  if (model.size_gb !== null) {
    parts.push(`${model.size_gb} GB`);
  }
  if (model.oversized) {
    parts.push("veći od VRAM-a");
  }
  if (!model.is_local && model.price_in_per_mtok > 0) {
    parts.push(`$${model.price_in_per_mtok}/M`);
  }
  if (!model.available && model.unavailable_reason !== "") {
    parts.push(model.unavailable_reason);
  }

  return parts.length === 0 ? model.label : `${model.label} (${parts.join(", ")})`;
}
```

- [ ] **Korak 4: Pokreni test i potvrdi da prolazi**

```bash
npm --prefix apps/gui run test -- modelPicker
```

Očekivano: 9 passed.

- [ ] **Korak 5: Commit**

```bash
git add apps/gui/src/features/codium/modelPicker.ts apps/gui/src/features/codium/modelPicker.test.ts
git commit -m "feat(gui): modelPicker - grupisanje i natpisi kataloga modela"
```

---

### Task 10: Dropdown modela u chat okviru

**Fajlovi:**
- Modify: `apps/gui/src/services/codiumApi.ts`
- Modify: `apps/gui/src/features/codium/AiAssistant.tsx`
- Modify: `apps/gui/src/styles/codium-ai.css`
- Test: `apps/gui/src/features/codium/AiAssistant.test.tsx`

**Interfejsi:**
- Consumes: `groupModels`, `formatModelLabel`, `CatalogModel` (Task 9); rute iz
  Task 8.
- Produces: ništa što naredni zadaci koriste — ovo je poslednji sloj.

Chat okvir postoji na tri mesta (hub, docking panel, odvojen prozor) i sva tri
koriste ovu komponentu, pa izbor modela stiže u sva tri bez dodatnog rada.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `apps/gui/src/features/codium/AiAssistant.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AiAssistant from "./AiAssistant";
import * as api from "../../services/codiumApi";

vi.mock("../../services/codiumApi");

const MODELS = [
  {
    id: "qwen2.5:7b",
    label: "qwen2.5:7b",
    provider: "ollama",
    is_local: true,
    context_window: 0,
    price_in_per_mtok: 0,
    price_out_per_mtok: 0,
    size_gb: 4.7,
    oversized: false,
    available: true,
    unavailable_reason: "",
  },
];

beforeEach(() => {
  vi.mocked(api.listAssistantPersonas).mockResolvedValue({
    personas: [{ id: "architect", name: "Arhitekta" }],
  });
  vi.mocked(api.listAssistantModels).mockResolvedValue({ models: MODELS });
  vi.mocked(api.getModelPref).mockResolvedValue({ pref: null });
  vi.mocked(api.setModelPref).mockResolvedValue({
    pref: { project_id: 1, persona: "architect", model: "qwen2.5:7b", provider: "ollama" },
  });
});

describe("AiAssistant izbor modela", () => {
  it("prikazuje dropdown modela sa grupom Lokalno", async () => {
    render(<AiAssistant projectId={1} />);

    const select = await screen.findByLabelText("Model");
    expect(select).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("group", { name: "Lokalno" })).toBeInTheDocument();
    });
  });

  it("prikazuje velicinu modela u natpisu", async () => {
    render(<AiAssistant projectId={1} />);

    await waitFor(() => {
      expect(screen.getByText("qwen2.5:7b (4.7 GB)")).toBeInTheDocument();
    });
  });

  it("ucitava zapamcenu postavku za projekat i personu", async () => {
    render(<AiAssistant projectId={1} />);

    await waitFor(() => {
      expect(api.getModelPref).toHaveBeenCalledWith(1, "architect");
    });
  });

  it("radi i kada katalog pukne", async () => {
    vi.mocked(api.listAssistantModels).mockRejectedValue(new Error("pao"));

    render(<AiAssistant projectId={1} />);

    // Chat mora da ostane upotrebljiv — polje za unos je i dalje tu.
    expect(await screen.findByRole("textbox")).toBeInTheDocument();
  });
});
```

- [ ] **Korak 2: Pokreni test i potvrdi da pada**

```bash
npm --prefix apps/gui run test -- AiAssistant
```

Očekivano: FAIL sa `api.listAssistantModels is not a function`.

- [ ] **Korak 3: Dopuni `apps/gui/src/services/codiumApi.ts`**

Uz postojeće AI funkcije (oko linije 335) dodaj:

Tip modela se **ne definiše ponovo** — `CatalogModel` iz Task 9 je jedini opis
tog oblika. Uvezi ga (uvoz tipa se briše pri prevođenju, pa ne pravi zavisnost u
izvršnom kodu):

```ts
import type { CatalogModel } from "../features/codium/modelPicker";

export type { CatalogModel };

export type ModelPrefDto = {
  project_id: number | null;
  persona: string;
  model: string;
  provider: string;
};

export function listAssistantModels(): Promise<{ models: CatalogModel[] }> {
  return getJson<{ models: CatalogModel[] }>("/api/v1/codium/ai/models");
}

export function getModelPref(
  projectId: number | null,
  persona: string,
): Promise<{ pref: ModelPrefDto | null }> {
  const query = new URLSearchParams({ persona });
  if (projectId !== null) {
    query.set("project_id", String(projectId));
  }
  return getJson<{ pref: ModelPrefDto | null }>(
    `/api/v1/codium/ai/prefs?${query.toString()}`,
  );
}

export function setModelPref(payload: {
  project_id: number | null;
  persona: string;
  model: string;
  provider: string;
}): Promise<{ pref: ModelPrefDto }> {
  return putJson<{ pref: ModelPrefDto }, typeof payload>(
    "/api/v1/codium/ai/prefs",
    payload,
  );
}
```

Dopuni postojeći `askAssistant` opcionim poljima:

```ts
export function askAssistant(payload: {
  project_id: number | null;
  persona: string;
  message: string;
  history: AssistantChatTurn[];
  model?: string;
  provider?: string;
}): Promise<AssistantAnswer> {
```

I dodaj `provider: string; source: string;` u tip `AssistantAnswer`.

- [ ] **Korak 4: Dopuni `apps/gui/src/features/codium/AiAssistant.tsx`**

Dopuni uvoze:

```tsx
import {
  askAssistant,
  getModelPref,
  listAssistantModels,
  listAssistantPersonas,
  setModelPref,
  type AssistantChatTurn,
  type AssistantPersona,
  type CatalogModel,
} from "../../services/codiumApi";
import { formatModelLabel, groupModels } from "./modelPicker";
```

Dodaj stanje uz postojeće `useState` pozive:

```tsx
  const [models, setModels] = useState<CatalogModel[]>([]);
  const [model, setModel] = useState("");
```

Dodaj dva efekta ispod postojećeg efekta za persone:

```tsx
  // Katalog modela. Ako backend pukne, chat i dalje radi — dropdown ostaje prazan
  // i poziv ide na podrazumevani model sa servera.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { models: list } = await listAssistantModels();
        if (!cancelled) {
          setModels(list);
        }
      } catch {
        // Katalog nedostupan — bez dropdown-a, chat neometan.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Zapamćen izbor za par (projekat, persona).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { pref } = await getModelPref(projectId, persona);
        if (!cancelled) {
          setModel(pref?.model ?? "");
        }
      } catch {
        if (!cancelled) {
          setModel("");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, persona]);
```

Dodaj rukovalac izbora iznad `send()`:

```tsx
  function chooseModel(next: string): void {
    setModel(next);
    const chosen = models.find((m) => m.id === next);
    if (chosen === undefined) {
      return;
    }
    void setModelPref({
      project_id: projectId,
      persona,
      model: chosen.id,
      provider: chosen.provider,
    }).catch(() => {
      // Pamćenje je pogodnost, ne uslov — neuspeh ne obara izbor u sesiji.
    });
  }
```

U `send()`, u poziv `askAssistant`, dodaj izabrani model:

```tsx
      const answer = await askAssistant({
        project_id: projectId,
        persona,
        message: text,
        history,
        ...(model === "" ? {} : {
          model,
          provider: models.find((m) => m.id === model)?.provider,
        }),
      });
```

U JSX, odmah iza postojećeg `<select className="cai-persona">`, dodaj dropdown
modela:

```tsx
        <select
          className="cai-model"
          aria-label="Model"
          value={model}
          onChange={(event) => chooseModel(event.target.value)}
        >
          <option value="">Podrazumevani model</option>
          {groupModels(models).map((group) => (
            <optgroup key={group.title} label={group.title}>
              {group.models.map((m) => (
                <option key={m.id} value={m.id} disabled={!m.available}>
                  {formatModelLabel(m)}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
```

- [ ] **Korak 5: Dopuni `apps/gui/src/styles/codium-ai.css`**

Uz postojeće pravilo `.cai-persona` dodaj:

```css
/* Dropdown modela — isti ton kao izbor persone, uži jer natpisi znaju biti dugi. */
.cai-model {
  max-width: 14rem;
  border-radius: 0;
}

.cai-model option:disabled {
  color: var(--text-muted);
}
```

- [ ] **Korak 6: Pokreni testove i potvrdi da prolaze**

```bash
npm --prefix apps/gui run test -- AiAssistant modelPicker
```

Očekivano: 13 passed.

- [ ] **Korak 7: Pokreni ceo GUI paket i proveru tipova**

```bash
npm --prefix apps/gui run test
```

```bash
npm --prefix apps/gui exec tsc --noEmit
```

Očekivano: nula neuspeha, `tsc` bez izlaza.

- [ ] **Korak 8: Commit**

```bash
git add apps/gui/src
git commit -m "feat(gui): izbor modela u CODIUM chat okviru, zapamcen po projektu i personi"
```

---

### Task 11: Provera uživo i dev-log

**Fajlovi:**
- Create: `.ai/dev-log/entries/2026-08-24.md` (ili dopuna ako fajl postoji)
- Modify: `.ai/dev-log/INDEX.md`
- Modify: `.ai/izgradnja/codium/00-INDEX.md`

**Interfejsi:**
- Consumes: sve prethodno.
- Produces: ništa u kodu.

- [ ] **Korak 1: Pokreni backend i proveri katalog uživo**

Pokreni Ollama, pa API, pa:

```bash
curl -s http://localhost:8000/api/v1/codium/ai/models
```

Očekivano: JSON sa modelima koje `ollama list` prijavljuje, svaki sa
`"provider": "ollama"`, `"is_local": true` i popunjenim `size_gb`.

- [ ] **Korak 2: Proveri ponašanje kada Ollama ne radi**

Ugasi Ollama, pa ponovi isti poziv.

Očekivano: jedan red sa `"available": false` i popunjenim
`"unavailable_reason"` — **ne** prazna lista. Pokreni Ollama nazad.

- [ ] **Korak 3: Proveri chat u GUI-ju**

Otvori CODIUM workspace, izaberi model u dropdown-u, pošalji poruku, pa osveži
stranicu.

Očekivano: odgovor stiže; posle osvežavanja dropdown pokazuje isti model
(postavka je zapamćena); prebacivanje persone menja zapamćeni izbor nezavisno.

- [ ] **Korak 4: Pokreni sve testove poslednji put**

```bash
./.venv/Scripts/python.exe -m pytest -q
```

```bash
npm --prefix apps/gui run test
```

```bash
npm --prefix apps/gui exec tsc --noEmit
```

Zapiši tačne brojeve — idu u dev-log unos.

- [ ] **Korak 5: Napiši dev-log unos**

Koristi `scripts/devlog.py` (isti datum daje „Sesija N"). Unos pokriva: šta je
Faza 1 donela, tri nalaza iz speca koji su promenili plan (`core_router.py`,
`CodiumAssistant`, `vram_guard`), izbor `COALESCE` u UNIQUE indeksu i zašto,
i tačne brojeve testova.

- [ ] **Korak 6: Označi fazu kao završenu u planu izgradnje**

U `.ai/izgradnja/codium/00-INDEX.md`, u tabeli enterprise trake, upiši status
`zavrseno` i datum za red Faze 1.

- [ ] **Korak 7: Commit**

```bash
git add .ai/dev-log .ai/izgradnja/codium/00-INDEX.md
git commit -m "docs(dev-log): CODIUM Faza 1 - lokalni modeli u chat okviru"
```

---

## Šta ovaj plan namerno NE radi

- **Nema Claude-a ni OpenRouter-a.** Faza 2 i Faza 3 dobijaju svoje planove.
- **Nema vault-a.** Lokalni modeli ne traže tajnu.
- **Nema evidencije potrošnje.** Lokalni poziv ne košta; tabela `codium_ai_usage`
  stiže u Fazi 2.
- **Nema streaming-a.** Postojeći chat je ne-stream.
- **Nema tvrdog odbijanja velikog modela.** Vidi Nalaz 5 u specu.
- **Ne prepravlja fazne fajlove E trake.** To ide uz Fazu 2, kada se `10-E0` i
  `18-E8` ionako menjaju.
