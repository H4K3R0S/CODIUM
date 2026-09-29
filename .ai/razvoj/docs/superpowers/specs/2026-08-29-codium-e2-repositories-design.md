---
id: codium-32ee86c0-2026-08-29-codium-e2-repositories-design-md
type: spec
domain: codium
namespace: global
visibility: global
tier: domain
title: E2 — Repositories (git kao prvorazredan podatak CODIUM-a)
summary: '**Datum:** 2026-08-29'
keywords:
- repositories
- git
- kao
- prvorazredan
- podatak
- codium
- docs
- superpowers
- specs
tags:
- superpowers
- specs
source_path: docs/superpowers/specs/2026-08-29-codium-e2-repositories-design.md
---

# E2 — Repositories (git kao prvorazredan podatak CODIUM-a)

**Datum:** 2026-08-29
**Faza:** E2 (fazni fajl `.ai/izgradnja/codium/12-E2-repositories.md`)
**Zavisi od:** E1 (ScopeGate, dnevnik, red odobrenja), F5 Explorer, F6 Monaco

---

## 1. Zašto

Git je danas u CODIUM-u nevidljiv. Projekat nosi `local_path` i `repository_url`
kao dva teksta, a sve ostalo — grana, stanje radnog stabla, istorija, razlika —
radi se u terminalu sa strane. Zbog toga E3 Pipelines nema šta da pokrene nad
commit-om, E4 Deployments nema šta da označi kao isporučenu verziju, a agent iz
E9 ima šest alata umesto osam: `git_log` i `git_diff` su tamo ostali neispisani
jer nije bilo servisa koji bi se omotao.

Ova faza uvodi repozitorijum kao entitet sa svojim redom u bazi, svojim servisom,
svojim ekranom i svoja dva alata agenta.

## 2. Odluke donete pre pisanja

Prve tri su iz razgovora 2026-08-29 i već stoje u faznom fajlu; ostale četiri su
iz razgovora koji je prethodio ovom dokumentu.

1. **Repozitorijum ulazi ručno, uz ponudu iz projekata.** Čovek registruje putanju,
   a strana uz to nudi spisak projekata čija je `local_path` git repo pa nisu
   registrovani — jedan klik ih dodaje. Automatski upis je odbijen: repo koji ne
   želiš da vidiš moraš da brišeš, a brisanje bi poništilo sledeće skeniranje.
2. **Čitanje plus `fetch`, ništa što menja radno stablo.** `checkout` i `pull` su
   odbijeni: prvi preko nesačuvanih izmena gubi rad, drugi ume da napravi konflikt
   koji ovaj ekran ne ume da reši.
3. **Domet je backend plus GUI plus alati agenta.** Pravilo „prvo backend celog
   bloka, pa GUI" se ovde ne primenjuje — blok su E2–E4, pa bi GUI čekao još dve
   faze; isto pravilo je već napušteno za AI blok, E1 i E9.
4. **GUI stoji na dva mesta:** zasebna strana `/codium/repositories` i novi „Git"
   panel u docking rasporedu workspace-a.
5. **Alati agenta rade nad prvim repozitorijumom projekta, bez argumenta.** Model
   ne mora da zna za id-jeve, a jedan repo po projektu je današnja stvarnost.
6. **`git` ulazi u `CORE_DEPENDENCIES`** po sva četiri koraka iz
   `docs/DEPENDENCIES.md`.
7. **`local_git` zove `git` kao podproces po pozivu**, sa argumentima kao listom.

## 3. Odnos prema postojećem modelu

Repozitorijum se **ne** poistovećuje sa projektom: jedan projekat može imati
frontend i backend repozitorijum, a jedan repozitorijum može stajati bez projekta.
Zato zaseban entitet sa opcionom vezom `project_id` (`ON DELETE SET NULL`).

Commit-i se **ne** kopiraju u bazu. Git im je već baza; duplirati ih znači držati
dva izvora istine. E7 Analytics kasnije čita agregate kroz provider i kešira samo
zbirove.

## 4. Backend

```
core/domains/codium/repositories/
    __init__.py
    models.py                 Repository, RepoInfo, RepoStatus, BranchInfo, CommitInfo
    providers/base.py         Protocol GitProvider
    providers/local_git.py    omotač oko podprocesa `git`
    repository.py             SQL nad codium.db, bez poslovne logike
    service.py                RepositoryService — jedini zove dnevnik i kapiju
```

