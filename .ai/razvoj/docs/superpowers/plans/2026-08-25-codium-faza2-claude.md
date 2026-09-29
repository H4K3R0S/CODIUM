---
id: codium-b6277258-2026-08-25-codium-faza2-claude-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: 'CODIUM Faza 2 — Claude (Anthropic API): plan implementacije'
summary: '> **Za agentske radnike:** OBAVEZNA POD-VEŠTINA: koristi'
keywords:
- codium
- faza
- claude
- anthropic
- api
- implementacije
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-25-codium-faza2-claude.md
edges:
- type: references
  target: core-abe7bfd0-2026-08-24-codium-ai-provajderi-design-md
  weight: 0.3
- type: references
  target: core-d6179b67-2026-08-24-codium-faza1-lokalni-modeli-md
  weight: 0.3
---

# CODIUM Faza 2 — Claude (Anthropic API): plan implementacije

> **Za agentske radnike:** OBAVEZNA POD-VEŠTINA: koristi
> `superpowers:subagent-driven-development` (preporučeno) ili
> `superpowers:executing-plans` da odradiš plan zadatak po zadatak. Koraci
> koriste `- [ ]` sintaksu za praćenje.

**Cilj:** u istoj listi modela pojavljuje se grupa „Online" sa Claude modelima i
cenom; ispod chata stoji trošak poslednjeg poziva; potrošnja se evidentira.

**Arhitektura:** `SecretVault` nad `keyring` čuva ključ u OS keychain-u; baza čuva
samo alias. `AnthropicProvider` staje iza istog `ChatProvider` protokola koji je
Faza 1 napravila, pa katalog, ruter i GUI ne znaju da je stigao nov provajder.
Cene su statična tabela u kodu jer ih Models API ne vraća. Potrošnja ide u novu
`codium_ops.db`, odvojenu od poslovne baze.

**Tehnologije:** Python 3.14, FastAPI, SQLite, `anthropic` SDK, `keyring`, pytest;
React + TypeScript, Vitest.

**Spec:** [`docs/superpowers/specs/2026-08-24-codium-ai-provajderi-design.md`](../specs/2026-08-24-codium-ai-provajderi-design.md)

**Prethodna faza:** [`2026-08-24-codium-faza1-lokalni-modeli.md`](2026-08-24-codium-faza1-lokalni-modeli.md) — završena 2026-08-25, `codium.db` na v3.

**Gustina zadataka nije ujednačena.** Zadaci 1–5 nose pun kod i pune testove.
Zadaci 6–12 nose ugovor, ključne odluke i testove koji ih pinuju, ali ne i ceo
kod — on se dopisuje u brief neposredno pre slanja, kada se stvarno stanje
repozitorijuma vidi. To je namerno: pisati ceo kod za Task 11 pre nego što
Task 9 postoji znači nagađati potpise.

## Globalna ograničenja

- **Dve nove Python zavisnosti: `keyring` i `anthropic`.** Obe se registruju po
  **sva četiri** koraka iz `docs/DEPENDENCIES.md`. Nema drugih novih zavisnosti,
  ni Python ni npm.
- **Tajna nikada ne ulazi u SQLite, u `config/`, niti u bilo koji fajl pod
  verzijom.** U bazi stoji alias; vrednost živi u OS keychain-u.
- **Nijedan API odgovor ne sme da vrati vrednost tajne** — samo `has_secret: bool`.
- **`core/ai/core_router.py` i `core/ai/vram_guard.py` se ne diraju.**
- **`OllamaClient.generate()` se ne dira.**
- **Faza 1 ne sme da regresira:** lokalni modeli, `/ask` bez polja `model`,
  `DELETE /prefs`, i označavanje embedding modela moraju da rade nepromenjeno.
- Podrazumevan Claude model je **`claude-opus-5`**. Mišljenje je
  `thinking={"type": "adaptive"}`. `max_tokens` je 16000 za ne-stream poziv.
- **Zabranjeno**, jer trenutni modeli to odbijaju sa HTTP 400: `budget_tokens`
  unutar `thinking`, i prefill poslednje `assistant` poruke.
- Komentari i docstring-ovi na srpskom, obrazac `# ========== NASLOV ==========`.
- Testovi: `./.venv/Scripts/python.exe -m pytest`, nikad sistemski python.
  GUI: `npm --prefix apps/gui run test`, tipovi `npm --prefix apps/gui run typecheck:test`.
- **`typecheck:test` je crven i pre ovog rada** — četiri greške u
  `CoreDockLayout.tsx`, `CodiumPage.test.tsx`, `CodiumWorkspace.test.tsx`,
  `CodiumWorkspace.tsx`. Ne popravljaju se. Prag: iste te četiri, nijedna peta.
- Polazna linija: **1060 pytest, 542 vitest**, oba zelena.
- **Nijedan test ne sme da zove pravi Anthropic API.** Svi testovi idu protiv
  lažnog SDK klijenta. Pravi poziv se radi samo u zadatku provere uživo.

---

## Struktura fajlova

| Fajl | Odgovornost |
|---|---|
| `core/security/secrets.py` | `SecretVault` nad `keyring`; CORE nivo, ne CODIUM |
| `core/ai/pricing.py` | statična tabela cena po modelu |
| `core/ai/providers/anthropic.py` | `AnthropicProvider` iza `ChatProvider` protokola |
| `core/ai/usage.py` | `UsageRecorder` — upis poziva u ops bazu |
| `core/domains/codium/integrations/models.py` | `Connector`, `ConnectorKind`, `ConnectorStatus` |
| `core/domains/codium/integrations/repository.py` | CRUD nad `codium_connectors` |
| `core/domains/codium/integrations/service.py` | `ConnectorService` — tajna u vault, alias u bazu |
| `core/domains/codium/integrations/providers/base.py` | `ConnectorProvider` protokol |
| `core/domains/codium/integrations/providers/anthropic.py` | `test()` konektora |
| `core/domains/codium/ops_migrations.py` | migracije `codium_ops.db` |
| `core/domains/codium/migrations.py` | *(izmena)* v4 — `codium_connectors` |
| `core/domains/codium/paths.py` | *(izmena)* `ops_database` |
| `core/domains/codium/runtime.py` | *(izmena)* inicijalizacija ops baze |
| `core/domains/codium/assistant/assistant_service.py` | *(izmena)* `AssistantAnswer` nosi tokene |
| `apps/api/routers/codium_integrations.py` | rute konektora |
| `apps/api/routers/codium_ai.py` | *(izmena)* `/usage` + upis potrošnje |
| `apps/gui/src/features/codium/ApiKeyDialog.tsx` | minimalan unos ključa |

---

### Task 1: Registracija zavisnosti `keyring` i `anthropic`

**Fajlovi:**
- Modify: `core/foundation/dependencies.py`
- Create: `scripts/install/keyring.ps1`, `scripts/install/anthropic.ps1`
- Modify: `core/foundation/installer.py`
- Modify: `docs/DEPENDENCIES.md`
- Modify: `requirements.txt`
- Test: `tests/test_dependencies.py`

