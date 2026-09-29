# ==========          REGISTAR ALATA          ==========
# Jedan zapis po alatu iz kojeg se izvodi i opis koji cita model i akcija koju
# proverava kapija. Dva mesta bi znacila alat koji modelu kaze jedno a kapiji
# prijavi drugo.
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    """Opis jednog alata: sta radi, sta trazi i sta pokrece."""

    name: str
    description: str
    args: dict[str, str]
    action: str
    run: Callable[..., str]
    # Kad alat pise sadrzaj, molba za odobrenje nosi otisak tog sadrzaja. Ovo
    # NE dokazuje da je covek video bas ove bajtove — samo da se `content` u
    # molbi nije promenio izmedju podnosenja i nastavka posla.
    writes_content: bool = False


class ToolRegistry:
    """Alati dostupni petlji, po imenu."""

    def __init__(self, specs: list[ToolSpec]) -> None:
        self._specs = {spec.name: spec for spec in specs}

    def names(self) -> list[str]:
        return list(self._specs)

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def describe(self, allowed: Sequence[str]) -> str:
        """Opis alata za sistemski prompt — samo oni koje agent sme."""

        redovi: list[str] = []
        for ime in allowed:
            spec = self._specs.get(ime)
            if spec is None:
                continue
            argumenti = ", ".join(
                f"{kljuc} ({opis})" for kljuc, opis in spec.args.items()
            ) or "bez argumenata"
            redovi.append(f"- {spec.name}: {spec.description} | argumenti: {argumenti}")
        return "\n".join(redovi)
