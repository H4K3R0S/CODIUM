"""CODIUM migracije v1–v8 — izdvojeno iz migrations.py radi veličine."""

from core.database import DatabaseMigration

# ---------- v1: osnovne tabele ----------

CODIUM_MIGRATION_V1 = DatabaseMigration(
    scope="codium",
    version=1,
    name="create_core_tables",
    statements=(
        # Klijent se pravi pre projekta (projekat referiše client_id).
        """
        CREATE TABLE codium_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company_name TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT '',
            email TEXT,
            phone TEXT,
            website TEXT,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE codium_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT '',
            visibility TEXT NOT NULL DEFAULT 'private'
                CHECK (visibility IN ('client', 'private')),
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'paused', 'done', 'archived')),
            local_path TEXT,
            project_brain_path TEXT,
            client_id INTEGER
                REFERENCES codium_clients (id) ON DELETE SET NULL,
            repository_url TEXT,
            live_url TEXT,
            staging_url TEXT,
            preview_url TEXT,
            stack TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
            started_at TEXT,
            deadline_at TEXT,
            last_opened_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE codium_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER
                REFERENCES codium_projects (id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo'
                CHECK (status IN ('todo', 'in_progress', 'done', 'blocked')),
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
            due_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE codium_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER
                REFERENCES codium_projects (id) ON DELETE SET NULL,
            client_id INTEGER
                REFERENCES codium_clients (id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'manual'
                CHECK (source IN ('manual', 'chat', 'ai', 'email',
                                  'preview', 'task', 'roadmap', 'meeting')),
            importance TEXT NOT NULL DEFAULT 'normal'
                CHECK (importance IN ('low', 'normal', 'high', 'urgent')),
            tags TEXT NOT NULL DEFAULT '',
            reminder_at TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'done', 'archived')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX idx_codium_tasks_project ON codium_tasks (project_id)",
        "CREATE INDEX idx_codium_notes_project ON codium_notes (project_id)",
        "CREATE INDEX idx_codium_notes_client ON codium_notes (client_id)",
    ),
)


# ---------- v2: lokalni dev server (auto host) ----------

CODIUM_MIGRATION_V2 = DatabaseMigration(
    scope="codium",
    version=2,
    name="add_dev_server_fields",
    statements=(
        # Komanda kojom projekat diže lokalni host (npr. "npm run dev").
        "ALTER TABLE codium_projects ADD COLUMN dev_command TEXT NOT NULL DEFAULT ''",
        # Port lokalnog hosta; iz njega se izvodi preview URL (localhost:port).
        "ALTER TABLE codium_projects ADD COLUMN dev_port INTEGER",
    ),
)


# ---------- v3: zapamćen izbor modela (Faza 1 AI provajdera) ----------

CODIUM_MIGRATION_V3 = DatabaseMigration(
    scope="codium",
    version=3,
    name="create_model_prefs",
    statements=(
        """
        CREATE TABLE codium_model_prefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES codium_projects (id) ON DELETE CASCADE,
            persona TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL,
            provider TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # COALESCE u indeksu: u SQLite-u su dve NULL vrednosti RAZLIČITE za
        # UNIQUE, pa bi obican UNIQUE (project_id, persona) dozvolio vise
        # redova za isti par (NULL, 'architect').
        ("CREATE UNIQUE INDEX idx_codium_model_prefs "
        "ON codium_model_prefs (COALESCE(project_id, 0), persona)"),
    ),
)


# ---------- v4: konektori (Faza 2 AI provajdera) ----------
# NAPUSTENA: konektori su preseljeni u core.db (`core_connectors`, scope
# "core_ai"), jer su API kljucevi CORE postavka koju dele svi domeni. Tabela
# ostaje u semi da migracija v4 ne bi menjala smisao kod postojecih baza —
# nista je vise ne cita. Brisanje ide u zaseban korak, kad se potvrdi da
# nijedna instalacija nema podatke u njoj.