**Interfejsi:**
- Consumes: ništa.
- Produces: ključevi `keyring` i `anthropic` u `CORE_DEPENDENCIES`. Svi naredni
  zadaci smeju da uvoze te biblioteke.

Ovo ide prvo jer bez registracije indikator pored „CORE Online" i dugme INSTALL
ne znaju za alat — tačno ono što se dogodilo sa Monaco i xterm paketima.

- [ ] **Korak 1: Napiši test koji pada**

U `tests/test_dependencies.py`, uz postojeći test koji proverava skup ključeva:

```python
def test_registar_zna_za_keyring_i_anthropic():
    keys = {d.key for d in CORE_DEPENDENCIES}
    assert {"keyring", "anthropic"} <= keys


def test_keyring_i_anthropic_imaju_install_skripte():
    from core.foundation.installer import INSTALL_SCRIPTS

    assert INSTALL_SCRIPTS["keyring"] == "keyring.ps1"
    assert INSTALL_SCRIPTS["anthropic"] == "anthropic.ps1"
```

- [ ] **Korak 2: Pokreni i potvrdi pad**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_dependencies.py -v
```

Očekivano: FAIL na oba nova testa.

- [ ] **Korak 3: Dodaj unose u `CORE_DEPENDENCIES`**

```python
    Dependency(
        key="keyring",
        label="keyring",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="keyring",
        purpose="Bezbedno čuvanje API ključeva u OS keychain-u (Credential Manager).",
        install_hint="python -m pip install keyring",
        installer=DependencyInstaller.PIP,
    ),
    Dependency(
        key="anthropic",
        label="anthropic SDK",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="anthropic",
        purpose="Zvanični klijent za Claude modele (CODIUM AI chat).",
        install_hint="python -m pip install anthropic",
        installer=DependencyInstaller.PIP,
    ),
```

Proveri tačna imena polja protiv postojećeg unosa u istom fajlu pre nego što
zalepiš — ako se razlikuju, prati postojeći oblik, ne ovaj.

- [ ] **Korak 4: Napiši install skripte**

`scripts/install/keyring.ps1` (obrazac: postojeći `deep_translator.ps1`):

```powershell
# Instalira `keyring` u projektni venv.
#
# Sluzi za cuvanje API kljuceva u OS keychain-u (na Windows-u: Credential
# Manager). Bez njega SecretVault degradira: get() vraca None i servis
# prijavljuje da keychain nije dostupan — nikad ne pada na cuvanje u fajl.

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Output "GRESKA: nema venv-a na $python"
    exit 1
}

& $python -m pip install keyring
exit $LASTEXITCODE
```

`scripts/install/anthropic.ps1` — isto, sa `anthropic` umesto `keyring` i
komentarom da je to zvanični SDK za Claude modele.

- [ ] **Korak 5: Upiši u `INSTALL_SCRIPTS`**

```python
    "keyring": "keyring.ps1",
    "anthropic": "anthropic.ps1",
```

- [ ] **Korak 6: Dopuni `docs/DEPENDENCIES.md` i `requirements.txt`**

Red u tabeli „Katalog alata" za svaki alat, i po jedna linija u
`requirements.txt`.

- [ ] **Korak 7: Instaliraj i potvrdi**

```bash
./.venv/Scripts/python.exe -m pip install keyring anthropic
```

```bash
./.venv/Scripts/python.exe -m pytest tests/test_dependencies.py -v
```

Očekivano: sve prolazi.

- [ ] **Korak 8: Commit**

```bash
git add core/foundation scripts/install docs/DEPENDENCIES.md requirements.txt tests/test_dependencies.py
git commit -m "feat(deps): registruj keyring i anthropic po sva cetiri koraka"
```

---

### Task 2: `SecretVault`

**Fajlovi:**
- Create: `core/security/secrets.py`
- Test: `tests/test_secret_vault.py`

**Interfejsi:**
- Consumes: `keyring` (Task 1).
- Produces: `SecretVault` sa `set(alias, value)`, `get(alias) -> str | None`,
  `delete(alias)`, `exists(alias) -> bool`, i `VAULT_SERVICE = "CORE"`.
  Task 5 (`ConnectorService`) i Task 7 (`AnthropicProvider`) ga koriste.

Backend keyring-a se ubrizgava, da testovi ne diraju pravi Credential Manager.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_secret_vault.py`:

```python
# ========== TESTOVI: SecretVault (tajne u OS keychain-u) ==========
from __future__ import annotations

from core.security.secrets import SecretVault


class _LazniKeychain:
    """Keyring backend u memoriji."""

    def __init__(self) -> None:
        self.podaci: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self.podaci[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self.podaci.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        del self.podaci[(service, username)]


class _MrtavKeychain:
    """Keychain koji nije dostupan — svaki poziv puca."""

    def set_password(self, service, username, password):
        raise RuntimeError("keychain nedostupan")

    def get_password(self, service, username):
        raise RuntimeError("keychain nedostupan")

    def delete_password(self, service, username):
        raise RuntimeError("keychain nedostupan")


def test_upis_pa_citanje_vraca_vrednost():
    vault = SecretVault(backend=_LazniKeychain())

    vault.set("anthropic", "tajna-vrednost")

    assert vault.get("anthropic") == "tajna-vrednost"


def test_nepostojeci_alias_vraca_none():
    assert SecretVault(backend=_LazniKeychain()).get("nema") is None


def test_exists_prati_upis_i_brisanje():
    vault = SecretVault(backend=_LazniKeychain())

    assert vault.exists("anthropic") is False
    vault.set("anthropic", "x")
    assert vault.exists("anthropic") is True
    vault.delete("anthropic")
    assert vault.exists("anthropic") is False


def test_brisanje_nepostojeceg_ne_puca():
    SecretVault(backend=_LazniKeychain()).delete("nema")


def test_nedostupan_keychain_daje_none_a_ne_izuzetak():
    # Degradacija je uslov: bez keychain-a servis mora da javi da tajne nema,
    # nikad da padne i nikad da tajnu upiše u fajl.
    vault = SecretVault(backend=_MrtavKeychain())

    assert vault.get("anthropic") is None
    assert vault.exists("anthropic") is False
    assert vault.available() is False


def test_dostupan_keychain_prijavljuje_available():
    assert SecretVault(backend=_LazniKeychain()).available() is True


def test_upis_u_nedostupan_keychain_die_vault_unavailable():
    from core.security.secrets import VaultUnavailable

    import pytest

    with pytest.raises(VaultUnavailable):
        SecretVault(backend=_MrtavKeychain()).set("anthropic", "x")
```

Uvoz `pytest` premesti na vrh fajla — bez `# noqa`.

- [ ] **Korak 2: Pokreni i potvrdi pad**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_secret_vault.py -v
```

Očekivano: `ModuleNotFoundError: No module named 'core.security.secrets'`.

- [ ] **Korak 3: Napiši `core/security/secrets.py`**

```python
# ========== VAULT TAJNI ==========
# Jedno mesto na kome CORE drži API ključeve i lozinke. Vrednost živi u OS
# keychain-u (na Windows-u: Credential Manager), nikad u SQLite-u, nikad u
# config/, nikad u fajlu pod verzijom.
#
# Modul je na CORE nivou, ne u CODIUM-u, jer će ga koristiti i drugi domeni.
from __future__ import annotations

