# ==========          POTEZ MODELA          ==========
# Protokol provajdera se ne dira. Model odgovara ili JSON blokom (poziv alata)
# ili prozom (konacan odgovor); ovaj modul razlikuje to dvoje.
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# Ograda koda oko JSON-a je toliko cesta kod modela da se ne isplati boriti
# protiv nje — jednostavnije je procitati je.
_OGRADA = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


@dataclass(frozen=True)
class ToolCall:
    """Poziv jednog alata."""

    tool: str
    args: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Move:
    """Potez modela: poziv alata, konacan odgovor, ili neprocitljiv pokusaj."""

    call: ToolCall | None
    answer: str
    # Nije prazan kad model jeste pokusao poziv, ali nerazumljivo. Petlja tu
    # poruku vraca modelu kao rezultat koraka — dobija priliku da se popravi.
    error: str = ""


def _kandidati(text: str) -> list[str]:
    """Delovi teksta koji bi mogli biti JSON objekat, po redu verovatnoce."""

    kandidati = [text.strip()]
    kandidati.extend(m.strip() for m in _OGRADA.findall(text))
    pocetak = text.find("{")
    kraj = text.rfind("}")
    if pocetak != -1 and kraj > pocetak:
        kandidati.append(text[pocetak:kraj + 1])
    return [k for k in kandidati if k]


def parse_move(text: str) -> Move:
    """Cita potez iz odgovora modela."""

    sirovo = text or ""
    poslednja_greska = ""
    # Objekat bez polja `tool` je pokusaj poziva, ne proza. Bez ove zastavice
    # bi takav tekst prosao kao konacan odgovor, jer se niz `"tool"` u njemu
    # po definiciji ne pojavljuje.
    objekat_bez_alata = False

    for kandidat in _kandidati(sirovo):
        try:
            podaci = json.loads(kandidat)
        except ValueError:
            continue
        if not isinstance(podaci, dict):
            continue
        if "tool" not in podaci:
            objekat_bez_alata = True
            poslednja_greska = "Objekat mora imati polje `tool` sa imenom alata."
            continue

        ime = podaci.get("tool")
        if not isinstance(ime, str) or not ime.strip():
            poslednja_greska = "Polje `tool` mora biti ime alata."
            continue

        argumenti = podaci.get("args", {})
        if argumenti is None:
            argumenti = {}
        if not isinstance(argumenti, dict):
            poslednja_greska = "Polje `args` mora biti objekat sa imenovanim argumentima."
            continue

        return Move(call=ToolCall(tool=ime.strip(), args=argumenti), answer="")

    # Tekst koji uopste ne lici na poziv je konacan odgovor: agent koji je
    # zavrsio pise prozu, i to nije greska.
    lici_na_poziv = objekat_bez_alata or ("{" in sirovo and '"tool"' in sirovo)
    if not lici_na_poziv:
        return Move(call=None, answer=sirovo.strip())

    greska = poslednja_greska or (
        "Poziv alata nije citljiv JSON. Posalji tacno jedan objekat oblika "
        '{"tool": "ime_alata", "args": {...}}.'
    )
    return Move(call=None, answer="", error=greska)


def system_prompt(agent_prompt: str, tools_description: str) -> str:
    """Sklapa ulogu agenta sa uputstvom kako se poziva alat."""

    return (
        f"{agent_prompt.strip()}\n\n"
        "Radis u koracima. U svakom koraku biras tacno jedno:\n\n"
        "1. Poziv alata — odgovori ISKLJUCIVO JSON objektom oblika\n"
        '   {"tool": "ime_alata", "args": {"argument": "vrednost"}}\n'
        "   Jedan alat po koraku. Bez teksta oko JSON-a.\n\n"
        "2. Konacan odgovor — obican tekst, bez JSON-a. Pisi ga tek kad si "
        "prikupio sve sto ti treba.\n\n"
        "Rezultat svakog poziva stize ti kao sledeca poruka.\n\n"
        f"Alati koje smes da koristis:\n{tools_description}"
    )
