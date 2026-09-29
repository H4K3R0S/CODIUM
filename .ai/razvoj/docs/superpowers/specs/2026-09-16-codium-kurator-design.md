# CODIUM Kurator — replikacija (C)

Datum: 2026-09-16
Status: dizajn odobren (usmeno), spec na reviziji
Podprojekat: **C** (K → **C** → Ka → D). Zavisi od K (kanonski framework, URAĐEN).

## 1. Cilj

Preneti dokazani Kurator obrazac na CODIUM domen: agent koji preko atoma
prepoznaje komande i izvršava dev-akcije (repozitorijumi + pipeline-i) uz potvrdu
pre upisa. Za razliku od FILMIUM-a (jedna persona), CODIUM je **multi-persona** —
12 razvojnih persona (Opšti, Arhitekta, Graditelj, Recenzent, Dizajner, Menadžer,
Debager, Pisac, Bezbednjak, DevOps, Tester, Data Engineer) iz
`NADOGRADNJE/KALIMA/Codium Persone.md`.

## 2. Kontekst i odluke

- **K je urađen:** kanonski domen-agnostični framework u CORE `core/cell/curator/`
  (agent na protokolima, `entity_key`, `Executors` run/preview/apply, `Resolver`)
  + generički cell backend/GUI. Deljenje: **kanon u CORE + ručna kopija u ćeliju**.
- **CODIUM ćelija** (`C:\Users\Game Centar\Desktop\CODIUM`) je samostalan repo sa
  bogatim servisima: `RepositoryService`, `PipelineService`, `DeployService`,
  infrastructure, monitoring, automations, agents, assistant (+ `personas.py`).
- **Odluke:**
  1. **12 persona = atom identiteti.** `personas/<id>/persona.md` za svih 12
     (sistemski promptovi iz Codium Persone.md). Aktivna persona bira se u chat-u.
  2. **Komande = deljene.** Jedan zajednički `commands/katalog.md` + `tools/`
     (repo/pipeline akcije) dostupan za BILO KOJU aktivnu personu. Persona menja
     ton/rezon odgovora; komande (dev akcije) su iste. Per-persona specijalizacija
     komandi = kasnija iteracija.
  3. **Komandni set (option 2):** `list_repos`, `list_pipelines`, `repo_status`,
     `sync_repo` (upis/potvrda), `run_pipeline` (upis/potvrda), `open` (navigate).
  4. **Malo proširenje K agenta:** `CuratorActionError` u kernel `protocols.py`;
     agent ga hvata u `handle` (run i preview) → graciozan „answer" umesto 500/
     proposal. Rešava „nije nađeno" za multi-entitet (repo vs pipeline).

## 3. Obim i non-goals

U obimu (C):
- **K amandman (CORE repo):** `CuratorActionError` + hvatanje u agentu.
- **Kopija K kanona** u CODIUM ćeliju (curator paket, ai_config, generički
  cell.py endpointi/scheme, GUI paneli).
- **CODIUM domenski deo:** `INTENTS` (6 komandi), `CodiumExecutors`, `CodiumResolver`,
  seed atomi (12 persona + deljene komande/tools), runtime, `codium_curator` router,
  GUI (Kurator chat sa persona pickerom + Settings paneli).
- Testovi (CORE za K amandman; CODIUM ćelija za domenski deo).

Non-goals (NE u C):
- Per-persona komande (svaka persona svoje tools) — kasnije.
- `deploy` (target+run, 2 id-ja, visok rizik) — kasnije.
- Pipeline operacije van `list`/`run` (create/update/cancel/logs) — kasnije.
- Usklađivanje FILMIUM-a sa kanonom — i dalje van obima.

## 4. K amandman (CORE `core/cell/curator/`)