from typing import Protocol


class VaultUnavailable(RuntimeError):
    """Keychain nije dostupan, pa se tajna ne može upisati."""


class KeychainBackend(Protocol):
    """Podskup `keyring` API-ja koji vault stvarno koristi."""

    def set_password(self, service: str, username: str, password: str) -> None: ...
    def get_password(self, service: str, username: str) -> str | None: ...
    def delete_password(self, service: str, username: str) -> None: ...


# Ime servisa pod kojim CORE upisuje sve svoje tajne u keychain.
VAULT_SERVICE = "CORE"


class SecretVault:
    """Čuva tajne po aliasu. Backend se ubrizgava radi testiranja."""

    def __init__(self, backend: KeychainBackend | None = None) -> None:
        self._backend = backend if backend is not None else self._default_backend()

    @staticmethod
    def _default_backend() -> KeychainBackend | None:
        try:
            import keyring
        except ImportError:
            return None
        return keyring

    def available(self) -> bool:
        """Da li keychain odgovara. Čitanje ne sme da padne ni kad ne odgovara."""

        if self._backend is None:
            return False
        try:
            self._backend.get_password(VAULT_SERVICE, "__proba__")
        except Exception:  # noqa: BLE001 — svaki backend puca na svoj način
            return False
        return True

    def set(self, alias: str, value: str) -> None:
        if self._backend is None:
            raise VaultUnavailable("keyring nije instaliran")
        try:
            self._backend.set_password(VAULT_SERVICE, alias, value)
        except Exception as error:  # noqa: BLE001
            raise VaultUnavailable(str(error)) from error

    def get(self, alias: str) -> str | None:
        """Vrednost tajne, ili None ako je nema — i ako keychain ne radi."""

        if self._backend is None:
            return None
        try:
            return self._backend.get_password(VAULT_SERVICE, alias)
        except Exception:  # noqa: BLE001
            return None

    def delete(self, alias: str) -> None:
        """Briše tajnu. Brisanje nepostojeće nije greška."""

        if self._backend is None:
            return
        try:
            self._backend.delete_password(VAULT_SERVICE, alias)
        except Exception:  # noqa: BLE001
            return

    def exists(self, alias: str) -> bool:
        return self.get(alias) is not None
```

Ako `core/security/` ne postoji, napravi ga sa praznim `__init__.py`.

- [ ] **Korak 4: Pokreni i potvrdi prolaz**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_secret_vault.py -v
```

Očekivano: 7 passed.

- [ ] **Korak 5: Commit**

```bash
git add core/security tests/test_secret_vault.py
git commit -m "feat(core-security): SecretVault nad OS keychain-om"
```

---

### Task 3: Tabela cena

**Fajlovi:**
- Create: `core/ai/pricing.py`
- Test: `tests/test_pricing.py`

**Interfejsi:**
- Consumes: ništa.
- Produces: `price_for(model_id) -> tuple[float, float] | None` (ulaz, izlaz po
  milionu tokena) i `cost_usd(model_id, prompt_tokens, output_tokens) -> float`.
  Task 7 i Task 8 ih koriste.

**Zašto statična tabela:** Anthropic `GET /v1/models` vraća `id`, `display_name`,
`max_input_tokens`, `max_tokens` i `capabilities` — **cenu ne vraća**. Lista
modela je zato živa iz API-ja, a cena je održavana ručno.

**Pažnja — uvodna cena koja ističe.** `claude-sonnet-5` ima uvodnu cenu
$2 / $10 po milionu tokena **do 2026-08-31**, posle čega prelazi na $3 / $15.
Tabela mora da nosi oba broja i datum prelaska, inače od 1. septembra tiho laže.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_pricing.py`:

```python
# ========== TESTOVI: tabela cena modela ==========
from __future__ import annotations

from datetime import date

from core.ai.pricing import cost_usd, price_for


def test_poznat_model_ima_cenu():
    ulaz, izlaz = price_for("claude-opus-5")

    assert ulaz == 5.0
    assert izlaz == 25.0


def test_nepoznat_model_nema_cenu():
    assert price_for("izmisljen-model") is None


def test_lokalni_model_je_besplatan():
    assert cost_usd("qwen2.5:7b", 1000, 1000) == 0.0


def test_trosak_se_racuna_po_milionu_tokena():
    # 1M ulaznih po $5 + 1M izlaznih po $25.
    assert cost_usd("claude-opus-5", 1_000_000, 1_000_000) == 30.0


def test_trosak_srazmeran_za_male_brojeve():
    assert cost_usd("claude-opus-5", 1000, 500) == round(
        1000 / 1_000_000 * 5.0 + 500 / 1_000_000 * 25.0, 6,
    )


def test_sonnet_ima_uvodnu_cenu_do_kraja_avgusta():
    # Uvodna cena vazi do 2026-08-31 ukljucivo.
    assert price_for("claude-sonnet-5", na_dan=date(2026, 8, 25)) == (2.0, 10.0)


def test_sonnet_posle_isteka_ima_punu_cenu():
    assert price_for("claude-sonnet-5", na_dan=date(2026, 9, 1)) == (3.0, 15.0)
```

- [ ] **Korak 2: Pokreni i potvrdi pad**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pricing.py -v
```

Očekivano: `ModuleNotFoundError: No module named 'core.ai.pricing'`.

- [ ] **Korak 3: Napiši `core/ai/pricing.py`**

```python
# ========== CENE MODELA ==========
# Anthropic Models API (`GET /v1/models`) vraća id, display_name,
# max_input_tokens, max_tokens i capabilities — ali NE vraća cenu. Zato je cena
# ručno održavana tabela.
#
# Proveri na https://www.anthropic.com/pricing pre nego što je menjaš.
# Poslednja provera: 2026-08-25.
#
# Lokalni modeli (Ollama) nemaju unos — trošak im je nula.
from __future__ import annotations

from datetime import date

# (ulaz, izlaz) u dolarima po milionu tokena.
_CENE: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

# Uvodne cene sa rokom. Posle roka važi vrednost iz `_CENE`.
# Bez ovoga bi tabela od 1.9.2026. tiho prikazivala nižu cenu nego što se
# stvarno naplaćuje.
_UVODNE: dict[str, tuple[tuple[float, float], date]] = {
    "claude-sonnet-5": ((2.0, 10.0), date(2026, 8, 31)),
}


def price_for(model_id: str, *,
              na_dan: date | None = None) -> tuple[float, float] | None:
    """Cena ulaza i izlaza po milionu tokena, ili None za nepoznat model."""

    if model_id not in _CENE:
        return None

    uvodna = _UVODNE.get(model_id)
    if uvodna is not None:
        vrednost, vazi_do = uvodna
        if (na_dan or date.today()) <= vazi_do:
            return vrednost

    return _CENE[model_id]


def cost_usd(model_id: str, prompt_tokens: int, output_tokens: int, *,
             na_dan: date | None = None) -> float:
    """Trošak jednog poziva. Nepoznat model (npr. lokalni) košta nula."""

    cena = price_for(model_id, na_dan=na_dan)
    if cena is None:
        return 0.0
    ulaz, izlaz = cena
    return round(
        prompt_tokens / 1_000_000 * ulaz + output_tokens / 1_000_000 * izlaz,
        6,
    )
```

