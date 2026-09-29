---
id: codium-1ad03ff9-2026-08-29-codium-openrouter-design-md
type: spec
domain: codium
namespace: global
visibility: global
tier: domain
title: AI-3 — OpenRouter u CORE ruteru modela
summary: '**Datum:** 2026-08-29'
keywords:
- openrouter
- core
- ruteru
- modela
- docs
- superpowers
- specs
tags:
- superpowers
- specs
source_path: docs/superpowers/specs/2026-08-29-codium-openrouter-design.md
---

# AI-3 — OpenRouter u CORE ruteru modela

**Datum:** 2026-08-29
**Faza:** AI-3 (fazni fajl `.ai/izgradnja/codium/18-E8-omniroute.md`)
**Zavisi od:** AI-1 (Ollama), AI-2 (vault, konektori, `ChatProvider` sloj), E1 (ScopeGate)

---

## 1. Zašto

Chat okvir danas bira između lokalnih modela (Ollama) i dva direktna online
provajdera (Anthropic, OpenAI), a svaki od njih traži svoj ključ i svoj račun.
OpenRouter je jedan ključ za sve — uključujući Claude i GPT modele — pa je za
svakodnevni rad jeftiniji put od tri odvojena naloga.

Fazni fajl `18-E8-omniroute.md` je pisan pre nego što su AI-1 i AI-2 postojali i
opisuje gradnju celog sloja provajdera. Taj sloj je u međuvremenu napravljen.
Ovaj dokument opisuje **ono što je stvarno preostalo**, i nadjačava fazni fajl
gde se razilaze.

### Šta već postoji i ne gradi se ponovo

| Modul | Uloga |
|---|---|
| `core/ai/providers/base.py` | `ChatProvider` protokol, `ModelInfo`, `ChatResult`, `ProviderUnavailable` |
| `core/ai/providers/{ollama,anthropic,openai}.py` | tri postojeća provajdera |
| `core/ai/catalog.py` | `ModelCatalog` — spaja provajdere, nedostupan daje red sa razlogom |
| `core/ai/model_router.py` | `ModelRouter` — override → zapamćeno → podrazumevano |
| `core/ai/usage.py` | evidencija poziva u `codium_ops.db` |
| `core/ai/pricing.py` | ručna tabela cena |
| `core/ai/visibility.py` | deny lista modela, globalna i po domenu |
| `core/integrations/` | konektori, `SecretVault`, proba konekcije |
| `apps/gui/.../modelPicker.ts` | grupisanje i natpisi u izborniku |

## 2. Odluke

Sve četiri su donete pre pisanja, u razgovoru:

1. **Online poziv prolazi kroz kapiju** (`ai.call_online`). Čovek prolazi, agent
   traži odobrenje. Fazni fajl je ovde zastareo — pisan je dok E1 nije postojao.
2. **Anthropic put se proverava istim prolazom** kad ključ bude unet, čime se
   zatvara i AI-2.
3. **OpenRouter dobija allow listu.** Deny lista ostaje netaknuta za sve ostale.
4. **Nema nove zavisnosti.** OpenRouter je OpenAI-kompatibilan, pa ide kroz već
   instaliran `openai` SDK sa drugim `base_url`.

## 3. Šta se dodaje

```
core/integrations/providers/openrouter.py   proba konekcije (da se ključ sačuva)
core/ai/providers/openrouter.py             ChatProvider: models(), chat()
core/ai/openrouter_catalog.py               dohvat kataloga + keš na disk
core/ai/allowlist.py                        allow lista (core_ai v3)
core/ai/selection.py                        jedno mesto koje računa `enabled`
```

### 3.1 Konektor (`core/integrations/providers/openrouter.py`)

Ogledalo `OpenAIConnectorProvider`-a: `kind = ConnectorKind.OPENROUTER`,
`secret_fields() -> ["api_key"]`, `test()` pravi klijent i zove `models.list()`.
Klijent se ubrizgava, pa testovi ne dodiruju mrežu.

