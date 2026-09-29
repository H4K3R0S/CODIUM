---
id: codium-0933a37b-21-e11-integrations-ekran-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E11 — Integrations (ekran)
summary: '**Blok:** završni · **Zavisi od:** E0 · **Migracija:** nema'
keywords:
- e11
- integrations
- ekran
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/21-E11-integrations-ekran.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E11 — Integrations (ekran)

**Blok:** završni · **Zavisi od:** E0 · **Migracija:** nema
**Sidebar:** `Integrations`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Vidljivo lice sloja napravljenog u E0. Jedno mesto gde se vidi sa čime je CODIUM
povezan, da li veza radi, i gde se dodaje nova.

Faza je namerno tanka i namerno poslednja: dok E2–E10 ne postoje, ekran bi
prikazivao prazan spisak. Pošto E0 već nosi model, servis i API, ovde nema
backend posla osim sitnica.

## Backend

Ništa novo. Ako se u toku E2–E10 pokaže da nekom konektoru fali polje ili tip,
dopuna ide u E0 module, ne ovde.

Jedini mogući dodatak: `GET /api/v1/codium/integrations/usage` — koji podsistemi
koriste koji konektor (deploy ciljevi iz E4, infra node-ovi iz E5, OpenRouter iz
E8). Potrebno da brisanje konektora može da upozori šta će se pokvariti.

## GUI

`pages/CodiumIntegrations.tsx`:

- Mreža kartica po konektoru: ime, tip, oznaka stanja (`ok`, `error`,
  `unconfigured`), vreme poslednje provere.
- Dugme „Testiraj vezu" na kartici; rezultat i trajanje se prikazuju odmah.
- „Dodaj konektor" otvara formu koja polja gradi iz odgovora `GET /kinds` —
  jedna forma za sve tipove, bez posebnog koda po tipu.
- Polja tajni se prikazuju kao `••••` sa dugmetom „Zameni". Vrednost se nikada ne
  prikazuje, jer je API i ne vraća.
- Brisanje traži potvrdu i navodi šta konektor koristi.

`features/codium/integrations/connectorForm.ts` — čist modul koji od opisa tipa
pravi opis forme i proverava obavezna polja. Testira se bez React-a.

## Zadatak zatvaranja trake

Kada je ovaj ekran gotov, u `Sidebar.tsx` nijedna CODIUM stavka više ne sme da
nosi `kind: "soon"` ni značku „USKORO". Provera je deo definicije završetka.

## Testovi

- `connectorForm.test.ts` — opis forme se gradi iz opisa tipa; nedostajuće
  obavezno polje se prijavljuje; polje tajne je označeno kao takvo.
- `CodiumIntegrations.test.tsx` — kartica prikazuje stanje; „Testiraj vezu" zove
  API i osvežava stanje; vrednost tajne se ne pojavljuje u DOM-u.

## Definicija završetka

Konektori se vide, dodaju, testiraju i brišu iz GUI-ja; forma se gradi iz opisa
tipa; nijedna CODIUM stavka u sidebar-u nije više „USKORO"; testovi prolaze.
