---
id: codium-2026-09-02-pipeline-petlja
type: log
domain: codium
title: 2026-09-02 — Pipeline dobija petlju koja ume podproces
summary: 'Cilj: Zatvoriti dug nađen pri proveri E4 uživo — **nijedan pipeline nije
  mogao'
keywords:
- '2026'
- pipeline
- dobija
- petlju
- koja
- ume
- podproces
- dev-log
tags:
- dev-log
- entries
source_path: .ai/dev-log/entries/2026-09-02-pipeline-petlja.md
edges:
- type: preceded_by
  target: codium-2026-09-02-e4
  weight: 0.8
- type: followed_by
  target: codium-2026-09-03
  weight: 0.8
---

# 2026-09-02 — Pipeline dobija petlju koja ume podproces

Cilj: Zatvoriti dug nađen pri proveri E4 uživo — **nijedan pipeline nije mogao
da se pokrene dok API server radi sa `--reload`**.

## Šta je bilo pokvareno

`uvicorn/loops/asyncio.py::asyncio_loop_factory` bira petlju ovako:

```
bez --reload (use_subprocess=False) -> ProactorEventLoop
sa  --reload (use_subprocess=True)  -> _WindowsSelectorEventLoop
```

Na Windows-u `SelectorEventLoop` ne ume `create_subprocess_shell`. Zato je
svako pokretanje kroz pokrenut dev server odmah završavalo kao `failed`, sa
`exit_code: null` i **praznim** razlogom — jer je `str(NotImplementedError())`
prazan string. U istoriji se nije videlo ni šta je puklo.

Bez `--reload` je radilo, i zato niko nije primetio: sve dosadašnje provere
vozile su motor direktno iz koda, gde je petlja Proactor.

## Popravka

Motor više ne zavisi od petlje koju zatekne — sam donosi onu koja ume posao.

`podrzava_podproces(loop)` odgovara na jedno pitanje: ume li ova petlja
podproces. Van Windows-a uvek da; na Windows-u samo `ProactorEventLoop`.

`PipelineRunner.start()` po tome bira gde da zakaže:

1. petlja **ove** niti, ako je ima i ako ume (asinhrona ruta na Proactor-u);
2. **povezana** petlja API procesa (`bind_loop`), ako ume (nit agenta, server
   bez `--reload`);
3. **sopstvena** petlja motora — uvek.

Sopstvena petlja je `ProactorEventLoop` u `daemon` niti, napravljena **tek kad
zatreba** i posle toga deljena: mašina koja taj problem nema nikad ne dobije ni
nit, a mašina koja ga ima ne dobija nit po pokretanju. `shutdown()` je gasi —
nije uslov za uredno gašenje procesa (nit je `daemon`), postoji da testovi ne
ostavljaju nit za sobom.

Dodat je i `wait_blocking(run_id, timeout)`: `wait()` je korutina i traži petlju
u pozivajućoj niti, a nit agenta je nema.

## Šta je time nestalo

Ranije je `start()` bez ijedne petlje i bez `bind_loop` dizao urednu grešku
(„bez radne petlje") — svesna odluka iz E3a popravnog talasa, da model ne dobije
golo `RuntimeError: no running event loop`. Otkako motor sam donosi petlju, taj
nedostatak više ne postoji: nit bez petlje je samo još jedan slučaj koji završi
na sopstvenoj petlji.

Test koji je čuvao tu grešku zato je prepisan da tvrdi novo ponašanje
(`test_start_bez_ijedne_petlje_vozi_na_sopstvenoj`), a ne obrisan — slučaj je i
dalje vredan provere, samo mu je ispravan ishod sada uspeh, ne greška.

`bind_loop` ostaje i dalje se koristi (korak 2), ali više nije jedini put i
više nije obavezan.

## Provera

**Testovi:** `./.venv/Scripts/python.exe -m pytest tests -q` — **1656 passed**
(bilo 1654). Dva nova u `test_pipeline_runner.py`:

- `test_petlja_bez_podprocesa_ne_obara_pokretanje` — pokretanje zakazano na
  pravom `SelectorEventLoop` mora da prođe;
- `test_povezana_petlja_bez_podprocesa_se_preskace` — `bind_loop` sa Selector
  petljom (tačno ono što `--reload` daje niti agenta) ne sme da odvede
  pokretanje u kvar.

Oba su prvo napisana i **potvrđeno su padala** iz istog razloga iz kog je padao
pravi server, pre nego što je motor promenjen.

**Uživo, kroz server koji radi sa `--reload`** (isti proces koji je pre ove
izmene padao):

- pokretanje pipeline-a `sa-artefaktom` → `success`, `exit_code: 0`, log
  `napravljeno B`, i paket spakovan (pokretanje je odmah ušlo u ponudu za
  isporuku);
- pipeline sa `sleep(60)` pokrenut pa otkazan → `cancelled`, razlog
  `otkazano`, log sačuvan. Otkazivanje sada prelazi granicu niti (ruta je u
  jednoj, petlja motora u drugoj) — zato je posebno provereno.

## Sledeće

- **E5 Infrastructure** ili **E0-pun**.
- Odluka o Monaco JSON worker-u (otvoreno od 2026-09-01).

## Napomene/odluke

- **Popravka je u motoru, ne u načinu pokretanja servera.** Moglo se rešiti i
  time da se dev server pokreće bez `--reload`, ali to bi značilo da ispravnost
  domena zavisi od zastavice na komandnoj liniji — i da se isti kvar vrati čim
  neko doda `--workers`, koji bira istu petlju.
- **Deljena stanja motora (`_tasks`, `_processes`, `_cancelled`) sada se dodiruju
  iz dve niti** — rute iz svoje, petlja motora iz svoje. To nije novo: isti
  raspored je postojao otkako nit agenta zakazuje preko `bind_loop`. Operacije
  su pojedinačni upisi i čitanja u `dict`/`set`, bez koraka koji bi smeo da se
  prepolovi.
- Testni pipeline `spor` (id 4), napravljen samo da se otkazivanje proveri,
  obrisan je posle provere. `sa-artefaktom` (id 3) ostaje.
