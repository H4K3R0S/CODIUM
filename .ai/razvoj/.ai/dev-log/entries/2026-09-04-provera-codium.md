---
id: core-99e076a4-2026-09-04-provera-codium-md
type: log
domain: core
namespace: global
visibility: global
tier: core
title: 2026-09-04 — Prolaz kroz ceo CODIUM i tri popravke izgleda
summary: 'Cilj: Proći kroz svih četrnaest CODIUM ekrana, naći greške i popraviti ih
  odmah.'
keywords:
- '2026'
- prolaz
- kroz
- ceo
- codium
- tri
- popravke
- izgleda
- dev-log
tags:
- dev-log
- entries
source_path: .ai/dev-log/entries/2026-09-04-provera-codium.md
edges:
- type: references
  target: core-9f4b55dd-2026-09-03-e10-md
  weight: 0.3
- type: references
  target: core-fe49d5cb-2026-09-04-e11-md
  weight: 0.3
- type: references
  target: core-f1e17f54-2026-09-04-sesija-md
  weight: 0.3
---

# 2026-09-04 — Prolaz kroz ceo CODIUM i tri popravke izgleda

Cilj: Proći kroz svih četrnaest CODIUM ekrana, naći greške i popraviti ih odmah.
Uz to tri prijavljene bele mrlje: definicija u Pipelines, padajući spiskovi u
Deployments → Nov cilj i u Infrastructure → Tip.

## Bele mrlje — jedan uzrok, jedno mesto

Sve tri su ista stvar: **padajući spisak, klizač i ostale sistemske kontrole crta
operativni sistem, ne stranica.** Dok dokument ne kaže da je taman, Windows ih
crta svetle — beo popup na tamnoj aplikaciji.

Popravka je zato jedna, u `index.css`: `color-scheme: dark` na `:root`, uz
eksplicitne boje za `option` (Windows za sam spisak ne nasleđuje boje polja).
Pravilo hvata **ceo CORE**, ne samo CODIUM — isti kvar je čekao na svakom
budućem ekranu i u ostalim domenima. Ranija pravila po stranicama (Automations,
Integrations) time su postala suvišna i uklonjena su; ostalo je samo ono što
nije tema, kao sopstvena strelica u Automations.

Definicija u Pipelines je bila drugi slučaj istog reda: Monaco podrazumevano
crta u svetloj temi `vs`. Dobio je `codium-json`, izvedenu iz `vs-dark`, sa
podlogom panela (`#0f1522`). Tema se definiše u samom uređivaču, a ne globalno,
jer `defineTheme` vezuje ime — F6 editor ima svoju (`core-editor`) sa providnom
podlogom.

## Nađeno usput

- **Dve greške tipova koje su stajale u repozitorijumu.**
  `CoreDockLayout.tsx` je koristio `JSX.Element`, a React 19 nema globalni `JSX`
  namespace — zamenjeno sa `ReactElement`. `CodiumWorkspace.tsx` je nosio uvoz
  `X` koji niko ne koristi. `tsc` sada prolazi čist; do sada su te dve greške
  bile stalan šum koji je krio sve nove.
- **Test uređivača je pao na novoj temi**, jer lažni Monaco nije imao
  `editor.defineTheme`. Mock je dopunjen (u pravom Monaco-u `editor` je uvek tu;
  JSON servis je taj koji ume da fali), i dodat test koji traži da tema bude
  izvedena iz `vs-dark`.

## Ispravka ranijih unosa

U unosima [E10](2026-09-03-e10.md), [E11](2026-09-04-e11.md) i
[briefu sesije](2026-09-04-sesija.md) piše da u konzoli stoje dve greške
(`metadata`, `notify`) i da postoje i na Dashboard-u. **To nije tačno.** Bile su
posledica Vite HMR-a nad modulom koji je u tom trenutku bio u nekonzistentnom
stanju (upravo je bio preimenovan `ConnectorForm`), a čitač konzole ih je
zadržao u baferu preko svih narednih navigacija.

Posle čistog učitavanja: **nijedna greška u konzoli** ni na jednom od četrnaest
CODIUM ekrana, ni na Dashboard-u, ni u radnom prostoru.

Raniji unosi se ne prepravljaju — ostaju kakvi su bili, a ova ispravka stoji uz
njih.

## Provera uživo

Svih četrnaest ruta prošlo redom kroz pokrenut CORE: svaka ima svoj naslov i
sadržaj, nijedan zahtev nije pao (sve 200), nijedna greška u konzoli, i nijedan
element svetlije podloge osim žutog akcenta na dugmetu. Svaki `select` na svakom
ekranu prijavljuje `color-scheme: dark`. Monaco u Pipelines i u radnom prostoru
crta u `vs-dark`.

## Brojevi

892 vitest (+1), `tsc` bez ijedne greške po prvi put. Backend nije diran.

## Napomena

Projekat nema `eslint.config.*`, pa `eslint` ne može da se pokrene — provera
stila koda za sada stoji samo na `tsc` i testovima.
