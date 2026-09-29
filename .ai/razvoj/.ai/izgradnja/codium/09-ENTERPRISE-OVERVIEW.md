---
id: codium-adabfbc2-09-enterprise-overview-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: CODIUM Enterprise (E0–E11) — zajednički okvir
summary: Ovaj fajl drži pravila i obrasce koji važe za **sve** enterprise faze (E0–E11),
keywords:
- codium
- enterprise
- e11
- zajednički
- okvir
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/09-ENTERPRISE-OVERVIEW.md
---

# CODIUM Enterprise (E0–E11) — zajednički okvir

Ovaj fajl drži pravila i obrasce koji važe za **sve** enterprise faze (E0–E11),
da ih svaki fazni fajl ne ponavlja. Fazni fajl opisuje samo ono što je specifično
za tu fazu.

Čitaj ovaj fajl jednom na početku enterprise trake, pa dalje samo fazni fajl.

---

## 1. Šta je enterprise traka

Sidebar CODIUM-a već prikazuje jedanaest stavki sa oznakom „USKORO"
(`apps/gui/src/components/layout/Sidebar.tsx`). Enterprise traka ih pretvara u
radne sekcije i uz njih gradi AI ruter koji ih sve poslužuje:

Repositories · Pipelines · Deployments · Infrastructure · Monitoring · Analytics ·
AI Agents · Automations · Integrations · Access & Users · Audit Logs · OmniRoute.

## 2. Odluke korisnika (zaključano 2026-08-22)

1. **Hibrid, lokalno prvo.** Svaka sekcija radi nad lokalnim resursima (lokalni
   git repo, lokalni Docker, lokalni procesi), ali iza `Provider` interfejsa, tako
   da se GitHub / VPS / cloud dodaju kasnije kao drugi provider — bez prepravke
   ekrana i servisa.
2. **„Access & Users" = ScopeGate.** Korisnik je jedini čovek. „Users" su AI
   agenti i automatizacije. Sekcija definiše šta koji akter sme da uradi, sa
   kapijom za ljudsko odobrenje.
3. **AI ide kroz OmniRoute nad dva provajdera:** Ollama (lokalno) i OpenRouter
   (jedan ključ, pristup više online modela). Izbor modela je vidljiv u chat okviru.
4. **Pipelines ima sopstveni lokalni runner.** Ne ogledalo tuđeg CI-ja.
5. **Motor pipeline-a živi u Python backend-u**, ne u Tauri PTY sloju. PTY je
   interaktivan i vezan za otvoren panel; pipeline mora da preživi zatvoren GUI i
   da ima istoriju u bazi. Prikaz uživo u pravom terminalu je moguć kasnije kao
   dodatni sloj nad istim motorom.
6. **Backend pre GUI-ja.** U svakom bloku prvo se završava backend svih faza tog
   bloka, pa se onda radi izgled. Fazni fajlovi zato razdvajaju odeljak
   „Backend" od odeljka „GUI".
7. **E8 se radi prvo, van redosleda brojeva** (dogovoreno 2026-08-22). Vidi
   odeljak „Zavisnosti između faza".
8. **Bez novih formata i biblioteka gde postojeće rade.** Definicije se pišu u
   **JSON**, ne u YAML — Python ga čita ugrađenim modulom, pa nema nove zavisnosti.

## 2a. Odloženo svesno

**Bezbednosne provere** (skeniranje tajni u commit-ovima, provera ranjivih
zavisnosti) **nisu** deo ove trake. Razlog: KALIMA domen, kome to pripada, još
nije počeo da se gradi. Kada KALIMA krene, CODIUM te provere zove kroz nju, a ne
gradi svoje. Ovo je odluka, ne propust.

## 3. Numeracija

Faze F1–F9 su završena istorija v0.1–v0.4 i ne diraju se. Enterprise traka nosi
prefiks **E** (E0–E11). Time je uklonjen raniji sudar, gde su iste oznake F13–F17
u `Sidebar.tsx` i u `90-kasnije.md` značile različite stvari.

Prevođenje starih oznaka:

| Stara oznaka | Bila | Sada |
|---|---|---|
| F13 | Integracije | E0 (sloj) + E11 (ekran) |
| F14 | OneRoute | E8 |
| F15 | OmniRoute | E8 |
| F16 | CODIUM_SICA | E9 |

Zadatak pripreme (radi se uz E0): u `Sidebar.tsx` zameniti badge oznake F13–F17
odgovarajućim E-kodovima, i menjati `kind: "soon"` u `kind: "route"` kako koja
sekcija dobije ekran.

## 4. Obrazac faze — backend

Svaka sekcija dobija paket modula pod `core/domains/codium/<sekcija>/`:

```
core/domains/codium/<sekcija>/
    __init__.py
    models.py        dataclass-ovi + enumeracije (stil postojećeg models.py)
    providers/
        base.py      Protocol: šta provider mora da ume
        local.py     prvi provider (lokalna mašina)
    repository.py    SQL nad codium.db, bez poslovne logike
    service.py       poslovna logika; jedina zove audit i scope gate
```

