# ========== ARTEFAKTI POKRETANJA ==========
# Cist modul nad diskom: pakuje ono sto je uspesno pokretanje ostavilo i
# brise stare pakete. Bez baze i bez kapije — zato se testira nad `tmp_path`.
#
# Artefakt je jedini ulaz u isporuku (E4). Deploy nema svoj build: isporucuje
# se tacno ono sto je proslo korake, pa se „radilo je kod mene" ne moze desiti.
from __future__ import annotations

import zipfile
from pathlib import Path

# Koliko poslednjih artefakata po pipeline-u ostaje na disku. Paketi su
# veliki (ceo `dist/`), a stariji od dvadesetog se u praksi ne vracaju.
ZADRZI_ARTEFAKATA = 20


class ArtifactError(RuntimeError):
    """Artefakt nije mogao da se napravi ili nije pronadjen."""


def artifact_path(artifacts_dir: Path, run_id: int) -> Path:
    """Gde stoji paket jednog pokretanja."""

    return artifacts_dir / f"{run_id}.zip"


def pack(*, run_id: int, source: Path, artifacts_dir: Path) -> Path:
    """Pakuje `source` (folder ili fajl) u `<artifacts_dir>/<run_id>.zip`.

    Args:
        run_id: Pokretanje ciji je ovo rezultat.
        source: Apsolutna putanja koju je definicija oznacila kao artefakt.
            Pozivalac je vec proverio da ne izlazi iz korena repozitorijuma.
        artifacts_dir: Folder u koji paketi idu (`CodiumPaths.artifacts`).

    Raises:
        ArtifactError: Putanja ne postoji — korak je „uspeo" a nije napravio
            ono sto je obecao, i to mora da se vidi, ne da se progura dalje.
    """

    if not source.exists():
        raise ArtifactError(f"Artefakt ne postoji na putanji: {source}")

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    odrediste = artifact_path(artifacts_dir, run_id)

    # Upisuje se u privremen fajl pa preimenuje: prekid usred pakovanja ne
    # sme da ostavi krnj `.zip` koji izgleda kao ispravan artefakt.
    privremen = odrediste.with_suffix(".zip.part")
    privremen.unlink(missing_ok=True)

    with zipfile.ZipFile(privremen, "w", zipfile.ZIP_DEFLATED) as paket:
        if source.is_file():
            paket.write(source, source.name)
        else:
            for putanja in sorted(source.rglob("*")):
                if putanja.is_file():
                    paket.write(putanja, putanja.relative_to(source).as_posix())

    odrediste.unlink(missing_ok=True)
    privremen.rename(odrediste)
    return odrediste


def unpack(*, archive: Path, destination: Path) -> None:
    """Raspakuje paket u odrediste. Odrediste se pravi ako ne postoji."""

    if not archive.is_file():
        raise ArtifactError(f"Artefakt ne postoji: {archive}")

    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as paket:
        # `extractall` u Python-u 3.12+ vec odbija apsolutne putanje i `..`
        # (`ZipFile._extract_member` ih sanira), pa se provera ne pise iznova.
        paket.extractall(destination)


def prune(*, artifacts_dir: Path, stale_run_ids: list[int]) -> int:
    """Brise pakete zadatih pokretanja. Vraca koliko ih je stvarno obrisano."""

    obrisano = 0
    for run_id in stale_run_ids:
        putanja = artifact_path(artifacts_dir, run_id)
        if putanja.exists():
            putanja.unlink()
            obrisano += 1
    return obrisano
