---
id: codium-b9e8f971-12-e2-repositories-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E2 — Repositories
summary: '**Blok:** razvojna loza · **Zavisi od:** E1 · **Migracija:** codium v10'
keywords:
- repositories
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/12-E2-repositories.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E2 — Repositories

**Blok:** razvojna loza · **Zavisi od:** E1 · **Migracija:** codium v10
**Sidebar:** `Repositories`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Odluke donete pre izrade (2026-08-29)

Fazni fajl je skelet; ovo su odluke iz razgovora sa korisnikom i one nadjacavaju
skelet gde se razilaze.

1. **Repozitorijum ulazi rucno, uz ponudu iz projekata.** Covek registruje
   putanju, a strana uz to nudi spisak projekata cija je `local_path` git repo pa
   nisu registrovani — jedan klik ih dodaje. Registar ostaje covekova odluka, ali
   se ne kuca putanja koju sistem vec zna. Automatski upis je odbijen: repo koji
   ne zelis da vidis moras da brises, a brisanje bi ponistilo sledece skeniranje.
2. **Citanje plus `fetch`, nista sto menja radno stablo.** `status`, grane,
   istorija, razlika, sadrzaj fajla na ref-u, i `fetch` kroz kapiju
   (`repo.fetch`). `checkout` i `pull` su odbijeni: prvi preko nesacuvanih izmena
   gubi rad, drugi ume da napravi konflikt koji ovaj ekran ne ume da resi. Sve
   ostalo ostaje terminalu dok se ne pokaze da treba.
3. **Domet je backend + GUI + alati agenta.** Kao E1 i E9: sloj, API, strana
   `/codium/repositories`, i dva nova alata agenta (`git_log`, `git_diff`) koja su
   u E9 ostala neispisana jer nije bilo sta da se omota. Sidebar stavka
   „Repositories" prestaje da bude „uskoro". Staro pravilo „prvo backend celog
   bloka, pa GUI" se ovde ne primenjuje — blok su E2–E4, pa bi GUI cekao jos dve
   faze; isto pravilo je vec napusteno za AI blok, E1 i E9.

## Cilj

Git postaje prvorazredan podatak u CODIUM-u, a ne nešto što se radi u terminalu
sa strane. Projekat dobija svoj repozitorijum, a repozitorijum daje granu,
stanje radnog stabla, istoriju i razliku — sve što E3 i E7 kasnije koriste.

## Odnos prema postojećem modelu

`Project` već ima `local_path` i `repository_url`. Repozitorijum se **ne**
poistovećuje sa projektom: jedan projekat može imati više repozitorijuma
(frontend i backend), a jedan repozitorijum može stajati bez projekta. Zato
zaseban entitet sa opcionom vezom `project_id`.

## Backend

`core/domains/codium/repositories/`

### Provider

`providers/base.py`

```
GitProvider
    detect(path) -> RepoInfo | None       # da li je putanja git repo
    status(repo) -> RepoStatus            # grana, dirty, ahead, behind
    branches(repo) -> list[BranchInfo]
    log(repo, branch, limit, offset) -> list[CommitInfo]
    diff(repo, ref_a, ref_b, path) -> str
    file_at(repo, ref, path) -> str
    fetch(repo) -> None                   # prolazi kroz ScopeGate
```

`providers/local_git.py` — prvi i jedini provider u ovoj fazi. Poziva `git` kao
podproces, uvek sa `cwd` postavljenim na koren repozitorijuma, uvek sa
`--no-pager` i mašinski čitljivim izlazom (`--porcelain=v2`, `--format=%H%x1f...`).

Nikada se ne sastavlja komanda spajanjem stringova sa korisničkim unosom —
argumenti idu kao lista.

`providers/github.py` **nije** deo ove faze. Interfejs postoji da bi kasnije
mogao da uđe bez prepravke servisa i ekrana.

### Modeli

`Repository` (id, project_id, name, local_path, remote_url, default_branch,
provider, last_synced_at), `RepoStatus`, `BranchInfo`, `CommitInfo`, `DiffChunk`.

`CommitInfo`: sha, kratak sha, autor, datum, naslov, telo, broj izmenjenih fajlova,
dodato i obrisano linija.