- `protocols.py`: dodati `class CuratorActionError(Exception)` — domenski izvršilac
  je diže kad namera ne može da se izvrši gracioznо (npr. „nema repoa tog imena").
- `agent.py` `handle`: obmotati pozive `executors.run(...)` i `executors.preview(...)`
  u `try/except CuratorActionError as e` → vrati `AgentResult(kind="answer",
  intent="unknown", reply=str(e), log_id=...)` (logovano). `confirm` isto obmotati
  oko `executors.apply` (vrati `{"error": str(e)}` ili diže — vidi §7). Ništa se ne
  izvrši na grešci; upisni token se NE izdaje ako `preview` digne.
- Test u CORE: executor koji diže `CuratorActionError` → `handle` vrati graciozan
  answer (run i preview putanja), bez proposal-a/tokena.

Napomena: postojeći K agent test i FILMIUM se ne kvare — `CuratorActionError` je
nov, opcion put; izvršioci koji ga ne dižu rade kao pre.

## 5. CODIUM domenski deo (u CODIUM ćeliji)

Lokacija: `C:\Users\Game Centar\Desktop\CODIUM\core\domains\codium\curator\`.

- **`intents.py`** — `CODIUM_INTENTS: dict[str, IntentSpec]`:
  - `list_repos` (read), `list_pipelines` (read) — `needs_entity=False`.
  - `repo_status` (read), `sync_repo` (write), `open` (navigate) — entitet=repo.
  - `run_pipeline` (write) — entitet=pipeline.
  - Napomena: dva tipa entiteta se ne razrešavaju kroz K `entity_key` (jedan tip),
    nego IZNUTRA u executoru: model daje `name` (ili `repo`/`pipeline`), executor
    razreši ime→id svog tipa; ako nema poklapanja → `CuratorActionError`.
    Zato svi CODIUM intenti imaju `needs_entity=False` (K resolver se ne koristi;
    razrešavanje + graciozno „nije nađeno" je u executoru + §4 amandman).
- **`executors.py`** — `CodiumExecutors(repositories, pipelines)` implementira
  `Executors` protokol:
  - `run(intent, params)`:
    - `list_repos` → `{"kind":"answer","sources":[imena repoa], ...}` (RepositoryService.list()).
    - `list_pipelines` → `{"kind":"answer","sources":[imena pipeline-a]}` (PipelineService.list()).
    - `repo_status` → razreši `params["name"]`→repo_id (ili CuratorActionError);
      `{"kind":"answer","reply": kratak status}` (RepositoryService.status).
    - `open` → razreši repo → `{"kind":"navigate","route":"/codium/repos/<id>"}`.
  - `preview(intent, params)`:
    - `sync_repo` → razreši repo; `{"repo": ime, "akcija":"sync"}` (bez upisa).
    - `run_pipeline` → razreši pipeline; `{"pipeline": ime, "akcija":"run"}`.
  - `apply(intent, params)`:
    - `sync_repo` → `RepositoryService.sync(repo_id, actor="kurator")`.
    - `run_pipeline` → `PipelineService.run(pipeline_id, actor="kurator")`.
  - Razrešavanje imena: mala pomoćna nad `.list()` (poklapanje po imenu/putanji);
    višesmisleno/nenađeno → `CuratorActionError`.
- **`seed atomi`** (`.ai/atomi/personas/`):
  - `personas/<id>/persona.md` za svih 12 (id-jevi: `opsti, arhitekta, graditelj,
    recenzent, dizajner, menadzer, debager, pisac, bezbednjak, devops, tester,
    data-engineer`), tekst iz Codium Persone.md.
  - **Deljene komande/tools:** pošto su komande iste za sve persone, svaka persona
    dobija ISTI `commands/katalog.md` + `tools/` (repo.md, pipeline.md). Da se ne
    dupliraju 12×: generator (K `scaffold`) upiše deljeni sadržaj u svaku, ILI
    (jednostavnije) agent učita deljeni katalog iz jednog mesta. **Odluka:** deljeni
    katalog/tools stoje u `personas/_shared/` a `AtomLoader` za personu čita
    `persona.md` iz `personas/<id>/` i komande iz `personas/_shared/`. (Blaga
    dopuna K `AtomLoader`-a: opcioni `shared_root` za commands/tools; ako nije dat,
    ponaša se kao dosad — vidi §6.)

## 6. Multi-persona wiring

- K `AtomLoader(root)` čita jednu personu. Za CODIUM dodaje se opcioni
  `AtomLoader(root, shared_root=None)`: `persona()` iz `root`, a `tool()`/
  `commands()`/`command_catalog()` iz `shared_root` ako je dat (inače iz `root`,
  kao dosad). Ovo je blaga, unazad-kompatibilna dopuna K `AtomLoader`-a (deo K
  amandmana, §4) — FILMIUM (bez `shared_root`) radi nepromenjeno.
- CODIUM runtime: po zahtevu sa `persona_id`, sklopi `AtomLoader(
  personas/<persona_id>, shared_root=personas/_shared)` → `CuratorAgent(...)`.
  Neispravan `persona_id` pada na `opsti`.

## 7. API (CODIUM ćelija)

- Nov router `apps/api/routers/codium_curator.py`:
  - `POST /api/v1/codium/curator/command` (telo: `{message, persona_id?}`) →
    CuratorCommandResponse (kao FILMIUM). Runtime bira AtomLoader po `persona_id`.
  - `POST /api/v1/codium/curator/confirm` (`{token}`) → izvrši upis; `KeyError`→400;
    `CuratorActionError`→422 (graciozna poruka).
  - `POST /api/v1/codium/curator/refute` (`{log_id?}`).
- Generički `/cell/ai-config` i `/cell/atoms` (iz kopiranog kanona) — atomi koren
  persona-neutralan; za CODIUM `persona_id` iz zahteva (ili podrazumevano `opsti`).
- Runtime: `apps/api/codium_curator_runtime.py` sklapa `CodiumExecutors` +
  agent-fabriku po personi (lokalna Ollama iz cell.json, kao FILMIUM).

## 8. GUI (CODIUM ćelija)

- **Kurator chat** sa **persona pickerom** (12 persona) — bira aktivnu personu;
  poruke idu na `/codium/curator/command` sa `persona_id`. Prikaz: answer+sources,
  proposal (Potvrdi/Otkaži), navigate (otvori rutu). Isti obrazac kao FILMIUM
  `FilmiumKuratorChat`, plus dropdown persona.
- **Settings:** ugraditi kanonske `ModelPanel`/`AtomiPanel` (`CuratorSettingsPanels`,
  `brand="CODIUM"`) u CODIUM `CellSettingsPage`. Atomi editor prikazuje atome
  aktivne/izabrane persone.

## 9. Testovi

- **CORE (K amandman):** `CuratorActionError` hvatanje u agentu (run/preview →
  graciozan answer, bez tokena); `AtomLoader` `shared_root` (persona iz root,
  commands iz shared).
- **CODIUM ćelija:** `CodiumExecutors` (list_repos/list_pipelines vraćaju imena;
  repo_status razreši ime→id ili CuratorActionError; sync/run apply zovu servise;
  nenađeno ime → CuratorActionError); intents registar; runtime `get_agent(persona_id)`;
  `codium_curator` API (command/confirm/refute); seed atomi (12 persona + deljeni
  katalog učitljivi). CODIUM test runner: `./.venv/Scripts/python.exe -m pytest`.

## 10. Rizici

- Multi-entitet razrešen IZNUTRA u executoru (ne kroz K `entity_key`) — jasno
  dokumentovano; K `entity_key` ostaje za jedno-entitetske domene (FILMIUM).
- `CuratorActionError` menja kernel (mali, unazad-kompatibilan dodatak) — mora se
  ubaciti u CORE kanon I u kopiju u CODIUM ćeliji (ista verzija).
- Deljeni katalog preko `shared_root` je dopuna K `AtomLoader`-a — mora u kanon i
  kopiju; FILMIUM (bez shared_root) nepromenjen.
- `sync_repo`/`run_pipeline` su realni upisi (git pull / pokretanje pipeline-a) —
  potvrda pre izvršenja obavezna; `actor="kurator"` u audit tragu.
