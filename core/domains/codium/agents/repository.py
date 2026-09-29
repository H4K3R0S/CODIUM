# ========== REPOZITORIJUMI AGENATA I POSLOVA ==========
# Prevod `tools` <-> `tools_json` radi ovaj sloj i niko drugi: ostatak koda
# vidi torku imena, baza vidi JSON.
from __future__ import annotations

import json
from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.agents.models import Agent, AgentRun, AgentStep
from core.domains.codium.runtime import codium_database_path

_AGENT_KOLONE = ("id, slug, name, description, system_prompt, model, "
                 "provider, tools_json, max_steps, enabled")
_RUN_KOLONE = ("id, agent_id, project_id, task, status, result, steps_used, "
               "cost_usd, pending_approval_id, started_at, finished_at")
_STEP_KOLONE = "id, run_id, idx, kind, tool, payload, at"

# Sta `update` sme da menja. Spisak stoji u kodu, jer bi inace naziv kolone
# stizao spolja pravo u SQL.
_IZMENJIVO = frozenset({
    "name", "description", "system_prompt", "model", "provider", "tools",
    "max_steps", "enabled",
})


def _to_agent(row) -> Agent:
    return Agent(
        id=row[0], slug=row[1], name=row[2], description=row[3],
        system_prompt=row[4], model=row[5], provider=row[6],
        tools=tuple(json.loads(row[7] or "[]")),
        max_steps=row[8], enabled=bool(row[9]),
    )


def _to_run(row) -> AgentRun:
    return AgentRun(
        id=row[0], agent_id=row[1], project_id=row[2], task=row[3],
        status=row[4], result=row[5], steps_used=row[6], cost_usd=row[7],
        pending_approval_id=row[8], started_at=row[9], finished_at=row[10],
    )


def _to_step(row) -> AgentStep:
    return AgentStep(id=row[0], run_id=row[1], idx=row[2], kind=row[3],
                     tool=row[4] or "", payload=row[5], at=row[6])


class AgentRepository:
    """Citanje i izmena definicija agenata."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def list(self) -> list[Agent]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                f"SELECT {_AGENT_KOLONE} FROM codium_agents ORDER BY id"
            ).fetchall()
        return [_to_agent(row) for row in rows]

    def get(self, agent_id: int) -> Agent | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_AGENT_KOLONE} FROM codium_agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
        return _to_agent(row) if row else None

    def by_slug(self, slug: str) -> Agent | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_AGENT_KOLONE} FROM codium_agents WHERE slug = ?",
                (slug,),
            ).fetchone()
        return _to_agent(row) if row else None

    def add(self, agent: Agent) -> Agent:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO codium_agents (
                    slug, name, description, system_prompt, model, provider,
                    tools_json, max_steps, enabled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (agent.slug, agent.name, agent.description,
                 agent.system_prompt, agent.model, agent.provider,
                 json.dumps(list(agent.tools)), agent.max_steps,
                 1 if agent.enabled else 0),
            )
            novi_id = cursor.lastrowid
        return self.get(novi_id)

    def update(self, agent_id: int,
               change: dict[str, object]) -> Agent | None:
        """Menja samo prosledjena polja; nepoznat kljuc se ignorise."""

        postavke: list[str] = []
        vrednosti: list[object] = []
        for kljuc, vrednost in change.items():
            if kljuc not in _IZMENJIVO:
                continue
            if kljuc == "tools":
                postavke.append("tools_json = ?")
                vrednosti.append(json.dumps(list(vrednost)))
            elif kljuc == "enabled":
                postavke.append("enabled = ?")
                vrednosti.append(1 if vrednost else 0)
            else:
                postavke.append(f"{kljuc} = ?")
                vrednosti.append(vrednost)

        if not postavke:
            return self.get(agent_id)

        postavke.append("updated_at = CURRENT_TIMESTAMP")
        vrednosti.append(agent_id)
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                f"UPDATE codium_agents SET {', '.join(postavke)} WHERE id = ?",
                tuple(vrednosti),
            )
        return self.get(agent_id)

    def delete(self, agent_id: int) -> None:
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                "DELETE FROM codium_agents WHERE id = ?", (agent_id,)
            )


class RunRepository:
    """Poslovi agenata i njihovi koraci."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def start(self, run: AgentRun) -> AgentRun:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO codium_agent_runs (agent_id, project_id, task) "
                "VALUES (?, ?, ?)",
                (run.agent_id, run.project_id, run.task),
            )
            novi_id = cursor.lastrowid
        return self.get(novi_id)

    def get(self, run_id: int) -> AgentRun | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_agent_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return _to_run(row) if row else None

    def recent(self, *, limit: int = 20) -> list[AgentRun]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_agent_runs "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_to_run(row) for row in rows]

    def append_step(self, step: AgentStep) -> AgentStep:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO codium_agent_steps (run_id, idx, kind, tool, "
                "payload) VALUES (?, ?, ?, ?, ?)",
                (step.run_id, step.idx, step.kind, step.tool or None,
                 step.payload),
            )
            novi_id = cursor.lastrowid
            row = connection.execute(
                f"SELECT {_STEP_KOLONE} FROM codium_agent_steps WHERE id = ?",
                (novi_id,),
            ).fetchone()
        return _to_step(row)

    def steps(self, run_id: int, *, since_idx: int = -1) -> list[AgentStep]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                f"SELECT {_STEP_KOLONE} FROM codium_agent_steps "
                "WHERE run_id = ? AND idx > ? ORDER BY idx",
                (run_id, since_idx),
            ).fetchall()
        return [_to_step(row) for row in rows]

    def finish(self, run_id: int, *, status: str, result: str = "",
               steps_used: int = 0, cost_usd: float = 0.0) -> AgentRun | None:
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                """
                UPDATE codium_agent_runs
                SET status = ?, result = ?, steps_used = ?, cost_usd = ?,
                    pending_approval_id = NULL,
                    finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, result, steps_used, cost_usd, run_id),
            )
        return self.get(run_id)

    def wait_for_approval(self, run_id: int,
                          approval_id: int) -> AgentRun | None:
        """Pauzira posao koji trazi odobrenje.

        Uslov stanja stoji u samom upitu, isto kao kod odobrenja: zavrsen
        posao ne sme da se vrati u cekanje.
        """

        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "UPDATE codium_agent_runs "
                "SET status = 'waiting_approval', pending_approval_id = ? "
                "WHERE id = ? AND status = 'running'",
                (approval_id, run_id),
            )
            promenjeno = cursor.rowcount
        return self.get(run_id) if promenjeno else None

    def by_pending_approval(self, approval_id: int) -> AgentRun | None:
        """Posao koji ceka bas ovu molbu, ili `None`.

        Trazi po `pending_approval_id`, ne skenira `recent()` — davno
        pauziran posao van tog dometa inace ne bi bio nadjen.
        """

        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_agent_runs "
                "WHERE pending_approval_id = ?",
                (approval_id,),
            ).fetchone()
        return _to_run(row) if row else None

    def resume(self, run_id: int) -> AgentRun | None:
        """Vraca posao u rad posle odluke; `None` ako nije cekao."""

        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                "UPDATE codium_agent_runs "
                "SET status = 'running', pending_approval_id = NULL "
                "WHERE id = ? AND status = 'waiting_approval'",
                (run_id,),
            )
            promenjeno = cursor.rowcount
        return self.get(run_id) if promenjeno else None