### Servis

`RepositoryService`:

- `register(path)` — proverava da li je putanja git repo (`detect`), izvlači
  `remote_url` i podrazumevanu granu, upisuje red. Ako nije repo, uredna greška.
- `list(project_id=None)` sa uživo dohvaćenim `status` po repozitorijumu.
- `history(repo_id, branch, limit, offset)`.
- `diff(repo_id, ref_a, ref_b, path=None)`.
- `sync(repo_id)` — `fetch`, pa osvežen `ahead`/`behind`. Prolazi kroz ScopeGate
  (`repo.fetch`) i piše u audit.

Čitanje istorije je jeftino ali ne besplatno — `status` se kešira u memoriji
servisa 10 sekundi po repozitorijumu, da lista ne pokreće `git` na svaki render.

## Šema (migracija — codium v10)

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

Commit-i se **ne** kopiraju u bazu. Git je već baza za njih; duplirati ih znači
držati dva izvora istine. E7 Analytics čita agregate kroz provider i kešira samo
zbirove.

## API

`apps/api/routers/codium_repositories.py`, prefiks `/api/v1/codium/repositories`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/` | lista sa stanjem (`?project_id=`) |
| GET | `/suggestions` | projekti čija je `local_path` git repo a još nisu u registru |
| POST | `/` | registruje postojeću putanju kao repozitorijum |
| DELETE | `/{id}` | uklanja iz registra (ne dira disk) |
| GET | `/{id}/status` | grana, dirty, ahead, behind |
| GET | `/{id}/branches` | grane |
| GET | `/{id}/commits` | istorija (`?branch=&limit=&offset=`) |
| GET | `/{id}/diff` | razlika (`?a=&b=&path=`) |
| GET | `/{id}/file` | sadržaj fajla na ref-u (`?ref=&path=`) |
| POST | `/{id}/sync` | `fetch` + osvežavanje |

`DELETE` briše samo red u bazi. Brisanje sa diska nije u dometu ove sekcije.

**Dve rute koje ovaj fazni fajl nije predvideo, dodate pri izradi:**

- `GET /suggestions` — nosi odluku 1 iz „Odluke donete pre izrade": ponuda iz
  projekata cija je putanja vec git repo, da se ne kuca putanja koju sistem vec
  zna. Bez nje bi tacka 1 ostala samo tekst u ovom fajlu.
- `GET /{id}/file` — GUI prikaz razlike koristi Monaco `DiffEditor`, kome trebaju
  oba sadrzaja fajla (na `ref_a` i `ref_b`), ne samo unified diff tekst koji vraca
  `/{id}/diff`.

## GUI (radi se posle backend-a bloka)

`pages/CodiumRepositories.tsx`:

- Lista repozitorijuma sa značkama: grana, broj neispraćenih izmena, ahead/behind.
- Detalj: istorija commit-a (virtuelizovana lista), klik na commit otvara razliku.
- Prikaz razlike koristi Monaco `DiffEditor` — Monaco je već instaliran i ožičen
  u F6, pa nema nove zavisnosti.
- Dugme „Otvori u Explorer-u" vodi u postojeći F5 Explorer na putanju repozitorijuma.

## Testovi

- `test_local_git_provider` — nad privremenim repozitorijumom napravljenim u
  `tmp_path` (`git init`, dva commit-a, jedna izmena): `detect`, `status` prijavljuje
  dirty, `log` vraća oba commit-a u tačnom redosledu, `diff` nije prazan.
  Ako `git` nije na putanji, test se preskače uz jasnu poruku.
- `test_codium_repositories` — registrovanje ne-git putanje vraća urednu grešku;
  `sync` bez dozvole ne izvršava `fetch` i ostavlja trag u audit-u; keš stanja
  ne poziva provider dvaput unutar prozora.
- `test_api_codium_repositories` — stranicanje istorije, `DELETE` ne dira disk.

## Definicija završetka

Lokalni repozitorijum se registruje, prikazuje stanje i istoriju, i vraća razliku
između dva ref-a; `github` provider nije napisan ali interfejs stoji; testovi
domena prolaze.
