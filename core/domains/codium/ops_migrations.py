# ========== MIGRACIJE CODIUM OPS BAZE ==========
# Sema operativne CODIUM baze (`codium_ops.db`): evidencija poziva modela.
#
# Zasto zasebna baza: tabela `codium_ai_usage` raste sa svakim pozivom modela.
# Poslovna `codium.db` se bekapuje i zakljucava, pa operativni saobracaj tu ne
# pripada. Zato ova migracija nosi i sopstveno brojanje verzija
# (scope="codium_ops"), nezavisno od `codium.db`.
from core.database import DatabaseMigration

# ---------- v1: evidencija potrosnje ----------

CODIUM_OPS_MIGRATION_V1 = DatabaseMigration(
    scope="codium_ops",
    version=1,
    name="create_ai_usage",
    statements=(
        # `at` je CURRENT_TIMESTAMP, dakle UTC — svako filtriranje po periodu
        # mora granicu da racuna iz UTC sadasnjosti, ne iz lokalnog datuma.
        # `cost_usd` se upisuje kao broj u trenutku poziva; cene se menjaju, pa
        # bi naknadno racunanje iz tokena prepisalo istoriju.
        """
        CREATE TABLE codium_ai_usage (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            provider      TEXT NOT NULL,
            model         TEXT NOT NULL,
            project_id    INTEGER,
            persona       TEXT NOT NULL DEFAULT '',
            actor         TEXT NOT NULL DEFAULT 'human',
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd      REAL NOT NULL DEFAULT 0,
            duration_ms   INTEGER NOT NULL DEFAULT 0,
            ok            INTEGER NOT NULL DEFAULT 1
        )
        """,
        "CREATE INDEX idx_codium_ai_usage_at ON codium_ai_usage (at DESC)",
    ),
)


# ---------- v2: dnevnik akcija (audit) ----------

CODIUM_OPS_MIGRATION_V2 = DatabaseMigration(
    scope="codium_ops",
    version=2,
    name="create_audit_log",
    statements=(
        # Append-heavy: u ovu tabelu pise svaka provera dozvole. Zato je ovde,
        # uz potrosnju, a ne u poslovnoj bazi.
        #
        # `at` je CURRENT_TIMESTAMP, dakle UTC — isto kao `codium_ai_usage`.
        """
        CREATE TABLE codium_audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actor      TEXT NOT NULL,
            action     TEXT NOT NULL,
            target     TEXT NOT NULL DEFAULT '',
            verdict    TEXT NOT NULL,
            outcome    TEXT NOT NULL DEFAULT 'ok',
            detail     TEXT NOT NULL DEFAULT '',
            project_id INTEGER
        )
        """,
        "CREATE INDEX idx_codium_audit_at ON codium_audit_log (at DESC)",
        ("CREATE INDEX idx_codium_audit_actor "
        "ON codium_audit_log (actor, at DESC)"),
        ("CREATE INDEX idx_codium_audit_action "
        "ON codium_audit_log (action, at DESC)"),
    ),
)



# ---------- ops v3: log pokretanja ----------

CODIUM_OPS_MIGRATION_V3 = DatabaseMigration(
    scope="codium_ops",
    version=3,
    name="create_run_logs",
    statements=(
        # Bez stranog kljuca: `run_id` pokazuje na red u drugoj bazi.
        # Ciscenje posle brisanja pokretanja radi servis, ne kaskada.
        """
        CREATE TABLE codium_run_logs (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id   INTEGER NOT NULL,
            step_idx INTEGER NOT NULL,
            seq      INTEGER NOT NULL,
            stream   TEXT NOT NULL DEFAULT 'stdout',
            line     TEXT NOT NULL,
            at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX idx_codium_run_logs_seq ON codium_run_logs (run_id, seq)",
    ),
)


# ---------- ops v4: uzorci merenja ----------

CODIUM_OPS_MIGRATION_V4 = DatabaseMigration(
    scope="codium_ops",
    version=4,
    name="create_metric_samples",
    statements=(
        # Bez stranog kljuca: `service_id` i `node_id` pokazuju na redove u
        # drugoj bazi. Ciscenje posle brisanja servisa radi servis, ne kaskada.
        #
        # Ovo je najbrze rastuca tabela u sistemu — uzorak na 30 s za deset
        # servisa je oko 29.000 redova dnevno. Zato zivi ovde, a ne u
        # poslovnoj bazi koja se bekapuje, i zato zadrzavanje NIJE opciono.
        """
        CREATE TABLE codium_metric_samples (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER,
            node_id    INTEGER,
            metric     TEXT NOT NULL,
            value      REAL NOT NULL,
            at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE INDEX idx_codium_samples_lookup "
        "ON codium_metric_samples (service_id, metric, at DESC)"),
        "CREATE INDEX idx_codium_samples_at ON codium_metric_samples (at)",
    ),
)


CODIUM_OPS_MIGRATIONS = (
    CODIUM_OPS_MIGRATION_V1,
    CODIUM_OPS_MIGRATION_V2,
    CODIUM_OPS_MIGRATION_V3,
    CODIUM_OPS_MIGRATION_V4,
)
