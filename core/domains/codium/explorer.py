# ========== CODIUM EXPLORER (file tree) ==========
# Namenski skener fajl-stabla projekta, ograničen na koren (Project.local_path).
# Ne postoji generički CORE System Layer za fajlove — ovo je novi servis.
# Sve putanje se resolve-uju UNUTAR korena; izlazak (`..`) je greška.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Folderi/fajlovi koji se ne prikazuju u stablu (šum razvoja).
DEFAULT_IGNORE: frozenset[str] = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        ".git",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".idea",
        ".vscode",
        ".cache",
        "cache",
        ".next",
        ".turbo",
    }
)

# Sadržaj fajla se ne učitava iznad ove granice (bajtova).
MAX_READ_BYTES = 1_000_000


class ExplorerError(Exception):
    """Bezbednosna ili I/O greška u exploreru (izlazak iz korena, nepostojanje)."""


@dataclass
class FileNode:
    """Jedna stavka u fajl-stablu (fajl ili folder)."""

    name: str
    path: str          # relativna putanja u odnosu na koren (POSIX separator)
    is_dir: bool
    size: int          # bajtovi; 0 za foldere


@dataclass
class FileContent:
    """Sadržaj tekstualnog fajla (ili oznaka da je binarno/preveliko)."""

    path: str
    content: str
    truncated: bool
    binary: bool


