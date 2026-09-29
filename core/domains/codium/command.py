# ========== POKRETANJE SPOLJNIH ALATA ==========
# Jedan izvrsilac za ceo domen. Postoji da `docker` (i slicni alati) ne bi
# imali po jednu kopiju istog koda u svakoj fazi koja ih zove — E4 isporuka i
# E5 infrastruktura zovu bas isti `docker`.
#
# Argumenti idu kao lista: komanda se nikada ne sastavlja spajanjem stringova
# sa unosom coveka. Isti obrazac koji `repositories/providers/local_git` vec
# koristi za `git`.
from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass

# Citanje stanja mora da bude brzo; build i slicno dobijaju svoj duzi rok na
# mestu poziva.
ROK_KRATKO = 30


class CommandError(RuntimeError):
    """Alat nije dao odgovor.

    Nenulti izlazni kod NIJE ovo — to je uredan odgovor alata, pa ga cita
    pozivalac. Ovde su samo slucajevi u kojima odgovora nema.
    """


class ToolMissing(CommandError):
    """Alata uopste nema na masini.

    Odvojeno od `CommandError` jer se sa ekrana razlicito cita: „instaliraj
    Docker" i „upali Docker" su dva razlicita saveta, a do ove podele su oba
    zavrsavala kao ista poruka. Nadjeno pri prvoj proveri sa stvarno
    instaliranim Docker-om, gde je demon bio ugasen a kod je tvrdio da alata
    nema.
    """


@dataclass(frozen=True)
class CommandResult:
    """Ishod jedne komande. Namerno mali oblik — pozivaoci ne citaju vise."""

    exit_code: int
    output: str


# Tip izvrsioca, da provajderi mogu da prime lazni u testovima.
CommandRunner = Callable[..., CommandResult]


def run_command(args: list[str], cwd: str | None = None,
                timeout: int = ROK_KRATKO) -> CommandResult:
    """Pokrece jednu komandu i vraca njen izlazni kod i ispis.

    `stdout` i `stderr` se spajaju: pozivaoci ovog sloja prikazuju ispis
    coveku ili ga upisuju u gresku, a nijednom ne treba razdvojeno.
    """

    try:
        ishod = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except FileNotFoundError as greska:
        raise ToolMissing(
            f"Alat `{args[0]}` nije instaliran na ovoj masini.") from greska
    except subprocess.TimeoutExpired as greska:
        raise CommandError(
            f"Komanda je istekla posle {timeout}s: {' '.join(args)}") from greska

    return CommandResult(ishod.returncode,
                         (ishod.stdout or "") + (ishod.stderr or ""))
