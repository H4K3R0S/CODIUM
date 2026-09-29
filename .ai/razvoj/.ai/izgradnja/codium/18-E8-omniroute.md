---
id: codium-f9a6cc01-18-e8-omniroute-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E8 — OmniRoute (AI ruter + izbor modela u chat okviru)
summary: '**Blok:** AI · **Zavisi od:** E0-mini · **Migracija:** codium v10 + ops
  v4'
keywords:
- omniroute
- ruter
- izbor
- modela
- chat
- okviru
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/18-E8-omniroute.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
- type: references
  target: core-a6bee7b8-codium-podsetnik-md
  weight: 0.3
---

# E8 — OmniRoute (AI ruter + izbor modela u chat okviru)

**Blok:** AI · **Zavisi od:** E0-mini · **Migracija:** codium v10 + ops v4
**Sidebar:** nema svoju stavku — vidi se kao izbor modela u AI chat okviru

> **Ova faza se radi prva u celoj traci**, odmah posle `E0-mini` (vault + jedan
> OpenRouter konektor). Razlog: jedina je koja donosi korist istog dana, jer AI
> chat okvir već postoji i koristi se svakodnevno. Obrazloženje je u odeljku
> „Redosled rada" u pregledu.
>
> ScopeGate iz E1 ovde još ne postoji. `ai.call_online` se zato piše kao **jedna
> tacka poziva** koju E1 kasnije popuni; do tada je to prolaz bez provere, što je
> tačno ponašanje za pozive koje pokreće čovek (pravilo E1: `human` zaobilazi gate).

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Jedan ulaz za sve modele. Chat okvir napravljen u F9 dobija izbor modela: lokalni
modeli kroz Ollama i online modeli kroz OpenRouter, u istoj listi, sa vidljivom
cenom i oznakom šta radi bez interneta.

Ovo objedinjuje ono što je ranije bilo razdvojeno na „F14 OneRoute" i
„F15 OmniRoute". Nema dva sistema — jedan ruter, jedan katalog.

## Šta već postoji (ne gradi se ponovo)

| Modul | Stanje | Uloga u E8 |
|---|---|---|
| `core/ai/model_registry.py` | radi; čita `config/models_config.json` | ostaje izvor podrazumevanog modela po domenu i ulozi |
| `core/ai/core_router.py` | radi | proširuje se, ne zamenjuje |
| `core/ai/ollama_client.py` | radi | uvija se u `OllamaProvider` |
| `core/ai/vram_guard.py` | radi | zabranjuje lokalni model koji ne staje u VRAM |
| `core/domains/codium/assistant/` | F9, 7 persona, radi | dobija parametar modela |
| `AiAssistant.tsx` | F9, chat sa personama | dobija drugi dropdown |

Konektor za OpenRouter je u `config/models_config.json` deklarisan još od ranije
(`Codium.provider = "openrouter"`), ali **nikada nije napisan**. E8 ga piše.

## Arhitektura

```
core/ai/
    providers/
        base.py         ChatProvider protokol
        ollama.py       omotač nad postojećim ollama_client
        openrouter.py   nov; ključ iz E0 vault-a
    catalog.py          spisak dostupnih modela iz oba izvora
    usage.py            evidencija poziva (tokeni, trošak, trajanje)
    core_router.py      prošireno: override_model, izbor provajdera
```

### Protokol provajdera

```
ChatProvider
    name: str
    is_local: bool
    models() -> list[ModelInfo]
    chat(messages, model, options) -> ChatResult
    stream(messages, model, options) -> AsyncIterator[ChatChunk]
    available() -> bool
```

`ModelInfo`: id, prikazno ime, provajder, kontekstni prozor, cena po milionu
ulaznih i izlaznih tokena (nula za lokalne), da li podržava alate, procenjen VRAM
za lokalne.

`ChatResult`: tekst, iskorišćeni tokeni (ulaz i izlaz), trajanje, model, da li je
bio fallback.

### Katalog

`catalog.py` spaja dva izvora:

- **Ollama** — `GET /api/tags` sa lokalnog endpoint-a. Uvek sveže; ako Ollama ne
  odgovara, lokalni modeli se prikazuju kao nedostupni umesto da nestanu iz liste.
- **OpenRouter** — `GET /api/v1/models`, keširano na disk pod
  `CodiumPaths.root / "model_catalog.json"` sa rokom od 24 sata. Cene se menjaju
  retko; dohvatanje na svaki otvor liste je bespotrebno.

Katalog nikada ne obara poziv: ako oba izvora zataje, vraća se poslednji poznati
keš uz oznaku da je zastareo.

### Ruter

`core_router` dobija:

```
route(domain, role, override_model=None) -> ResolvedRoute
```

Redosled odlučivanja:

1. `override_model` — izričit izbor korisnika u chatu. Uvek pobeđuje.
2. Zapamćena postavka za taj projekat i tu personu.
3. `model_registry` — podrazumevano po domenu i ulozi (postojeće ponašanje).

Pre poziva:

- lokalni model prolazi kroz `vram_guard`; ako ne staje, poziv se odbija sa
  urednom porukom i predlogom manjeg modela,
