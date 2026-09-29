"""CODIUM migracije v9–v15 — izdvojeno iz migrations.py radi veličine."""

from core.database import DatabaseMigration

# ---------- v9: agent za online model trazi odobrenje ----------

CODIUM_MIGRATION_V9 = DatabaseMigration(
    scope="codium",
    version=9,
    name="agent_online_needs_approval",
    statements=(
        # Podrazumevani glagol `call_online` je u `ScopeGate` namerno `allow`
        # (gate ne sme da obori postojeci chat u trenutku spajanja). Za agenta
        # to ne vazi: on trosi novac bez coveka za tastaturom, pa mu treba
        # izricito pravilo. Covek i dalje prolazi — `human` zaobilazi kapiju.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'ai.call_online', '*', 'needs_approval',
                'online poziv trosi novac — covek odobrava')
        """,
    ),
)


# ---------- v10: registar repozitorijuma ----------

CODIUM_MIGRATION_V10 = DatabaseMigration(
    scope="codium",
    version=10,
    name="repositories",
    statements=(
        # Repozitorijum nije projekat: jedan projekat sme dva repozitorijuma,
        # a repozitorijum sme da stoji bez projekta.
        """
        CREATE TABLE codium_repositories (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id     INTEGER REFERENCES codium_projects (id)
                           ON DELETE SET NULL,
            name           TEXT NOT NULL,
            local_path     TEXT NOT NULL,
            remote_url     TEXT,
            default_branch TEXT NOT NULL DEFAULT 'main',
            provider       TEXT NOT NULL DEFAULT 'local_git',
            last_synced_at TEXT,
            created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE UNIQUE INDEX idx_codium_repos_path "
        "ON codium_repositories (local_path)"),
        # `ScopeGate` nepoznat glagol odbija, a `fetch` i `register` su
        # nepoznati. Pravila stoje ovde, a ne u `_DEFAULTS` CORE kapije:
        # `fetch` je git pojam, ne CORE glagol.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'repo.fetch', '*', 'needs_approval',
                'fetch ide na mrezu — covek odobrava')
        """,
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'repo.register', '*', 'deny',
                'registar repozitorijuma je covekova odluka')
        """,
    ),
)



# ---------- v11: pipeline-i, pokretanja i koraci ----------

CODIUM_MIGRATION_V11 = DatabaseMigration(
    scope="codium",
    version=11,
    name="pipelines",
    statements=(
        """
        CREATE TABLE codium_pipelines (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            repository_id INTEGER NOT NULL
                          REFERENCES codium_repositories (id) ON DELETE CASCADE,
            name          TEXT NOT NULL,
            definition    TEXT NOT NULL,
            enabled       INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # `detail` nosi zasto je pokretanje zavrsilo bas tako. Bez njega se
        # „istek" i „aplikacija zatvorena" ne razlikuju od obicnog pada.
        """
        CREATE TABLE codium_pipeline_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_id INTEGER NOT NULL
                        REFERENCES codium_pipelines (id) ON DELETE CASCADE,
            status      TEXT NOT NULL DEFAULT 'queued',
            trigger     TEXT NOT NULL DEFAULT 'manual',
            commit_sha  TEXT,
            branch      TEXT,
            exit_code   INTEGER,
            detail      TEXT NOT NULL DEFAULT '',
            started_at  TEXT,
            finished_at TEXT,
            created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE INDEX idx_codium_runs_pipeline "
        "ON codium_pipeline_runs (pipeline_id, id DESC)"),
        """
        CREATE TABLE codium_run_steps (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL
                        REFERENCES codium_pipeline_runs (id) ON DELETE CASCADE,
            idx         INTEGER NOT NULL,
            name        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'queued',
            exit_code   INTEGER,
            started_at  TEXT,
            finished_at TEXT
        )
        """,
        "CREATE INDEX idx_codium_run_steps_run ON codium_run_steps (run_id, idx)",
        # Glagol `run` i inace pada na needs_approval u `_DEFAULTS`, ali
        # izricito pravilo nosi razlog u dnevniku umesto „podrazumevano".
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'pipeline.run', '*', 'needs_approval',
                'agent pokrece tudje komande — covek odobrava')
        """,
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'pipeline.write', '*', 'deny',
                'definiciju pipeline-a pise covek')
        """,
    ),
)


# ---------- v12: ciljevi isporuke i isporuke ----------

CODIUM_MIGRATION_V12 = DatabaseMigration(
    scope="codium",
    version=12,
    name="deployments",
    statements=(
        """
        CREATE TABLE codium_deploy_targets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id   INTEGER REFERENCES codium_projects (id)
                         ON DELETE SET NULL,
            name         TEXT NOT NULL,
            kind         TEXT NOT NULL,
            config_json  TEXT NOT NULL DEFAULT '{}',
            connector_id INTEGER REFERENCES codium_connectors (id)
                         ON DELETE SET NULL,
            enabled      INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE codium_deployments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id   INTEGER NOT NULL
                        REFERENCES codium_deploy_targets (id) ON DELETE CASCADE,
            run_id      INTEGER REFERENCES codium_pipeline_runs (id)
                        ON DELETE SET NULL,
            commit_sha  TEXT,
            status      TEXT NOT NULL DEFAULT 'pending',
            release_ref TEXT,
            detail      TEXT NOT NULL DEFAULT '',
            started_at  TEXT,
            finished_at TEXT,
            created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE INDEX idx_codium_deploys_target "
        "ON codium_deployments (target_id, id DESC)"),
        # Isporuka menja ono sto ljudi vide — agent sme da je zatrazi, ali je
        # covek potvrdjuje. Glagol `execute` i inace pada na needs_approval u
        # `_DEFAULTS`; izricito pravilo nosi razlog u dnevniku.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'deploy.execute', '*', 'needs_approval',
                'isporuka menja ono sto ljudi vide — covek potvrdjuje')
        """,
        # Povratak unazad je hitan potez u kvaru, ali i dalje menja isto mesto.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'deploy.rollback', '*', 'needs_approval',
                'povratak menja isporucenu verziju — covek potvrdjuje')
        """,
        # Cilj isporuke opisuje covek: gde se isporucuje nije agentska odluka.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'deploy.write', '*', 'deny',
                'cilj isporuke definise covek')
        """,
    ),
)


