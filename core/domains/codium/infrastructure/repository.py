# ========== SQL SLOJ INFRASTRUKTURE ==========
# Samo citanje i pisanje redova. Zivo stanje servisa se OVDE ne upisuje —
# ono se cita od provajdera i kesira u memoriji; istorija stanja je posao E6.
from __future__ import annotations

import json
from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.infrastructure.models import Node, Service
from core.domains.codium.runtime import codium_database_path

_KOLONE_NODE = "id, name, kind, connector_id, created_at"
_KOLONE_SERVIS = ("id, node_id, project_id, name, kind, config_json, "
                  "auto_start, created_at, updated_at")


def _config(sirovo: str) -> dict[str, str]:
    """Cita `config_json`. Krnj JSON u bazi ne sme da obori citanje liste."""

    try:
        vrednost = json.loads(sirovo or "{}")
    except json.JSONDecodeError:
        return {}
    return vrednost if isinstance(vrednost, dict) else {}


def _node_od_reda(row) -> Node:
    return Node(id=row[0], name=row[1], kind=row[2], connector_id=row[3],
                created_at=row[4])


def _servis_od_reda(row) -> Service:
    return Service(
        id=row[0], node_id=row[1], project_id=row[2], name=row[3],
        kind=row[4], config=_config(row[5]), auto_start=bool(row[6]),
        created_at=row[7], updated_at=row[8],
    )


class NodeRepository:
    """Perzistencija mesta na kojima nesto radi."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, node: Node) -> Node:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_infra_nodes (name, kind, connector_id) "
                "VALUES (?, ?, ?)",
                (node.name, str(node.kind), node.connector_id),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self) -> list[Node]:
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_NODE} FROM codium_infra_nodes ORDER BY id",
            ).fetchall()
        return [_node_od_reda(red) for red in redovi]

    def get(self, node_id: int) -> Node | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_NODE} FROM codium_infra_nodes WHERE id = ?",
                (node_id,),
            ).fetchone()
        return _node_od_reda(red) if red else None


class ServiceRepository:
    """Perzistencija registra servisa."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, service: Service) -> Service:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_infra_services (node_id, project_id, name, "
                "kind, config_json, auto_start) VALUES (?, ?, ?, ?, ?, ?)",
                (service.node_id, service.project_id, service.name,
                 str(service.kind), json.dumps(service.config),
                 int(service.auto_start)),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self, node_id: int | None = None,
             project_id: int | None = None) -> list[Service]:
        uslovi: list[str] = []
        parametri: list[int] = []
        if node_id is not None:
            uslovi.append("node_id = ?")
            parametri.append(node_id)
        if project_id is not None:
            uslovi.append("project_id = ?")
            parametri.append(project_id)
        gde = (" WHERE " + " AND ".join(uslovi)) if uslovi else ""

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_KOLONE_SERVIS} FROM codium_infra_services{gde} "
                "ORDER BY id",
                tuple(parametri),
            ).fetchall()
        return [_servis_od_reda(red) for red in redovi]

    def get(self, service_id: int) -> Service | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_KOLONE_SERVIS} FROM codium_infra_services WHERE id = ?",
                (service_id,),
            ).fetchone()
        return _servis_od_reda(red) if red else None

    def update(self, service_id: int, *, name: str, config: dict[str, str],
               project_id: int | None, auto_start: bool) -> Service | None:
        """Menja ono sto sme da se menja.

        `kind` nije u listi namerno: promena tipa bi ostavila servis ciji
        registar zapis opisuje jedan provajder, a zatecen proces ili kontejner
        pripada sasvim drugom.
        """

        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_infra_services SET name = ?, config_json = ?, "
                "project_id = ?, auto_start = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (name, json.dumps(config), project_id, int(auto_start),
                 service_id),
            )
        return self.get(service_id)

    def delete(self, service_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute("DELETE FROM codium_infra_services WHERE id = ?",
                         (service_id,))
