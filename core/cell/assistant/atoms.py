# ========== ATOMI: uređivi fajlovi znanja persone ==========
# Atom = markdown sa laganim YAML frontmatter-om. Frontmatter nosi meta
# (id, type, tags, related), telo je uputstvo/tekst za model. Parser je
# namerno minimalan (bez PyYAML zavisnosti): key: value, liste [a, b].
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Atom:
    """Jedan atom: meta iz frontmatera i telo teksta."""

    meta: dict = field(default_factory=dict)
    body: str = ""


def _parse_scalar(value: str) -> object:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip() for part in inner.split(",")]
    return value


def parse_atom(text: str) -> Atom:
    """Deli frontmatter (između prvih `---`) od tela; bez njega sve je telo."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return Atom(meta={}, body=text)

    meta: dict = {}
    body_start = len(lines)
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            body_start = index + 1
            break
        raw = lines[index]
        if ":" in raw:
            key, _, value = raw.partition(":")
            meta[key.strip()] = _parse_scalar(value)

    # Ako se loop završi bez pronalaženja zatvarajućeg ---, to je greška:
    # tretiramo CIJELI tekst kao telo (sigurna rezerva, bez gubitka podataka).
    if body_start == len(lines):
        return Atom(meta={}, body=text)

    body = "\n".join(lines[body_start:])
    return Atom(meta=meta, body=body)


class AtomLoader:
    """Čita atome: persona.md iz `root`, tools/*.md i commands/katalog.md iz
    `shared_root` (ako je dat) — inače iz istog `root` (staro ponašanje).
    `shared_root` omogućava da više persona dele isti katalog komandi/alata
    (multi-persona/multi-entitet), dok svaka zadržava sopstvenu personu."""

    def __init__(self, root: Path, shared_root: Path | None = None) -> None:
        self._root = root
        self._shared = shared_root or root

    def _read_from(self, base: Path, relative: str) -> Atom:
        path = base / relative
        if not path.is_file():
            raise FileNotFoundError(f"Atom ne postoji: {path}")
        return parse_atom(path.read_text(encoding="utf-8"))

    def _read(self, relative: str) -> Atom:
        return self._read_from(self._root, relative)

    def persona(self) -> Atom:
        return self._read("persona.md")

    def tool(self, name: str) -> Atom:
        return self._read_from(self._shared, f"tools/{name}.md")

    def commands(self) -> Atom:
        return self._read_from(self._shared, "commands/katalog.md")

    def command_catalog(self) -> str:
        """Telo kataloga komandi — kompaktan izvor za sistemski prompt."""

        return self.commands().body.strip()