# ---------- v13: node-ovi i servisi ----------

CODIUM_MIGRATION_V13 = DatabaseMigration(
    scope="codium",
    version=13,
    name="infrastructure",
    statements=(
        """
        CREATE TABLE codium_infra_nodes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            kind         TEXT NOT NULL DEFAULT 'local',
            connector_id INTEGER REFERENCES codium_connectors (id)
                         ON DELETE SET NULL,
            created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE codium_infra_services (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id     INTEGER NOT NULL
                        REFERENCES codium_infra_nodes (id) ON DELETE CASCADE,
            project_id  INTEGER REFERENCES codium_projects (id)
                        ON DELETE SET NULL,
            name        TEXT NOT NULL,
            kind        TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            auto_start  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE INDEX idx_codium_infra_services_node "
        "ON codium_infra_services (node_id)"),
        # Ova masina je uvek tu — bez nje bi prvi ekran bio prazan i trazio
        # da covek upise „localhost" pre nego sto uopste nesto vidi.
        """
        INSERT INTO codium_infra_nodes (name, kind) VALUES ('localhost', 'local')
        """,
        # Gasenje i restart ruse ono sto radi, pa ih covek potvrdjuje.
        # Pokretanje ne rusi nista — ostaje na podrazumevanom za glagol.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'infra.stop', '*', 'needs_approval',
                'gasenje rusi ono sto radi — covek potvrdjuje')
        """,
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'infra.restart', '*', 'needs_approval',
                'restart prekida ono sto radi — covek potvrdjuje')
        """,
        # Sta je servis i cime se pokrece opisuje covek.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'infra.write', '*', 'deny',
                'registar servisa vodi covek')
        """,
    ),
)


# ---------- v14: pravila alarma i alarmi ----------

CODIUM_MIGRATION_V14 = DatabaseMigration(
    scope="codium",
    version=14,
    name="monitoring_alerts",
    statements=(
        """
        CREATE TABLE codium_alert_rules (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id  INTEGER REFERENCES codium_infra_services (id)
                        ON DELETE CASCADE,
            metric      TEXT NOT NULL,
            comparison  TEXT NOT NULL CHECK (comparison IN ('<', '>', '==')),
            threshold   REAL NOT NULL,
            for_samples INTEGER NOT NULL DEFAULT 2,
            enabled     INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE codium_alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id     INTEGER NOT NULL
                        REFERENCES codium_alert_rules (id) ON DELETE CASCADE,
            state       TEXT NOT NULL DEFAULT 'firing',
            value       REAL,
            started_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT
        )
        """,
        "CREATE INDEX idx_codium_alerts_rule ON codium_alerts (rule_id, id DESC)",
        # Prag i metrika su odluka o tome sta se smatra kvarom — to pise covek.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'monitor.write', '*', 'deny',
                'sta se smatra kvarom definise covek')
        """,
    ),
)


# ---------- v15: pravila automatizacije i njihova okidanja ----------

CODIUM_MIGRATION_V15 = DatabaseMigration(
    scope="codium",
    version=15,
    name="automations",
    statements=(
        """
        CREATE TABLE codium_automation_rules (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            name               TEXT NOT NULL,
            event              TEXT NOT NULL,
            condition_expr     TEXT NOT NULL DEFAULT '',
            actions_json       TEXT NOT NULL DEFAULT '[]',
            project_id         INTEGER REFERENCES codium_projects (id)
                               ON DELETE CASCADE,
            enabled            INTEGER NOT NULL DEFAULT 1,
            rate_limit_n       INTEGER NOT NULL DEFAULT 5,
            rate_limit_seconds INTEGER NOT NULL DEFAULT 600,
            created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE INDEX idx_codium_automation_rules_event "
        "ON codium_automation_rules (event, enabled)"),
        """
        CREATE TABLE codium_automation_runs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id    INTEGER NOT NULL
                       REFERENCES codium_automation_rules (id) ON DELETE CASCADE,
            event_json TEXT NOT NULL DEFAULT '{}',
            matched    INTEGER NOT NULL DEFAULT 1,
            status     TEXT NOT NULL DEFAULT 'done',
            detail     TEXT NOT NULL DEFAULT '',
            at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ("CREATE INDEX idx_codium_automation_runs "
        "ON codium_automation_runs (rule_id, at DESC)"),
        # Sta se automatizuje pise covek. Agent sme da predlozi, ne da upise.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('agent:*', 'automation.write', '*', 'deny',
                'pravila automatizacije pise covek')
        """,
        # Automatizacija nema vise prava od agenta: isti glagoli, ista tezina.
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('automation:*', 'pipeline.run', '*', 'needs_approval',
                'automatizacija pokrece tudje komande — covek odobrava')
        """,
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('automation:*', 'deploy.execute', '*', 'needs_approval',
                'isporuka menja ono sto ljudi vide — covek potvrdjuje')
        """,
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('automation:*', 'infra.restart', '*', 'needs_approval',
                'restart prekida ono sto radi — covek potvrdjuje')
        """,
        """
        INSERT INTO codium_scope_rules (actor, action, target, verdict, note)
        VALUES ('automation:*', 'automation.write', '*', 'deny',
                'automatizacija ne pise sopstvena pravila')
        """,
    ),
)
