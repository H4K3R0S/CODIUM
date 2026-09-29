# ========== MIGRACIJE CODIUM ==========
# Šema zasebne CODIUM baze: 4 tabele (projekat, klijent, task, beleška).
# Razdvojeno na v1–v8 / v9–v15 module radi veličine (public API nepromenjen).

from core.domains.codium.migrations_v1_v8 import (
    CODIUM_MIGRATION_V1,
    CODIUM_MIGRATION_V2,
    CODIUM_MIGRATION_V3,
    CODIUM_MIGRATION_V4,
    CODIUM_MIGRATION_V5,
    CODIUM_MIGRATION_V6,
    CODIUM_MIGRATION_V7,
    CODIUM_MIGRATION_V8,
)
from core.domains.codium.migrations_v9_v15 import (
    CODIUM_MIGRATION_V9,
    CODIUM_MIGRATION_V10,
    CODIUM_MIGRATION_V11,
    CODIUM_MIGRATION_V12,
    CODIUM_MIGRATION_V13,
    CODIUM_MIGRATION_V14,
    CODIUM_MIGRATION_V15,
)

CODIUM_MIGRATIONS = (
    CODIUM_MIGRATION_V1,
    CODIUM_MIGRATION_V2,
    CODIUM_MIGRATION_V3,
    CODIUM_MIGRATION_V4,
    CODIUM_MIGRATION_V5,
    CODIUM_MIGRATION_V6,
    CODIUM_MIGRATION_V7,
    CODIUM_MIGRATION_V8,
    CODIUM_MIGRATION_V9,
    CODIUM_MIGRATION_V10,
    CODIUM_MIGRATION_V11,
    CODIUM_MIGRATION_V12,
    CODIUM_MIGRATION_V13,
    CODIUM_MIGRATION_V14,
    CODIUM_MIGRATION_V15,
)


# Dodatne baze CODIUM ćelije (pored glavne `codium.db`): operativna
# `codium_ops.db` sa sopstvenim brojanjem verzija (scope="codium_ops"). Ćelijski
# okvir (`core/cell/database.py::domain_extra_databases`) je čita po ovoj
# konvenciji i pravi u `data_dir/codium_ops.db`. CORE i dalje koristi
# `core/domains/codium/runtime.py` (initialize_codium_ops_database).
from core.domains.codium.ops_migrations import CODIUM_OPS_MIGRATIONS

CODIUM_EXTRA_DATABASES = (
    ("codium_ops.db", CODIUM_OPS_MIGRATIONS),
)
