"""Sklapanje foldera ćelije iz živog repoa.

Ništa se ne briše iz repoa — ovo je kopiranje. Brisanje FILMIUM koda iz CORE-a
je zaseban, kasniji korak, tek kad ćelija dokaže rad.

Ćelija zadržava Python korene `core` i `apps`, pa se nijedan uvoz u kopiranom
kodu ne prepisuje — osim jednog: auto-uvoz prelazi sa KALIMA skenera na
`import_guard` domena.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from core.cell.build_common import (
    _copy,
    _ignore_kernel_extras,
    _logger,
    _remove_path,
)
from core.cell.build_gui import (
    CELL_GUI_PROJECT_FILES,
    _assemble_gui,
    build_gui_dist,
)
from core.cell.build_import_checks import (
    find_unresolved_local_imports,
)
from core.cell.manifest import CELL_MANIFEST_FILENAME, CellManifest, load_cell_manifest
from core.cell.requirements import build_requirements

GuiBuilder = Callable[[Path, Path], None]


KERNEL_VERSION = "0.1.0"

# Prozor aplikacije ćelije (Rust ljuska, Task 3): putanja relativna na koren
# repoa. `build_cell` ga kopira u koren ćelije pod imenom domena (`<IME>.exe`),
# a `start.bat` ga pokreće. Ako ne postoji, sklapanje staje sa uputstvom da se
# napravi `cargo build --release`.
CELL_SHELL_EXE: str = "apps/cell-shell/target/release/cell-shell.exe"


def cell_exe_name(manifest_name: str) -> str:
    """
    Ime `.exe` fajla ćelije iz imena domena — npr. `"FILMIUM"` -> `"FILMIUM.exe"`.

    Ime zadržava samo slova, cifre, `-` i `_`; sve ostalo (razmaci, tačke,
    kose crte) se izbacuje, pa se dobija bezbedno ime fajla za koren ćelije.
    """

    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", manifest_name)
    return f"{cleaned}.exe"

# Šablon za `config/tmdb.json` u sklopljenoj ćeliji — SAMO rezervisane
# vrednosti, nikad prava CORE tajna niti kopija CORE-ovog `config/tmdb.json`
# (koji na ovoj mašini nosi pravu vrednost — vidi docs/CELIJA_TAJNE.md).
# `core.domains.filmium.tmdb_client` čita baš ovu putanju i baš ovaj oblik;
# ćelija dobija isti "podesi ručno" korak kao svež klon CORE repoa.
_TMDB_CONFIG_TEMPLATE = (
    "{\n"
    '  "access_token": "[ Here put access token for TMDB ]",\n'
    '  "api_key": "[Here put api_key]"\n'
    "}\n"
)

# Kernel ćelije: putanje relativne na koren repoa.
KERNEL_PYTHON_MODULES: tuple[str, ...] = (
    "core/__init__.py",
    "core/foundation",
    "core/database",
    "core/cell",
    "core/rag",
    "core/system/__init__.py",
    "core/system/file_monitor",
    "core/ai/__init__.py",
    "core/ai/ollama_client.py",
    "core/ai/model_registry.py",
    "core/ai/core_router.py",
    "core/ai/personas.py",
    "core/ai/persona_store.py",
    "core/models",
    "core/domains/__init__.py",
    "apps/__init__.py",
    "apps/api/__init__.py",
    "apps/api/streaming.py",
    "apps/api/routers/__init__.py",
    "apps/api/routers/cell.py",
    "apps/api/schemas/cell.py",
)

# Paketi/moduli izvan KERNEL_PYTHON_MODULES koje ćelija ipak mora da nosi u
# celini — po-domenski, GENERIČKI: nijedan domenski put nije zakucan u okviru.
# Svaki domen prijavi šta mu treba van `core`/`apps` u
# `core/domains/<domen>/cell_extra.py::CELL_EXTRA` (tuple repo-relativnih
# POSIX putanja). Domen bez tog modula/atributa nema dodatnih paketa (`()`).
#
# Ovo su STVARNI nalazi (`find_unresolved_local_imports`), ne pretpostavke:
# npr. FILMIUM je tražio `integrations/translator` (lenji uvoz u
# `filmium.py`/`filmium_wishlist.py`) i `core/media_player.py` (lenji uvoz u
# `filmium_series.py`). Takav uvoz pukne tek pri POKRETANJU ćelije
# (`ModuleNotFoundError`), van svakog testa koji samo parsira vrh fajla —
# zato ga domen mora eksplicitno prijaviti. Kopira se, ne premešta.
def domain_extra_packages(domain_id: str) -> tuple[str, ...]:
    """
    Dodatni paketi domena po konvenciji `core/domains/<domen>/cell_extra.py::CELL_EXTRA`.

    Ako modul `cell_extra` ne postoji ili nema atribut `CELL_EXTRA`, domen nema
    dodatnih paketa i vraća se prazan skup — okvir ne pretpostavlja nijedan put.

    Args:
        domain_id: Identifikator domena, npr. `kalima`.

    Returns:
        Tuple repo-relativnih POSIX putanja (folderi ili `.py` fajlovi) koje
        ćelija nosi u celini pored kernela.
    """
    try:
        module = importlib.import_module(f"core.domains.{domain_id}.cell_extra")
    except ModuleNotFoundError:
        return ()
    extra = getattr(module, "CELL_EXTRA", None)
    if extra is None:
        return ()
    return tuple(extra)

# `apps/api/schemas/__init__.py` namerno NIJE na listi: taj fajl ne postoji
# ni u repou (apps.api.schemas radi kao implicitni namespace paket, bez
# __init__.py) — bio je naveden u ranijoj verziji ove liste kao greška, ne
# kao opcioni modul. Otkriveno kad je uveden `skipped`; uklonjeno umesto
# tiho zaobiđeno.

# `core/ai/persona_store.py` ulazi u kernel — ćelijin AI sloj je "lokalna
# Ollama plus podešavanja persone" (core/cell/ai.py, Task 6), a personu čuva
# baš ovaj modul. Njegov lenji uvoz CODIUM personi se u ćeliji prepisuje na
# uklanjanje (vidi `rewrite_persona_store`), jer CODIUM domen ne postoji u
# jednodomenskoj ćeliji.
#
# `core/foundation/context.py`, `core/foundation/runtime.py` i
# `core/database/runtime.py` se ne kopiraju iz istog razloga (vidi
# `_EXCLUDED_KERNEL_FILES` i `_ignore_kernel_extras`): uvoze `core.domains.registry`
# (registar SVIH CORE domena) ili `core.integrations.migrations`. Ćelija je
# jednodomenska pa ništa od toga ne kopira.

# `apps/api/dependencies.py` je jedini OBAVEZAN, generički runtime modul ćelije.
#
# Nije u `KERNEL_PYTHON_MODULES` iako živi na istoj putanji za svaku ćeliju:
# sadržaj mu je domenska žica (konstruiše repozitorijume/servise na nivou
# modula), ne zamrznut kernel — spec §5 kaže da kernel ne nosi domene. U
# ćeliji se prepisuje da ne traži `ContextService` (vidi
# `_strip_cross_domain_dependencies`) — inače bi povukao `core.domains.registry`
# (registar SVIH CORE domena), koji ne ulazi u ćeliju. Nedostajući fajl diže
# `FileNotFoundError` (kao `KERNEL_PYTHON_MODULES`).
DOMAIN_DEPENDENCIES_MODULE: str = "apps/api/dependencies.py"

# Domenski runtime moduli (`apps/api/<domen>*.py` na vrhu paketa, npr.
# `kalima_runtime.py`, `codium_*_runtime.py`) se otkrivaju GLOB-om po imenu
# domena i kopiraju kakvi jesu — isti obrazac kao routeri/sheme domena
# (`_domain_router_paths`). Nijedno filmium ime nije zakucano u okviru; domen
# bez ijednog takvog modula prosto nema nijedan (npr. IMPERIUM).

# GUI fajlovi ćelije se od Task 6 više NE nabrajaju ručno (bivši
# `KERNEL_GUI_MODULES`) — `_assemble_gui` računa tačno zatvorenje uvoza od
# `src/cell/cellMain.tsx` preko `collect_gui_closure` (Task 4), primenjujući
# `cell-substitutions.json` (Task 3). To zatvorenje samo od sebe pokupi
# `httpClient.ts`, `sound.ts`, `useCoreSetting.ts` i `CoreChat.tsx` (jer ih
# FILMIUM fajlovi stvarno uvoze), a `CoreAssistantChat.tsx` NIKAD ne uđe —
# zamenjuje ga `src/cell/CellAssistantChat.tsx` pre razrešavanja uvoza.

# Fajlovi GUI projekta koje ćelija nosi pored izvornog zatvorenja.

# Generisane putanje (relativne na koren ćelije) koje `--update` zamenjuje.
# JEDINI izvor politike ažuriranja — zamena, rollback i oporavak rade samo nad
# ovom listom. Sve što NIJE na njoj ostaje tačno gde jeste: `data/`,
# `config/`, ostatak `.ai/` (§9.4 beleške u `.ai/nadogradnje/`, §10 atomi u
# `.ai/atomi/`, dev-log), `.git` ćelije, `gui/node_modules`, korisnikovi
# fajlovi u korenu. `gui/src` JESTE na listi: generiše se iz repoa, pa se
# korisnikove izmene u njemu pri ažuriranju NAMERNO zamenjuju — trajna izmena
# GUI-ja ide u CORE repo.
def generated_on_update(
    exe_name: str,
    extra_packages: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """
    Generisane putanje (relativne na koren ćelije) koje `--update` zamenjuje,
    uključujući `<IME>.exe` (prozor aplikacije) — ime se izračuna iz imena
    domena pri sklapanju (`cell_exe_name`), pa se prosleđuje ovde.

    Ovo je JEDINI izvor politike ažuriranja — zamena, rollback i oporavak rade
    samo nad ovom listom. Sve što NIJE na njoj ostaje tačno gde jeste: `data/`,
    `config/`, `.venv` (korisnički prostor, vidi core/cell/venv.py), ostatak
    `.ai/` (§9.4 beleške u `.ai/nadogradnje/`, §10 atomi u `.ai/atomi/`,
    dev-log), `.git` ćelije, `gui/node_modules`, korisnikovi fajlovi u korenu.
    `gui/src` JESTE na listi: generiše se iz repoa, pa se korisnikove izmene u
    njemu pri ažuriranju NAMERNO zamenjuju — trajna izmena GUI-ja ide u CORE repo.

    Args:
        exe_name: Ime `.exe` fajla ćelije (npr. `"FILMIUM.exe"`), iz `cell_exe_name`.
        extra_packages: Dodatni paketi domena (iz `domain_extra_packages`) —
            njihov gornji koren se mora naći u politici da bi ga `--update`
            preneo (vidi niže). Prazan za domen bez dodatnih paketa.
    """

    base = (
        "core",
        "apps",
        "cell_app.py",
        "start.bat",
        "requirements.txt",
        exe_name,
        CELL_MANIFEST_FILENAME,
        ".ai/CLAUDE.md",
        "gui/src",
        "gui/dist",
        "gui/public",
        "gui/package.json",
        *(f"gui/{name}" for name in CELL_GUI_PROJECT_FILES),
    )
    # Gornji koren svakog dodatnog paketa domena (npr. `integrations` iz
    # `integrations/translator`) MORA biti u politici: sklapanje ga stavi u
    # staging, a `--update` prenosi samo ono što je ovde — bez ovoga bi ćelija
    # koja se ažurira ostala bez tog korena i pukla sa ModuleNotFoundError.
    # `core` je već gore; dodaju se samo novi koreni.
    extra_roots = tuple(
        root
        for root in dict.fromkeys(module.split("/", 1)[0] for module in extra_packages)
        if root not in base
    )
    return base + extra_roots

# Direktorijumi ćelije koje ažuriranje pravi samo ako nedostaju.
CELL_AI_DIRECTORIES: tuple[str, ...] = (".ai/atomi", ".ai/nadogradnje", ".ai/dev-log/entries")

# Marker u backup folderu: zamena je u potpunosti završena, backup je višak.
SWAP_COMPLETE_MARKER = ".swap-complete"

# Alati za ponovni build u ćeliji; verzije se čitaju iz repoa.


# Pojedinačni fajlovi koji se izostavljaju iz inače kopiranih kernel
# direktorijuma, po imenu direktorijuma (ne globalno po imenu fajla — `core/rag`
# i `core/cell` imaju sopstvene, nezavisne `runtime.py` fajlove koji ćeliji
# trebaju). `core/foundation/context.py` i `core/foundation/runtime.py` uvoze
# `core.domains.registry` (registar SVIH CORE domena); `core/database/runtime.py`
# uvozi `core.integrations.migrations` (CORE-ova migracija za konektore, ne
# domenska). Ćeliji ne treba nijedno od ovoga — nijedan kopiran fajl ih ne zove.




# Modul-putanje koje odgovaraju `_EXCLUDED_KERNEL_FILES` (npr. "database" +
# "runtime.py" -> "core.database.runtime"). Izvedeno iz iste mape da ta dva
# spiska ne mogu da se razminu: svaki fajl koji `_ignore_kernel_extras`
# izbaci iz kopije MORA imati odgovarajući unos u `_FORBIDDEN_MODULES`, jer
# fajl koji ga uvozi bi inače prošao i `_ignore_kernel_extras` (fajl
# nedostaje) i `find_forbidden_module_imports` (uvoz nije na crnoj listi) —
# i pao tek na `ModuleNotFoundError` pri pokretanju ćelije.

# Moduli koje ćelija ni pod kojim uslovom ne nosi — svaki od njih vodi ka
# CORE-ovim višedomenskim slojevima (konektori, tajne, registar domena, punog
# AI runtime-a) ili ka fajlovima koje `build_cell` namerno ne kopira
# (`_EXCLUDED_KERNEL_FILE_MODULES`, izvedeno iznad). Za razliku od
# `find_foreign_domain_imports` (koji hvata `core.domains.<bilo koji>`), ovo
# je poimenična crna lista — brana za slučaj da neki budući kopiran fajl
# ponovo uveze nešto što je namerno izbačeno iz kernela, ili da neka buduća
# izmena `_strip_cross_domain_dependencies`/`.replace()` teksta nemo omane
# (npr. jer se tekst iznad nje preformatirao pa se ankerski string više ne
# poklapa) — u tom slučaju `ContextService`-ov uvoz bi ostao u kopiranom
# `dependencies.py`, a `context.py` mu ne bi postojao u ćeliji.
# `core.security.secrets` (stvarni store tajni), a NE ceo `core.security`:
# `core.security.scope_gate` je self-contained (samo stdlib) i neki domeni ga
# legitimno nose preko `cell_extra` (npr. CODIUM `ScopeGate`). Zabranjuje se
# baš `secrets`, ne ceo paket, da bezopasni scope_gate može u ćeliju.










def _guard_not_data(relative: str) -> None:
    """
    Poslednja linija odbrane: nijedno premeštanje pri ažuriranju ne sme da
    dirne `data/` ili `config/` (ni njihov podfajl).

    Pozivajuće petlje (`_swap_staged_cell`, `_recover_backup_before_update`)
    ionako rade samo nad `generated_on_update(...)` — ovo postoji da BUDUĆA
    izmena te liste ili petlji odmah pukne glasno, umesto da tiho premesti
    korisnikovu FILMIUM bazu ili pravu TMDB tajnu.

    Raises:
        ValueError: Ako putanja počinje sa `data` ili `config`.
    """
    parts = Path(relative).parts
    if parts and parts[0] in ("data", "config"):
        raise ValueError(
            f"Pokušaj da se dirne '{relative}' (data/ ili config/) pri zameni/oporavku ćelije — uvek greška."
        )


def _move_child(source_root: Path, relative: str, dest_root: Path) -> None:
    """
    Premešta `source_root/relative` u `dest_root/relative`, uz `_guard_not_data`.

    Odredište NE sme da postoji: `shutil.move` bi postojeći direktorijum
    tiho iskoristio kao roditelja i ugnezdio izvor u njega.

    Raises:
        FileExistsError: Ako odredište već postoji.
    """
    _guard_not_data(relative)
    destination = dest_root / relative
    if os.path.lexists(destination):
        raise FileExistsError(f"Odredište već postoji, premeštanje odbijeno: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_root / relative), str(destination))


def _prune_empty_dirs(root: Path) -> None:
    """Uklanja PRAZNE direktorijume ispod `root` (i sam `root` ako ostane prazan)."""

    if not root.is_dir():
        return
    for directory, _dirs, _files in os.walk(root, topdown=False):
        path = Path(directory)
        try:
            if not any(path.iterdir()):
                path.rmdir()
        except OSError:
            pass  # neprazan ili zaključan — ostaje, ništa se ne gubi


def _strip_cross_domain_dependencies(text: str) -> str:
    """
    Uklanja CORE Context servis iz `apps/api/dependencies.py` u ćeliji.

    `ContextService` prati aktivni domen među SVIM CORE domenima; ćelija ima
    samo jedan domen, pa joj ta zavisnost ne treba, a njen uvoz bi povukao
    `core.domains.registry` (koji ne ulazi u ćeliju — vidi
    `_ignore_kernel_extras`). `get_runtime_lifecycle` ostaje: on koristi
    `core/foundation/lifecycle.py`, koji nema uvoze ka domenima.

    Args:
        text: Sadržaj `apps/api/dependencies.py` iz repoa.

    Returns:
        Izmenjen sadržaj, bez pomena `ContextService`.
    """
    text = text.replace(
        "from core.foundation.context import ContextService, context_service\n",
        "",
    )
    return text.replace(
        'def get_context_service() -> ContextService:\n'
        '    """Vraca CORE Context servis (trenutno stanje sesije)."""\n'
        "\n"
        "    return context_service\n"
        "\n"
        "\n",
        "",
    )


def _domain_router_paths(repo_root: Path, domain_id: str) -> tuple[Path, ...]:
    """Putanje `apps/api/routers/{domain_id}*.py` fajlova, sortirane.

    Jedino mesto koje zna za taj glob — i kopiranje routera u `build_cell` i
    `_api_router_modules` (imena modula za `cell_app.py`) ga pozivaju, da se
    dva spiska nikad ne razmimoiđu.
    """

    routers = repo_root / "apps" / "api" / "routers"
    return tuple(sorted(routers.glob(f"{domain_id}*.py")))


def _api_router_modules(repo_root: Path, domain_id: str) -> tuple[str, ...]:
    """Imena modula `apps.api.routers.{domain_id}*` koje ćelija montira."""

    return tuple(
        f"apps.api.routers.{router.stem}"
        for router in _domain_router_paths(repo_root, domain_id)
    )


def _domain_runtime_module_paths(repo_root: Path, domain_id: str) -> tuple[Path, ...]:
    """
    Putanje domenskih runtime modula `apps/api/{domain_id}*.py`, sortirane.

    To su moduli na vrhu `apps/api` paketa koje domenski routeri uvoze (npr.
    `kalima_runtime.py`, `codium_*_runtime.py`), za razliku od routera
    (`apps/api/routers/`) i shema (`apps/api/schemas/`). `apps/api/main.py`,
    `dependencies.py` i `streaming.py` ne počinju imenom domena, pa ih ovaj
    glob nikad ne pokupi.
    """

    api = repo_root / "apps" / "api"
    return tuple(sorted(api.glob(f"{domain_id}*.py")))


def _cell_override(repo_root: Path, domain_id: str, relative: str) -> Path | None:
    """
    Ćelijska zamena za repo modul, ili `None` ako je nema.

    Konvencija: `core/domains/<domen>/cell_overrides/<relative>`, gde je
    `relative` putanja modula relativna na koren repoa (npr.
    `apps/api/routers/codium_ai.py`). Domen tu drži verziju modula bezbednu za
    ćeliju — bez CORE-only slojeva (`core_ai_runtime`, `core.security.secrets`)
    — koju `build_cell` kopira UMESTO repo verzije. Bez override-a vraća `None`
    (kopira se repo modul kakav jeste).
    """
    candidate = (
        repo_root / "core" / "domains" / domain_id / "cell_overrides" / Path(relative)
    )
    return candidate if candidate.is_file() else None


def _render_api_routers(modules: tuple[str, ...]) -> str:
    """
    `API_ROUTERS` kao Python literal spreman za ubacivanje u šablon.

    `repr(tuple(...))` je ispravan Python i za prazan tuple (`()`), i za
    tuple sa jednim elementom (`('a',)`), i za više — za razliku od ručnog
    spajanja zarezima (`", ".join(...) + ","`), koje za praznu listu daje
    `(,)`, sintaksnu grešku. Dormant za FILMIUM (16 routera), ali spisak se
    izvodi iz globa baš zato da radi i za budući domen sa 0 ili 1 routerom.
    """

    return repr(tuple(modules))


def _render_template(repo_root: Path, name: str, values: dict[str, str]) -> str:
    """Učitava šablon iz `scripts/cell/templates` i popunjava ga."""

    text = (repo_root / "scripts" / "cell" / "templates" / name).read_text(
        encoding="utf-8"
    )

    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)

    return text


def rewrite_persona_store(text: str, domain_id: str) -> str:
    """
    Uklanja CODIUM personu iz `core/ai/persona_store.py` u ćeliji NE-codium domena.

    Repo verzija nudi CORE, CODIUM i domenske persone iz jednog modula, pa
    lenjo (unutar `_defaults()`) uvozi `core.domains.codium.assistant.personas`.
    U ćeliji domena RAZLIČITOG od codium taj uvoz vodi ka stranom domenu koji
    ćelija ne nosi — uklanja se ceo "codium" opseg iz `_defaults()` (ne samo
    uvoz), inače bi `PersonaStore.scopes()` prijavljivao opseg koji ne radi.

    Za CODIUM ćeliju se NIŠTA ne dira: codium domen i njegove persone JESU u
    ćeliji, pa opseg treba da ostane.

    Args:
        text: Sadržaj `core/ai/persona_store.py` iz repoa.
        domain_id: Domen ćelije. Ako je `codium`, tekst se vraća nepromenjen.

    Returns:
        Izmenjen sadržaj (bez CODIUM opsega) za ne-codium domen; nepromenjen za codium.
    """
    if domain_id == "codium":
        return text

    text = text.replace(
        "    from core.domains.codium.assistant.personas import (  # noqa: PLC0415\n"
        "        PERSONAS as CODIUM_PERSONAS,\n"
        "        persona_ids as codium_persona_ids,\n"
        "    )\n"
        "\n",
        "",
    )
    return text.replace(
        '        "codium": {\n'
        "            GLOBAL_PERSONA: _CODIUM_GLOBAL,\n"
        "            **{pid: CODIUM_PERSONAS[pid] for pid in codium_persona_ids()},\n"
        "        },\n",
        "",
    )


















def _ensure_cell_user_space(root: Path) -> None:
    """
    Pravi korisnički prostor ćelije SAMO ako nedostaje; postojeće ne dira.

    - `.ai/atomi/`, `.ai/nadogradnje/`, `.ai/dev-log/entries/` — sadržaj im je
      korisnikov (§9.4, §10), pa ih ažuriranje nikad ne zamenjuje.
    - `config/tmdb.json` — samo šablon sa rezervisanim vrednostima (vidi
      `_TMDB_CONFIG_TEMPLATE`). Bez njega `tmdb_client.load_credentials` ne bi
      imao šta da pročita i ćelija bi tiho izgubila TMDB metapodatke. Nikad se
      ne prepisuje ako postoji: može da nosi korisnikovu pravu TMDB tajnu,
      koju build_cell nikad ne sme da vidi ni prepiše.
    """
    for relative in CELL_AI_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)

    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    tmdb_config_path = config_dir / "tmdb.json"
    if not tmdb_config_path.exists():
        tmdb_config_path.write_text(_TMDB_CONFIG_TEMPLATE, encoding="utf-8")


def _assemble_cell_contents(
    domain_id: str,
    target: Path,
    *,
    repo_root: Path,
    port: int,
    detached_from: str,
    skipped: list[str] | None,
    gui_builder: GuiBuilder,
    existing_manifest_data: dict | None,
    shell_exe: Path,
    exe_name: str,
    extra_packages: tuple[str, ...],
) -> None:
    """
    Puni `target` kompletnim sadržajem ćelije: Python deo, GUI, `.ai/`,
    pokretanje i manifest.

    Ne proverava da li je `target` prazan niti da li već postoji ćelija — to
    je posao pozivaoca (`build_cell`), koji ovu funkciju zove ili DIREKTNO na
    ciljni folder (prvo sklapanje), ili na privremeni STAGING folder
    (ažuriranje) — tako da neuspešno ažuriranje NIKAD ne ostavi pravi `target`
    u polu-sklopljenom stanju (vidi `build_cell`).

    Args:
        domain_id: Identifikator domena, npr. `filmium`.
        target: Folder u koji se sklapa (ciljni folder ili staging).
        repo_root: Koren CORE repoa iz kog se kopira.
        port: Port koji ide u renderovan `cell.json` PRE eventualnog spajanja
            sa `existing_manifest_data`.
        detached_from: Kratak hash commita iz kog je ćelija izvučena/ažurirana.
        skipped: Zadržana opciona lista (kompatibilnost sa `build_cell`/CLI).
            Domenski runtime moduli se sada otkrivaju glob-om, pa nema
            „naveden ali odsutan" slučaja — ostaje prazna.
        gui_builder: Pravi `gui/dist` iz sklopljenog `gui/` foldera.
        existing_manifest_data: Manifest postojeće ćelije (pri ažuriranju), iz
            kog se `port`, `core_url`, `ai` i `rag` prenose u novi manifest;
            `None` pri prvom sklapanju (ništa se ne prenosi).

    Raises:
        FileNotFoundError: Ako neki modul iz `KERNEL_PYTHON_MODULES` ne
            postoji u repou; ako `apps/api/dependencies.py` ne postoji u
            repou; ako `apps/gui/public` ne postoji u repou; ili ako GUI build
            ne napravi `gui/dist/index.html`.
        ValueError: Ako GUI zatvorenje (Task 4) vuče CORE-only module.
    """
    target.mkdir(parents=True, exist_ok=True)

    # Kernel — isti raspored kao u repou, pa uvozi rade nepromenjeni. Svaki
    # unos ovde je obavezan; ako ga nema u repou, neko je pogrešno otkucao
    # putanju (ili ga je repo u međuvremenu preimenovao/uklonio) — to se
    # prijavljuje odmah, ne tiho preskače.
    for module in KERNEL_PYTHON_MODULES:
        source = repo_root / module
        if not source.exists():
            raise FileNotFoundError(
                f"Modul iz KERNEL_PYTHON_MODULES ne postoji u repou: "
                f"{module} (očekivano na {source}). Ako je modul stvarno "
                "opcion, izbaci ga iz liste — 'naveden ali odsutan' ovde "
                "znači pogrešno otkucanu putanju, ne opcioni modul."
            )

        if module == "core/ai/persona_store.py":
            destination = target / module
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                rewrite_persona_store(source.read_text(encoding="utf-8"), domain_id),
                encoding="utf-8",
            )
        elif module in ("core/foundation", "core/database"):
            _copy(source, target / module, ignore=_ignore_kernel_extras)
        else:
            _copy(source, target / module)

    # Dodatni paketi domena izvan core/apps (iz `domain_extra_packages`) —
    # isti obavezan ugovor kao KERNEL_PYTHON_MODULES: nedostajuća putanja u
    # repou znači pogrešno otkucanu putanju u domenskom `cell_extra.py`, ne
    # opcioni paket.
    for module in extra_packages:
        source = repo_root / module
        if not source.exists():
            raise FileNotFoundError(
                f"Dodatni paket domena (cell_extra) ne postoji u repou: "
                f"{module} (očekivano na {source})."
            )
        # cell_extra fajl može imati ćelijski override (npr. CODIUM nosi
        # trimovan `core/ai/providers/__init__.py` bez online provajdera).
        override = _cell_override(repo_root, domain_id, module)
        _copy(override or source, target / module)

    # Domen. `cell_overrides/` (ćelijske zamene apps/api modula) se NE kopira u
    # domenski folder ćelije — te fajlove `build_cell` već stavlja na njihovo
    # pravo `apps/api/...` mesto (vidi `_cell_override`); kopija ovde bi bila
    # mrtav duplikat.
    _copy(
        repo_root / "core" / "domains" / domain_id,
        target / "core" / "domains" / domain_id,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "cell_overrides"),
    )

    # Routeri i sheme domena. Router može imati ćelijski OVERRIDE (vidi
    # `_cell_override`): npr. CODIUM `codium_ai` u ćeliji ne sme da vuče
    # `core_ai_runtime`, pa domen nosi svoju ćelijsku verziju.
    router_paths = _domain_router_paths(repo_root, domain_id)
    for router in router_paths:
        rel = f"apps/api/routers/{router.name}"
        override = _cell_override(repo_root, domain_id, rel)
        _copy(override or router, target / "apps" / "api" / "routers" / router.name)

    schemas = repo_root / "apps" / "api" / "schemas"
    for schema in sorted(schemas.glob(f"{domain_id}*.py")):
        _copy(schema, target / "apps" / "api" / "schemas" / schema.name)

    # Obavezni generički runtime modul: `apps/api/dependencies.py`, prepisan da
    # ne traži `ContextService` (vidi `_strip_cross_domain_dependencies`).
    dependencies_source = repo_root / DOMAIN_DEPENDENCIES_MODULE
    if not dependencies_source.exists():
        raise FileNotFoundError(
            f"Obavezni runtime modul {DOMAIN_DEPENDENCIES_MODULE} ne postoji u "
            f"repou (očekivano na {dependencies_source})."
        )
    dependencies_dest = target / DOMAIN_DEPENDENCIES_MODULE
    dependencies_dest.parent.mkdir(parents=True, exist_ok=True)
    dependencies_dest.write_text(
        _strip_cross_domain_dependencies(dependencies_source.read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    # Domenski runtime moduli (`apps/api/<domen>*.py`, npr. `kalima_runtime.py`,
    # `codium_*_runtime.py`) — kopiraju se kakvi jesu (ili ćelijski override, npr.
    # CODIUM `codium_assistant_runtime` bez `core_ai_runtime`), po istom
    # glob-obrascu kao routeri/sheme. Domen bez ijednog ih nema.
    for module_path in _domain_runtime_module_paths(repo_root, domain_id):
        rel = f"apps/api/{module_path.name}"
        override = _cell_override(repo_root, domain_id, rel)
        _copy(override or module_path, target / "apps" / "api" / module_path.name)

    # GUI — izvorno zatvorenje, projektni fajlovi i Vite build (posle Python
    # dela, pre upisa manifesta, vidi docstring gore).
    _assemble_gui(repo_root, target, gui_builder, domain_id)

    # `.ai` direktorijum ćelije: `CLAUDE.md` je generisan, ostalo je korisnikovo
    # (vidi `_ensure_cell_user_space`).
    _ensure_cell_user_space(target)
    (target / ".ai" / "CLAUDE.md").write_text(
        _render_template(
            repo_root,
            "CLAUDE.md.tpl",
            {"DOMAIN_ID": domain_id, "DOMAIN_NAME": domain_id.upper()},
        ),
        encoding="utf-8",
    )

    # Pokretanje i zavisnosti.
    api_routers = _api_router_modules(repo_root, domain_id)
    (target / "cell_app.py").write_text(
        _render_template(
            repo_root,
            "cell_app.py.tpl",
            {
                "DOMAIN_ID": domain_id,
                "API_ROUTERS": _render_api_routers(api_routers),
            },
        ),
        encoding="utf-8",
    )
    # Prozor aplikacije (Rust ljuska): kopira se u koren ćelije pod imenom
    # domena; `start.bat` ga pokreće. Deo je `generated_on_update`, pa ga
    # `--update` osvežava (izvor exe-a je proveren u `build_cell`).
    _copy(shell_exe, target / exe_name)
    (target / "start.bat").write_text(
        _render_template(
            repo_root,
            "start.bat.tpl",
            {
                "DOMAIN_NAME": domain_id.upper(),
                "DOMAIN_ID": domain_id,
                "PORT": str(port),
                "EXE_NAME": exe_name,
            },
        ),
        encoding="utf-8",
    )
    # Suženi requirements.txt — samo ono što kod ćelije stvarno uvozi (vidi
    # core/cell/requirements.py), ne CORE-ov puni requirements.txt (koji nosi
    # i anthropic/openai/mcp/keyring, CORE-ov AI/tajne sloj). Piše se OVDE,
    # posle kopiranja svih Python modula (core/apps/integrations, cell_app.py
    # iznad) — build_requirements skenira baš njih.
    (target / "requirements.txt").write_text(build_requirements(target), encoding="utf-8")

    # Manifest. `detached_from`, `kernel_version` i `created_at` su uvek novi;
    # pri ažuriranju se `port`, `core_url`, `ai` i `rag` zadržavaju iz
    # postojećeg manifesta (pročitanog PRE brisanja, na vrhu funkcije), a novi
    # `port` argument se ignoriše — CORE ne sme da premesti ćeliju na drugi
    # port samim ažuriranjem koda.
    manifest_data = json.loads(
        _render_template(
            repo_root,
            "cell.json.tpl",
            {
                "DOMAIN_ID": domain_id,
                "DOMAIN_NAME": domain_id.upper(),
                "KERNEL_VERSION": KERNEL_VERSION,
                "PORT": str(port),
                "CREATED_AT": datetime.now().isoformat(timespec="seconds"),  # noqa: DTZ005
                "DETACHED_FROM": detached_from,
            },
        )
    )
    if existing_manifest_data is not None:
        manifest_data["port"] = existing_manifest_data.get("port", manifest_data["port"])
        manifest_data["core_url"] = existing_manifest_data.get("core_url")
        manifest_data["ai"] = existing_manifest_data.get("ai")
        manifest_data["rag"] = existing_manifest_data.get("rag")

    (target / CELL_MANIFEST_FILENAME).write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _backup_dir_for(target: Path) -> Path:
    """Susedni folder u koji `_swap_staged_cell` premešta stari sadržaj `target`-a."""

    return target.parent / f".{target.name}.old"


def _remove_completed_backup(backup: Path) -> None:
    """
    Uklanja backup ZAVRŠENE zamene, marker `SWAP_COMPLETE_MARKER` poslednji.

    Kad bi marker nestao prvi a brisanje ostatka puklo (zaključan fajl),
    sledeće ažuriranje bi video backup bez markera, sa imenima koja se sudaraju
    sa `target`-om, i odbijalo bi zauvek. Ovako marker preživi svaki
    delimičan neuspeh.

    Raises:
        OSError: Ako nešto ne može da se ukloni (marker tad ostaje).
    """
    for child in list(backup.iterdir()):
        if child.name != SWAP_COMPLETE_MARKER:
            _remove_path(child)
    (backup / SWAP_COMPLETE_MARKER).unlink(missing_ok=True)
    backup.rmdir()


def _swap_staged_cell(
    target: Path, staging: Path, exe_name: str, extra_packages: tuple[str, ...]
) -> None:
    """
    Menja GENERISANE putanje `target`-a (`generated_on_update`) sadržajem iz
    `staging`-a — PREMEŠTANJEM, nikad brisanjem, dok se ne zna da je zamena
    uspela. Sve što nije na listi ostaje netaknuto na svom mestu.

    - FAZA A: svaka generisana putanja koja postoji u `target`-u se premesti u
      susedni BACKUP folder (`_backup_dir_for(target)`), na istu relativnu
      putanju (npr. `gui/src`, `.ai/CLAUDE.md`). Svako premeštanje se beleži.
    - FAZA B: svaka generisana putanja iz `staging`-a se premesti u `target`.
      Zatim se prave `.ai/` direktorijumi i `config/tmdb.json` šablon SAMO ako
      nedostaju (`_ensure_cell_user_space`).
    - Ako BILO ŠTA u A ili B pukne: ono što je faza B prebacila se vrati u
      `staging`, a ono što je faza A prebacila se vrati u `target`. Svaki
      korak vraćanja je u sopstvenom `try` — pokušavaju se SVI, neuspesi se
      skupljaju i dodaju kao beleške (`add_note`) na ORIGINALNI izuzetak, koji
      se prosleđuje dalje. Ništa se ne briše: što ne može da se vrati ostaje u
      backup-u (sledeće ažuriranje ga oporavlja).
    - Na uspeh: u backup se upisuje `SWAP_COMPLETE_MARKER`, pa se backup i
      staging uklanjaju. Ako čišćenje padne (zaključan fajl), samo upozorenje —
      živa ćelija je kompletna, a marker govori sledećem pokretanju da je
      backup višak (vidi `_recover_backup_before_update`).

    Raises:
        RuntimeError: Ako backup folder već postoji (oporavak ga nije uklonio).
    """
    backup = _backup_dir_for(target)
    if os.path.lexists(backup):
        raise RuntimeError(
            f"Backup folder {backup} i dalje postoji (verovatno zaključan fajl iz "
            "prethodnog ažuriranja). Zatvori program koji ga drži i pokušaj ponovo."
        )
    backup.mkdir(parents=True)

    moved_to_backup: list[str] = []
    moved_to_target: list[str] = []

    generated = generated_on_update(exe_name, extra_packages)
    try:
        for relative in generated:
            if os.path.lexists(target / relative):
                _move_child(target, relative, backup)
                moved_to_backup.append(relative)

        for relative in generated:
            if os.path.lexists(staging / relative):
                _move_child(staging, relative, target)
                moved_to_target.append(relative)

        _ensure_cell_user_space(target)
    except BaseException as error:
        rollback_failures: list[str] = []

        for relative in reversed(moved_to_target):
            try:
                _move_child(target, relative, staging)
            except Exception as rollback_error:  # noqa: BLE001 — skuplja se, ne guta
                rollback_failures.append(
                    f"vraćanje novog '{relative}' iz {target} u {staging}: {rollback_error!r}"
                )

        for relative in reversed(moved_to_backup):
            try:
                _move_child(backup, relative, target)
            except Exception as rollback_error:  # noqa: BLE001 — skuplja se, ne guta
                rollback_failures.append(
                    f"vraćanje starog '{relative}' iz {backup} u {target}: {rollback_error!r}"
                )

        _prune_empty_dirs(backup)

        for failure in rollback_failures:
            error.add_note(
                f"Rollback ažuriranja ćelije NIJE uspeo za {failure}. Ništa nije "
                "obrisano — stara verzija ostaje u backup folderu i sledeće "
                "ažuriranje je prvo oporavlja."
            )
        raise

    try:
        (backup / SWAP_COMPLETE_MARKER).write_text(
            datetime.now().isoformat(timespec="seconds") + "\n", encoding="utf-8"  # noqa: DTZ005
        )
        _remove_completed_backup(backup)
    except OSError as error:
        _logger.warning(
            "Ažuriranje ćelije je uspelo, ali uklanjanje backup-a %s nije: %s", backup, error,
        )

    try:
        _remove_path(staging)
    except OSError as error:
        _logger.warning(
            "Ažuriranje ćelije je uspelo, ali uklanjanje staging-a %s nije: %s", staging, error,
        )


def _recover_backup_before_update(
    target: Path, exe_name: str, extra_packages: tuple[str, ...]
) -> None:
    """
    Oporavak od backup foldera koji je ostao iza prethodnog ažuriranja.

    - Backup SA `SWAP_COMPLETE_MARKER`: zamena je bila završena, samo čišćenje
      nije (zaključan fajl, pad procesa) — backup se ukloni, a neuspeh je samo
      upozorenje.
    - Backup BEZ markera: proces je ugašen NASRED zamene, pa `target` možda
      NEMA `cell.json` (u backup-u je). "Sve ili ništa" provera: ako ijedna
      generisana putanja postoji i u `target`-u i u backup-u, ništa se ne
      dira i diže se jasna greška. Inače se svaka generisana putanja vraća u
      `target`, svaka u sopstvenom `try`; neuspesi se skupljaju kao beleške.

    Args:
        target: Koren ćelije koji `--update` cilja.

    Raises:
        RuntimeError: Ako `target` i backup imaju istu generisanu putanju; ili
            ako vraćanje nije potpuno (backup posle njega nije prazan) — beleške
            izuzetka nabrajaju svaki neuspeo korak.
    """
    backup = _backup_dir_for(target)
    if not backup.is_dir():
        return

    if (backup / SWAP_COMPLETE_MARKER).is_file():
        try:
            _remove_completed_backup(backup)
        except OSError as error:
            _logger.warning(
                "Backup završenog ažuriranja %s nije mogao da se ukloni: %s", backup, error,
            )
        return

    target.mkdir(parents=True, exist_ok=True)
    present = [
        relative
        for relative in generated_on_update(exe_name, extra_packages)
        if os.path.lexists(backup / relative)
    ]

    conflicts = [relative for relative in present if os.path.lexists(target / relative)]
    if conflicts:
        raise RuntimeError(
            "Oporavak posle prekinutog ažuriranja nije bezbedan: i "
            f"{target} i {backup} imaju {', '.join(conflicts)}. Uporedi ih "
            "ručno (koja verzija treba da ostane) i obriši stariju pre novog "
            "pokušaja ažuriranja — ništa nije obrisano ni premešteno."
        )

    failures: list[str] = []
    for relative in present:
        try:
            _move_child(backup, relative, target)
        except Exception as restore_error:  # noqa: BLE001 — skuplja se, ne guta
            failures.append(f"vraćanje '{relative}' iz {backup} u {target}: {restore_error!r}")

    _prune_empty_dirs(backup)

    if failures or backup.exists():
        error = RuntimeError(
            f"Oporavak posle prekinutog ažuriranja nije potpun: {backup} i dalje "
            "postoji. Ništa nije obrisano — premesti ostatak ručno u ćeliju pa "
            "pokušaj ažuriranje ponovo."
        )
        for failure in failures:
            error.add_note(f"Neuspeo korak oporavka: {failure}")
        raise error


def _validate_target(target: Path) -> None:
    """
    Odbija cilj bez imena ili koren diska (npr. `F:\\`).

    Staging i backup su SUSEDI cilja (`<roditelj>/.<ime>.staging`), pa koren
    diska ili prazno ime daju besmislene putanje (`..staging` u samom korenu),
    a ažuriranje korena diska bi premeštalo tuđe fajlove.

    Raises:
        ValueError: Ako `target` nema ime ili mu je roditelj on sam.
    """
    absolute = Path(os.path.abspath(target))
    if not absolute.name or absolute.parent == absolute:
        raise ValueError(
            f"Ciljni folder ćelije mora biti imenovan podfolder, ne koren diska: {target}"
        )


def _existing_cell_port(target: Path) -> int | None:
    """Port iz `cell.json` postojeće ćelije (ili iz backup-a prekinute zamene)."""

    for candidate in (target / CELL_MANIFEST_FILENAME, _backup_dir_for(target) / CELL_MANIFEST_FILENAME):
        try:
            return int(json.loads(candidate.read_text(encoding="utf-8"))["port"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def _cell_is_running(port: int) -> bool:
    """
    Da li na `127.0.0.1:<port>` nešto odgovara na `/cell/status` (1 s rok).

    Svaki HTTP odgovor (i 503) znači da proces sluša na tom portu. Proxy se
    zaobilazi — lokalna provera ne sme da ode kroz sistemski proxy.
    """
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}/cell/status", timeout=1.0):
            return True
    except urllib.error.HTTPError:
        return True
    except (OSError, ValueError):
        return False


def build_cell(
    domain_id: str,
    target: Path,
    *,
    repo_root: Path,
    port: int,
    detached_from: str,
    skipped: list[str] | None = None,
    gui_builder: GuiBuilder = build_gui_dist,
    shell_exe: Path | None = None,
    update: bool = False,
) -> CellManifest:
    """
    Sklapa folder ćelije za zadati domen.

    Args:
        domain_id: Identifikator domena, npr. `filmium`.
        target: Ciljni folder ćelije. Kad `update=False`, mora biti prazan ili
            nepostojeći. Kad `update=True`, mora već sadržati `cell.json`.
        repo_root: Koren CORE repoa iz kog se kopira.
        port: Port koji CORE dodeljuje ćeliji. Pri `update=True` se ignoriše —
            zadržava se port iz postojećeg manifesta (vidi `update` niže).
        detached_from: Kratak hash commita iz kog je ćelija izvučena/ažurirana.
        skipped: Zadržana opciona lista (kompatibilnost). Domenski runtime
            moduli se otkrivaju glob-om (`apps/api/<domen>*.py`), a
            `apps/api/dependencies.py` je obavezan — pa nema „naveden ali
            odsutan" slučaja i lista ostaje prazna. `KERNEL_PYTHON_MODULES`
            NIJE opcion: nedostatak diže `FileNotFoundError`.
        gui_builder: Pravi `gui/dist` iz sklopljenog `gui/` foldera; podrazumevano
            `build_gui_dist` (pravi Vite build). Testovi prosleđuju lažni builder
            da izbegnu pravi build u svakom pokretanju.
        update: Kad je `True`, ćelija se ponovo sklapa u PRIVREMENI folder
            (`<target roditelj>/.{target ime}.staging`, na istom disku kao
            `target`), a `target` se menja tim sadržajem TEK kad je sklapanje
            u potpunosti uspelo (Python deo, GUI zatvorenje, `public/`, Vite
            build — vidi `_assemble_cell_contents`). Sama zamena
            (`_swap_staged_cell`) ide PREMEŠTANJEM u susedni backup folder
            (`<target roditelj>/.{target ime}.old`), nikad brisanjem, dok se
            ne zna da je uspela — ako bilo šta u zameni pukne (npr. zaključan
            fajl), sve što je već premešteno se vrati nazad i `target` ostaje
            BAJT-ZA-BAJT onakav kakav je bio pre poziva; `staging` ostaje za
            sledeći pokušaj. Ako proces bude ugašen NASRED zamene (posle
            backup-a, pre nego što sama zamena stigne da se vrati), sledeći
            poziv sa `update=True` prvo oporavlja iz backup foldera (vidi
            `_recover_backup_before_update`) pre bilo čega drugog. Menjaju se
            SAMO putanje iz `generated_on_update(...)`; `data`, `config`, ostatak
            `.ai/`, `.git`, `gui/node_modules` i sve ostalo ostaje na mestu.
            `port`, `core_url`, `ai` i `rag` se zadržavaju iz postojećeg
            `cell.json`; `detached_from`, `kernel_version` i `created_at`
            postaju novi. `config/tmdb.json` se NIKAD ne prepisuje ako već
            postoji — korisnikova prava TMDB tajna se ne sme izgubiti.
            Ostatak staging foldera iz prethodnog prekinutog pokušaja
            ažuriranja se ukloni pre novog pokušaja. Ažuriranje se odbija dok
            ćelija radi (odgovara na `/cell/status` na svom portu).

    Returns:
        Manifest sklopljene ćelije.

    Raises:
        FileExistsError: Ako `update=False` i ciljni folder postoji i nije prazan.
        FileNotFoundError: Ako `update=True` a folder nema `cell.json` (folder
            ostaje netaknut); ako neki modul iz `KERNEL_PYTHON_MODULES` ne
            postoji u repou; ako `apps/api/dependencies.py` ili
            `apps/gui/public` ne postoje u repou; ili ako GUI build ne napravi
            `gui/dist/index.html`. Pri `update=True`, `target` ostaje netaknut
            u svim ovim slučajevima.
        ValueError: Ako `target` nema ime ili je koren diska; ako GUI zatvorenje
            vuče CORE-only module ili kopija GUI izvora nije samodovoljna
            (isto, `target` ostaje netaknut pri `update=True`).
        RuntimeError: Ako ćelija radi dok se ažurira; ili ako oporavak od
            prekinute zamene (`_recover_backup_before_update`) nailazi na istu
            putanju i u `target`-u i u backup folderu — ništa se ne dira,
            korisnik mora ručno da odluči koja verzija ostaje.
    """
    _validate_target(target)

    # Prozor aplikacije: podrazumevano iz repoa (`repo_root / CELL_SHELL_EXE`).
    # Proverava se PRE diranja diska — nedostajući exe ne sme da obori radnu
    # ćeliju pri `--update`, ni da ostavi polu-sklopljen `target` pri sklapanju.
    if shell_exe is None:
        shell_exe = repo_root / CELL_SHELL_EXE
    if not shell_exe.is_file():
        raise FileNotFoundError(
            f"Prozor aplikacije ćelije ne postoji: {shell_exe}. "
            "Napravi ga u apps/cell-shell: `cargo build --release`."
        )
    exe_name = cell_exe_name(domain_id.upper())
    # Dodatni paketi domena (po-domenski, iz `cell_extra.py`) — potrebni i za
    # kopiranje u staging i za politiku `--update` (koreni tih paketa).
    extra_packages = domain_extra_packages(domain_id)

    if update:
        # Pre bilo kakvog diranja diska: pokrenuta ćelija drži fajlove
        # zaključane i menjala bi kod ispod sebe.
        running_port = _existing_cell_port(target)
        if running_port is not None and _cell_is_running(running_port):
            raise RuntimeError(
                f"Ćelija u {target} radi (odgovara na http://127.0.0.1:{running_port}/cell/status). "
                "Zaustavi je (zatvori prozor start.bat) pa pokreni ažuriranje ponovo."
            )

        # Zatim, pre svega ostalog: ako je proces prošli put ugašen NASRED
        # zamene, `target` možda NEMA `cell.json` (već je u backup folderu).
        _recover_backup_before_update(target, exe_name, extra_packages)

        manifest_path = target / CELL_MANIFEST_FILENAME
        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"Ažuriranje traži postojeću ćeliju: nema {CELL_MANIFEST_FILENAME} u {target}"
            )
        existing_manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Staging je UVEK sused `target`-a (isti disk, isti roditeljski
        # folder) — premeštanja u `_swap_staged_cell` su onda preimenovanja,
        # ne kopiranja preko particija.
        staging = target.parent / f".{target.name}.staging"
        if staging.exists():
            # Ostatak iz prethodnog prekinutog pokušaja ažuriranja.
            _remove_path(staging)

        try:
            _assemble_cell_contents(
                domain_id,
                staging,
                repo_root=repo_root,
                port=port,
                detached_from=detached_from,
                skipped=skipped,
                gui_builder=gui_builder,
                existing_manifest_data=existing_manifest_data,
                shell_exe=shell_exe,
                exe_name=exe_name,
                extra_packages=extra_packages,
            )
            # Poslednja provera PRE zamene: ako sklopljeni staging ima uvoz
            # ka paketu koji postoji u repou a ne u samoj ćeliji (npr. neki
            # budući router lenjo uveze novi top-level paket koji niko nije
            # prijavio u domenskom `cell_extra.py`), ažuriranje nikad ne sme da
            # tim kodom zameni radnu ćeliju.
            unresolved = find_unresolved_local_imports(staging, repo_root)
            if unresolved:
                raise ValueError(
                    "Sklopljena ćelija (staging) ima nerazrešene lokalne "
                    "uvoze — ažuriranje je zaustavljeno PRE zamene, target "
                    "ostaje netaknut:\n" + "\n".join(unresolved)
                )
        except BaseException:
            if staging.exists():
                _remove_path(staging)
            raise

        # `_swap_staged_cell` sam uklanja i backup i `staging` na uspeh (i
        # ostavlja `staging` netaknut da bi se izuzetak ispod mogao prosledi-
        # ti dalje ako zamena sama pukne — vidi njen docstring).
        _swap_staged_cell(target, staging, exe_name, extra_packages)
    else:
        if target.exists() and any(target.iterdir()):
            raise FileExistsError(f"Ciljni folder nije prazan: {target}")

        _assemble_cell_contents(
            domain_id,
            target,
            repo_root=repo_root,
            port=port,
            detached_from=detached_from,
            skipped=skipped,
            gui_builder=gui_builder,
            existing_manifest_data=None,
            shell_exe=shell_exe,
            exe_name=exe_name,
            extra_packages=extra_packages,
        )

    return load_cell_manifest(target)
