Uz to:

- **Migracija** — novi `CODIUM_MIGRATION_V<n>` u postojećem
  `core/domains/codium/migrations.py` i dodavanje u `CODIUM_MIGRATIONS`. Jedan
  fajl, nabavka-stil. Trenutna verzija baze je **v2**; enterprise faze nastavljaju
  od v3 (raspored u tabeli u `00-INDEX.md`).

- **Runtime** — `core/domains/codium/<sekcija>_runtime.py` sastavlja servis
  (po uzoru na `codium_assistant_runtime.py`).
- **Schema** — `apps/api/schemas/codium_<sekcija>.py`, Pydantic ulaz/izlaz.
- **Router** — `apps/api/routers/codium_<sekcija>.py`, prefiks
  `/api/v1/codium/<sekcija>`.
- **Putanje** — isključivo preko `CodiumPaths`. Nijedan modul ne sklapa putanju sam.

### Dve baze, ne jedna

`codium.db` drži **poslovne podatke**: projekte, klijente, taskove, beleške,
repozitorijume, pipeline definicije, ciljeve isporuke, agente, pravila.

Nova `data/database/codium_ops.db` drži **operativni saobraćaj**: `run_logs`,
`metric_samples`, `audit_log`, `ai_usage`. To su tabele u koje se piše stalno i
mnogo — uzorak na 30 sekundi za deset servisa je oko 29.000 redova dnevno, a log
jednog `npm ci` je par hiljada redova.

Razlog razdvajanja: bekap poslovne baze ostaje mali i brz, `VACUUM` nad
operativnom bazom ne dira projekte, a dug upis loga ne zaključava čitanje
projekata. CORE već drži više baza (`core.db`, `finansije.db`, `nabavka.db`), pa
je obrazac postojeći.

`CodiumPaths` dobija atribut `ops_database`. Migracije operativne baze idu u
zaseban niz `CODIUM_OPS_MIGRATIONS` sa svojim `scope="codium_ops"`, da se brojanje
verzija dve baze ne pomeša.

Ukrštanje upita između dve baze se **ne radi** SQL-om. E7 Analytics čita iz obe i
spaja u Python-u; podataka je malo posle agregacije.


## 5. Obrazac faze — GUI

```
apps/gui/src/pages/Codium<Sekcija>.tsx        ekran, montiran na rutu
apps/gui/src/features/codium/<sekcija>/       komponente i čisti moduli
apps/gui/src/services/codiumApi.ts            dopuna poziva
apps/gui/src/types/codium.ts                  dopuna tipova
apps/gui/src/styles/codium-<sekcija>.css      stil
```

Ruta se dodaje u router aplikacije, a stavka u `Sidebar.tsx` prelazi iz
`kind: "soon"` u `kind: "route"`.

## 6. Presečna pravila

- **Audit.** Svaka mutacija u servisu poziva `audit.record(...)` iz E1. Nema
  mutacije bez traga.
- **ScopeGate.** Svaka destruktivna ili spoljna akcija prolazi
  `scope_gate.check(actor, action, target)` iz E1. Podrazumevani odgovor za
  destruktivno je odbijanje; potvrda čoveka se traži kroz red za odobrenje.
- **Tajne.** Nijedan kredencijal ne ulazi u SQLite ni u fajl u repozitorijumu.
  Baza čuva samo alias; vrednost živi u OS keychain-u (E0).
- **Bez WebSocket-a.** Live prikaz (log pipeline-a, metrika) rešava se
  inkrementalnim čitanjem uz `?after_seq=` ili `?since=`, pa polling-om iz GUI-ja.
  Pravilo „WebSocket NE dok nema pravog real-time slučaja" ostaje na snazi.
- **Integracije.** Spoljni servisi se zovu isključivo kroz `integrations/` sloj
  (obrazac: postojeći `integrations/translator`). Domen ih ne zove direktno.
- **AI.** Modeli isključivo kroz `core/ai/`. Ne graditi paralelni ruter.
- **Jezik.** Kod i identifikatori na engleskom; komentari, docstring-ovi, UI
  stringovi i dokumentacija na srpskom.
- **Veličina fajla.** 150–300 linija je cilj; preko 500 razmotriti podelu; preko
  1000 obavezan refaktor.
- **Ne gradi ono što `explorer.py` već ima.** `core/domains/codium/explorer.py`
  nosi `list_dir`, `read_file`, `write_file`, `create`, `rename`, `delete`,
  `copy`, `move`, `reveal` i — bitno — `_safe(rel)`, koji brani izlazak iz korena
  projekta. Svaka faza kojoj treba rad sa fajlovima ili provera putanje **uvija
  taj servis**. Ne piše se druga provera putanje.
- **Novi ekran se veže na Overview.** `apps/gui/src/pages/CodiumOverview.tsx` je
  zbirna tabla CODIUM-a i već drži pločice za sekcije koje još ne rade. Faza koja
  pusti sekciju u rad mora u istom potezu da oživi njenu pločicu — inače Overview
  polako postaje laž.