- [ ] **Korak 4: Pokreni i potvrdi prolaz**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pricing.py -v
```

Očekivano: 7 passed.

- [ ] **Korak 5: Commit**

```bash
git add core/ai/pricing.py tests/test_pricing.py
git commit -m "feat(core-ai): staticna tabela cena sa rokom uvodne cene"
```

---

### Task 4: `AnthropicProvider`

**Fajlovi:**
- Create: `core/ai/providers/anthropic.py`
- Modify: `core/ai/providers/__init__.py`
- Test: `tests/test_anthropic_provider.py`

**Interfejsi:**
- Consumes: `ChatMessage`, `ChatResult`, `ModelInfo`, `ProviderUnavailable`
  (Faza 1); `price_for` (Task 3); `SecretVault` (Task 2).
- Produces: `AnthropicProvider(vault, alias="anthropic", client_factory=None)` sa
  `name = "anthropic"`, `is_local = False`. Task 9 ga registruje u runtime.

**Dve stvari koje se lako pogreše:**

1. **Anthropic ne prima `system` kao poruku.** `system` je top-level parametar
   `messages.create()`. Naš `ChatMessage` niz počinje sistemskom porukom (tako je
   Faza 1 napravila `_build_messages`), pa provajder mora da je **izdvoji** i
   pošalje odvojeno. Ostale poruke idu kao `messages`. Ako ovo promašiš, API
   vraća grešku o nedozvoljenoj ulozi.
2. **Bez ključa provajder ne sme da padne** — mora da digne `ProviderUnavailable`
   sa razlogom „nema API ključa", da bi katalog prikazao red koji GUI pretvara u
   „Potreban API ključ".

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_anthropic_provider.py`:

```python
# ========== TESTOVI: Anthropic provajder ==========
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.ai.providers import ChatMessage, ProviderUnavailable
from core.ai.providers.anthropic import AnthropicProvider


class _LazniVault:
    def __init__(self, vrednost: str | None = "sk-ant-test") -> None:
        self.vrednost = vrednost

    def get(self, alias: str) -> str | None:
        return self.vrednost


class _LazniMessages:
    def __init__(self, odgovor) -> None:
        self._odgovor = odgovor
        self.poziv: dict = {}

    def create(self, **kwargs):
        self.poziv = kwargs
        if isinstance(self._odgovor, Exception):
            raise self._odgovor
        return self._odgovor


class _LazniModels:
    def __init__(self, stavke) -> None:
        self._stavke = stavke

    def list(self):
        if isinstance(self._stavke, Exception):
            raise self._stavke
        return SimpleNamespace(data=self._stavke)


class _LazniKlijent:
    def __init__(self, odgovor=None, modeli=None) -> None:
        self.messages = _LazniMessages(odgovor)
        self.models = _LazniModels(modeli if modeli is not None else [])


def _odgovor(tekst="Zdravo.", ulaz=12, izlaz=5):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=tekst)],
        usage=SimpleNamespace(input_tokens=ulaz, output_tokens=izlaz),
        model="claude-opus-5",
        stop_reason="end_turn",
    )


def _provider(klijent=None, vault=None) -> AnthropicProvider:
    klijent = klijent or _LazniKlijent(_odgovor())
    return AnthropicProvider(
        vault=vault or _LazniVault(),
        client_factory=lambda kljuc: klijent,
    )


# ---------- kljuc ----------

def test_bez_kljuca_models_die_provider_unavailable():
    provider = _provider(vault=_LazniVault(vrednost=None))

    assert provider.available() is False
    with pytest.raises(ProviderUnavailable, match="ključ"):
        provider.models()


def test_bez_kljuca_chat_die_provider_unavailable():
    provider = _provider(vault=_LazniVault(vrednost=None))

    with pytest.raises(ProviderUnavailable):
        provider.chat([ChatMessage(role="user", content="a")], "claude-opus-5")


# ---------- katalog ----------

def test_models_spaja_listu_sa_cenama():
    klijent = _LazniKlijent(modeli=[
        SimpleNamespace(id="claude-opus-5", display_name="Claude Opus 5",
                        max_input_tokens=1_000_000),
    ])

    info = _provider(klijent).models()[0]

    assert info.id == "claude-opus-5"
    assert info.provider == "anthropic"
    assert info.is_local is False
    assert info.price_in_per_mtok == 5.0
    assert info.price_out_per_mtok == 25.0
    assert info.context_window == 1_000_000
    assert info.available is True


def test_model_bez_cene_ostaje_u_listi_sa_nulom():
    # Nov model koji tabela cena jos ne zna ne sme da nestane iz izbornika.
    klijent = _LazniKlijent(modeli=[
        SimpleNamespace(id="claude-nesto-novo", display_name="Novo",
                        max_input_tokens=200_000),
    ])

    info = _provider(klijent).models()[0]

    assert info.id == "claude-nesto-novo"
    assert info.price_in_per_mtok == 0.0


# ---------- razgovor ----------

def test_chat_salje_system_odvojeno_a_ne_kao_poruku():
    klijent = _LazniKlijent(_odgovor())

    _provider(klijent).chat([
        ChatMessage(role="system", content="Ti si CORE."),
        ChatMessage(role="user", content="Pitanje"),
    ], "claude-opus-5")

    poziv = klijent.messages.poziv
    assert poziv["system"] == "Ti si CORE."
    assert poziv["messages"] == [{"role": "user", "content": "Pitanje"}]
    assert all(m["role"] != "system" for m in poziv["messages"])


def test_chat_koristi_adaptivno_misljenje_i_max_tokens():
    klijent = _LazniKlijent(_odgovor())

    _provider(klijent).chat([ChatMessage(role="user", content="a")], "claude-opus-5")

    poziv = klijent.messages.poziv
    assert poziv["thinking"] == {"type": "adaptive"}
    assert poziv["max_tokens"] == 16000
    # budget_tokens i prefill su zabranjeni — trenutni modeli ih odbijaju sa 400.
    assert "budget_tokens" not in str(poziv.get("thinking"))


def test_chat_cita_tekst_i_tokene():
    rezultat = _provider(_LazniKlijent(_odgovor("Odgovor.", 20, 7))).chat(
        [ChatMessage(role="user", content="a")], "claude-opus-5",
    )

    assert rezultat.text == "Odgovor."
    assert rezultat.provider == "anthropic"
    assert rezultat.prompt_tokens == 20
    assert rezultat.output_tokens == 7
    assert rezultat.duration_ms >= 0


def test_chat_spaja_vise_tekstualnih_blokova():
    odgovor = SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking="..."),
            SimpleNamespace(type="text", text="Prvi. "),
            SimpleNamespace(type="text", text="Drugi."),
        ],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        model="claude-opus-5",
        stop_reason="end_turn",
    )

    rezultat = _provider(_LazniKlijent(odgovor)).chat(
        [ChatMessage(role="user", content="a")], "claude-opus-5",
    )

    # Blok mišljenja se preskače, tekstualni se spajaju.
    assert rezultat.text == "Prvi. Drugi."


def test_greska_sdk_a_postaje_provider_unavailable():
    klijent = _LazniKlijent(RuntimeError("401 nevalidan kljuc"))

    with pytest.raises(ProviderUnavailable, match="401"):
        _provider(klijent).chat(
            [ChatMessage(role="user", content="a")], "claude-opus-5",
        )
```

