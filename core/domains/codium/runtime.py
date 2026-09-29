# ========== RUNTIME CODIUM ==========
# Zasebna CODIUM baza (odvojena od core.db) i njena inicijalizacija.
from pathlib import Path

from core.database.connection import core_database_connection
from core.database.migrations import apply_database_migrations
from core.domains.codium.migrations import CODIUM_MIGRATIONS
from core.domains.codium.ops_migrations import CODIUM_OPS_MIGRATIONS
from core.domains.codium.paths import codium_paths


def codium_database_path() -> Path:
    """Podrazumevana putanja CODIUM baze."""

    return codium_paths.database


def initialize_codium_database(database_path: Path | None = None) -> None:
    """
    Inicijalizuje CODIUM bazu i primenjuje sve registrovane migracije.

    Baza je namerno odvojena od core.db — CODIUM je samostalan domen.
    Ponovno pokretanje ne pravi štetu (migracije su idempotentne).

    Args:
        database_path: Opciona putanja baze, prvenstveno namenjena testovima.
    """
    target = database_path or codium_database_path()
    with core_database_connection(target) as connection:
        apply_database_migrations(connection, CODIUM_MIGRATIONS)


def codium_ops_database_path() -> Path:
    """Podrazumevana putanja operativne CODIUM baze."""

    return codium_paths.ops_database


def initialize_codium_ops_database(database_path: Path | None = None) -> None:
    """
    Inicijalizuje operativnu CODIUM bazu i primenjuje njene migracije.

    Ova baza je odvojena i od core.db i od poslovne codium.db: evidencija
    poziva modela raste sa svakim pozivom, a poslovna baza se bekapuje i
    zaključava. Zato ops migracije nose sopstveno brojanje verzija
    (scope="codium_ops").

    Args:
        database_path: Opciona putanja baze, prvenstveno namenjena testovima.
    """
    target = database_path or codium_ops_database_path()
    with core_database_connection(target) as connection:
        apply_database_migrations(connection, CODIUM_OPS_MIGRATIONS)
