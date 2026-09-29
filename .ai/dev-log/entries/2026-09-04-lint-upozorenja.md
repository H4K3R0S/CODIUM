---
id: codium-2026-09-04-lint-upozorenja
type: log
domain: codium
title: '2026-09-04 — 139 lint upozorenja: 101 rešeno, 38 procenjeno'
summary: 'Cilj: Popraviti 139 upozorenja koja je pokazao novouvedeni ESLint.'
keywords:
- '2026'
- '139'
- lint
- upozorenja
- '101'
- rešeno
- procenjeno
- dev-log
tags:
- dev-log
- entries
source_path: .ai/dev-log/entries/2026-09-04-lint-upozorenja.md
edges:
- type: preceded_by
  target: codium-2026-09-04-eslint
  weight: 0.8
- type: followed_by
  target: codium-2026-09-04-sesija
  weight: 0.8
---

# 2026-09-04 — 139 lint upozorenja: 101 rešeno, 38 procenjeno

Cilj: Popraviti 139 upozorenja koja je pokazao novouvedeni ESLint.

## Rezultat

**139 → 38.** Nijedna greška, `tsc` čist, 892 vitest prolazi.

| Pravilo | Bilo | Sada |
|---|---|---|
| `react-hooks/set-state-in-effect` | 74 | 38 |
| `react-hooks/refs` | 48 | 0 |
| `react-refresh/only-export-components` | 8 | 0 |
| `react-hooks/exhaustive-deps` | 6 | 0 |
| `react-hooks/purity` | 3 | 0 |

## Šta je popravljeno i zašto to nije bilo samo ćutanje lintera

**Ref-ovi (48).** Analizator prijavljuje svako čitanje polja objekta koji vraća
hook — ne razlikuje ref od obične vrednosti. Stranice zato polja rasporeda
uzimaju razlaganjem, jednom. Uz to su nađena **tri prava** upisa u ref tokom
crtanja (CodeEditorPanel, VremeWidgetShell, VremeProvider); ta tri su prešla u
efekat, jer telo crtanja sme samo da čita.

**Čistoća (3).** `Date.now()` u telu komponente znači da isti render dva puta
daje različit rezultat. Boot sada meri početak lenjom inicijalizacijom stanja, a
stoperica čita vreme u petlji frejmova.

**Hot reload (8).** Fajl koji uz komponentu izvozi i nešto drugo Vite ne ume da
osveži bez gubitka stanja ekrana. Izdvojeni su boot kontekst i hook, položaj
chat okvira, sastavljanje uslova automatizacije, računica statistike biblioteke,
i konteksti sa hook-ovima za FILMIUM workspace i CODIUM UI.

**Zavisnosti efekata (6).** Četiri efekta su zavisila od celog objekta a rade
nad njegovim poljima; Window Manager je držao spisak profila u memoizaciji nad
brojačem verzije (sada obično stanje).

**Dohvat u efektu (36 od 74).** Ovo je bila „lažna uzbuna" — stanje se menja
tek posle `await`, a analizator ne vidi tu granicu. Ipak nije rešeno ćutanjem:
svaki učitavač sada prima `josTraje` i upisuje samo dok ekran stoji, a efekat ga
zove kroz sopstvenu async funkciju koja pri odmontiranju gasi zastavicu. Do sada
je odgovor koji stigne posle odlaska sa strane upisivao u komponentu koje više
nema. Pogođeno 21 mesto (osam CODIUM hook-ova, četiri FILMIUM hook-a, sistemski
widgeti, Finance, Hardware, PersonaPanel, Audit…).

Uz to su tri komponente (CommitHistory, CommitDiff, RunHistory) prestale da
**upisuju** prazno stanje kad ništa nije izabrano — prazan spisak se izvodi pri
crtanju; a ServiceDetail izvodi i indikator učitavanja iz ključa upita.

## Šta ostaje: 38 upozorenja, sva `set-state-in-effect`

Sve preostalo je isti obrazac koji React zove „stanje prepisano iz props-a".
Popravka svakog je stvarna izmena ponašanja, ne preimenovanje.

