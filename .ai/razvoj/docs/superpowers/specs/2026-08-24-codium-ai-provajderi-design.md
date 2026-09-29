---
id: codium-abe7bfd0-2026-08-24-codium-ai-provajderi-design-md
type: spec
domain: codium
namespace: global
visibility: global
tier: domain
title: CODIUM — sloj AI provajdera u tri faze
summary: '**Datum:** 2026-08-24'
keywords:
- codium
- sloj
- provajdera
- tri
- faze
- docs
- superpowers
- specs
tags:
- superpowers
- specs
source_path: docs/superpowers/specs/2026-08-24-codium-ai-provajderi-design.md
---

# CODIUM — sloj AI provajdera u tri faze

**Datum:** 2026-08-24
**Domen:** CODIUM
**Zamenjuje redosled iz:** `.ai/izgradnja/codium/00-INDEX.md` (E traka, verzija od 2026-08-22)

---

## Zašto se plan menja

Plan enterprise trake od 2026-08-22 predviđa da se prvo uradi `E0-mini`
(credential vault plus jedan OpenRouter konektor), pa `E8 OmniRoute`. Odluka
korisnika od 2026-08-24 menja taj redosled u tri faze:

1. lokalni modeli,
2. Claude preko direktnog Anthropic API-ja,
3. OmniRoute sa OpenRouter-om kao trećim provajderom.

Razlog za promenu je što lokalni modeli ne traže nijednu tajnu — Ollama sluša na
`localhost:11434` bez ključa. Vault je zato nepotreban za prvu upotrebljivu
verziju izbora modela, a bio je prvi u starom redosledu samo zato što je
OpenRouter tražio ključ.

Uz to, korisnik je odlučio da svaka faza bude upotrebljiva kraj-do-kraju
(backend plus GUI), umesto ranijeg pravila „backend celog bloka, pa GUI tog
bloka". Pravilo iz 2026-08-22 ostaje na snazi za ostatak E trake; ovaj blok je
izuzetak, jer se AI chat okvir koristi svakodnevno i svaka faza mu odmah
dodaje vrednost.

## Šta se ne menja

Ostatak E trake (`E1` do `E11`) zadržava obim i međuzavisnosti iz postojećih
faznih fajlova. Menjaju se samo redni brojevi migracija, jer ovaj blok troši
verzije pre njih.

## Zatečeno stanje

| Modul | Stanje | Uloga |
|---|---|---|
| `core/ai/ollama_client.py` | radi; `generate()` preko `/api/generate` | uvija se u `OllamaProvider` |
| `core/ai/model_registry.py` | radi; čita `config/models_config.json` | ostaje izvor podrazumevanog modela po domenu i ulozi |
| `core/ai/core_router.py` | radi | **ne dira se** — vidi nalaz niže |
| `core/ai/vram_guard.py` | mutex za jedan GPU | **ne dira se** — vidi nalaz 5 |
| `core/domains/codium/assistant/` | F9, sedam persona | dobija provajder-svestan poziv |
| `AiAssistant.tsx`, `CodiumHubChat.tsx` | F9 i kasnije | dele istu komponentu; dobijaju izbor modela |
| `codium.db` | šema v2 | E faze nastavljaju od v3 |
| `codium_ops.db` | ne postoji | pravi se u fazi 2 |

### Nalaz 1: `core_router.py` nije ruter modela

Fazni fajl `18-E8-omniroute.md` tvrdi da se `core/ai/core_router.py` proširuje.
To je pogrešno. `CoreRouter` je klasifikator namere: uzima tekst korisnika i
opcionu putanju fajla, pa preko lokalnog modela vraća strukturiran JSON intent
(`intent`, `target_domain`, `action`, `parameters`). Sa biranjem modela nema
veze.

Biranje modela je nov modul, `core/ai/model_router.py`. `core_router.py` ostaje
netaknut.

### Nalaz 2: `CodiumAssistant` je vezan za jedan provajder

`CodiumAssistant.__init__` prima `generate: Callable[..., str]` sa potpisom
`generate(model, prompt, *, system=None, fmt=None)`. To je oblik Ollama
`/api/generate` poziva: jedan string prompta, jedan string odgovora, bez
brojanja tokena.

Anthropic API radi sa listom poruka i vraća broj potrošenih tokena. Da bi oba
provajdera stala iza istog poziva, `CodiumAssistant` mora da primi
`chat(messages, resolved) -> ChatResult` umesto `generate`. To je jedina
invazivna izmena u postojećem F9 kodu.