CODIUM_MIGRATION_V4 = DatabaseMigration(
    scope="codium",
    version=4,
    name="create_connectors",
    statements=(
        # secret_alias je KLJUC u vault-u, nikad vrednost tajne.
        # config_json je slobodna NE-tajna konfiguracija (base_url, model,
        # timeout...) — pozivalac ne sme tu upisati vrednost tajne, tu
        # dužnost ne izvršava baza vec sloj iznad (Task 6: ConnectorService).
        """
        CREATE TABLE codium_connectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            secret_alias TEXT,
            status TEXT NOT NULL DEFAULT 'unconfigured',
            last_tested_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE UNIQUE INDEX idx_codium_connectors_name "
        "ON codium_connectors (name)"),
    ),
)


# ---------- v5: iskljuceni modeli (CODIUM podesavanja) ----------

CODIUM_MIGRATION_V5 = DatabaseMigration(
    scope="codium",
    version=5,
    name="create_model_visibility",
    statements=(
        # DENY lista, ne allow: novi model koji se pojavi u Ollami ili kod
        # provajdera je odmah upotrebljiv, bez ijednog upisa. Allow lista bi
        # svaki nov model sakrila dok ga korisnik rucno ne odobri.
        """
        CREATE TABLE codium_model_visibility (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Par (provajder, model) mora biti jedinstven: bez toga bi dvostruko
        # iskljucivanje napravilo dva reda, a ponovno ukljucivanje obrisalo
        # samo jedan — model bi ostao nevidljiv bez ikakvog objasnjenja.
        ("CREATE UNIQUE INDEX idx_codium_model_visibility "
        "ON codium_model_visibility (provider, model)"),
    ),
)


# ---------- v6: pravila dozvola (ScopeGate) ----------

CODIUM_MIGRATION_V6 = DatabaseMigration(
    scope="codium",
    version=6,
    name="create_scope_rules",
    statements=(
        # Pravila su poslovni podatak: malo ih je, retko se menjaju, i idu u
        # bekap zajedno sa projektima. Zato stoje ovde, a ne u ops bazi.
        #
        # CHECK nad verdiktom je namerno u semi: pogresna vrednost bi inace
        # tiho prosla i gate bi je vratio kao nepoznat verdikt.
        """
        CREATE TABLE codium_scope_rules (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            actor      TEXT NOT NULL,
            action     TEXT NOT NULL,
            target     TEXT NOT NULL DEFAULT '*',
            verdict    TEXT NOT NULL
                       CHECK (verdict IN ('allow','deny','needs_approval')),
            note       TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE INDEX idx_codium_scope_rules_actor "
        "ON codium_scope_rules (actor, action)"),
    ),
)


# ---------- v7: red odobrenja ----------

CODIUM_MIGRATION_V7 = DatabaseMigration(
    scope="codium",
    version=7,
    name="create_approvals",
    statements=(
        # Tabela je namerno genericna: nosi aktera, akciju i payload, a ne zna
        # ko trazi. Vezu drzi trazilac (agent, automatizacija), pa nova vrsta
        # trazioca ne trazi novu kolonu.
        #
        # Status `expired` stoji u skupu ali ga prvi rez ne postavlja — nema
        # roka trajanja molbe. Skup je tu da kasniji posao odrzavanja ne trazi
        # izmenu seme.
        """
        CREATE TABLE codium_approvals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            actor        TEXT NOT NULL,
            action       TEXT NOT NULL,
            target       TEXT NOT NULL DEFAULT '',
            payload      TEXT NOT NULL DEFAULT '',
            status       TEXT NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','approved',
                                           'rejected','expired')),
            note         TEXT NOT NULL DEFAULT '',
            requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            decided_at   TEXT
        )
        """,
        ("CREATE INDEX idx_codium_approvals_status "
        "ON codium_approvals (status, requested_at)"),
    ),
)


# ---------- v8: agenti, njihovi poslovi i koraci ----------

CODIUM_MIGRATION_V8 = DatabaseMigration(
    scope="codium",
    version=8,
    name="create_agents",
    statements=(
        # Agent je red, ne klasa: dodavanje agenta je unos u tabelu, a nov kod
        # treba samo za nov alat.
        """
        CREATE TABLE codium_agents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            slug          TEXT NOT NULL UNIQUE,
            name          TEXT NOT NULL,
            description   TEXT NOT NULL DEFAULT '',
            system_prompt TEXT NOT NULL DEFAULT '',
            model         TEXT NOT NULL DEFAULT '',
            provider      TEXT NOT NULL DEFAULT '',
            tools_json    TEXT NOT NULL DEFAULT '[]',
            max_steps     INTEGER NOT NULL DEFAULT 12,
            enabled       INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Prazan `model` i `provider` znace „koristi ono sto bi chat koristio" —
        # nasledjivanje kroz ModelRouter, ne greska.
        """
        INSERT INTO codium_agents (slug, name, description, system_prompt)
        VALUES (
            'architect',
            'Architect',
            'Cita kod, analizira i predlaze plan izmene. Ne izvrsava.',
            'Ti si ARCHITECT, agent koji analizira postojeci kod i predlaze '
            || 'plan izmene. Citas fajlove, trazis obrasce i pises predlog. '
            || 'Ne menjas stanje bez potrebe; kad ti treba izmena, trazi je '
            || 'alatom i cekaj odluku coveka.'
        )
        """,
        """
        CREATE TABLE codium_agent_runs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id            INTEGER NOT NULL
                                REFERENCES codium_agents (id) ON DELETE CASCADE,
            project_id          INTEGER
                                REFERENCES codium_projects (id)
                                ON DELETE SET NULL,
            task                TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'running'
                                CHECK (status IN ('running','waiting_approval',
                                                  'done','failed','cancelled')),
            result              TEXT NOT NULL DEFAULT '',
            steps_used          INTEGER NOT NULL DEFAULT 0,
            cost_usd            REAL NOT NULL DEFAULT 0,
            pending_approval_id INTEGER,
            started_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at         TEXT
        )
        """,
        ("CREATE INDEX idx_codium_agent_runs_agent "
        "ON codium_agent_runs (agent_id, id DESC)"),
        # Korak se samo dopisuje. Petlja koja se ne moze procitati unazad je
        # petlja kojoj se ne moze verovati.
        """
        CREATE TABLE codium_agent_steps (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id  INTEGER NOT NULL
                    REFERENCES codium_agent_runs (id) ON DELETE CASCADE,
            idx     INTEGER NOT NULL,
            kind    TEXT NOT NULL,
            tool    TEXT,
            payload TEXT NOT NULL DEFAULT '',
            at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE INDEX idx_codium_agent_steps_run "
        "ON codium_agent_steps (run_id, idx)"),
    ),
)