## 6a. Nova zavisnost — obavezan postupak

Ako faza uvodi novu biblioteku ili alat, prati se `docs/DEPENDENCIES.md`, sva
četiri koraka:

1. `Dependency(...)` u `CORE_DEPENDENCIES` (`core/foundation/dependencies.py`) —
   `key`, `label`, `kind`, `severity`, `probe`, `purpose`, `install_hint`,
   `installer`.
2. `scripts/install/<tool>.ps1`, pa ime skripte u `INSTALL_SCRIPTS`
   (`core/foundation/installer.py`).
3. Red u tabeli „Katalog alata" u `docs/DEPENDENCIES.md`.
4. Unos u `requirements.txt` (Python) ili `apps/gui/package.json` (GUI).

Bez prvog koraka indikator zdravlja pored „CORE Online" i INSTALL dugme ne znaju
za alat, pa alat postoji a sistem tvrdi da ne postoji.

Cela enterprise traka uvodi **tačno jednu** novu Python biblioteku: `keyring`
(E0). Sve ostalo koristi ugrađene module ili već registrovane alate. Pipeline
definicije su zato JSON, a ne YAML.

## 7. Testovi

Svaka faza donosi:

- **pytest** za repository, service i provider. Provider se testira preko lažne
  (fake) implementacije `base.py` protokola — nijedan test ne ide na mrežu i ne
  pokreće pravi proces. Obrazac: postojeći `test_codium_assistant`.
- **vitest** za čiste TS module i za komponentu ekrana. Obrazac: postojeći
  `previewProfiles.test.ts` i `AgendaPanel.test.tsx`.

Faza nije završena dok testovi domena ne prolaze u celini i dok je `tsc` čist.

## 8. Zavisnosti između faza

```
E0-mini  vault + jedan OpenRouter konektor
 ├── E8 OmniRoute  (radi se odmah posle E0-mini)
 └── E0-pun  registar svih tipova konektora
      ├── E11 Integrations ekran
      └── E1 Audit + ScopeGate
           ├── E2 Repositories ── E3 Pipelines ── E4 Deployments ─┐
           ├── E5 Infrastructure ── E6 Monitoring ─────────────┤
           │                                                      ├── E7 Analytics
           └── E9 AI Agents (E8 + E1) ── E10 Automations ──────┘
```

E8 zavisi samo od E0-mini. E9 je prva faza kojoj stvarno treba i E8 i E1.

**Redosled izvođenja nije redosled brojeva.** Broj označava mesto u priči, ne
mesto u rasporedu.

### Redosled rada (dogovoreno 2026-08-22)

```
E0-mini → E8 → E0-pun → E1 → E2 → E3 → E4 → E5 → E6 → E7 → E9 → E10 → E11
```

**E8 ide prvi** iako nosi osmi broj. Razlozi:

- Jedina faza koja donosi korist istog dana — AI chat okvir koji je već u
  svakodnevnoj upotrebi dobija izbor modela, lokalnih i online. Sve ostale faze
  su alati za posao koji tek treba da nastane.
- Zavisnost od E1 je slabija nego što izgleda: pravilo E1 kaže da `human`
  zaobilazi gate, a u E8 pozive pokreće čovek. ScopeGate stvarno zatreba tek u
  E9, kad agent počne sam da zove online model. Do tada je `ai.call_online`
  provera koju E8 ostavi kao mesto, a E1 popuni.
- Da E8 čeka svoj red, prvoj stvari koja olakšava svakodnevni rad prethodilo bi
  nekoliko meseci nevidljivog vodovoda. To je najčešći način da se ovakva traka
  napusti na pola.

**E0 se zato cepa na dva reza:**

- **E0-mini** — samo `SecretVault` plus jedan konektor tipa `openrouter`. Toliko
  koliko E8 treba da negde drži API ključ. Mali posao, radi se pre E8.
- **E0-pun** — registar svih tipova konektora (`github`, `docker_registry`,
  `ssh_host`, `smtp`), `test_connection` po tipu, pun API. Radi se posle E8, kada
  E4 i E5 zatraže SSH i Docker.

**E7 Analytics** čita podatke koje pišu E2, E3, E4, E6 i E8, pa ide posle svih njih.

**E10 Automations** povezuje događaje iz E2–E6 sa akcijama, pa traži da su ti
podsistemi već operativni.

## 9. Šta se u postojećem kodu menja

| Fajl | Izmena | Faza |
|---|---|---|
| `apps/gui/src/components/layout/Sidebar.tsx` | badge F13–F17 → E-kodovi; `soon` → `route` kad ekran stigne | E0 pa dalje |
| `core/domains/codium/migrations.py` | nove verzije v3+ | po fazi |
| `config/models_config.json` | Codium dobija listu modela umesto jednog | E8 |
| `core/ai/core_router.py` | prima `override_model` | E8 |
| `.ai/izgradnja/codium/90-kasnije.md` | F13–F16 uklonjeni, pokazuju na E-fajlove | E0 |