### Provider

```
GitProvider
    detect(path)                     -> RepoInfo | None
    status(root)                     -> RepoStatus        grana, dirty, ahead, behind
    branches(root)                   -> list[BranchInfo]
    log(root, branch, limit, offset) -> list[CommitInfo]
    diff(root, ref_a, ref_b, path)   -> str
    file_at(root, ref, path)         -> str
    fetch(root)                      -> None
```

`providers/github.py` **nije** deo ove faze. Interfejs postoji da bi kasnije mogao
da uđe bez prepravke servisa i ekrana.

`local_git.py` drži jednu privatnu funkciju `_git(root, *args)` koju svi pozivi
dele: `["git", "--no-pager", *args]`, `cwd=root`, `capture_output`, `text=True`,
`encoding="utf-8"`, `timeout` 10 s za čitanje i 60 s za `fetch`. Nenulti izlaz
diže `GitError` sa `stderr`-om; `FileNotFoundError` diže `GitUnavailable` sa
porukom da git nije instaliran — isti obrazac kao `OllamaUnavailable`.

Komanda se nikada ne sastavlja spajanjem stringova sa korisničkim unosom;
argumenti idu kao lista.

Izlaz je uvek mašinski čitljiv, nikada ljudski: `status --porcelain=v2 --branch`,
`for-each-ref --format=...`, `log --format=...` sa `%x1f` kao razdvajačem polja i
`%x1e` kao razdvajačem zapisa, plus `--shortstat`. Commit poruka sme da sadrži
sve osim ta dva bajta.

### Servis

- `register(path, project_id=None, name=None)` — `detect`, izvlačenje `remote_url`
  i podrazumevane grane, upis reda. Putanja koja nije repo daje `NotAGitRepo`;
  već upisana putanja daje urednu grešku (`UNIQUE` indeks).
- `suggestions()` — projekti čija je `local_path` git repo a nisu registrovani.
  Ovo je odluka 1.
- `list(project_id=None)` — redovi plus uživo dohvaćen `status`. Repozitorijum
  koji je nestao sa diska nije greška liste: `status` nosi `missing=True`.
- `history(repo_id, branch, limit, offset)`, `diff(repo_id, a, b, path=None)`,
  `file_at(repo_id, ref, path)`.
- `sync(repo_id, actor)` — `gate.check(actor, "repo.fetch", f"repo:{id}")`, pa
  `fetch`, pa `audit.record`. Odbijeno znači bez `fetch`-a, ali sa tragom.
- `remove(repo_id, actor)` — briše red i piše u dnevnik. Disk se ne dira.

Čitanje istorije je jeftino ali ne besplatno, pa se `status` kešira u memoriji
servisa 10 sekundi po repozitorijumu (`dict[int, tuple[float, RepoStatus]]` uz
`time.monotonic`), da lista ne pokreće `git` na svaki render.

### Migracija `CODIUM_MIGRATION_V10`

```sql
CREATE TABLE codium_repositories (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     INTEGER REFERENCES codium_projects (id) ON DELETE SET NULL,
    name           TEXT NOT NULL,
    local_path     TEXT NOT NULL,
    remote_url     TEXT,
    default_branch TEXT NOT NULL DEFAULT 'main',
    provider       TEXT NOT NULL DEFAULT 'local_git',
    last_synced_at TEXT,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_codium_repos_path ON codium_repositories (local_path);
```

Uz tabelu, ista migracija upisuje dva pravila kapije u `codium_scope_rules`:

- `agent:*` / `repo.fetch` / `*` → `needs_approval`, uz napomenu da fetch ide na
  mrežu pa ga čovek odobrava.
- `agent:*` / `repo.register` / `*` → `deny`, uz napomenu da je registar čovekova
  odluka.

Razlog: `ScopeGate` nepoznat glagol odbija, a `fetch` i `register` su nepoznati.
`_DEFAULTS` u `core/security/scope_gate.py` ostaje netaknut — `fetch` je git
pojam, ne CORE glagol, pa mu nije mesto u podrazumevanim vrednostima celog
sistema. Čovek i dalje prolazi bez pitanja, jer `HUMAN` zaobilazi kapiju.

## 5. API

`apps/api/schemas/codium_repositories.py` — Pydantic izlaz koji preslikava
dataclass-e (`RepositoryResponse`, `RepositoryStatusResponse`, `BranchResponse`,
`CommitResponse`, `DiffResponse`, `SuggestionResponse`) plus
`RepositoryCreateRequest` (`local_path`, opcioni `project_id`, opcioni `name`).