- online model prolazi kroz ScopeGate akciju `ai.call_online`. Za čoveka je
  dozvoljena; za agente i automatizacije podrazumevano traži odobrenje, jer online
  poziv troši novac.

Ako izabrani provajder nije dostupan, ruter **ne** ćuti: vraća grešku sa
predlogom zamene i razlogom. Tiha zamena modela je zabranjena — korisnik mora znati
čime je odgovoreno.

### Evidencija potrošnje

`usage.py` posle svakog poziva upisuje red: model, provajder, projekat, persona,
ulazni i izlazni tokeni, izračunat trošak, trajanje, uspeh. Ovo je izvor za AI
odeljak u E7 Analytics.

Trošak se računa iz cena u katalogu u trenutku poziva i **upisuje kao broj**, ne
računa se naknadno — cene se menjaju, a istorija treba da ostane tačna.

## Šema

`codium_ai_usage` raste sa svakim pozivom modela, pa ide u `codium_ops.db`
(**ops v4**). `codium_model_prefs` je postavka korisnika i ide u `codium.db`
(**v10**).

### `codium_ops.db` — migracija ops v4

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

### `codium.db` — migracija v10

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

## Izmene u konfiguraciji

`config/models_config.json` — `Codium` prestaje da bude jedan model:

```json
"Codium": {
  "developer_model": "<slug iz OpenRouter kataloga>",
  "light_model": "qwen2.5:7b",
  "embedding_model": "nomic-embed-text:latest",
  "provider": "openrouter",
  "endpoint": "https://openrouter.ai",
  "local_endpoint": "http://localhost:11434"
}
```

Tačan `developer_model` se **ne prepisuje iz plana**. Postojeća vrednost u
`config/models_config.json` je `anthropic/claude-3.5-sonnet` i zastarela je.
Ispravna vrednost se bira iz kataloga koji `catalog.py` dohvati sa
`GET /api/v1/models` u trenutku implementacije — slug-ovi i cene se menjaju, a
plan napisan danas ne sme da ih zamrzne.

`model_registry` dobija podršku za `local_endpoint`, da jedan domen može imati i
lokalne i online uloge. Postojeći domeni (`CORE`, `Filmium`, `Kalima`) rade
nepromenjeno — polje je opciono.

Preporučeni lokalni modeli za kodiranje su već popisani u
[`docs/CODIUM_PODSETNIK.md`](../../../docs/CODIUM_PODSETNIK.md)
(`qwen2.5-coder:7b`, `deepseek-r1:7b`). E8 ih ne instalira, samo ih prikazuje kada
ih Ollama prijavi.

## API

`apps/api/routers/codium_ai.py` (postojeći router iz F9) se dopunjuje:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/models` | katalog: lokalni + online, sa cenom i dostupnošću |
| POST | `/models/refresh` | ručno osvežavanje keša OpenRouter kataloga |
| GET | `/prefs` | zapamćen model (`?project_id=&persona=`) |
| PUT | `/prefs` | pamćenje izbora |
| POST | `/ask` | **dopunjeno** opcionim poljem `model` |
| GET | `/usage` | potrošnja (`?period=&project_id=`) |

Postojeće ponašanje `/ask` bez polja `model` ostaje isto — F9 ne sme da regresira.

## GUI (radi se posle backend-a bloka)

`features/codium/AiAssistant.tsx`:

- Pored postojećeg dropdown-a persona dolazi **dropdown modela**, sa dve grupe:
  „Lokalno" i „Online". Lokalni nose oznaku VRAM-a, online cenu po milionu tokena.
- Nedostupan model je prikazan sivo sa razlogom u opisu, a ne sakriven — korisnik
  treba da vidi da Ollama ne radi, a ne da mu modeli nestanu.
- Izbor se pamti po projektu i personi.
- Ispod chata mala oznaka: model kojim je odgovoreno i trošak poslednjeg poziva.
- Novi `features/codium/modelPicker.ts` — čist modul: grupisanje, sortiranje,
  filtriranje kataloga. Lako testabilan, bez React-a.

Chat okvir postoji na tri mesta (hub, docking panel, odvojen prozor) i sva tri
koriste istu komponentu — izbor modela stiže u sva tri bez dodatnog rada.

## Testovi

- `test_chat_providers` — oba provajdera protiv lažnog HTTP sloja: uspeh, greška
  mreže, prazan odgovor, brojanje tokena.
- `test_model_catalog` — spajanje izvora, keš se poštuje, nedostupan izvor daje
  zastareo keš umesto praznog spiska.
- `test_router_override` — redosled odlučivanja (override, postavka, registar);
  lokalni model preko VRAM granice se odbija; online poziv iz agenta traži odobrenje.
- `test_ai_usage` — trošak se računa iz cena u trenutku poziva i upisuje kao broj.
- `modelPicker.test.ts` — grupisanje i sortiranje kataloga.
- Regresija: postojeći `test_codium_assistant` i `test_api_codium_ai` moraju
  prolaziti nepromenjeni.

## Definicija završetka

Chat okvir nudi izbor između lokalnih i online modela; izbor se pamti po projektu
i personi; potrošnja se evidentira; nedostupan provajder daje jasnu poruku a ne
tihu zamenu; F9 ponašanje bez izbora modela nije promenjeno; testovi domena prolaze.