Bez ovoga panel „API ključevi" prikazuje OpenRouter kao nepodržan i ne da ključ
da se sačuva — `ConnectorService.supported_kinds()` vraća samo vrste koje imaju
provajdera. Zato je ovo **prvi** posao u planu.

Registracija u `apps/api/core_ai_runtime.py`, uz postojeća dva.

### 3.2 Katalog (`core/ai/openrouter_catalog.py`)

`GET https://openrouter.ai/api/v1/models` vraća id, ime, dužinu konteksta i
**cene po tokenu** (kao tekst, u dolarima). Cena time dolazi iz izvora, a ne iz
ručne tabele.

Keš na disk: `data/cache/openrouter_models.json`, rok **24 sata**. Zapis nosi
vreme dohvatanja i sirov spisak.

Pravila:

- Katalog **nikada ne obara poziv.** Ako dohvatanje padne a keš postoji, vraća se
  keš uz `stale=True`. Ako ni keš ne postoji, diže se `ProviderUnavailable`, što
  `ModelCatalog` već ume da pretvori u jedan red sa razlogom.
- Keš se piše **atomično** (upis u privremeni fajl pa `os.replace`), da prekinut
  upis ne ostavi polovan JSON koji sledeći start ne ume da pročita.
- Modul ne zna za vault ni za HTTP klijent — dohvatanje se ubrizgava kao
  funkcija, pa se rok, zastarelost i pad testiraju bez mreže.

Cene se prevode u dolare **po milionu tokena**, jer je to jedinica koju
`ModelInfo` i `pricing.py` već koriste. Prevod na jednom mestu, u ovom modulu.

### 3.3 Provajder (`core/ai/providers/openrouter.py`)

```python
name = "openrouter"
is_local = False
```

- `available()` — ima li ključa u vault-u (isti obrazac kao Anthropic i OpenAI:
  alias se traži u trenutku poziva, jer konektor nastaje dok aplikacija radi).
- `models()` — iz kataloga, u `ModelInfo` sa cenom i kontekstom.
- `chat()` — `openai.OpenAI(api_key=…, base_url="https://openrouter.ai/api/v1")`,
  pa `chat.completions.create`. Zaglavlja `HTTP-Referer` i `X-Title` se šalju sa
  imenom CORE-a — OpenRouter ih koristi za pripisivanje saobraćaja.

Bez ključa `models()` diže `ProviderUnavailable`, isto kao ostali online
provajderi. Katalog je javan, ali prikazivati 300 modela koji ne mogu da odgovore
znači ponuditi izbor koji puca pri prvom kliku.

### 3.4 Allow lista (`core/ai/allowlist.py`, migracija core_ai v3)

```sql
CREATE TABLE core_model_allowlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    provider   TEXT NOT NULL,
    model      TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_core_model_allowlist
    ON core_model_allowlist (provider, model);
```

**Semantika, izgovorena da se dve liste ne pobrkaju:**

> Deny lista kaže **šta se ne nudi**. Allow lista kaže **šta uopšte postoji**.
> Provajder bez allow liste nudi sve osim onoga što je zabranjeno; provajder sa
> allow listom ne nudi ništa osim onoga što je izričito pušteno.

Allow lista je **globalna, bez opsega.** CORE odlučuje koji OpenRouter modeli
uopšte postoje; postojeća deny lista po domenu i dalje sme da ih suzi. Dve
dimenzije opsega nad istim modelom niko nije tražio.

Provajder deklariše da je traži:

```python
needs_allowlist = True
```

Polje je opciono na protokolu (`getattr(provider, "needs_allowlist", False)`),
pa tri postojeća provajdera ostaju nepromenjena.

#### Prvo punjenje

Prazna allow lista znači prazan OpenRouter u chatu — tačno, ali neupotrebljivo na
prvom startu. Zato se **pri prvom uspešnom dohvatu kataloga** upisuje pregršt
modela izabranih **pravilom nad živim katalogom**, ne spiskom slug-ova zamrznutim
u kodu:

- porodica iz popisa (`anthropic/`, `openai/`, `google/`, `deepseek/`, `qwen/`),
- ima cenu veću od nule (besplatne varijante imaju oštra ograničenja),
- kontekst najmanje 100k,
- po jedan najskuplji (dakle najjači) model po porodici.