- [ ] **Korak 2: Pokreni i potvrdi pad**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_anthropic_provider.py -v
```

Očekivano: `ModuleNotFoundError: No module named 'core.ai.providers.anthropic'`.

- [ ] **Korak 3: Napiši `core/ai/providers/anthropic.py`**

```python
# ========== PROVAJDER: ANTHROPIC (Claude) ==========
# Direktan Anthropic API kroz zvanični SDK. Ključ se uzima iz vault-a u trenutku
# upotrebe — nikad se ne drži u konfiguraciji ni u bazi.
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from core.ai.pricing import price_for
from core.ai.providers.base import (
    ChatMessage,
    ChatResult,
    ModelInfo,
    ProviderUnavailable,
)

# Alias pod kojim vault čuva Anthropic ključ.
DEFAULT_ALIAS = "anthropic"

# Podrazumevani model i parametri poziva. `budget_tokens` i prefill poslednje
# assistant poruke su ZABRANJENI — trenutni modeli ih odbijaju sa HTTP 400.
DEFAULT_MODEL = "claude-opus-5"
MAX_TOKENS = 16000
THINKING: dict[str, str] = {"type": "adaptive"}

ClientFactory = Callable[[str], Any]


class AnthropicProvider:
    """Claude modeli kroz zvanični `anthropic` SDK."""

    name = "anthropic"
    is_local = False

    def __init__(self, vault: Any, *, alias: str = DEFAULT_ALIAS,
                 client_factory: ClientFactory | None = None) -> None:
        self._vault = vault
        self._alias = alias
        self._client_factory = client_factory or self._default_factory

    @staticmethod
    def _default_factory(api_key: str) -> Any:
        import anthropic

        return anthropic.Anthropic(api_key=api_key)

    # ---------- interno ----------

    def _client(self) -> Any:
        kljuc = self._vault.get(self._alias)
        if not kljuc:
            raise ProviderUnavailable(
                "Nema API ključa za Anthropic — unesi ga u podešavanjima.",
            )
        try:
            return self._client_factory(kljuc)
        except Exception as error:  # noqa: BLE001 — SDK puca na svoj način
            raise ProviderUnavailable(str(error)) from error

    # ---------- protokol ----------

    def available(self) -> bool:
        return bool(self._vault.get(self._alias))

    def models(self) -> list[ModelInfo]:
        klijent = self._client()
        try:
            odgovor = klijent.models.list()
        except Exception as error:  # noqa: BLE001
            raise ProviderUnavailable(str(error)) from error

        return [self._to_info(m) for m in getattr(odgovor, "data", [])]

    def chat(self, messages: list[ChatMessage], model: str,
             **options: object) -> ChatResult:
        klijent = self._client()
        system, ostale = self._razdvoji_system(messages)
        started = time.perf_counter()

        payload: dict[str, Any] = {
            "model": model or DEFAULT_MODEL,
            "max_tokens": MAX_TOKENS,
            "thinking": dict(THINKING),
            "messages": ostale,
        }
        if system:
            payload["system"] = system

        try:
            odgovor = klijent.messages.create(**payload)
        except Exception as error:  # noqa: BLE001
            raise ProviderUnavailable(str(error)) from error

        usage = getattr(odgovor, "usage", None)
        return ChatResult(
            text=self._tekst(odgovor),
            model=model,
            provider=self.name,
            prompt_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ---------- pomoćno ----------

    @staticmethod
    def _razdvoji_system(
        messages: list[ChatMessage],
    ) -> tuple[str, list[dict[str, str]]]:
        """Anthropic prima `system` kao top-level parametar, ne kao poruku."""

        delovi = [m.content for m in messages if m.role == "system"]
        ostale = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        return "\n\n".join(delovi), ostale

    @staticmethod
    def _tekst(odgovor: Any) -> str:
        """Spaja tekstualne blokove; blokove mišljenja preskače."""

        delovi = [
            str(getattr(blok, "text", ""))
            for blok in getattr(odgovor, "content", [])
            if getattr(blok, "type", "") == "text"
        ]
        return "".join(delovi)

    @classmethod
    def _to_info(cls, model: Any) -> ModelInfo:
        model_id = str(getattr(model, "id", ""))
        cena = price_for(model_id)
        ulaz, izlaz = cena if cena is not None else (0.0, 0.0)
        return ModelInfo(
            id=model_id,
            label=str(getattr(model, "display_name", "") or model_id),
            provider=cls.name,
            is_local=False,
            context_window=int(getattr(model, "max_input_tokens", 0) or 0),
            price_in_per_mtok=ulaz,
            price_out_per_mtok=izlaz,
        )
```

- [ ] **Korak 4: Reeksportuj u `core/ai/providers/__init__.py`**

Dodaj `AnthropicProvider` u uvoz i u `__all__`.

- [ ] **Korak 5: Pokreni i potvrdi prolaz**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_anthropic_provider.py tests/test_chat_providers.py -v
```

Očekivano: novi testovi prolaze, Faza 1 testovi bez regresije.

- [ ] **Korak 6: Commit**

```bash
git add core/ai/providers tests/test_anthropic_provider.py
git commit -m "feat(core-ai): AnthropicProvider iza ChatProvider protokola"
```

---

### Task 5: Migracija `codium.db` v4 — konektori

**Fajlovi:**
- Modify: `core/domains/codium/migrations.py`
- Create: `core/domains/codium/integrations/__init__.py`, `models.py`, `repository.py`
- Test: `tests/test_codium_connectors.py`

**Interfejsi:**
- Consumes: ništa iz Faze 2.
- Produces: `Connector`, `ConnectorKind`, `ConnectorStatus`,
  `ConnectorRepository` sa `create`, `list`, `get`, `update`, `delete`,
  `mark_tested`. Task 6 (`ConnectorService`) ih koristi.

Migracija je **aditivna**: `CODIUM_MIGRATION_V1`–`V3` se ne diraju, dodaje se V4
i proširuje `CODIUM_MIGRATIONS`.

- [ ] **Korak 1: Napiši test koji pada**

Novi fajl `tests/test_codium_connectors.py`:

```python
# ========== TESTOVI: konektori (baza) ==========
from __future__ import annotations

import pytest

from core.domains.codium import initialize_codium_database
from core.domains.codium.integrations.models import (
    ConnectorCreate,
    ConnectorKind,
    ConnectorStatus,
)
from core.domains.codium.integrations.repository import ConnectorRepository


@pytest.fixture()
def repository(tmp_path):
    database = tmp_path / "codium_conn.db"
    initialize_codium_database(database)
    return ConnectorRepository(database)


def _create(name="Claude", alias="anthropic"):
    return ConnectorCreate(
        name=name, kind=ConnectorKind.ANTHROPIC, secret_alias=alias,
    )


def test_nov_konektor_dobija_status_unconfigured(repository):
    konektor = repository.create(_create())

    assert konektor.id > 0
    assert konektor.kind is ConnectorKind.ANTHROPIC
    assert konektor.status is ConnectorStatus.UNCONFIGURED
    assert konektor.secret_alias == "anthropic"


def test_baza_cuva_alias_a_ne_vrednost(repository):
    repository.create(_create(alias="anthropic"))

    # Ceo sadrzaj tabele ne sme nigde da nosi vrednost tajne.
    sve = repository.list()
    spojeno = " ".join(
        f"{k.name}{k.kind.value}{k.secret_alias}{k.config_json}" for k in sve
    )
    assert "sk-ant" not in spojeno


def test_ime_konektora_je_jedinstveno(repository):
    repository.create(_create(name="Claude"))

    with pytest.raises(Exception):
        repository.create(_create(name="Claude"))


def test_brisanje_uklanja_konektor(repository):
    konektor = repository.create(_create())

    assert repository.delete(konektor.id) is True
    assert repository.get(konektor.id) is None


def test_mark_tested_upisuje_status_i_vreme(repository):
    konektor = repository.create(_create())

    repository.mark_tested(konektor.id, ok=True, message="")

    posle = repository.get(konektor.id)
    assert posle.status is ConnectorStatus.OK
    assert posle.last_tested_at != ""
    assert posle.last_error == ""


def test_mark_tested_neuspeh_upisuje_gresku(repository):
    konektor = repository.create(_create())

    repository.mark_tested(konektor.id, ok=False, message="401")

    posle = repository.get(konektor.id)
    assert posle.status is ConnectorStatus.ERROR
    assert "401" in posle.last_error
```

- [ ] **Korak 2: Pokreni i potvrdi pad**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_connectors.py -v
```

Očekivano: `ModuleNotFoundError` za `integrations`.

- [ ] **Korak 3: Dodaj migraciju v4**

Ispod `CODIUM_MIGRATION_V3` u `core/domains/codium/migrations.py`:

```python
# ---------- v4: konektori (Faza 2 AI provajdera) ----------

CODIUM_MIGRATION_V4 = DatabaseMigration(
    scope="codium",
    version=4,
    name="create_connectors",
    statements=(
        # secret_alias je KLJUC u vault-u, nikad vrednost tajne.
        """
        CREATE TABLE codium_connectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            secret_alias TEXT,
            status TEXT NOT NULL DEFAULT 'unconfigured',
            last_tested_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE UNIQUE INDEX idx_codium_connectors_name "
        "ON codium_connectors (name)",
    ),
)
```

I dopuni tuple:

```python
CODIUM_MIGRATIONS = (
    CODIUM_MIGRATION_V1,
    CODIUM_MIGRATION_V2,
    CODIUM_MIGRATION_V3,
    CODIUM_MIGRATION_V4,
)
```

- [ ] **Korak 4: Napiši `models.py` i `repository.py`**

`core/domains/codium/integrations/models.py`:

```python
# ========== MODELI KONEKTORA ==========
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConnectorKind(str, Enum):
    """Tipovi konektora. U Fazi 2 se koristi samo `anthropic`."""

    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    GITHUB = "github"
    DOCKER_REGISTRY = "docker_registry"
    SSH_HOST = "ssh_host"
    SMTP = "smtp"


class ConnectorStatus(str, Enum):
    UNCONFIGURED = "unconfigured"
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True)
class ConnectorCreate:
    name: str
    kind: ConnectorKind
    secret_alias: str | None = None
    config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Connector:
    id: int
    name: str
    kind: ConnectorKind
    config_json: str
    secret_alias: str | None
    status: ConnectorStatus
    last_tested_at: str
    last_error: str
    created_at: str
    updated_at: str
```

`repository.py` prati obrazac `CodiumRepository`: `core_database_connection`,
`lastrowid is None` provera, `_row_to_connector` statička metoda. Metode:
`create`, `list`, `get`, `delete`, `mark_tested(id, *, ok, message)`.

- [ ] **Korak 5: Pokreni i potvrdi prolaz**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_codium_connectors.py tests/test_codium_model_prefs.py tests/test_codium_service.py -v
```

Očekivano: novi prolaze, postojeći bez regresije (migracija je aditivna).

- [ ] **Korak 6: Commit**

```bash
git add core/domains/codium tests/test_codium_connectors.py
git commit -m "feat(codium): migracija v4 - tabela konektora"
```

---

### Task 6: `ConnectorService` — tajna u vault, alias u bazu

**Fajlovi:**
- Create: `core/domains/codium/integrations/service.py`
- Create: `core/domains/codium/integrations/providers/base.py`, `providers/anthropic.py`
- Test: `tests/test_codium_connector_service.py`

**Interfejsi:**
- Consumes: `SecretVault` (Task 2), `ConnectorRepository` (Task 5).
- Produces: `ConnectorService(repository, vault, providers)` sa
  `create(payload, secret)`, `update_secret(id, secret)`, `delete(id)`,
  `test_connection(id) -> ConnectorProbe`. Task 9 ga izlaže kroz API.

Ključno ponašanje: `create` upisuje **alias** u bazu i **vrednost** u vault;
`delete` briše i tajnu, ne samo red.

- [ ] **Korak 1: Napiši test koji pada**

```python
# ========== TESTOVI: servis konektora ==========
from __future__ import annotations

import pytest

from core.domains.codium import initialize_codium_database
from core.domains.codium.integrations.models import ConnectorCreate, ConnectorKind
from core.domains.codium.integrations.providers.base import ConnectorProbe
from core.domains.codium.integrations.repository import ConnectorRepository
from core.domains.codium.integrations.service import ConnectorService


class _Vault:
    def __init__(self) -> None:
        self.podaci: dict[str, str] = {}

    def set(self, alias, value):
        self.podaci[alias] = value

    def get(self, alias):
        return self.podaci.get(alias)

    def delete(self, alias):
        self.podaci.pop(alias, None)

    def exists(self, alias):
        return alias in self.podaci


class _Provider:
    kind = ConnectorKind.ANTHROPIC

    def __init__(self, ok=True, message="") -> None:
        self._ok = ok
        self._message = message
        self.videna_tajna: str | None = None

    def test(self, config, secret) -> ConnectorProbe:
        self.videna_tajna = secret
        return ConnectorProbe(ok=self._ok, message=self._message)


@pytest.fixture()
def okruzenje(tmp_path):
    database = tmp_path / "codium_svc.db"
    initialize_codium_database(database)
    vault = _Vault()
    provider = _Provider()
    service = ConnectorService(
        ConnectorRepository(database), vault, {ConnectorKind.ANTHROPIC: provider},
    )
    return service, vault, provider


def _payload():
    return ConnectorCreate(name="Claude", kind=ConnectorKind.ANTHROPIC)


def test_create_upisuje_vrednost_u_vault_a_alias_u_bazu(okruzenje):
    service, vault, _ = okruzenje

    konektor = service.create(_payload(), secret="[Here put secret]")

    assert vault.get(konektor.secret_alias) == "sk-ant-tajna"
    assert konektor.secret_alias != "sk-ant-tajna"


def test_brisanje_konektora_brise_i_tajnu(okruzenje):
    service, vault, _ = okruzenje
    konektor = service.create(_payload(), secret="[Here put secret]")

    service.delete(konektor.id)

    assert vault.exists(konektor.secret_alias) is False


def test_test_connection_prosledjuje_tajnu_provajderu(okruzenje):
    service, _, provider = okruzenje
    konektor = service.create(_payload(), secret="[Here put secret]")

    service.test_connection(konektor.id)

    assert provider.videna_tajna == "sk-ant-tajna"


def test_uspesan_test_upisuje_status_ok(okruzenje):
    service, _, _ = okruzenje
    konektor = service.create(_payload(), secret="x")

    proba = service.test_connection(konektor.id)

    assert proba.ok is True
    assert service.get(konektor.id).status.value == "ok"


def test_update_secret_menja_vrednost_a_ne_alias(okruzenje):
    service, vault, _ = okruzenje
    konektor = service.create(_payload(), secret="stara")

    service.update_secret(konektor.id, "nova")

    assert vault.get(konektor.secret_alias) == "nova"
    assert service.get(konektor.id).secret_alias == konektor.secret_alias
```

- [ ] **Korak 2–5:** pad → implementacija → prolaz → commit, po istom obrascu.

`providers/base.py` nosi `ConnectorProbe(ok: bool, message: str, latency_ms: int | None = None)`
i `ConnectorProvider` protokol (`kind`, `required_fields()`, `secret_fields()`,
`test(config, secret)`).

`providers/anthropic.py` — `test()` pravi klijent sa datom tajnom i zove
`models.list()`; uspeh znači `ok=True`. Klijent se ubrizgava, kao u Task 4.

```bash
git commit -m "feat(codium): ConnectorService - tajna u vault, alias u bazu"
```

---

### Task 7: `codium_ops.db` i evidencija potrošnje

**Fajlovi:**
- Create: `core/domains/codium/ops_migrations.py`
- Create: `core/ai/usage.py`
- Modify: `core/domains/codium/paths.py`, `core/domains/codium/runtime.py`
- Test: `tests/test_ai_usage.py`

**Interfejsi:**
- Consumes: `cost_usd` (Task 3).
- Produces: `initialize_codium_ops_database(path)`, `UsageRecorder(database_path)`
  sa `record(...)` i `summary(period, project_id)`. Task 8 ga zove iz rute.

**Zašto druga baza:** `codium_ai_usage` raste sa svakim pozivom modela. Poslovna
baza se bekapuje i zaključava; operativni saobraćaj tu ne pripada.

Migracija ops baze nosi **sopstveno brojanje verzija** (`scope="codium_ops"`),
nezavisno od `codium.db`.

- [ ] **Korak 1: Napiši test koji pada**

```python
# ========== TESTOVI: evidencija potrosnje ==========
from __future__ import annotations

import pytest

from core.ai.usage import UsageRecorder
from core.domains.codium.ops_migrations import initialize_codium_ops_database


@pytest.fixture()
def recorder(tmp_path):
    database = tmp_path / "codium_ops.db"
    initialize_codium_ops_database(database)
    return UsageRecorder(database)


def test_upisan_poziv_se_vidi_u_sazetku(recorder):
    recorder.record(
        provider="anthropic", model="claude-opus-5", project_id=None,
        persona="architect", prompt_tokens=1000, output_tokens=500,
        duration_ms=1200, ok=True,
    )

    sazetak = recorder.summary()

    assert sazetak.calls == 1
    assert sazetak.prompt_tokens == 1000
    assert sazetak.output_tokens == 500


def test_trosak_se_upisuje_kao_broj_a_ne_racuna_naknadno(recorder):
    recorder.record(
        provider="anthropic", model="claude-opus-5", project_id=None,
        persona="architect", prompt_tokens=1_000_000, output_tokens=1_000_000,
        duration_ms=10, ok=True,
    )

    # 1M ulaznih po $5 + 1M izlaznih po $25.
    assert recorder.summary().cost_usd == 30.0


def test_lokalni_poziv_kosta_nula(recorder):
    recorder.record(
        provider="ollama", model="qwen2.5:7b", project_id=None,
        persona="architect", prompt_tokens=5000, output_tokens=5000,
        duration_ms=800, ok=True,
    )

    assert recorder.summary().cost_usd == 0.0


def test_sazetak_se_filtrira_po_projektu(recorder):
    recorder.record(provider="anthropic", model="claude-opus-5", project_id=1,
                    persona="architect", prompt_tokens=100, output_tokens=100,
                    duration_ms=1, ok=True)
    recorder.record(provider="anthropic", model="claude-opus-5", project_id=2,
                    persona="architect", prompt_tokens=100, output_tokens=100,
                    duration_ms=1, ok=True)

    assert recorder.summary(project_id=1).calls == 1


def test_neuspeo_poziv_se_evidentira(recorder):
    recorder.record(provider="anthropic", model="claude-opus-5", project_id=None,
                    persona="architect", prompt_tokens=0, output_tokens=0,
                    duration_ms=50, ok=False)

    assert recorder.summary().calls == 1
```

- [ ] **Korak 2–5:** pad → implementacija → prolaz → commit.

Šema (`scope="codium_ops"`, verzija 1) je doslovno iz speca. `UsageRecorder.record`
računa trošak kroz `cost_usd` **u trenutku upisa** i upisuje ga kao broj.

```bash
git commit -m "feat(codium): codium_ops.db i UsageRecorder"
```

---

### Task 8: `AssistantAnswer` nosi tokene, ruta evidentira potrošnju

**Fajlovi:**
- Modify: `core/domains/codium/assistant/assistant_service.py`
- Modify: `apps/api/schemas/codium_ai.py`, `apps/api/routers/codium_ai.py`
- Modify: `apps/api/codium_assistant_runtime.py`
- Test: `tests/test_codium_assistant.py`, `tests/test_api_codium_ai.py`

**Interfejsi:**
- Consumes: `UsageRecorder` (Task 7).
- Produces: `AssistantAnswer` sa `prompt_tokens`, `output_tokens`, `duration_ms`,
  `cost_usd`; `GET /api/v1/codium/ai/usage`.

**Odluka o mestu upisa:** `CodiumAssistant` **ne** zna za ops bazu — vraća tokene
u `AssistantAnswer`, a **ruta** ih upisuje. Time domenski servis ostaje bez
zavisnosti na bazu, kao što je i posle Faze 1.

Danas `ask()` odbacuje `result.prompt_tokens`; ovaj zadatak ih provlači.

- [ ] **Korak 1–5:** testovi → implementacija → prolaz → commit.

Testovi moraju da pokriju: da `/ask` sa lokalnim modelom upiše red sa nula
troška; da `/ask` bez polja `model` i dalje radi kao pre (regresija Faze 1); da
`GET /usage` vraća zbir.

```bash
git commit -m "feat(api): tokeni i trosak kroz /ask, izvestaj na /usage"
```

---

### Task 9: Rute konektora i registracija provajdera

**Fajlovi:**
- Create: `apps/api/routers/codium_integrations.py`, `apps/api/schemas/codium_integrations.py`
- Modify: `apps/api/main.py`, `apps/api/codium_assistant_runtime.py`
- Test: `tests/test_api_codium_integrations.py`

**Interfejsi:**
- Consumes: `ConnectorService` (Task 6), `AnthropicProvider` (Task 4).
- Produces: `/api/v1/codium/integrations/{kinds,,{id},{id}/test}`;
  `AnthropicProvider` registrovan u `get_providers()`.

**Nepregovaračko:** nijedan odgovor ne sme da nosi vrednost tajne — samo
`has_secret: bool`. Test to proverava tako što traži da se vrednost ne pojavi
**nigde** u telu odgovora, ni pod jednim ključem.

- [ ] **Korak 1: Test koji to pini**

```python
def test_odgovor_ne_sadrzi_tajnu_ni_pod_jednim_kljucem(client):
    client.post("/api/v1/codium/integrations/", json={
        "name": "Claude", "kind": "anthropic", "secret": "[Here put secret]",
    })

    for putanja in ("/api/v1/codium/integrations/",):
        telo = client.get(putanja).text
        assert "sk-ant-TAJNA-123" not in telo
        assert "TAJNA" not in telo
```

- [ ] **Korak 2–6:** pad → implementacija → prolaz → registracija provajdera →
  commit.

Posle registracije `AnthropicProvider` u `get_providers()`, katalog bez ključa
mora da vrati red `available=False` sa razlogom o ključu — GUI ga u Task 11
pretvara u „Potreban API ključ".

```bash
git commit -m "feat(api): rute konektora + AnthropicProvider u katalogu"
```

---

### Task 10: Konfiguracija modela

**Fajlovi:**
- Modify: `config/models_config.json`
- Modify: `core/ai/model_registry.py`
- Test: `tests/test_core_ai.py` (ili postojeći test registra)

**Interfejsi:**
- Produces: podrška za opciono polje `local_endpoint`.

`Codium` unos prestaje da bude `provider: "openrouter"` sa zastarelim
`anthropic/claude-3.5-sonnet`:

```json
"Codium": {
  "developer_model": "claude-opus-5",
  "provider": "anthropic",
  "endpoint": "https://api.anthropic.com",
  "light_model": "qwen2.5:7b",
  "local_endpoint": "http://localhost:11434"
}
```

**Pažnja:** `_default_model` u `codium_assistant_runtime.py` bira samo veze gde
je `is_local` tačno, a `ModelBinding.is_local` je `provider == "ollama"`. Posle
ove izmene `Codium.developer_model` više nije lokalan, pa podrazumevani model
pada na `CORE.model` — što je i dalje `llama3.2:latest`. To je **namerno**:
podrazumevani model ostaje lokalan i besplatan, Claude se bira izričito.
Test mora da to pini, da neko kasnije ne „popravi" filter i ne počne da troši
novac na svaki poziv.

```bash
git commit -m "feat(config): Codium ide na anthropic, podrazumevani ostaje lokalan"
```

---

### Task 11: GUI — grupa „Online", unos ključa, trošak

**Fajlovi:**
- Create: `apps/gui/src/features/codium/ApiKeyDialog.tsx`
- Modify: `apps/gui/src/features/codium/AiAssistant.tsx`, `modelPicker.ts`
- Modify: `apps/gui/src/services/codiumApi.ts`
- Modify: `apps/gui/src/styles/codium-ai.css`
- Test: `ApiKeyDialog.test.tsx`, `modelPicker.test.ts`, `AiAssistant.test.tsx`

**Interfejsi:**
- Consumes: rute iz Task 9 i Task 8.

Tri stvari:

1. **Grupa „Online"** se puni sama — `groupModels` je već deli po `is_local`.
   `formatModelLabel` mora da prikaže **i ulaznu i izlaznu** cenu (danas prikazuje
   samo ulaznu): `$5/$25 po M`.
2. **Unos ključa.** Kad nijedan online model nije dostupan, na mestu grupe
   „Online" stoji red **„Potreban API ključ"** koji otvara dijalog: jedno polje
   `type="password"`, dugme „Proveri i sačuvaj". Dijalog zove
   `POST /integrations` pa `POST /{id}/test`. Posle upisa vrednost se **ne
   prikazuje nigde** — dijalog dalje pokazuje samo `has_secret` i nudi zamenu.
3. **Trošak.** Ispod chata mala oznaka: model kojim je odgovoreno i trošak
   poslednjeg poziva, iz polja koja `/ask` sad vraća.

- [ ] **Korak 1–8:** testovi → implementacija → fokusirani testovi → cela GUI
  suita → typecheck (iste 4 greške, nijedna peta) → commit.

```bash
git commit -m "feat(gui): grupa Online, unos API kljuca, trosak ispod chata"
```

---

### Task 12: Provera uživo i dev-log

**Fajlovi:**
- Create/Modify: `.ai/dev-log/entries/`, `.ai/dev-log/INDEX.md`
- Modify: `.ai/izgradnja/codium/00-INDEX.md`

**Ključ unosi korisnik.** Agent nikada ne unosi API ključ ni u polje, ni u
komandu, ni u fajl. Ovaj zadatak se zaustavlja i traži od korisnika da unese
ključ kroz dijalog iz Task 11, pa tek onda nastavlja.

- [ ] **Korak 1: Bez ključa** — `/models` vraća red „Potreban API ključ" sa
  `available=false`; lokalni modeli i dalje rade.
- [ ] **Korak 2:** zamoli korisnika da unese ključ kroz dijalog. Sačekaj potvrdu.
- [ ] **Korak 3: Sa ključem** — `/models` vraća Claude modele sa cenama uz
  lokalne; izbor Claude modela daje odgovor; `GET /usage` pokazuje upisan trošak
  veći od nule.
- [ ] **Korak 4: Provera da tajna ne curi** —
  `grep -ri "sk-ant" data/ config/ --include=* | head` mora biti prazno, i
  `sqlite3 codium.db "SELECT * FROM codium_connectors"` sme da pokaže samo alias.
- [ ] **Korak 5:** cele suite + typecheck; zapiši tačne brojeve.
- [ ] **Korak 6:** dev-log unos kroz `scripts/devlog.py`.
- [ ] **Korak 7:** označi `AI-2` kao završeno u `.ai/izgradnja/codium/00-INDEX.md`.
- [ ] **Korak 8: Commit**

```bash
git commit -m "docs(dev-log): CODIUM Faza 2 - Claude preko Anthropic API-ja"
```

---

## Šta ovaj plan namerno NE radi

- **Nema OpenRouter-a** — treći provajder je Faza 3.
- **Nema keša kataloga** — Faza 3. Anthropic lista modela je kratka i brza.
- **Nema punog ekrana konektora** — to je `E11`. Ovde je samo dijalog za ključ.
- **Nema streaming-a** — postojeći chat je ne-stream.
- **Nema ScopeGate provere** `ai.call_online` — to je `E1`. Poziv koji pokreće
  čovek ionako prolazi.
- **Ne menja podrazumevani model na Claude** — podrazumevani ostaje lokalan i
  besplatan; Claude se bira izričito.
- **Ne popravlja 4 zatečene `tsc` greške** — van obima.
