from pathlib import Path

from core.foundation.paths import core_paths

# ==========          CODIUM PUTANJE          ==========

class CodiumPaths:
    """
    Centralizuje putanje koje pripadaju CODIUM domenu.

    Ostali CODIUM moduli treba da koriste ovaj objekat umesto ručnog
    sastavljanja putanja do baze, sistemskog brain-a i project asset-a.
    """

    def __init__(
        self,
        data_path: Path | None = None,
    ) -> None:
        """
        Inicijalizuje CODIUM putanje.

        Args:
            data_path: Opcioni osnovni data direktorijum.
                Koristi se prvenstveno u testovima.
        """

        self.data = data_path or core_paths.data

        self.root = self.data / "codium"
        # Sistemski brain: fajlovi koje CODIUM čuva o samom sebi (kasnije faze).
        self.system = self.root / "system"
        # Registry brain za projekte bez lokalnog repo-a (F3):
        # data/codium/projects/<project-id>/brain/.
        self.projects = self.root / "projects"
        # Zasebna SQLite baza domena, odvojena od core.db.
        self.database = core_paths.database_dir / "codium.db"
        # Operativna baza: evidencija poziva modela. Odvojena od poslovne
        # `codium.db` jer raste sa svakim pozivom, a poslovna se bekapuje.
        self.ops_database = core_paths.database_dir / "codium_ops.db"
        # Artefakti uspesnih pokretanja pipeline-a: `<run_id>.zip`. Ulaz u
        # svaku isporuku (E4) je tacno ono sto je proslo korake, ne nov build.
        self.artifacts = self.root / "artifacts"

    def project_registry_brain(self, project_id: int) -> Path:
        """Registry lokacija brain foldera za projekat bez lokalnog repo-a."""

        return self.projects / str(project_id) / "brain"

    def ensure_dirs(self) -> None:
        """
        Kreira bezbedne CODIUM runtime direktorijume ako ne postoje.

        Metoda ne kreira projektnu strukturu, već samo direktorijume
        potrebne tokom rada domena.
        """

        self.root.mkdir(parents=True, exist_ok=True)
        self.system.mkdir(parents=True, exist_ok=True)
        self.artifacts.mkdir(parents=True, exist_ok=True)


# ==========          JAVNI CODIUM PATH REGISTAR          ==========

codium_paths = CodiumPaths()
