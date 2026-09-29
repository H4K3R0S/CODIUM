# ========== REPOSITORY CODIUM ==========
# Čita/piše projekte, klijente, taskove i beleške u zasebnoj CODIUM bazi.
import sqlite3
from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.models import (
    Client,
    ClientCreate,
    ClientUpdate,
    ModelPref,
    Note,
    NoteCreate,
    NoteImportance,
    NoteSource,
    NoteStatus,
    NoteUpdate,
    Priority,
    Project,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
    ProjectVisibility,
    Task,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
)
from core.domains.codium.runtime import codium_database_path


class CodiumRepository:
    """Perzistencija CODIUM domena (projekti, klijenti, taskovi, beleške)."""

    def __init__(self, database_path: Path | None = None) -> None:
        # Default na zasebnu CODIUM bazu — bez ovoga bi None pao na core.db.
        self._database_path = database_path or codium_database_path()

    # ==========          PROJEKTI          ==========

    def create_project(self, project: ProjectCreate, slug: str) -> Project:
        """Ubacuje nov projekat sa već izvedenim jedinstvenim slug-om."""

        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO codium_projects (
                    name, slug, type, visibility, client_id, local_path,
                    repository_url, stack, priority, deadline_at,
                    dev_command, dev_port, preview_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.name, slug, project.type,
                    project.visibility.value, project.client_id,
                    project.local_path, project.repository_url,
                    project.stack, project.priority.value, project.deadline_at,
                    project.dev_command, project.dev_port, project.preview_url,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite nije vratio ID novog projekta.")
            row = connection.execute(
                "SELECT * FROM codium_projects WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._row_to_project(row)

    def list_projects(
        self, visibility: ProjectVisibility | None = None,
    ) -> list[Project]:
        """Svi projekti (opciono filtrirani po vidljivosti), noviji prvi."""

        query = "SELECT * FROM codium_projects"
        params: tuple[object, ...] = ()
        if visibility is not None:
            query += " WHERE visibility = ?"
            params = (visibility.value,)
        query += " ORDER BY COALESCE(last_opened_at, created_at) DESC, id DESC"

        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_project(row) for row in rows]

    def get_project(self, project_id: int) -> Project | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                "SELECT * FROM codium_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        return self._row_to_project(row) if row is not None else None

    def slug_exists(self, slug: str) -> bool:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM codium_projects WHERE slug = ?",
                (slug,),
            ).fetchone()
        return row is not None

    def update_project(
        self, project_id: int, change: ProjectUpdate,
    ) -> Project | None:
        fields: list[str] = []
        values: list[object] = []

        def add(column: str, value: object) -> None:
            fields.append(f"{column} = ?")
            values.append(value)

        if change.name is not None:
            add("name", change.name)
        if change.type is not None:
            add("type", change.type)
        if change.visibility is not None:
            add("visibility", change.visibility.value)
        if change.status is not None:
            add("status", change.status.value)
        if change.client_id is not None:
            add("client_id", change.client_id)
        if change.local_path is not None:
            add("local_path", change.local_path)
        if change.project_brain_path is not None:
            add("project_brain_path", change.project_brain_path)
        if change.repository_url is not None:
            add("repository_url", change.repository_url)
        if change.live_url is not None:
            add("live_url", change.live_url)
        if change.staging_url is not None:
            add("staging_url", change.staging_url)
        if change.preview_url is not None:
            add("preview_url", change.preview_url)
        if change.stack is not None:
            add("stack", change.stack)
        if change.priority is not None:
            add("priority", change.priority.value)
        if change.dev_command is not None:
            add("dev_command", change.dev_command)
        if change.dev_port is not None:
            add("dev_port", change.dev_port)
        if change.started_at is not None:
            add("started_at", change.started_at)
        if change.deadline_at is not None:
            add("deadline_at", change.deadline_at)
        if change.last_opened_at is not None:
            add("last_opened_at", change.last_opened_at)

        if not fields:
            return self.get_project(project_id)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(project_id)

        with core_database_connection(self._database_path) as connection:
            connection.execute(
                f"UPDATE codium_projects SET {', '.join(fields)} WHERE id = ?",
                tuple(values),
            )
            row = connection.execute(
                "SELECT * FROM codium_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        return self._row_to_project(row) if row is not None else None

    # ==========          KLIJENTI          ==========

    def create_client(self, client: ClientCreate) -> Client:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO codium_clients (
                    name, company_name, type, email, phone, website, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client.name, client.company_name, client.type,
                    client.email, client.phone, client.website, client.notes,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite nije vratio ID novog klijenta.")
            row = connection.execute(
                "SELECT * FROM codium_clients WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._row_to_client(row)

    def list_clients(self) -> list[Client]:
        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM codium_clients ORDER BY name ASC, id ASC"
            ).fetchall()
        return [self._row_to_client(row) for row in rows]

    def get_client(self, client_id: int) -> Client | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                "SELECT * FROM codium_clients WHERE id = ?",
                (client_id,),
            ).fetchone()
        return self._row_to_client(row) if row is not None else None

    def update_client(
        self, client_id: int, change: ClientUpdate,
    ) -> Client | None:
        fields: list[str] = []
        values: list[object] = []

        def add(column: str, value: object) -> None:
            fields.append(f"{column} = ?")
            values.append(value)

        if change.name is not None:
            add("name", change.name)
        if change.company_name is not None:
            add("company_name", change.company_name)
        if change.type is not None:
            add("type", change.type)
        if change.email is not None:
            add("email", change.email)
        if change.phone is not None:
            add("phone", change.phone)
        if change.website is not None:
            add("website", change.website)
        if change.notes is not None:
            add("notes", change.notes)

        if not fields:
            return self.get_client(client_id)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(client_id)

        with core_database_connection(self._database_path) as connection:
            connection.execute(
                f"UPDATE codium_clients SET {', '.join(fields)} WHERE id = ?",
                tuple(values),
            )
            row = connection.execute(
                "SELECT * FROM codium_clients WHERE id = ?",
                (client_id,),
            ).fetchone()
        return self._row_to_client(row) if row is not None else None

    # ==========          TASKOVI          ==========

    def create_task(self, task: TaskCreate) -> Task:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO codium_tasks (
                    project_id, title, description, priority, due_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task.project_id, task.title, task.description,
                    task.priority.value, task.due_at,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite nije vratio ID novog taska.")
            row = connection.execute(
                "SELECT * FROM codium_tasks WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._row_to_task(row)

    def list_tasks(self, project_id: int | None = None) -> list[Task]:
        """Taskovi; opciono filtrirani po projektu. Nezavršeni prvi."""

        query = "SELECT * FROM codium_tasks"
        params: tuple[object, ...] = ()
        if project_id is not None:
            query += " WHERE project_id = ?"
            params = (project_id,)
        query += (
            " ORDER BY CASE status WHEN 'done' THEN 1 ELSE 0 END ASC, "
            "COALESCE(due_at, '9999') ASC, id ASC"
        )

        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task(self, task_id: int) -> Task | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                "SELECT * FROM codium_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return self._row_to_task(row) if row is not None else None

    def update_task(self, task_id: int, change: TaskUpdate) -> Task | None:
        fields: list[str] = []
        values: list[object] = []

        def add(column: str, value: object) -> None:
            fields.append(f"{column} = ?")
            values.append(value)

        if change.title is not None:
            add("title", change.title)
        if change.project_id is not None:
            add("project_id", change.project_id)
        if change.description is not None:
            add("description", change.description)
        if change.status is not None:
            add("status", change.status.value)
        if change.priority is not None:
            add("priority", change.priority.value)
        if change.due_at is not None:
            add("due_at", change.due_at)
        if change.completed_at is not None:
            add("completed_at", change.completed_at)

        if not fields:
            return self.get_task(task_id)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)

        with core_database_connection(self._database_path) as connection:
            connection.execute(
                f"UPDATE codium_tasks SET {', '.join(fields)} WHERE id = ?",
                tuple(values),
            )
            row = connection.execute(
                "SELECT * FROM codium_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return self._row_to_task(row) if row is not None else None

    # ==========          BELEŠKE          ==========

    def create_note(self, note: NoteCreate) -> Note:
        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO codium_notes (
                    project_id, client_id, title, body, source,
                    importance, tags, reminder_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note.project_id, note.client_id, note.title, note.body,
                    note.source.value, note.importance.value, note.tags,
                    note.reminder_at,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite nije vratio ID nove beleške.")
            row = connection.execute(
                "SELECT * FROM codium_notes WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._row_to_note(row)

    def list_notes(
        self,
        project_id: int | None = None,
        *,
        inbox_only: bool = False,
    ) -> list[Note]:
        """
        Beleške, novije prvo.

        - `project_id` filtrira po projektu.
        - `inbox_only` vraća globalni inbox (project_id IS NULL).
        """

        query = "SELECT * FROM codium_notes"
        params: tuple[object, ...] = ()
        if inbox_only:
            query += " WHERE project_id IS NULL"
        elif project_id is not None:
            query += " WHERE project_id = ?"
            params = (project_id,)
        query += " ORDER BY created_at DESC, id DESC"

        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_note(row) for row in rows]

    def get_note(self, note_id: int) -> Note | None:
        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                "SELECT * FROM codium_notes WHERE id = ?",
                (note_id,),
            ).fetchone()
        return self._row_to_note(row) if row is not None else None

    def update_note(self, note_id: int, change: NoteUpdate) -> Note | None:
        fields: list[str] = []
        values: list[object] = []

        def add(column: str, value: object) -> None:
            fields.append(f"{column} = ?")
            values.append(value)

        if change.title is not None:
            add("title", change.title)
        if change.body is not None:
            add("body", change.body)
        if change.project_id is not None:
            add("project_id", change.project_id)
        if change.client_id is not None:
            add("client_id", change.client_id)
        if change.source is not None:
            add("source", change.source.value)
        if change.importance is not None:
            add("importance", change.importance.value)
        if change.tags is not None:
            add("tags", change.tags)
        if change.reminder_at is not None:
            add("reminder_at", change.reminder_at)
        if change.status is not None:
            add("status", change.status.value)

        if not fields:
            return self.get_note(note_id)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(note_id)

        with core_database_connection(self._database_path) as connection:
            connection.execute(
                f"UPDATE codium_notes SET {', '.join(fields)} WHERE id = ?",
                tuple(values),
            )
            row = connection.execute(
                "SELECT * FROM codium_notes WHERE id = ?",
                (note_id,),
            ).fetchone()
        return self._row_to_note(row) if row is not None else None

    # ==========          POSTAVKA MODELA          ==========

    def get_model_pref(self, project_id: int | None,
                       persona: str) -> ModelPref | None:
        """Zapamćen model za par (projekat, persona); None ako ga nema."""

        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT * FROM codium_model_prefs
                WHERE COALESCE(project_id, 0) = COALESCE(?, 0) AND persona = ?
                """,
                (project_id, persona),
            ).fetchone()
        return self._row_to_model_pref(row) if row is not None else None

    def set_model_pref(self, project_id: int | None, persona: str,
                       model: str, provider: str) -> ModelPref:
        """Upisuje ili menja postavku. Par (projekat, persona) je jedinstven."""

        with core_database_connection(self._database_path) as connection:
            existing = connection.execute(
                """
                SELECT id FROM codium_model_prefs
                WHERE COALESCE(project_id, 0) = COALESCE(?, 0) AND persona = ?
                """,
                (project_id, persona),
            ).fetchone()

            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO codium_model_prefs (
                        project_id, persona, model, provider
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (project_id, persona, model, provider),
                )
                pref_id = cursor.lastrowid
                if pref_id is None:
                    raise RuntimeError("SQLite nije vratio ID postavke modela.")
            else:
                pref_id = existing["id"]
                connection.execute(
                    """
                    UPDATE codium_model_prefs
                    SET model = ?, provider = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (model, provider, pref_id),
                )

            row = connection.execute(
                "SELECT * FROM codium_model_prefs WHERE id = ?",
                (pref_id,),
            ).fetchone()
        return self._row_to_model_pref(row)

    def delete_model_pref(self, project_id: int | None, persona: str) -> bool:
        """Briše zapamćen model za par (projekat, persona).

        Vraća True ako je red postojao. Brisanje je način da se korisnik vrati
        na podrazumevani model: dok red stoji, ruter ga bira ispred registra,
        pa bi izbornik pokazivao „Podrazumevani model" a odgovarao zapamćeni.
        """

        with core_database_connection(self._database_path) as connection:
            cursor = connection.execute(
                """
                DELETE FROM codium_model_prefs
                WHERE COALESCE(project_id, 0) = COALESCE(?, 0) AND persona = ?
                """,
                (project_id, persona),
            )
        return cursor.rowcount > 0

    def count_model_prefs(self) -> int:
        """Broj upisanih postavki (koristi se u testovima i dijagnostici)."""

        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM codium_model_prefs",
            ).fetchone()
        return int(row["n"])

    # ==========          MAPIRANJE REDOVA          ==========

    @staticmethod
    def _row_to_project(row: sqlite3.Row) -> Project:
        return Project(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            type=row["type"],
            visibility=ProjectVisibility(row["visibility"]),
            status=ProjectStatus(row["status"]),
            local_path=row["local_path"],
            project_brain_path=row["project_brain_path"],
            client_id=row["client_id"],
            repository_url=row["repository_url"],
            live_url=row["live_url"],
            staging_url=row["staging_url"],
            preview_url=row["preview_url"],
            stack=row["stack"],
            priority=Priority(row["priority"]),
            dev_command=row["dev_command"],
            dev_port=row["dev_port"],
            started_at=row["started_at"],
            deadline_at=row["deadline_at"],
            last_opened_at=row["last_opened_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_client(row: sqlite3.Row) -> Client:
        return Client(
            id=row["id"],
            name=row["name"],
            company_name=row["company_name"],
            type=row["type"],
            email=row["email"],
            phone=row["phone"],
            website=row["website"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            priority=Priority(row["priority"]),
            due_at=row["due_at"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_note(row: sqlite3.Row) -> Note:
        return Note(
            id=row["id"],
            project_id=row["project_id"],
            client_id=row["client_id"],
            title=row["title"],
            body=row["body"],
            source=NoteSource(row["source"]),
            importance=NoteImportance(row["importance"]),
            tags=row["tags"],
            reminder_at=row["reminder_at"],
            status=NoteStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_model_pref(row: sqlite3.Row) -> ModelPref:
        return ModelPref(
            id=row["id"],
            project_id=row["project_id"],
            persona=row["persona"],
            model=row["model"],
            provider=row["provider"],
            updated_at=row["updated_at"],
        )
