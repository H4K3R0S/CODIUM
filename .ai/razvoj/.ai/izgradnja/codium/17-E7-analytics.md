---
id: codium-17c5584a-17-e7-analytics-md
type: reference
domain: codium
namespace: global
visibility: global
tier: domain
title: E7 — Analytics
summary: '**Blok:** operativna loza · **Zavisi od:** E2, E3, E4, E6, E8 · **Migracija:**
  nema'
keywords:
- analytics
- izgradnja
- codium
tags:
- izgradnja
- codium
source_path: .ai/izgradnja/codium/17-E7-analytics.md
edges:
- type: references
  target: codium-adabfbc2-09-enterprise-overview-md
  weight: 0.3
---

# E7 — Analytics

**Blok:** operativna loza · **Zavisi od:** E2, E3, E4, E6, E8 · **Migracija:** nema
**Sidebar:** `Analytics`

Pravila obrasca su u [09-ENTERPRISE-OVERVIEW.md](09-ENTERPRISE-OVERVIEW.md).

---

## Cilj

Odgovoriti na pitanja koja se ne vide iz pojedinačnog ekrana: gde odlazi vreme,
šta se najčešće kvari, koliko košta AI, da li se stanje popravlja ili pogoršava.

Faza namerno ide **posle** ostalih: ona ne proizvodi nove podatke, nego čita ono
što E2, E3, E4, E6 i E8 već upisuju. Zato nema svoju migraciju.

## Šta se meri

### Razvoj
- Commit-i po danu i po projektu (izvor: E2, kroz `GitProvider.log`).
- Aktivni dani po projektu, najduži niz.
- Vreme od prvog do poslednjeg commit-a u danu — gruba mera radnog dana.

### Isporuka
- Uspešnost pipeline-a: udeo uspešnih pokretanja, po pipeline-u i kroz vreme.
- Prosečno i najgore trajanje pokretanja; koji korak najčešće pada.
- Učestalost isporuka po cilju; vreme od commit-a do isporuke.
- Udeo isporuka koje su vraćene unazad.

### Rad sistema
- Dostupnost po servisu (udeo uzoraka `up = 1`) za period.
- Broj alarma po servisu; ukupno vreme u stanju `firing`.

### AI
- Pozivi, tokeni i trošak po modelu, po projektu i po personi (izvor: E8).
- Odnos lokalnih i online poziva — koliko je stvarno plaćeno.

## Backend

`core/domains/codium/analytics/`

- `queries.py` — jedan imenovani upit po metrici. Čist SQL nad `codium.db`, bez
  poslovne logike u Python-u gde SQL može sam. Svaki upit prima period i opcioni
  `project_id`.
- `service.py` — `AnalyticsService.report(name, period, filters)` i
  `AnalyticsService.summary(period)` za zbirnu tablu.
- `cache.py` — rezultat po ključu (ime upita + period + filteri) se drži u
  memoriji 60 sekundi. Agregati preko celog perioda nisu jeftini, a ekran se često
  ponovo iscrtava.

Nema pisanja u bazu. Ako neki izveštaj ne može bez međutabele, to je znak da
podatak fali u izvornoj fazi — dopunjava se **tamo**, ne ovde. Ovo pravilo čuva
E7 od pretvaranja u drugo skladište.

## API

`apps/api/routers/codium_analytics.py`, prefiks `/api/v1/codium/analytics`:

| Metoda | Putanja | Radi |
|---|---|---|
| GET | `/summary` | zbirna tabla (`?period=7d\|30d\|90d`) |
| GET | `/reports` | spisak dostupnih izveštaja i njihovih parametara |
| GET | `/reports/{name}` | jedan izveštaj (`?period=&project_id=`) |
| GET | `/export/{name}` | isti podaci kao CSV |

Odgovor izveštaja je uvek isti oblik: `{ name, period, series: [{ label, points: [{x, y}] }], totals: {...} }`.
Jedinstven oblik znači da GUI ima jednu komponentu grafikona, a ne osam.

## GUI (radi se posle backend-a bloka)

`pages/CodiumAnalytics.tsx`:

- Vrh: red pločica sa ključnim brojevima za izabrani period i promenom u odnosu
  na prethodni period jednake dužine.
- Ispod: grafikoni po odeljcima Razvoj / Isporuka / Rad sistema / AI.
- Prekidač perioda je jedan, na vrhu, i važi za celu stranu.
- Grafikoni prate `dataviz` pravila projekta: ista paleta, čitljivo u svetloj i
  tamnoj temi, širok sadržaj skroluje u svom okviru.

## Testovi

- `test_analytics_queries` — nad bazom napunjenom poznatim podacima svaki upit
  vraća tačan broj; period se poštuje na obe granice.
- `test_analytics_shape` — svaki izveštaj vraća dogovoreni oblik odgovora.
- `test_analytics_cache` — dva ista poziva unutar prozora pogađaju bazu jednom.
- `test_api_codium_analytics` — CSV izvoz ima zaglavlje i isti broj redova kao
  JSON odgovor.

## Definicija završetka

Zbirna tabla i pojedinačni izveštaji rade nad stvarnim podacima ostalih faza;
nijedan upit ne piše u bazu; oblik odgovora je jedinstven; testovi domena prolaze.
