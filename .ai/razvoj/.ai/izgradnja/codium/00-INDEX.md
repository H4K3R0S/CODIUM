---
id: codium-66d262ea-00-index-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: CODIUM — INDEX izgradnje
summary: Ruter za izgradnju CODIUM domena. Ovde se prati status. Fazni fajlovi su
  plan.
keywords:
- codium
- index
- izgradnje
- izgradnja
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/00-INDEX.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
- type: references
  target: core-abe7bfd0-2026-08-24-codium-ai-provajderi-design-md
  weight: 0.3
- type: references
  target: codium-9e822470-14-e4-deployments-md
  weight: 0.3
- type: references
  target: codium-d048df85-15-e5-infrastructure-md
  weight: 0.3
- type: references
  target: codium-22e3d9cd-16-e6-monitoring-md
  weight: 0.3
- type: references
  target: codium-b9e8f971-12-e2-repositories-md
  weight: 0.3
- type: references
  target: codium-ab5c8ca7-90-kasnije-md
  weight: 0.3
- type: references
  target: codium-4dd4d4da-01-backend-skeleton-md
  weight: 0.3
- type: references
  target: codium-580b9d17-02-project-hub-md
  weight: 0.3
- type: references
  target: codium-058228c1-03-project-brain-md
  weight: 0.3
- type: references
  target: codium-0d3e24f5-04-workspace-shell-md
  weight: 0.3
- type: references
  target: codium-3d1b3b0a-05-explorer-md
  weight: 0.3
---

# CODIUM — INDEX izgradnje

Ruter za izgradnju CODIUM domena. Ovde se prati status. Fazni fajlovi su plan.