### Nalaz 3: Anthropic API ne daje cene

`GET /v1/models` vraća `id`, `display_name`, `created_at`, `max_input_tokens`,
`max_tokens` i `capabilities`. Cenu ne vraća.

Posledica: lista modela je živa iz API-ja, a cena je statična tabela u kodu
(`core/ai/pricing.py`), sa komentarom koji upućuje na zvaničnu stranicu cena.
Trošak poziva se računa iz te tabele u trenutku poziva i upisuje u bazu kao
broj — nikada se ne računa naknadno, jer se cene menjaju a istorija treba da
ostane tačna.

### Nalaz 4: dve nove Python zavisnosti, ne jedna

Fazni fajl `10-E0-integracije-i-vault.md` tvrdi da je `keyring` jedina nova
biblioteka u celoj enterprise traci. Netačno — direktan Anthropic API traži i
zvanični `anthropic` SDK.

Obe se registruju po sva četiri koraka iz `docs/DEPENDENCIES.md`:

1. unos u `CORE_DEPENDENCIES` (`core/foundation/dependencies.py`),
2. `scripts/install/<ime>.ps1` plus ime skripte u `INSTALL_SCRIPTS`
   (`core/foundation/installer.py`),
3. red u tabeli „Katalog alata" u `docs/DEPENDENCIES.md`,
4. unos u `requirements.txt`.

Bez prvog koraka indikator pored „CORE Online" i dugme INSTALL ne znaju za alat
— to je tačno ono što se dogodilo sa Monaco i xterm paketima pre ove sesije.

### Nalaz 5: `vram_guard` ne proverava veličinu

Raniji nacrt je govorio da lokalni model „prolazi kroz `vram_guard`, i ako ne
staje poziv se odbija". To ne stoji. `VramGuard` je mutex sa imenom aktivnog
držaoca — serijalizuje Whisper i LLM na jednom GPU-u da nikada dva modela nisu
istovremeno u VRAM-u. O veličini modela ne zna ništa.

Prava provera veličine bila bi nagađanje: Ollama `/api/tags` vraća `size` u
bajtovima (veličina na disku), što je samo približna mera potrebe za VRAM-om.
Tvrdo odbijanje poziva na osnovu te procene odbijalo bi i modele koji bi radili.