`apps/api/codium_repositories_runtime.py` — po uzoru na `codium_agents_runtime.py`:
lenji singletoni `get_repositories()` i `get_service()` (servis sklopljen sa
`LocalGitProvider`, kapijom i dnevnikom iz `codium_security_runtime`), plus
`reset()` za testove.

`apps/api/routers/codium_repositories.py`, prefiks `/api/v1/codium/repositories`,
registrovan u `apps/api/main.py`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/` | lista sa stanjem (`?project_id=`) |
| GET | `/suggestions` | git repozitorijumi projekata koji nisu upisani |
| POST | `/` | upisuje postojeću putanju kao repozitorijum |
| DELETE | `/{id}` | uklanja iz registra, disk netaknut |
| GET | `/{id}/status` | grana, dirty, ahead, behind |
| GET | `/{id}/branches` | grane |
| GET | `/{id}/commits` | istorija (`?branch=&limit=&offset=`) |
| GET | `/{id}/diff` | razlika (`?a=&b=&path=`) |
| GET | `/{id}/file` | sadržaj fajla na ref-u (`?ref=&path=`) |
| POST | `/{id}/sync` | `fetch` kroz kapiju |

`/suggestions` i `/{id}/file` su nove u odnosu na fazni fajl. Prvu traži odluka 1,
drugu Monaco `DiffEditor`, kome trebaju dva puna teksta a ne unified patch.

**Preslikavanje grešaka:** `RepositoryNotFound` → 404, `NotAGitRepo` i sudar
jedinstvenog indeksa → 400, `GitUnavailable` → 503, `GitError` → 502 sa prvom
linijom `stderr`-a. Ceo `stderr` se ne prosleđuje — ume da nosi apsolutne putanje.

**Akter.** Rute nose `actor="human"`, pa `sync` iz GUI-ja prolazi kapiju bez
pitanja. Agent ide istim servisom sa `actor=f"agent:{slug}"` i pada na pravilo iz
migracije v10.

## 6. Zavisnost `git`

Sva četiri koraka iz `docs/DEPENDENCIES.md`:

1. `Dependency(key="git", label="Git", kind=DependencyKind.SYSTEM,
   severity=DependencySeverity.IMPORTANT, probe="git",
   purpose="Čitanje istorije i razlike u CODIUM Repositories.",
   installer=DependencyInstaller.WINGET)` u `CORE_DEPENDENCIES`.
2. `scripts/install/git.ps1` (`winget install --id Git.Git`), pa `"git": "git.ps1"`
   u `INSTALL_SCRIPTS`.
3. Red u tabeli „Katalog alata" u `docs/DEPENDENCIES.md`.
4. Ništa u `requirements.txt` — git nije Python paket.

`severity=IMPORTANT`, ne `CRITICAL`: bez git-a ceo CORE i dalje radi, samo ova
sekcija javlja 503.

## 7. GUI

Deljeno jezgro, da strana i panel ne budu dve implementacije iste stvari:

```
apps/gui/src/features/codium/repositories/
    useRepositories.ts     dohvatanje liste i statusa, osvežavanje
    RepoList.tsx           lista sa značkama (grana, dirty, ahead/behind)
    CommitHistory.tsx      virtuelizovana istorija, klik bira commit
    CommitDiff.tsx         Monaco DiffEditor nad dva `/{id}/file` poziva
    RegisterRepo.tsx       ručan upis plus ponuda iz `/suggestions`
    repoBadges.ts          čist modul: stanje u tekst značke