Da uključivanje ne bi vaskrsavalo ono što si izbacio, upisuje se i marker red
`("openrouter", "__seeded__")`. Punjenje se izvršava **samo ako markera nema.**

Slug-ovi se menjaju, pa ih plan ne sme zamrznuti — otud pravilo, a ne spisak.

### 3.5 Jedno mesto za `enabled` (`core/ai/selection.py`)

Danas i `routers/core_models.py` i `routers/codium_ai.py` imaju svoju kopiju
funkcije `_red` koja spaja deny liste u polje `enabled`. Allow lista bi bila
treća stvar koju obe kopije moraju da znaju — a to je tačno onaj oblik dupliranja
koji se raziđe.

```python
class ModelSelection:
    """Odlucuje da li se model nudi: allow lista, pa deny liste."""

    def __init__(self, visibility: ModelVisibilityRepository,
                 allowlist: ModelAllowlist) -> None: ...

    def decide(self, model: ModelInfo, scope: str) -> Decision: ...
```

`Decision` nosi `enabled` i `disabled_globally` — tačno ono što oba routera već
šalju GUI-ju. Ponašanje za postojeće provajdere ostaje identično; ovo je premeštaj,
ne promena.

Red-čuvar (`is_placeholder=True`) nikada nije `enabled` — nije model.

### 3.6 Cene (`core/ai/pricing.py`)

`price_for()` dobija drugi izvor: prvo ručna tabela, pa keš OpenRouter kataloga.
Ručna tabela ostaje prva, jer je za direktne Anthropic i OpenAI pozive tačnija od
OpenRouter-ove marže.

`usage.py` se **ne dira.** Trošak se i dalje računa u trenutku upisa i čuva kao
broj — istorija ostaje tačna kad se cene promene.

### 3.7 Kapija (`ai.call_online`)

Provera ide u `core/domains/codium/agents/loop.py`, gde agent i bira model.
**Ne** u `core/ai` — ruter modela ne sme da zna za CODIUM kapiju; to bi CORE sloj
vezalo za jedan domen.

- Čovek: pravilo E1 (`human` zaobilazi kapiju) — nepromenjeno.
- Agent: pre poziva online modela pita kapiju za `ai.call_online` sa ciljem
  `<provajder>/<model>`. `deny` obara potez, `needs_approval` pauzira posao istim
  putem kojim već pauzira `file.write`.

Lokalni model ne pita ništa — ne troši novac.

Podrazumevano pravilo se upisuje uz migraciju: `agent:* / ai.call_online / * →
needs_approval`.

## 4. API

Bez novih ruta. Dve dopune:

| Ruta | Dopuna |
|---|---|
| `GET /api/v1/core/ai/models` | `?only_enabled=true` — vraća samo ono što se nudi |
| `GET /api/v1/codium/ai/models` | isto |
| `PUT /api/v1/core/ai/models/enabled` | u globalnom opsegu, za provajdera sa allow listom, upisuje u nju umesto u deny listu |

Opseg odlučuje u koju listu ide upis, jer je allow lista globalna: u opsegu
`global` model provajdera sa allow listom se u nju upisuje ili iz nje briše, a u
opsegu domena (`codium`, `core`…) i dalje radi postojeća deny lista. Tako domen
sme da suzi izbor, ali ne i da pusti model koji CORE nije pustio — isto pravilo
koje deny lista već poštuje.

`only_enabled` postoji zbog obima: chat izborniku ne treba 300 redova od kojih
prikazuje pet. Podrazumevano je `false`, pa podešavanja i dalje vide sve i mogu da
vrate isključen model — postojeće ponašanje se ne menja.

## 5. GUI

`ModelsPanel` dobija sekciju **„OpenRouter katalog"**:

- polje za pretragu (po id-u i imenu),
- red po modelu: ime, kontekst, cena ulaz/izlaz, prekidač uključi/isključi,
- prikazuje se samo kada OpenRouter ima ključ; bez ključa stoji jedan red sa
  razlogom, kao i za ostale provajdere,