class CodiumExplorer:
    """Read/write pristup fajl-stablu jednog projekta, zaključan na koren."""

    def __init__(
        self, root: Path, ignore: frozenset[str] = DEFAULT_IGNORE,
    ) -> None:
        self._root = Path(root).resolve()
        self._ignore = ignore

    @property
    def root(self) -> Path:
        return self._root

    # ==========          BEZBEDNA PUTANJA          ==========

    def _safe(self, rel: str) -> Path:
        """
        Resolve-uje relativnu putanju unutar korena i brani izlazak.

        Prazan string / '.' / '/' → koren. Bilo koji rezultat van korena → greška.
        """

        cleaned = (rel or "").strip().replace("\\", "/").lstrip("/")
        target = (self._root / cleaned).resolve()
        # target mora biti koren ili ispod korena.
        if target != self._root and self._root not in target.parents:
            raise ExplorerError(f"Putanja izlazi iz korena projekta: {rel}")
        return target

    def _to_rel(self, path: Path) -> str:
        return path.resolve().relative_to(self._root).as_posix()

    # ==========          ČITANJE          ==========

    def list_dir(self, rel: str = "") -> list[FileNode]:
        """Jedan nivo direktorijuma: folderi prvi, pa fajlovi; alfabetski."""

        target = self._safe(rel)
        if not target.exists():
            raise ExplorerError(f"Folder ne postoji: {rel}")
        if not target.is_dir():
            raise ExplorerError(f"Nije folder: {rel}")

        nodes: list[FileNode] = []
        for entry in target.iterdir():
            if entry.name in self._ignore:
                continue
            is_dir = entry.is_dir()
            try:
                size = 0 if is_dir else entry.stat().st_size
            except OSError:
                size = 0
            nodes.append(
                FileNode(
                    name=entry.name,
                    path=self._to_rel(entry),
                    is_dir=is_dir,
                    size=size,
                )
            )

        nodes.sort(key=lambda node: (not node.is_dir, node.name.lower()))
        return nodes

    def read_file(self, rel: str) -> FileContent:
        """Sadržaj tekstualnog fajla; binarno/preveliko se ne učitava."""

        target = self._safe(rel)
        if not target.is_file():
            raise ExplorerError(f"Fajl ne postoji: {rel}")

        size = target.stat().st_size
        if size > MAX_READ_BYTES:
            return FileContent(
                path=self._to_rel(target), content="", truncated=True,
                binary=False,
            )

        data = target.read_bytes()
        if b"\x00" in data:
            return FileContent(
                path=self._to_rel(target), content="", truncated=False,
                binary=True,
            )

        return FileContent(
            path=self._to_rel(target),
            content=data.decode("utf-8", errors="replace"),
            truncated=False,
            binary=False,
        )

    # ==========          PISANJE          ==========

    def write_file(self, rel: str, content: str) -> FileNode:
        """Upisuje tekstualni sadržaj u postojeći fajl (unutar korena)."""

        target = self._safe(rel)
        if target == self._root:
            raise ExplorerError("Ne mogu pisati u sam koren.")
        if target.is_dir():
            raise ExplorerError(f"Putanja je folder: {rel}")
        if not target.parent.exists():
            raise ExplorerError(f"Roditeljski folder ne postoji: {rel}")

        target.write_text(content, encoding="utf-8", newline="")
        return FileNode(
            name=target.name,
            path=self._to_rel(target),
            is_dir=False,
            size=target.stat().st_size,
        )

    def create(self, rel: str, kind: str) -> FileNode:
        """Pravi fajl ('file') ili folder ('dir'); roditelj mora postojati."""

        target = self._safe(rel)
        if target == self._root:
            raise ExplorerError("Ne mogu kreirati sam koren.")
        if target.exists():
            raise ExplorerError(f"Već postoji: {rel}")
        if not target.parent.exists():
            raise ExplorerError(f"Roditeljski folder ne postoji: {rel}")

        if kind == "dir":
            target.mkdir()
        elif kind == "file":
            target.touch()
        else:
            raise ExplorerError(f"Nepoznat tip: {kind}")

        return FileNode(
            name=target.name,
            path=self._to_rel(target),
            is_dir=(kind == "dir"),
            size=0,
        )

    def rename(self, rel: str, new_name: str) -> FileNode:
        """Preimenuje fajl/folder unutar istog roditelja (samo ime, ne putanja)."""

        source = self._safe(rel)
        if source == self._root:
            raise ExplorerError("Ne mogu preimenovati koren.")
        if not source.exists():
            raise ExplorerError(f"Ne postoji: {rel}")

        clean_name = new_name.strip()
        if clean_name == "" or "/" in clean_name or "\\" in clean_name:
            raise ExplorerError(f"Neispravno ime: {new_name}")

        destination = source.parent / clean_name
        if destination.exists():
            raise ExplorerError(f"Već postoji: {clean_name}")

        source.rename(destination)
        return FileNode(
            name=destination.name,
            path=self._to_rel(destination),
            is_dir=destination.is_dir(),
            size=0 if destination.is_dir() else destination.stat().st_size,
        )

    def delete(self, rel: str) -> None:
        """Briše fajl ili (rekurzivno) folder unutar korena."""

        target = self._safe(rel)
        if target == self._root:
            raise ExplorerError("Ne mogu obrisati koren projekta.")
        if not target.exists():
            raise ExplorerError(f"Ne postoji: {rel}")

        if target.is_dir():
            import shutil

            shutil.rmtree(target)
        else:
            target.unlink()

    # ==========          KOPIRAJ / PREMESTI          ==========

    def _unique_destination(self, dest_dir: Path, name: str) -> Path:
        """Nađe slobodno ime u ciljnom folderu (dodaje „-copy", „-copy-2"...)."""

        candidate = dest_dir / name
        if not candidate.exists():
            return candidate
        stem = candidate.stem
        suffix = candidate.suffix
        index = 1
        while True:
            extra = "-copy" if index == 1 else f"-copy-{index}"
            candidate = dest_dir / f"{stem}{extra}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    def copy(self, src_rel: str, dest_dir_rel: str) -> FileNode:
        """Kopira fajl/folder u ciljni folder (bez pregaženja — jedinstveno ime)."""

        import shutil

        source = self._safe(src_rel)
        if source == self._root:
            raise ExplorerError("Ne mogu kopirati koren.")
        if not source.exists():
            raise ExplorerError(f"Ne postoji: {src_rel}")

        dest_dir = self._safe(dest_dir_rel)
        if not dest_dir.is_dir():
            raise ExplorerError(f"Cilj nije folder: {dest_dir_rel}")

        destination = self._unique_destination(dest_dir, source.name)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)

        return FileNode(
            name=destination.name,
            path=self._to_rel(destination),
            is_dir=destination.is_dir(),
            size=0 if destination.is_dir() else destination.stat().st_size,
        )

    def move(self, src_rel: str, dest_dir_rel: str) -> FileNode:
        """Premešta fajl/folder u ciljni folder (jedinstveno ime u cilju)."""

        import shutil

        source = self._safe(src_rel)
        if source == self._root:
            raise ExplorerError("Ne mogu premestiti koren.")
        if not source.exists():
            raise ExplorerError(f"Ne postoji: {src_rel}")

        dest_dir = self._safe(dest_dir_rel)
        if not dest_dir.is_dir():
            raise ExplorerError(f"Cilj nije folder: {dest_dir_rel}")

        # Zabrani premeštanje foldera u samog sebe/svoje dete.
        if source.is_dir() and (dest_dir == source or source in dest_dir.parents):
            raise ExplorerError("Ne mogu premestiti folder u samog sebe.")

        destination = self._unique_destination(dest_dir, source.name)
        shutil.move(str(source), str(destination))

        return FileNode(
            name=destination.name,
            path=self._to_rel(destination),
            is_dir=destination.is_dir(),
            size=0 if destination.is_dir() else destination.stat().st_size,
        )

    # ==========          OTKRIJ U OS EXPLORER-U          ==========

    def reveal(self, rel: str) -> None:
        """Otvara stavku u sistemskom fajl-menadžeru (Windows-first)."""

        import subprocess
        import sys

        target = self._safe(rel)
        if not target.exists():
            raise ExplorerError(f"Ne postoji: {rel}")

        if sys.platform == "win32":
            # explorer /select markira fajl u otvorenom prozoru.
            subprocess.Popen(
                ["explorer", "/select,", str(target)],
            )
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(target)])
        else:
            # Linux: otvori roditeljski folder.
            parent = target if target.is_dir() else target.parent
            subprocess.Popen(["xdg-open", str(parent)])


__all__ = [
    "DEFAULT_IGNORE",
    "MAX_READ_BYTES",
    "CodiumExplorer",
    "ExplorerError",
    "FileContent",
    "FileNode",
]