```

**Strana** `pages/CodiumRepositories.tsx` na ruti `/codium/repositories`: dve
kolone — `RepoList` levo, detalj izabranog desno (`CommitHistory` iznad,
`CommitDiff` ispod), `RegisterRepo` iznad liste. Stil
`styles/codium-repositories.css`.

**Workspace panel** — nov dockview panel `git` u `CodiumDockLayout.tsx`: unos u
`PANEL_COMPONENTS`, unos u `PANEL_META` (naslov „Git", ikonica `GitBranch`), i
ništa u `buildDefaultLayout` — panel se dodaje ručno iz trake panela, kao Preview
i Tasks danas. Sadržaj je uži rez: repozitorijum aktivnog projekta, grana, spisak
izmena, istorija, razlika u istom panelu.

**Fiksni raspored ne dobija Git.** Njegovih šest regiona je zaključano i nema
slobodnu zonu; AI panel je već rešen istim izuzetkom. Dodavati sedmi region zbog
ove faze znači prepravljati raspored koji radi.

**Sidebar** — stavka `repositories` prelazi iz `kind: "soon", phase: "F13"` u
`kind: "route", path: "/codium/repositories"`.

**Overview** — pločica „Repositories" danas broji projekte sa `repository_url`,
što je pogađanje. Prelazi na stvaran broj iz API-ja, uz hint o broju
repozitorijuma sa neispraćenim izmenama. To traži pravilo iz
`09-ENTERPRISE-OVERVIEW.md`: faza koja pusti sekciju u rad oživljava njenu pločicu.

**Dopune** `services/codiumApi.ts` (deset poziva) i `types/codium.ts`
(`Repository`, `RepoStatus`, `BranchInfo`, `CommitInfo`, `RepoSuggestion`).

Monaco je već instaliran i ožičen u F6 — nema nove GUI zavisnosti.

## 8. Alati agenta

Dva nova `ToolSpec`-a u `core/domains/codium/agents/tools/builtin.py`:

| Alat | Argumenti | Akcija za kapiju |
|---|---|---|
| `git_log` | `limit` | `repo.read` |
| `git_diff` | `a`, `b`, `path` | `repo.read` |

Oba su tanki omotači nad `RepositoryService` — isti servis koji hrani rute, bez
druge staze do git-a. Glagol `read` pada na `ALLOW`, pa agent čita bez odobrenja;
`fetch` mu se ne nudi kao alat uopšte.

`build_tools(explorer, service, project_id)` dobija četvrti parametar
`repos: RepositoryService | None`. Kad je `None` ili projekat nema registrovan
repozitorijum, alat vraća rečenicu („Projekat nema registrovan repozitorijum."),
ne grešku — model to pročita i nastavi. Kad ih projekat ima više, alat uzima
najstariji upis i to kaže u odgovoru.

`tools_for()` i `tool_catalog()` u `codium_agents_runtime.py` sklapaju servis, pa
ruta `/tools` opisuje osam alata umesto šest.

## 9. Testovi

- `test_local_git_provider` — pravi repozitorijum u `tmp_path` (`git init`, dva
  commit-a, jedna nesačuvana izmena): `detect` prepoznaje, `status` javlja dirty i
  granu, `log` vraća oba commit-a u tačnom redosledu, `diff` nije prazan, `file_at`
  vraća stari sadržaj. Bez git-a na putanji test se preskače uz jasnu poruku. Ovo
  je jedini test koji pokreće pravi proces — provider je omotač oko procesa, pa
  lažni provider ovde ne dokazuje ništa.
- `test_codium_repositories` — servis nad lažnim providerom: putanja koja nije
  repo daje urednu grešku, duplikat putanje takođe, `sync` bez dozvole ne poziva
  `fetch` i ostavlja trag u dnevniku, keš stanja ne poziva provider dvaput unutar
  prozora, `suggestions` izostavlja već upisane.
- `test_api_codium_repositories` — straničenje istorije, `DELETE` ne dira disk,
  `GitUnavailable` daje 503.
- `test_codium_agent_tools` — dopuna: `git_log` bez registrovanog repozitorijuma
  vraća rečenicu, ne puca.
- `repoBadges.test.ts` (vitest) — stanje u tekst značke.
- `CodiumRepositories.test.tsx` (vitest) — strana crta listu i prazno stanje.

## 10. Definicija završetka

Repozitorijum se upisuje ručno i iz ponude, lista pokazuje stanje, istorija i
razlika rade i na strani i u workspace panelu, `sync` prolazi kroz kapiju sa
tragom u dnevniku, agent ima `git_log` i `git_diff`, `github` provider nije
napisan ali interfejs stoji, testovi domena prolaze u celini i `tsc` je čist.

## 11. Van dometa svesno

- `checkout`, `pull`, `commit`, `push`, `stage` — sve što menja radno stablo.
- `providers/github.py`.
- Skeniranje tajni u commit-ima i provera ranjivih zavisnosti — to pripada KALIMA
  domenu, po odeljku 2a u `09-ENTERPRISE-OVERVIEW.md`.
- Kopiranje commit-a u bazu.
- Git panel u fiksnom rasporedu workspace-a.