- lista je odsečena na prvih 50 pogodaka, sa brojem ostalih — 300 redova u DOM-u
  nije spisak nego kazna.

Chat izbornik se **ne menja.** Zove `/models?only_enabled=true` i kroz postojeći
`modelPicker.ts` dobija grupe „Lokalno" i „Online".

Novi čist modul `features/settings/openrouterCatalog.ts` — pretraga, odsecanje,
format cene. Bez React-a, testira se bez renderovanja (isti obrazac kao
`modelPicker.ts`).

## 6. Testovi

Backend:

- `test_openrouter_connector` — proba bez ključa, uspeh, pad SDK-a.
- `test_openrouter_catalog` — svež dohvat, keš unutar roka ne poziva mrežu,
  istekao keš poziva, pad mreže vraća zastareo keš, pad bez keša diže grešku,
  prekinut upis ne ostavlja polovan fajl.
- `test_openrouter_provider` — `available()` bez ključa, `models()` mapira cenu i
  kontekst, `chat()` prosleđuje `base_url` i broji tokene.
- `test_model_allowlist` — prazna lista ne nudi ništa; prvo punjenje bira po
  pravilu; drugi poziv ne puni ponovo (marker); izbačen model ostaje izbačen.
- `test_model_selection` — postojeći provajderi se ponašaju identično kao pre;
  provajder sa allow listom ne; red-čuvar nikada nije `enabled`.
- `test_agent_online_gate` — agent sa online modelom traži odobrenje; sa lokalnim
  ne pita ništa; `deny` obara potez i upisuje trag.
- Regresija: `test_codium_assistant`, `test_api_codium_ai`, `test_core_models`
  prolaze nepromenjeni.

GUI:

- `openrouterCatalog.test.ts` — pretraga, odsecanje, format cene.
- Regresija: `modelPicker.test.ts` nepromenjen.

## 7. Provera uživo

Testovi ne dokazuju da OpenRouter radi — dokazuju da naš kod radi. Zato,
tvojim ključem, unetim kroz **Podešavanja → API ključevi**:

1. Konektor se sačuva i proba konekcije prođe.
2. Katalog stigne; drugi otvor ne poziva mrežu (keš).
3. Allow lista se napunila sama, i to razumnim izborom.
4. Model odgovori u chatu; odgovor kaže kojim je modelom odgovoreno.
5. Potrošnja upisana sa tačnim brojem tokena i troškom većim od nule.
6. Isključen model se više ne nudi u chatu, a u podešavanjima se vraća.
7. Agent sa online modelom pauzira posao i čeka odobrenje.
8. Isti prolaz za Anthropic, ako i taj ključ bude unet — čime se zatvara AI-2.

## 8. Šta ostaje van dometa

- **Streaming kroz OpenRouter.** `ChatProvider` danas nema `stream()`; nijedan
  postojeći provajder ga ne implementira. Dodavanje streaminga je izmena
  protokola za sve, ne posao ovog provajdera.
- **`codium_model_prefs`** (pamćenje modela po projektu i personi) iz faznog
  fajla. `ModelRouter` već prima `pref_lookup`, ali ga runtime danas vezuje na
  `lambda: None`. To je zasebna faza sa svojom tabelom i svojim ekranom.
- **Izveštaj potrošnje** — `usage.py` upisuje, E7 Analytics prikazuje.
- **`developer_model` u `config/models_config.json`** ostaje zastareo
  (`anthropic/claude-3.5-sonnet`) dok se ne izabere iz živog kataloga. Ispravlja
  se u koraku provere uživo, ne iz plana.

## 9. Bezbednosna napomena

Ključ je u ovoj sesiji poslat kao čist tekst i time je zapisan u transkript na
disku. Posle provere treba ga poništiti na openrouter.ai i napraviti nov. Nova
vrednost ide isključivo kroz **Podešavanja → API ključevi**, koja je smešta u OS
keychain preko `SecretVault`-a — baza čuva samo `secret_alias`, nikad vrednost.
