# ========== SQL SLOJ REPOZITORIJUMA ==========
# Samo citanje i pisanje redova. Poslovna logika, kapija i dnevnik su u
# servisu — ovde ih namerno nema.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.repositories.models import Repository
from core.domains.codium.runtime import codium_database_path

_KOLONE = ("id, project_id, name, local_path, remote_url, default_branch, "
           "provider, last_synced_at, created_at, updated_at")


def _od_reda(row) -> Repository:
    return Repository(
        id=row[0], project_id=row[1], name=row[2], local_path=row[3],
        remote_url=row[4], default_branch=row[5], provider=row[6],
        last_synced_at=row[7], created_at=row[8], updated_at=row[9],
    )


class RepositoryRepository:
    """Perzistencija registra repozitorijuma."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, repo: Repository) -> Repository:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_repositories (project_id, name, "
                "local_path, remote_url, default_branch, provider) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (repo.project_id, repo.name, repo.local_path, repo.remote_url,
                 repo.default_branch, repo.provider),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self, project_id: int | None = None) -> list[Repository]:
        uslov = " WHERE project_id = ?" if project_id is not None else ""
        parametri = (project_id,) if project_id is not None else ()
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE} FROM codium_repositories{uslov} ORDER BY id",
                parametri,
            ).fetchall()
        return [_od_reda(red) for red in redovi]

    def get(self, repo_id: int) -> Repository | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE} FROM codium_repositories WHERE id = ?",
                (repo_id,),
            ).fetchone()
        return _od_reda(red) if red else None

    def get_by_path(self, local_path: str) -> Repository | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE} FROM codium_repositories WHERE local_path = ?",
                (local_path,),
            ).fetchone()
        return _od_reda(red) if red else None

    def delete(self, repo_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute("DELETE FROM codium_repositories WHERE id = ?",
                         (repo_id,))

    def mark_synced(self, repo_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_repositories SET last_synced_at = "
                "CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (repo_id,),
            )