Trenutno stanje domena: **v0.1 MVP završen (F1 + F2 + F3)**. Backend pun (`paths`,
`models`, `migrations`, `runtime`, `repository`, `service`, `brain`, API,
`data/database/codium.db`). GUI Project Hub (`pages/CodiumPage.tsx` + `codiumApi.ts`
+ `types/codium.ts` + `codium-hub.css`, ruta `/codium`) i Brain panel
(`features/codium/BrainModal.tsx`, read-only `.codium/` prikaz + generisanje +
dev-log). Tasks/Beleške panel na kartici (`features/codium/ProjectWorkModal.tsx`,
tabovi Taskovi/Beleške preko F1 API, čekiranje→done). **F4 Workspace shell**
(`pages/CodiumWorkspace.tsx` + `codium-workspace.css`, ruta `/codium/workspace/:id`):
6 regiona (toolbar/rail/explorer/editor/right/bottom), rail nav (Tasks/Beleške/Brain
aktivni, ostalo placeholder „uskoro"), „Otvori" vodi u workspace. Aktivan projekat u
localStorage. Sve potvrđeno uživo. Odloženo (F5+): Explorer, Monaco editor, Preview,
Terminal, Git, AI Chat, embeddings, protocol.

## Vizija (kratko)

CODIUM = CORE domen za razvoj softvera: project manager + brz editor + preview
orkestrator + AI dev partner + dnevnik rada + baza klijenata/projekata. Ne kopija
VS Code-a. VS Code/Sublime = inspiracija za editor. Razlika = projekti, ciljevi,
kontekst, AI, dev-log, rokovi, klijenti, domenski protokol.

Princip: **model je zamenljiv, protokol je trajan.**

## Status faza

| Faza | Naziv                        | Prioritet | Status        | Datum |
|------|------------------------------|-----------|---------------|-------|
| F1   | Backend domain skeleton      | v0.1      | zavrseno      | 2026-08-17 |
| F2   | Project Hub GUI              | v0.1      | zavrseno      | 2026-08-17 |
| F3   | Project Brain folder         | v0.1      | zavrseno      | 2026-08-17 |
| —    | Tasks/Beleške panel (kartica)| v0.1+     | zavrseno      | 2026-08-17 |
| F4   | Workspace shell              | v0.2      | zavrseno      | 2026-08-17 |
| F5   | Explorer (file tree)         | v0.2      | zavrseno (+DnD/ikonice 2026-08-21) | 2026-08-17 |
| F6   | Editor (Monaco)              | v0.2      | zavrseno      | 2026-08-18 |
| F8   | Notes / agenda / kalendar    | v0.2      | zavrseno      | 2026-08-18 |
| F7   | Preview Orchestrator         | v0.3      | zavrseno (MVP)| 2026-08-18 |
| F9   | AI panel (chat po personi)   | v0.4      | slice 1 zavrsen | 2026-08-21 |
| F10  | Embeddings / project search  | kasnije   | plan zapisan  | —     |
| F11  | AI Development Protocol      | kasnije   | plan zapisan  | —     |
| F12  | Visual Design shell          | kasnije   | plan zapisan  | —     |

## Status faza — enterprise traka (E)

Cilj trake: jedanaest sidebar stavki koje stoje kao „USKORO" postaju radne
sekcije, plus AI ruter koji ih poslužuje. Zajednička pravila i obrasci su u
[09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md) — pročitaj taj fajl jednom
pre prve E faze, pa dalje samo fazni fajl.

**Redosled rada: backend celog bloka, pa GUI tog bloka.** Odluka korisnika
(2026-08-22): „prvo napravi sve u backendu kako treba, pa onda da to lepo izgleda".

**AI blok je izuzetak od tog pravila** (odluka korisnika 2026-08-25). Stari
`E8 OmniRoute` je razbijen na tri faze koje idu prvo, i svaka je upotrebljiva
kraj-do-kraju (backend plus GUI), jer se AI chat okvir koristi svakodnevno i
svaka faza mu odmah dodaje vrednost. Redosled je lokalni modeli, pa Claude preko
direktnog Anthropic API-ja, pa OmniRoute sa OpenRouter-om. Obrazloženje i pun
opis su u
[`docs/superpowers/specs/2026-08-24-codium-ai-provajderi-design.md`](../../../docs/superpowers/specs/2026-08-24-codium-ai-provajderi-design.md).

Brojevi migracija se dodeljuju redosledom **izrade**, ne redosledom u tabeli;
fazi koja još nije napravljena zato ne stoji broj, nego napomena da se
dodeljuje kad na nju dođe red.

| # | Faza | Naziv | Zavisi od | Baza | Status | Datum |
|---|------|-------|-----------|------|--------|-------|
| 1  | AI-1 | Lokalni modeli (Ollama) u chat okviru | — | codium v3 | **zavrseno** | 2026-08-25 |
| 2  | AI-2 | Claude (Anthropic API) + vault + potrošnja | AI-1 | codium v4 + ops v1 | **kod gotov, kljuc ispravan, nalog bez kredita** | — |
| 3  | AI-3 | OpenRouter (katalog, allow lista, kapija) | AI-2 | core_ai v3 + codium v9 | **zavrseno** (potvrdjeno uzivo) | 2026-08-29 |
| 4  | E2  | Repositories | E1 | codium v10 | **zavrseno** | 2026-08-30 |
| 5  | E1  | Audit Logs + ScopeGate (Access & Users) | AI-2 | codium v6 (pravila) + v7 (odobrenja) + ops v2 | **zavrseno** | 2026-08-29 |
| 6  | E0-pun | Registar svih tipova konektora | AI-2 | nema (tabela je u core.db od AI-2) | **zavrseno** | 2026-09-04 |
| 7  | E3  | Pipelines (lokalni runner) | E1, E2 | codium v11 + ops v3 | **zavrseno** | 2026-09-01 |
| 8  | E4  | Deployments | E1–E3 | codium v12 | **zavrseno** | 2026-09-02 |
| 9  | E5  | Infrastructure | E1 | codium v13 | **zavrseno** | 2026-09-03 |
| 10 | E6  | Monitoring | E5 | codium v14 + ops v4 | **zavrseno** | 2026-09-03 |
| 11 | E7  | Analytics | E2–E4, E6, AI-3 | nema (samo cita) | **zavrseno** | 2026-09-03 |
| 12 | E9  | AI Agents | E1 | codium v8 | **zavrseno** | 2026-08-29 |
| 13 | E10 | Automations | E2–E6, E9 | codium v15 | **zavrseno** | 2026-09-03 |
| 14 | E11 | Integrations (ekran) | E0-pun | — | **zavrseno** | 2026-09-04 |

**E3 je podeljen na E3a i E3b — oboje sada zavrseno.** E3a (motor, dve baze,
API, agentski alati) je zavrsen 2026-08-30 — vidi tabelu iznad i dev-log unos
za taj dan. E3b (ekran pipeline-a — stranica `/codium/pipelines`, Monaco JSON
editor sa registrovanom semom, prikaz pokretanja sa ANSI logom, Overview
plocica, potvrda pri zatvaranju prozora u toku pokretanja) je zavrsen
2026-09-01 — vidi dev-log unos za taj dan. Fazni datumi se namerno ne
poklapaju: cela faza E3 je trajala dva dana, ne jedan.

**E4 Deployments je zavrsen 2026-09-02** (backend i GUI zajedno, kao E2 —
odluka korisnika). Migracija je dobila broj **v12** pri izradi; fazni fajl
[14-E4-deployments.md](14-E4-deployments.md) jos pise `v7`, po staroj
numeraciji od pre AI bloka.

**E5 Infrastructure je zavrsen 2026-09-03** (backend i GUI zajedno, kao E4).
Migracija je dobila broj **v13** pri izradi; fazni fajl
[15-E5-infrastructure.md](15-E5-infrastructure.md) jos pise `v8`, po staroj
numeraciji od pre AI bloka. Logika iz `dev_server.py` nije duplirana —
izdvojena je u `infrastructure/process_registry.py`, a F7 Preview je postao
njen pozivalac i nije regresirao.

**E6 Monitoring je zavrsen 2026-09-03**, istog dana kad i E5. Migracije su
dobile brojeve **codium v14** i **ops v4** pri izradi; fazni fajl
[16-E6-monitoring.md](16-E6-monitoring.md) jos pise `v9 + ops v3`.

**E7 Analytics je zavrsen 2026-09-03**, istog dana kad i E5 i E6. Jedina faza
BEZ migracije: ne proizvodi nove podatke nego cita ono sto E2, E3, E4, E6 i AI
blok vec upisuju. Dva odstupanja od faznog fajla, oba iz stvarnog stanja koda:
podaci su u DVE baze (podela postoji od E1 i E6), a commit-i uopste nisu u bazi
— E2 ih namerno ne kopira, pa `commits_per_day` ide kroz `GitProvider`.

**E10 Automations je zavrsen 2026-09-03** (migracija `codium v15`, ne v12 kako
je fazni fajl predvidjao — brojaci su odmakli zbog E5 i E6). Uslov pravila se
parsira sopstvenom gramatikom, nikad `eval`-om, a tri kocnice (sopstvena
posledica, ucestalost koja GASI pravilo, dubina lanca) postoje jer je ovo prva
faza u kojoj sistem pokrece sam sebe.

**E0-pun i E11 su zavrseni 2026-09-04, zajedno.** Konektori ne zive u CODIUM-u
nego u CORE-u (`/api/v1/core/ai/connectors`) jos od preseljenja u AI bloku, pa
je E11 napravljen kao CODIUM ekran nad CORE rutama; `codium v4` ostaje napustena
migracija. Time nijedna CODIUM stavka u sidebar-u vise nije „USKORO“.

**Enterprise traka je time zaokruzena.** Stari `E8 OmniRoute` ne stoji kao
zaseban posao — razbijen je na AI-1, AI-2 i AI-3, a te tri faze su zavrsene.
Ostaje AI-2, koji ceka kredit na nalogu, ne kod.

`E2 Repositories` je ranije presao ispred `E0-pun` iz dva razloga koji su se
ostvarili: otkljucao je E3 i E4, i dao agentu iz E9 dva alata (`git_log`,
`git_diff`) koji su tamo ostali neispisani jer nije bilo sta da se omota.
`E0-pun` je docekao svog potrosaca tek sa E11: cetiri preostala tipa konektora
(GitHub, Docker registry, SSH, SMTP) napravljena su onog dana kad je ekran koji
ih prikazuje — dok ekrana nije bilo, nista ih ne bi ni pozvalo.

**Odluke za E2 su vec donete** (razgovor 2026-08-29) i zapisane u faznom fajlu
[12-E2-repositories.md](12-E2-repositories.md): rucan upis uz ponudu iz projekata,
citanje plus `fetch` (nista sto menja radno stablo), i domet backend + GUI + alati
agenta. Sledeci korak je dizajn pa plan izvodjenja, po istom putu kao AI-3.

**Kolona `#` je redosled rada; oznaka faze je samo ime.** `E0-mini` više ne stoji
samostalno — vault i tabela konektora ulaze u `AI-2`, jer im je prvi potrošač
Anthropic ključ. Podela E0 na `mini`/`pun` opisana je u
[09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md); `E0-pun` ostaje kao
zasebna faza.

**Numeracija migracija je pomerena** u odnosu na verziju od 2026-08-22: AI blok
troši `codium v3` i `v4` i prvu verziju `codium_ops.db`, pa sve kasnije faze idu
za jedan naviše. Tabela iznad već nosi ispravne brojeve; fazni fajlovi
`11-E1`…`17-E6` još nose stare i ispravljaju se kad na njih dođe red.

**Dve baze.** `codium.db` drži poslovne podatke (trenutno **v3**, potrošeno u
`AI-1`; `AI-2` nastavlja od v4; E1 je stvarno potrošio v6 i v7 — vidi tabelu
iznad i napomenu ispod nje o dodeli brojeva pri izradi). Nova
`codium_ops.db` drži operativni saobraćaj — `audit_log`, `run_logs`,
`metric_samples`, `ai_usage` — sa sopstvenim brojanjem verzija (`ops v1`…).
Razlog: te tabele rastu hiljadama redova dnevno i ne smeju da opterećuju bekap i
zaključavanje poslovne baze.

**Dve nove zavisnosti u celoj traci:** `keyring` i `anthropic` (obe u `AI-2`,
E0-mini više ne stoji samostalno — vidi tabelu iznad), svaka registrovana po sva
četiri koraka iz `docs/DEPENDENCIES.md`. Pipeline definicije su zato JSON, a ne
YAML — `PyYAML` se ne uvodi.

Numeracija: F1–F12 je postojeća traka i ne dira se. E0–E11 je enterprise traka.
Raniji sudar oznaka (F13–F17 u `Sidebar.tsx` naspram F13–F16 u `90-kasnije.md`)
uklonjen je ovim razdvajanjem; tabela prevođenja starih oznaka je u
[09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

## F9 slice 1 (2026-08-21)

- **Backend** `core/domains/codium/assistant/`: `personas.py` (7 chat modova — Arhitekta/
  Graditelj/Recenzent/Dizajner/Menadžer/Debager/Pisac, svaki svoj srpski sistemski prompt),
  `assistant_service.py` `CodiumAssistant.ask(project_id, persona, message, history)` — ide
  kroz `core/ai` (ModelRegistry + Ollama), lokalni CORE model (openrouter `developer_model`
  čeka konektor), kontekst projekta (ime/stack/status) + istorija u promptu; `OllamaUnavailable`
  → uredan fallback. Runtime `codium_assistant_runtime.py`, schema `codium_ai.py`, router
  `/api/v1/codium/ai/{personas,ask}`. Testovi: `test_codium_assistant` (6) + `test_api_codium_ai` (3).
- **GUI** `features/codium/AiAssistant.tsx`: persona dropdown + chat nit (me/assistant balončići,
  fallback obeležen) + input (Enter šalje) → `codiumApi.askAssistant`; „kuca" indikator. Ožičen u
  docking panel „AI" (bio placeholder). `styles/codium-ai.css`. codium 50/50, tsc čist.
- Sledeći slice-ovi: attach (otvoreni fajl/selekcija/log), akcije (save note/create task iz chata),
  streaming, izbor modela (F14 OneRoute), OpenRouter konektor za `developer_model`.

## F9 slice 2 — uvek dostupan AI + pozicioniranje/odvajanje (2026-08-21)

- **Uvek dostupan**: workspace toolbar dobio „AI" toggle → desni **vertikalni AI panel**
  (`WorkspaceAiColumn`), radi u oba rasporeda (fiksni/docking), stanje+širina se pamte
  (`codium.aiOpen`/`codium.aiWidth`), leva ivica se prevlači (clamp 300–900).
- **Hub chat** (dno-centar) + **docking „AI" panel** (prevuci pored Terminala / veliki desni
  vertikalni / float) i dalje tu — sad je isti asistent dostupan i kao stalna kolona.
- **Odvajanje u zaseban prozor**: „Odvoji" dugme → `openAiChatWindow` otvara čist prozor
  prilepljen uz **desnu ivicu ekrana, pune visine** (`gridSnap.computeScreenRightEdgeFrame` +
  `openScreenRightEdge`, bare view `codium-ai` čita `project` iz query-ja). Test:
  `computeScreenRightEdgeFrame` (3). Van Tauri-ja no-op (browser).
- gridSnap+codium 61/61, tsc čist. Uživo potvrđeno: toggle → desna kolona (prislonjena, resize
  380→520, persona+chat). Bez Rust promene.

v0.1 = F1 + F2 + F3 → **MVP ZAVRŠEN**. Zatim odmrznuti i završeni **F4 Workspace shell**
+ **F5 Explorer** (namenski skener) + **F6 Editor** (Monaco, multi-tab, save) + **F8 Agenda**
(rokovi + podsetnici, lista + kalendar) + **F7 Preview** (MVP: ručni URL, uređajni profili,
izbor monitora, zaseban Tauri prozor). Redosled po dogovoru: F8 pa F7. Sve od F9 naviše je
zamrznuto u [90-kasnije.md](90-kasnije.md) dok se ne stabilizuje.

## Fazni fajlovi

- [01-backend-skeleton.md](01-backend-skeleton.md) — F1: baza, modeli, servisi, router
- [02-project-hub.md](02-project-hub.md) — F2: prvi ekran, kartice projekata
- [03-project-brain.md](03-project-brain.md) — F3: `.codium/` folder po projektu
- [04-workspace-shell.md](04-workspace-shell.md) — F4: radno okruženje (ljuska + regioni)
- [05-explorer.md](05-explorer.md) — F5: file tree (nov skener + GUI Explorer)
- [06-editor.md](06-editor.md) — F6: Monaco editor (multi-tab, save)
- [07-notes-agenda.md](07-notes-agenda.md) — F8: agenda (rokovi + podsetnici) + kalendar
- [08-preview.md](08-preview.md) — F7: preview orkestrator (uređajni profili, Tauri prozor)
- [90-kasnije.md](90-kasnije.md) — F10–F12 sažeto (embeddings, protocol, vision)

## Fazni fajlovi — enterprise traka

- [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md) — zajednička pravila, obrasci, zavisnosti
- [10-E0-integracije-i-vault.md](10-E0-integracije-i-vault.md) — konektori + tajne u OS keychain-u
- [11-E1-audit-i-scopegate.md](11-E1-audit-i-scopegate.md) — dnevnik + dozvole nad akcijama
- [12-E2-repositories.md](12-E2-repositories.md) — git registar, stanje, istorija, razlika
- [13-E3-pipelines.md](13-E3-pipelines.md) — sopstveni lokalni runner + log
- [14-E4-deployments.md](14-E4-deployments.md) — artefakt, ciljevi, povratak unazad
- [15-E5-infrastructure.md](15-E5-infrastructure.md) — servisi, procesi, Docker
- [16-E6-monitoring.md](16-E6-monitoring.md) — probe, uzorci, alarmi
- [17-E7-analytics.md](17-E7-analytics.md) — izveštaji nad podacima ostalih faza
- [18-E8-omniroute.md](18-E8-omniroute.md) — AI ruter, Ollama + OpenRouter, izbor modela u chatu
- [19-E9-ai-agents.md](19-E9-ai-agents.md) — agenti sa alatima, petlja, odobrenja
- [20-E10-automations.md](20-E10-automations.md) — pravila događaj → akcija
- [21-E11-integrations-ekran.md](21-E11-integrations-ekran.md) — ekran nad E0

## Ispravke u odnosu na prvobitni predlog (NADOGRADNJE/NOVO)

Prvobitni fajlovi bili dobar skelet, ali pisani kao da grade na praznom. Ovde
ispravljeno:

1. **OneRoute/OmniRoute nisu nova gradnja.** `core/ai/model_registry.py` +
   `core_router.py` već rade domen+uloga routing i swap provajdera
   (ollama ↔ openrouter). CODIUM proširuje `core/ai/`, ne gradi paralelni router.
2. **Nema "PathService".** Ne postoji takva klasa. Pravi se `CodiumPaths` po
   uzoru na `FilmiumPaths`, oslonjen na `core_paths`.
3. **Model imena po registru**, ne po starom planu. Stvarno instalirano/konfigurisano:
   `llama3.2:latest`, `qwen2.5:7b`, `nomic-embed-text:latest`. Stari plan je imao
   nepostojeće tagove (`qwen3.6`, `gemma4:e4b`).
4. **Nema generičkog "CORE System Layer" za fajlove** — ne postoji. Explorer se
   gradi kroz novi servis ili reuse FILMIUM scanner koda. To je posao, ne pretpostavka.
5. **Migracije: jedan `migrations.py`** (stil `nabavka`), ne 31 zaseban fajl kao FILMIUM.
6. **DB kreće manje:** Project + Client + Task + Note. Goal, Contact, ProjectLink,
   ProjectAsset se dodaju kad zatrebaju.

## Dugovi (parkirano, ne blokira nijednu fazu)

Zapisano da ne zivi samo u dev-logu. Nijedan nije uslov za sledecu fazu.

| Dug | Sta trazi | Odakle |
|---|---|---|
| Trosak `0.00` za nepoznatu cenu | nova kolona u `codium_ai_usage` (ops migracija) — placen poziv sa nepoznatom cenom danas je nerazluciv od besplatnog | AI-3, zavrsna recenzija |
| „cena nepoznata" nad Claude modelima sa datumom | isto polje kao gore: nula i neznanje se danas razlikuju samo posredno | AI-3, provera uzivo |
| Pamcenje modela po projektu i personi | `ModelRouter` vec prima `pref_lookup`, runtime ga vezuje na `lambda: None`; treba tabela i ekran | AI-3, van dometa |
| Nativni tool-calling | zamena sloja ISPOD petlje agenta; petlja se ne menja | E9, van dometa |
| Identity-linked Anthropic kljucevi | ne-tajno polje `workspace_id` u konektoru, zaglavlje `anthropic-workspace-id` | AI-2, zaobidjeno workspace kljucem |
| Oznaka zastarelog kataloga | `CatalogSnapshot.stale` se racuna a nigde ne prikazuje | AI-3, sitan nalaz |
| Uzorci po node-u (`host_cpu`, `host_memory`) | `system_metrics.py` ih vec meri; uzorak ima kolonu `node_id`, pa dodavanje ne trazi migraciju — samo mesto u pregledu uz node | E6, van dometa reza |
| Obrazac za pravila alarma na ekranu | API ih ume (`POST /monitoring/rules`) i pokriven je testovima; dok obrasca nema, pravila se prave kroz API | E6, van dometa reza |
| Birac projekta na ekranu Analytics | Pet izvestaja podrzava suzenje (`supports_project`) i pokriveno je testovima; dok biraca nema, suzava se kroz API | E7, van dometa reza |
| `commit_sha` na pokretanju pipeline-a se ne popunjava | Bez njega nema izvestaja „vreme od commit-a do isporuke“ koji fazni fajl E7 navodi. Podatak fali u IZVORNOJ fazi (E3), pa se dopunjava tamo — ne u E7 | E7, nadjeno pri izradi |


## Kada se faza završi

Executor upisuje u tabelu gore: status → `zavrseno`, datum → današnji. Kratka
beleška šta je stvarno urađeno ide u `.ai/dev-log/`. Onda sledeća nezavršena faza.
