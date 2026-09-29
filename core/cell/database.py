"""Inicijalizacija baze ćelije.

Ćelija primenjuje samo migracije svog domena. CORE migracije (konektori,
vidljivost modela) ostaju u CORE bazi i nikad ne ulaze u ćeliju.

Migracije se učitavaju GENERIČKI, po konvenciji — bez ijednog domenskog imena
u okviru: svaki domen izloži svoj skup u
`core/domains/<domen>/migrations.py::<DOMEN>_MIGRATIONS` (npr.
`KALIMA_MIGRATIONS`, `CODIUM_MIGRATIONS`, `FILMIUM_MIGRATIONS`). Domen bez
migracija (nema modul ili atribut) dobija praznu bazu — to je legitimno
(npr. KALIMA drži stanje na fajl-sistemu, ne u bazi).
"""

from __future__ import annotations

import importlib

from core.cell.manifest import CellManifest
from core.database.connection import core_database_connection
from core.database.migrations import DatabaseMigration, apply_database_migrations


def _domain_migrations_module(domain_id: str):
    """Modul `core.domains.<domen>.migrations`, ili `None` ako ne postoji."""

    try:
        return importlib.import_module(f"core.domains.{domain_id}.migrations")
    except ModuleNotFoundError:
        return None


def domain_migrations(domain_id: str) -> tuple[DatabaseMigration, ...]:
    """
    Migracije domena po konvenciji `core/domains/<domen>/migrations.py::<DOMEN>_MIGRATIONS`.

    Ako modul `migrations` ne postoji ili nema očekivani atribut, domen nema
    migracije ćelije i vraća se prazan skup (baza se svejedno napravi, prazna).
    Ime atributa je `<DOMEN>_MIGRATIONS` velikim slovima (isti obrazac koji
    CODIUM/FILMIUM već koriste u svojim `runtime`-ima).

    Args:
        domain_id: Identifikator domena, npr. `kalima`.

    Returns:
        Skup migracija domena, ili prazan skup ako ih domen nema.
    """
    module = _domain_migrations_module(domain_id)
    if module is None:
        return ()

    migrations = getattr(module, f"{domain_id.upper()}_MIGRATIONS", None)
    if migrations is None:
        return ()
    return tuple(migrations)


def domain_extra_databases(
    domain_id: str,
) -> tuple[tuple[str, tuple[DatabaseMigration, ...]], ...]:
    """
    Dodatne baze domena pored glavne (`manifest.database_path`), po konvenciji
    `core/domains/<domen>/migrations.py::<DOMEN>_EXTRA_DATABASES`.

    Neki domeni drže više SQLite baza (npr. CODIUM: poslovna `codium.db` +
    operativna `codium_ops.db` sa sopstvenim brojanjem verzija). Atribut je
    tuple parova `(ime_fajla, migracije)`; svaka baza se pravi u
    `manifest.data_dir/<ime_fajla>`. Domen bez tog atributa nema dodatnih baza.

    Args:
        domain_id: Identifikator domena.

    Returns:
        Tuple `(ime_fajla, migracije)` parova; prazan ako ih domen nema.
    """
    module = _domain_migrations_module(domain_id)
    if module is None:
        return ()

    extra = getattr(module, f"{domain_id.upper()}_EXTRA_DATABASES", None)
    if extra is None:
        return ()
    return tuple((str(name), tuple(migrations)) for name, migrations in extra)


def initialize_cell_database(manifest: CellManifest) -> None:
    """
    Gradi ili dopunjuje baze ćelije migracijama njenog domena.

    Glavna baza (`manifest.database_path`) dobija `<DOMEN>_MIGRATIONS`; svaka
    dodatna baza iz `domain_extra_databases` se pravi u `manifest.data_dir` sa
    svojim migracijama. Sve migracije su idempotentne — ponovni poziv ne šteti.

    Args:
        manifest: Učitan manifest ćelije.
    """
    manifest.data_dir.mkdir(parents=True, exist_ok=True)

    with core_database_connection(manifest.database_path) as connection:
        apply_database_migrations(connection, domain_migrations(manifest.domain_id))

    for filename, migrations in domain_extra_databases(manifest.domain_id):
        with core_database_connection(manifest.data_dir / filename) as connection:
            apply_database_migrations(connection, migrations)