**Lako i bezbedno (~12):** `FilmiumMediaDetailsPage` (2 — prazne sezone/izvori,
isto kao CommitHistory), `FilmiumFeaturedCarousel`, `FilmiumLibraryManager`,
`FilmiumLibraryNotifications`, `FilmiumSharePage`, `CronStatusIndicator`,
`TerminalSplit`, `VremeWidgetShell`, `CodiumWorkspace`, `AppShell`,
`DomainDock`.

**Srednje (~16):** `DefinitionEditor` (2), `useRunPolling` (2), `FilmiumPlayer`
(2), `FilmiumAcquireModal` (2), `FilmiumLibraryImportPreview` (2),
`RoadmapPage` (2), `IgnitionOverlay`, `ChatDock`, `CodeEditorPanel`,
`FilmiumMediaForm`. Ovde su reset pri otvaranju prozora i faze animacije —
izmena se ne vidi iz testova, nego samo na ekranu.

**Zahtevno (10):** `FilmiumEditorPanel`, fajl od pet hiljada redova. Deset mesta
gde se lokalno stanje puni iz props-a i iz TMDB obogaćivanja. Svako traži
čitanje okoline i proveru uživo po karticama editora.

Preporuka: lake i srednje raditi kao zaseban posao sa proverom na ekranu, a
FILMIUM editor tek posle toga i odvojeno.

## Napomena

Testovi prolaze na svakom koraku, ali oni ovde nisu dokaz — ovog istog dana smo
tri puta imali slučaj da testovi prolaze a ekran laže. Zato za preostale izmene
ide provera uživo, ekran po ekran.


## Dopuna: svih 139 rešeno, lint je čist

Posle procene su odrađene i preostale grupe.

**Lakih dvanaest** — ono što se može izvesti pri crtanju više se ne upisuje iz
efekta: prazne sezone i izvori na FILMIUM detaljima, pozicija van opsega u
carousel-u, animacija izlaska cron indikatora (pamti se *koji* posao izlazi),
ravnomerne težine u terminal split-u, ulazna animacija u AppShell-u, sekvenca
skeniranja u DomainDock-u (stanje kartice pamti se uz korak kome pripada),
neispravan id rute u CodiumWorkspace-u, napredak reda i klizni panel u FILMIUM
biblioteci, spisak u „Podeli", i prevučena pozicija VREME widgeta.

**Srednjih šesnaest** — uređivač definicije (izmene se pamte uz definiciju od
koje su krenule; greške su računica), praćenje pokretanja pipeline-a (sve
prikupljeno nosi oznaku pokretanja, reset efekat nestao), overlay paljenja i
chat okvir (pamti se za šta je animacija odigrana), forma FILMIUM stavke (`key`
po stavci), Roadmap, plejer, uvoz u biblioteku, CodeEditorPanel.

Dva mesta u prozoru „Dodaj za preuzeti" nose izričit `eslint-disable` sa
zapisanim razlogom: fade-out i reset forme zavise od PROMENE `open`, ne od
njegove trenutne vrednosti.

**Deset u `FilmiumEditorPanel`** — ogledala props-a pamte izmene uz spisak od
koga su krenule; prazna stanja (TMDB epizode, ffprobe, `tmdb_id`) nose ključ
upita; rezultat „Dopuni preko TMDB" primenjuje se tokom crtanja, po React-ovom
obrascu za podešavanje stanja pri promeni props-a. Normalizacija žanrova je
računica, ne stanje.

**Ispravka sopstvene greške u brojanju.** U prethodnom koraku sam napisao da je
preostalih trinaest sve u `FilmiumEditorPanel`. Nije bilo tačno: deset ih je
bilo tamo, a tri su nastale od mojih izmena (`position` u VREME widgetu i
`nodes` u Roadmap-u ulaze u zavisnosti efekata, pa im treba `useMemo`). Ispravke
su odrađene zajedno sa ostatkom.

**Stanje: `npx eslint .` → 0 problema** (bilo 139), 892 vitest, `tsc` čist.
Provereno uživo: FILMIUM editor otvara sve kartice, epizode se prebacuju sa
tačnim naslovom, brojem, datumom, TMDB ocenom i sličicom; žanrovi pokazuju četiri
aktivna; Ocene TMDB 8.2 — bez ijedne greške u konzoli.
