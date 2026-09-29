# ========== PARSER DEFINICIJE ==========
# Cist modul: ulaz je tekst, izlaz je `PipelineDefinition` ili uredna greska.
# Bez baze, bez podprocesa, bez mreze — zato je i najlaksi za testiranje.
from __future__ import annotations

import json
from pathlib import Path

from core.domains.codium.explorer import CodiumExplorer, ExplorerError
from core.domains.codium.pipelines.models import (
    ArtifactDefinition,
    PipelineDefinition,
    StepDefinition,
)

PODRAZUMEVAN_TIMEOUT = 20


class DefinitionError(ValueError):
    """Definicija nije ispravna. Poruka kaze koje polje i zasto."""


def _tekst(vrednost: object, polje: str) -> str:
    if not isinstance(vrednost, str) or not vrednost.strip():
        raise DefinitionError(f"Polje `{polje}` mora biti neprazan tekst.")
    return vrednost.strip()


def _proveri_putanju(root: Path, rel: str, polje: str) -> None:
    """Brani izlazak iz korena repozitorijuma.

    Provera se NE pise iznova: `CodiumExplorer._safe` je vec brani za
    Explorer, a dve provere putanje znace dva mesta na kojima se gresi.
    """

    try:
        CodiumExplorer(root)._safe(rel)
    except ExplorerError as greska:
        raise DefinitionError(
            f"Polje `{polje}` izlazi iz korena repozitorijuma: {rel}"
        ) from greska


def _artefakt(sirovo: object, root: Path | None) -> ArtifactDefinition | None:
    """Cita opciono polje `artifact`.

    Bez njega pokretanje jednostavno nema sta da isporuci; to nije greska,
    jer vecina pipeline-a samo proverava kod.
    """

    if sirovo is None:
        return None
    if not isinstance(sirovo, dict):
        raise DefinitionError("Polje `artifact` mora biti objekat.")

    putanja = _tekst(sirovo.get("path"), "artifact.path")
    if root is not None:
        _proveri_putanju(root, putanja, "artifact.path")
    return ArtifactDefinition(path=putanja)


def _korak(sirovi: object, redni: int, root: Path | None) -> StepDefinition:
    if not isinstance(sirovi, dict):
        raise DefinitionError(f"Korak {redni} nije objekat.")

    ime = _tekst(sirovi.get("name"), f"steps[{redni}].name")
    komanda = _tekst(sirovi.get("run"), f"steps[{redni}].run")

    radni = sirovi.get("working_dir", "")
    if not isinstance(radni, str):
        raise DefinitionError(f"Polje `steps[{redni}].working_dir` mora biti tekst.")
    if radni and root is not None:
        _proveri_putanju(root, radni, f"steps[{redni}].working_dir")

    nastavi = sirovi.get("continue_on_error", False)
    if not isinstance(nastavi, bool):
        raise DefinitionError(
            f"Polje `steps[{redni}].continue_on_error` mora biti tacno ili netacno."
        )

    return StepDefinition(name=ime, run=komanda, working_dir=radni,
                          continue_on_error=nastavi)


def parse(text: str, root: Path | None = None) -> PipelineDefinition:
    """Cita JSON definiciju i proverava je.

    Args:
        text: JSON tekst definicije.
        root: Koren repozitorijuma. Kad je zadat, `working_dir` se proverava
            protiv njega. Bez njega se ta provera preskace — definicija sme
            da se snimi i pre nego sto se zna nad cim se pokrece.
    """

    try:
        sirovo = json.loads(text)
    except json.JSONDecodeError as greska:
        raise DefinitionError(f"Definicija nije ispravan JSON: {greska}") from greska

    if not isinstance(sirovo, dict):
        raise DefinitionError("Definicija mora biti JSON objekat.")

    ime = _tekst(sirovo.get("name"), "name")

    koraci_sirovi = sirovo.get("steps")
    if not isinstance(koraci_sirovi, list) or not koraci_sirovi:
        raise DefinitionError("Polje `steps` mora biti neprazna lista.")

    timeout = sirovo.get("timeout_minutes", PODRAZUMEVAN_TIMEOUT)
    # `bool` je podtip `int` u Python-u; bez ove provere `true` prolazi kao 1.
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise DefinitionError("Polje `timeout_minutes` mora biti pozitivan ceo broj.")

    okruzenje = sirovo.get("env", {})
    if not isinstance(okruzenje, dict):
        raise DefinitionError("Polje `env` mora biti objekat.")
    for kljuc, vrednost in okruzenje.items():
        if not isinstance(kljuc, str) or not isinstance(vrednost, str):
            raise DefinitionError(
                "Polje `env` sme da drzi samo tekst kao kljuc i kao vrednost."
            )

    koraci = tuple(_korak(sirovi, redni, root)
                   for redni, sirovi in enumerate(koraci_sirovi))

    return PipelineDefinition(name=ime, steps=koraci, timeout_minutes=timeout,
                              env=dict(okruzenje),
                              artifact=_artefakt(sirovo.get("artifact"), root))
