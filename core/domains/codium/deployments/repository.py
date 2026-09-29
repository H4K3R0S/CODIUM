# ========== SQL SLOJ ISPORUKE ==========
# Samo citanje i pisanje redova. Poslovna logika, kapija i dnevnik su u
# servisu — ovde ih namerno nema.
from __future__ import annotations

import json
from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.deployments.models import (
    Deployment,
    DeployStatus,
    DeployTarget,
)
from core.domains.codium.runtime import codium_database_path

_KOLONE_CILJ = ("id, project_id, name, kind, config_json, connector_id, "
                "enabled, created_at, updated_at")
_KOLONE_ISPORUKA = ("id, target_id, run_id, commit_sha, status, release_ref, "
                    "detail, started_at, finished_at, created_at")


def _config(sirovo: str) -> dict[str, str]:
    """Cita `config_json`. Krnj JSON u bazi ne sme da obori citanje liste."""

    try:
        vrednost = json.loads(sirovo or "{}")
    except json.JSONDecodeError:
        return {}
    return vrednost if isinstance(vrednost, dict) else {}


def _cilj_od_reda(row) -> DeployTarget:
    return DeployTarget(
        id=row[0], project_id=row[1], name=row[2], kind=row[3],
        config=_config(row[4]), connector_id=row[5], enabled=bool(row[6]),
        created_at=row[7], updated_at=row[8],
    )


def _isporuka_od_reda(row) -> Deployment:
    return Deployment(
        id=row[0], target_id=row[1], run_id=row[2], commit_sha=row[3],
        status=row[4], release_ref=row[5], detail=row[6],
        started_at=row[7], finished_at=row[8], created_at=row[9],
    )


class DeployTargetRepository:
    """Perzistencija ciljeva isporuke."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, target: DeployTarget) -> DeployTarget:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_deploy_targets (project_id, name, kind, "
                "config_json, connector_id, enabled) VALUES (?, ?, ?, ?, ?, ?)",
                (target.project_id, target.name, str(target.kind),
                 json.dumps(target.config), target.connector_id,
                 int(target.enabled)),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self, project_id: int | None = None) -> list[DeployTarget]:
        uslov = " WHERE project_id = ?" if project_id is not None else ""
        parametri = (project_id,) if project_id is not None else ()
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_CILJ} FROM codium_deploy_targets{uslov} "
                "ORDER BY id",
                parametri,
            ).fetchall()
        return [_cilj_od_reda(red) for red in redovi]

    def get(self, target_id: int) -> DeployTarget | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_CILJ} FROM codium_deploy_targets WHERE id = ?",
                (target_id,),
            ).fetchone()
        return _cilj_od_reda(red) if red else None

    def update(self, target_id: int, *, name: str, config: dict[str, str],
               enabled: bool) -> DeployTarget | None:
        """Menja ono sto sme da se menja.

        `kind` nije u listi namerno: promena tipa bi ostavila istoriju
        isporuka koje je pravio sasvim drugi provider, a arhiva i oznake
        slika iz nje vise ne bi znacile nista.
        """

        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_deploy_targets SET name = ?, config_json = ?, "
                "enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, json.dumps(config), int(enabled), target_id),
            )
        return self.get(target_id)

    def delete(self, target_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute("DELETE FROM codium_deploy_targets WHERE id = ?",
                         (target_id,))


class DeploymentRepository:
    """Perzistencija samih isporuka."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def create(self, deployment: Deployment) -> Deployment:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_deployments (target_id, run_id, "
                "commit_sha, status, detail) VALUES (?, ?, ?, ?, ?)",
                (deployment.target_id, deployment.run_id, deployment.commit_sha,
                 str(deployment.status), deployment.detail),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def get(self, deployment_id: int) -> Deployment | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_ISPORUKA} FROM codium_deployments WHERE id = ?",
                (deployment_id,),
            ).fetchone()
        return _isporuka_od_reda(red) if red else None

    def list(self, target_id: int | None = None,
             limit: int = 50) -> list[Deployment]:
        uslov = " WHERE target_id = ?" if target_id is not None else ""
        parametri = ((target_id, limit) if target_id is not None else (limit,))
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_ISPORUKA} FROM codium_deployments{uslov} "
                "ORDER BY id DESC LIMIT ?",
                parametri,
            ).fetchall()
        return [_isporuka_od_reda(red) for red in redovi]

    def current(self, target_id: int) -> Deployment | None:
        """Poslednja uspesna isporuka na cilj — ono sto tamo sada stoji."""

        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_ISPORUKA} FROM codium_deployments "
                "WHERE target_id = ? AND status = ? ORDER BY id DESC LIMIT 1",
                (target_id, str(DeployStatus.SUCCESS)),
            ).fetchone()
        return _isporuka_od_reda(red) if red else None

    def mark_started(self, deployment_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_deployments SET status = ?, "
                "started_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(DeployStatus.RUNNING), deployment_id),
            )

    def mark_finished(self, deployment_id: int, status: str,
                      release_ref: str | None = None,
                      detail: str = "") -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_deployments SET status = ?, release_ref = ?, "
                "detail = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, release_ref, detail, deployment_id),
            )

    def mark_rolled_back(self, deployment_id: int) -> None:
        """Isporuka koja vise ne stoji na cilju, jer je nesto vraceno preko nje."""

        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_deployments SET status = ? WHERE id = ?",
                (str(DeployStatus.ROLLED_BACK), deployment_id),
            )