Odluka: **bez tvrdog odbijanja.** Katalog čita `size` i prikazuje ga uz model.
Model veći od budžeta VRAM-a nosi upozorenje („veći od 8 GB VRAM-a — može biti
spor"), ali se sme izabrati. Budžet je konstanta u `core/ai/providers/ollama.py`
sa komentarom zašto je 8.

Postojeći `vram_guard` mutex ostaje netaknut i nije deo ovog bloka.

---

## Arhitektura

```
core/ai/
    providers/
        base.py         ChatProvider protokol + zajednički tipovi
        ollama.py       omotač nad postojećim ollama_client (faza 1)
        anthropic.py    direktan Anthropic API (faza 2)
        openrouter.py   treći provajder (faza 3)
    catalog.py          spajanje izvora modela
    pricing.py          statična tabela cena (faza 2)
    usage.py            evidencija poziva (faza 2)
    model_router.py     biranje modela; NOV, ne dira core_router.py
    core_router.py      klasifikator namere; netaknut
    model_registry.py   netaknut
    vram_guard.py       netaknut (mutex, nije provera veličine)
```

### Protokol provajdera

```
ChatMessage      role ("system" | "user" | "assistant"), content: str
ModelInfo        id, label, provider, is_local, context_window,
                 price_in_per_mtok, price_out_per_mtok, size_gb | None,
                 oversized: bool, available: bool, unavailable_reason: str
ChatResult       text, model, provider, prompt_tokens, output_tokens,
                 duration_ms
ProviderUnavailable(RuntimeError)

ChatProvider (Protocol)
    name: str
    is_local: bool
    available() -> bool
    models() -> list[ModelInfo]
    chat(messages: list[ChatMessage], model: str, **options) -> ChatResult
```

`stream()` namerno nije u protokolu. Postojeći chat je ne-stream; streaming se
dodaje kada zatreba, a ne unapred.

`ChatMessage` je naš tip, ne SDK tip, jer apstrahuje najmanje tri provajdera.
Konverzija u oblik koji SDK očekuje dešava se unutar `providers/anthropic.py` i
nigde drugde.

### Ruter modela

```
ResolvedModel    provider_name, model, source ("override" | "pref" | "registry")

ModelRouter
    resolve(domain, role, *, project_id, persona, override=None) -> ResolvedModel
    chat(messages, resolved, **options) -> ChatResult
```

Redosled odlučivanja:

1. `override` — izričit izbor korisnika u chatu; uvek pobeđuje,
2. zapamćena postavka za taj projekat i tu personu,
3. `model_registry` — podrazumevano po domenu i ulozi (postojeće ponašanje).

Od faze 3 važi pravilo: ako izabrani provajder nije dostupan, ruter vraća grešku
sa razlogom i predlogom zamene. Tiha zamena modela je zabranjena — korisnik mora
znati čime mu je odgovoreno.

### Katalog

`ModelCatalog(providers).list()` spaja izvore. Nedostupan izvor ne briše svoje
modele iz liste nego ih vraća sa `available=False` i razlogom. Korisnik treba da
vidi da Ollama ne radi, a ne da mu modeli nestanu.

---

## Faza 1 — Lokalni modeli

**Cilj:** chat okvir dobija izbor modela; lista se puni iz Ollama; izbor se pamti
po projektu i personi. Bez ključeva, bez troška, bez vault-a.

### Backend

| Fajl | Izmena |
|---|---|
| `core/ai/providers/base.py` | nov — tipovi i protokol |
| `core/ai/providers/ollama.py` | nov — `OllamaProvider` |
| `core/ai/ollama_client.py` | dodaje `tags()` (`GET /api/tags`) i `chat()` (`POST /api/chat`); `generate()` se ne dira |
| `core/ai/catalog.py` | nov — samo Ollama izvor |
| `core/ai/model_router.py` | nov |
| `core/domains/codium/migrations.py` | v3 |
| `core/domains/codium/repository.py` | CRUD nad `codium_model_prefs` |
| `core/domains/codium/assistant/assistant_service.py` | `generate` postaje `chat` |
| `apps/api/routers/codium_ai.py` | tri nove rute plus dopuna `/ask` |

`generate()` u `ollama_client.py` ostaje netaknut jer ga koriste `CoreRouter` i
FILMIUM `CuratorService`. Nove metode se dodaju pored njega.

Ollama `/api/chat` vraća `prompt_eval_count` i `eval_count` — brojanje tokena je
besplatno, bez posebnog koraka.

### Migracija `codium.db` v3

```sql
CREATE TABLE codium_model_prefs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES codium_projects (id) ON DELETE CASCADE,
    persona    TEXT NOT NULL DEFAULT '',
    model      TEXT NOT NULL,
    provider   TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_codium_model_prefs ON codium_model_prefs (project_id, persona);
```

### API

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/api/v1/codium/ai/models` | katalog dostupnih modela |
| GET | `/api/v1/codium/ai/prefs` | zapamćen model (`?project_id=&persona=`) |
| PUT | `/api/v1/codium/ai/prefs` | pamćenje izbora |
| POST | `/api/v1/codium/ai/ask` | dopunjeno opcionim poljem `model` |

Poziv `/ask` bez polja `model` mora da se ponaša tačno kao pre. F9 ne sme da
regresira.

### GUI

- `apps/gui/src/features/codium/modelPicker.ts` — nov, čist modul bez React-a:
  grupisanje, sortiranje i filtriranje kataloga.
- `AiAssistant.tsx` — pored postojećeg dropdown-a persona dolazi dropdown modela,
  grupa „Lokalno", uz svaki model njegova veličina; model veći od budžeta nosi
  upozorenje.
- Nedostupan model je siv sa razlogom u opisu, ne sakriven.
- `codiumApi.ts` i `types/codium.ts` — nove rute i tipovi.

Chat okvir postoji na tri mesta (hub, docking panel, odvojen prozor) i sva tri
koriste istu komponentu, pa izbor modela stiže u sva tri bez dodatnog rada.

### Testovi

- `test_chat_providers` — `OllamaProvider` protiv lažnog transporta: uspeh,
  greška mreže, prazan odgovor, brojanje tokena.
- `test_model_catalog` — nedostupan izvor daje modele sa `available=False`, ne
  prazan spisak.
- `test_model_router` — redosled odlučivanja: override pobeđuje postavku,
  postavka pobeđuje registar, prazan override pada na registar.
- `modelPicker.test.ts` — grupisanje i sortiranje.
- Regresija: `test_codium_assistant` i `test_api_codium_ai` prolaze.

### Definicija završetka

Chat okvir nudi izbor lokalnog modela, izbor se pamti po projektu i personi,
nedostupan model se vidi sa razlogom, `/ask` bez polja `model` radi kao pre,
testovi domena prolaze.

---

## Faza 2 — Claude (direktan Anthropic API)

**Cilj:** u istoj listi modela pojavljuje se grupa „Online" sa Claude modelima i
cenom. Ispod chata stoji trošak poslednjeg poziva. Evidencija potrošnje počinje
ovde, jer poziv prvi put košta novac.

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

Implementacija preko biblioteke `keyring` (ime servisa `CORE`, korisničko ime
jednako aliasu). Ako keychain nije dostupan, `get` vraća `None` i servis
prijavljuje degradirano stanje. Nikada ne pada na čuvanje tajne u fajl.

### Konektori

`core/domains/codium/integrations/` — `models.py`, `repository.py`,
`service.py`, `providers/base.py`, `providers/anthropic.py`.

Baza čuva opis konektora i **alias** tajne. Sama tajna nikada ne ulazi u SQLite,
u `config/`, niti u bilo koji fajl pod verzijom.

`ConnectorKind` u ovoj fazi ima jednu vrednost koja se koristi — `anthropic`.
Enumeracija se piše u punom obliku (`github`, `docker_registry`, `ssh_host`,
`openrouter`, `smtp`, `anthropic`), ali provajder postoji jedan. Ostali dolaze u
`E0-pun`.

### Provajder i cene

`core/ai/providers/anthropic.py` — `AnthropicProvider` preko zvaničnog
`anthropic` SDK-a. Ključ se dohvata iz vault-a po aliasu u trenutku upotrebe.

- `models()` — `client.models.list()`, spojeno sa cenama iz `pricing.py`.
- `chat()` — `client.messages.create()`; podrazumevan model `claude-opus-5`,
  adaptivno mišljenje (`thinking={"type": "adaptive"}`), `max_tokens` 16000 za
  ne-stream poziv.
- Tokeni se čitaju iz `response.usage.input_tokens` i
  `response.usage.output_tokens`.

Zabranjeno u kodu ove faze, jer trenutni modeli to odbijaju sa HTTP 400:
`budget_tokens` u `thinking`, i prefill poslednje `assistant` poruke.

`core/ai/pricing.py` — statična tabela cena po modelu (ulaz i izlaz po milionu
tokena), sa komentarom koji kaže gde se cene proveravaju i da ih Models API ne
vraća.

### Evidencija potrošnje

`core/ai/usage.py` — `UsageRecorder` posle svakog poziva upisuje red: provajder,
model, projekat, persona, akter, ulazni i izlazni tokeni, izračunat trošak,
trajanje, uspeh. Ovo je izvor za AI odeljak u `E7 Analytics`.

### Migracije

`codium.db` **v4** — poslovni podaci:

```sql
CREATE TABLE codium_connectors (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    kind           TEXT NOT NULL,
    config_json    TEXT NOT NULL DEFAULT '{}',
    secret_alias   TEXT,
    status         TEXT NOT NULL DEFAULT 'unconfigured',
    last_tested_at TEXT,
    last_error     TEXT,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_codium_connectors_name ON codium_connectors (name);
```

Nova baza `codium_ops.db`, **ops v1** — operativni saobraćaj:

```sql
CREATE TABLE codium_ai_usage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    provider      TEXT NOT NULL,
    model         TEXT NOT NULL,
    project_id    INTEGER,
    persona       TEXT NOT NULL DEFAULT '',
    actor         TEXT NOT NULL DEFAULT 'human',
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd      REAL NOT NULL DEFAULT 0,
    duration_ms   INTEGER NOT NULL DEFAULT 0,
    ok            INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_codium_ai_usage_at ON codium_ai_usage (at DESC);
```

Razlog za drugu bazu: te tabele rastu hiljadama redova dnevno i ne smeju da
opterećuju bekap i zaključavanje poslovne baze. `CodiumPaths` dobija polje
`ops_database`.

### Zavisnosti

`keyring` i `anthropic`, svaka po sva četiri koraka iz `docs/DEPENDENCIES.md`.

### API

`apps/api/routers/codium_integrations.py`, prefiks
`/api/v1/codium/integrations`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/kinds` | podržani tipovi i polja koja traže |
| GET | `/` | lista konektora bez tajni |
| POST | `/` | novi konektor; tajna ide u vault |
| PATCH | `/{id}` | izmena; prazna tajna znači „ne diraj postojeću" |
| DELETE | `/{id}` | briše konektor i njegovu tajnu |
| POST | `/{id}/test` | pokreće `test()` provajdera |

Odgovori nikada ne vraćaju vrednost tajne, samo `has_secret: bool`.

Uz to `GET /api/v1/codium/ai/usage` za potrošnju.

### Izmena konfiguracije

`config/models_config.json` — unos `Codium` prestaje da bude jedan model iza
`openrouter` provajdera:

```json
"Codium": {
  "developer_model": "claude-opus-5",
  "provider": "anthropic",
  "endpoint": "https://api.anthropic.com",
  "light_model": "qwen2.5:7b",
  "local_endpoint": "http://localhost:11434"
}
```

Postojeća vrednost `anthropic/claude-3.5-sonnet` sa `provider: "openrouter"` je
zastarela i briše se. `model_registry` dobija podršku za opciono polje
`local_endpoint`, da jedan domen može imati i lokalne i online uloge. Domeni
`CORE`, `Filmium` i `Kalima` rade nepromenjeno.

### GUI

- Dropdown modela dobija grupu „Online" sa cenom po milionu ulaznih i izlaznih
  tokena.
- Ispod chata mala oznaka: kojim modelom je odgovoreno i koliko je poslednji
  poziv koštao.
- Punog ekrana za konektore nema — on je `E11`. Dodaju se samo tipovi u
  `types/codium.ts` i pozivi u `codiumApi.ts`, da `E11` kasnije bude tanak.
- Minimalan unos ključa **jeste** u obimu ove faze, jer bez njega faza nije
  upotrebljiva bez ručnog HTTP poziva. Kada u dropdown-u nema nijednog dostupnog
  online modela, na mestu grupe „Online" stoji red „Potreban API ključ" koji
  otvara mali dijalog sa jednim poljem tipa lozinke i dugmetom „Proveri i
  sačuvaj". Dijalog zove `POST /integrations` pa `POST /{id}/test`. Vrednost se
  posle upisa ne prikazuje nigde — dijalog kasnije pokazuje samo `has_secret` i
  nudi zamenu.

### Testovi

- `test_secret_vault` — lažni keyring backend: upis, čitanje, brisanje, i
  ponašanje kada keychain nije dostupan.
- `test_codium_connectors` — kreiranje upisuje alias a ne vrednost; brisanje
  konektora briše i tajnu; `test_connection` upisuje `last_tested_at`.
- `test_api_codium_integrations` — odgovor ne sadrži tajnu ni pod jednim ključem.
- `test_anthropic_provider` — protiv lažnog SDK klijenta: mapiranje poruka,
  čitanje tokena, uredna greška kada ključ nedostaje.
- `test_ai_usage` — trošak se računa iz cena u trenutku poziva i upisuje kao broj.

### Definicija završetka

Claude model se bira u chatu i odgovara; ključ nije pronalaziv u `codium.db` ni u
jednom fajlu repozitorijuma; trošak svakog poziva je upisan i vidljiv; lokalni
modeli iz faze 1 rade nepromenjeno; testovi domena prolaze.

---

## Faza 3 — OmniRoute

**Cilj:** ono što ima smisla tek kada postoji više od jednog provajdera — treći
provajder, keširanje kataloga, stroga pravila zamene i izveštaj potrošnje.

### Obim

| Fajl | Izmena |
|---|---|
| `core/ai/providers/openrouter.py` | nov — treći provajder, ključ iz vault-a |
| `core/ai/catalog.py` | keš na disk sa rokom od 24 sata |
| `core/ai/model_router.py` | pravilo „bez tihe zamene"; tačka `ai.call_online` |

OpenRouter katalog (`GET /api/v1/models`) nosi nekoliko stotina modela sa
cenama, pa mu treba keš pod `CodiumPaths.root / "model_catalog.json"`. Ako oba
izvora zataje, vraća se poslednji poznati keš uz oznaku da je zastareo. Katalog
nikada ne obara poziv.

`ai.call_online` se piše kao **jedna tačka poziva** koju `E1` kasnije popuni
ScopeGate proverom. Do tada je prolaz bez provere, što je tačno ponašanje za
pozive koje pokreće čovek — po pravilu iz `E1`, akter `human` zaobilazi gate.

### API

| Metoda | Putanja | Radi |
|---|---|---|
| POST | `/api/v1/codium/ai/models/refresh` | ručno osvežavanje keša kataloga |
| GET | `/api/v1/codium/ai/usage` | dopunjeno filtrima `?period=&project_id=` |

Konektor `openrouter` koristi tabelu i servis iz faze 2 — nema nove migracije.

### GUI

Grupa „Online" u dropdown-u se puni iz oba online izvora, sortirano po ceni.

Potrošnja se vidi kroz mali modal koji se otvara iz zaglavlja chata: zbir za
period i pet najskupljih modela. Pun ekran analitike nije ovde — on dolazi sa
`E7 Analytics`, koji ovu istu tabelu čita.

### Testovi

- `test_catalog_cache` — keš se poštuje; nedostupan izvor daje zastareo keš
  umesto praznog spiska.
- `test_router_no_silent_swap` — nedostupan provajder vraća grešku sa predlogom,
  nikada tiho drugi model.
- `test_openrouter_provider` — protiv lažnog HTTP sloja.

### Definicija završetka

Sva tri provajdera stoje u istoj listi; keš kataloga radi i ume da se osveži
ručno; nedostupan provajder daje jasnu poruku a ne tihu zamenu; potrošnja se
vidi po periodu i projektu; testovi domena prolaze.

---

## Posledice po postojeće plan fajlove

| Fajl | Izmena |
|---|---|
| `.ai/izgradnja/codium/00-INDEX.md` | nova tabela redosleda E trake; ops numeracija kasnijih faza pomerena za jedan |
| `.ai/izgradnja/codium/09-ENTERPRISE-OVERVIEW.md` | ispravka „jedna nova zavisnost" u dve; napomena o izuzetku od pravila „backend pa GUI" |
| `.ai/izgradnja/codium/10-E0-integracije-i-vault.md` | prvi konektor je `anthropic`, ne `openrouter`; migracija v3 postaje v4 |
| `.ai/izgradnja/codium/18-E8-omniroute.md` | cepa se na tri fazna fajla; briše se tvrdnja da se `core_router.py` proširuje |
| `apps/gui/src/components/layout/Sidebar.tsx` | badge oznake F13–F17 se menjaju E kodovima (zadatak pripreme iz starog plana, ostaje) |

Pomeranje numeracije migracija:

| Faza | Staro | Novo |
|---|---|---|
| Faza 1 (lokalni modeli) | — | codium v3 |
| Faza 2 (Claude) | codium v3 (E0-mini) | codium v4 plus ops v1 |
| E1 Audit i ScopeGate | codium v4, ops v1 | codium v5, ops v2 |
| E2 Repositories | codium v5 | codium v6 |
| E3 Pipelines | codium v6, ops v2 | codium v7, ops v3 |
| E4 Deployments | codium v7 | codium v8 |
| E5 Infrastructure | codium v8 | codium v9 |
| E6 Monitoring | codium v9, ops v3 | codium v10, ops v4 |
| E9 AI Agents | codium v11 | codium v11 (nepromenjeno) |
| E10 Automations | codium v12 | codium v12 (nepromenjeno) |

`E9` i `E10` ostaju na istim brojevima slučajno: stari plan je za `E8` rezervisao
`codium v10`, a novi raspored do `E6` potroši tačno isti broj verzija.

Fazi 3 nije potrebna migracija — koristi tabele iz faze 2.

## Ograničenja i svesno izostavljeno

- Streaming odgovora nije u protokolu. Postojeći chat je ne-stream; dodaje se kad
  zatreba.
- Bezbednosne provere (tajne u commit-ovima, ranjive zavisnosti) ostaju izvan
  trake dok se ne počne KALIMA domen — odluka od 2026-08-22, i dalje važi.
- ScopeGate provera online poziva postoji samo kao tačka poziva; stvarna provera
  stiže sa `E1`.
- Prompt caching Anthropic API-ja se ne koristi u prvom prolazu. Persona sistemski
  prompt je kratak, a minimalni keširani prefiks je oko 1024 tokena — ne bi se ni
  aktivirao.
