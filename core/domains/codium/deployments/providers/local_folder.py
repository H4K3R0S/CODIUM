# ========== PROVIDER: LOKALNI FOLDER ==========
# Raspakuje artefakt u ciljni folder. Zatecen sadrzaj se NIKAD ne brise, nego
# premesta u `<cilj>/.codium-releases/<vreme>/` — premestanje je na istom disku
# jedan potez, pa je i jeftino i tesko da ostane napola.
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from core.domains.codium.deployments.models import (
    DeployKind,
    Deployment,
    DeployResult,
    DeployTarget,
    HealthResult,
)
from core.domains.codium.deployments.providers.base import (
    DeployError,
    RollbackUnsupported,
    TargetConfigError,
)
from core.domains.codium.pipelines import artifacts

# Folder u koji ide zatecen sadrzaj pre svake isporuke. Tacka na pocetku ga
# drzi van pogleda servera koji taj folder poslužuje.
ARHIVA = ".codium-releases"


class LocalFolderProvider:
    """Isporuka u folder na istoj masini."""

    kind = DeployKind.LOCAL_FOLDER

    # ----------          PROVERE          ----------

    def validate(self, target: DeployTarget) -> None:
        koren = target.config.get("path", "")
        if not isinstance(koren, str) or not koren.strip():
            raise TargetConfigError("Cilj trazi polje `path` (folder isporuke).")
        putanja = Path(koren)
        if not putanja.is_absolute():
            raise TargetConfigError(
                f"Polje `path` mora biti apsolutna putanja: {koren}")
        # Roditelj mora da postoji; sam folder isporuke sme da nastane pri
        # prvoj isporuci. Trazenje da vec postoji bi teralo coveka da rucno
        # pravi prazan folder pre nego sto uopste isporuci nesto.
        if not putanja.parent.is_dir():
            raise TargetConfigError(
                f"Roditeljski folder ne postoji: {putanja.parent}")
        # Putanja koja vec postoji a nije folder ne moze da primi isporuku.
        # Provera stoji ovde, a ne samo u `health`, jer `deploy` inace puca
        # golim `FileExistsError` iz `mkdir` umesto urednom greskom.
        if putanja.exists() and not putanja.is_dir():
            raise TargetConfigError(f"Putanja nije folder: {putanja}")

    def health(self, target: DeployTarget) -> HealthResult:
        try:
            self.validate(target)
        except TargetConfigError as greska:
            return HealthResult(healthy=False, detail=str(greska))

        putanja = Path(target.config["path"])
        if not putanja.exists():
            return HealthResult(healthy=True,
                                detail="folder jos ne postoji — nastace pri "
                                       "prvoj isporuci")
        if not putanja.is_dir():
            return HealthResult(healthy=False,
                                detail=f"putanja nije folder: {putanja}")
        return HealthResult(healthy=True, detail=str(putanja))

    # ----------          ISPORUKA          ----------

    def deploy(self, target: DeployTarget, artifact_path: Path,
               run_id: int | None) -> DeployResult:
        self.validate(target)
        koren = Path(target.config["path"])
        koren.mkdir(parents=True, exist_ok=True)

        oznaka = self._skloni_zatecen(koren)
        try:
            artifacts.unpack(archive=artifact_path, destination=koren)
        except artifacts.ArtifactError as greska:
            # Raspakivanje je puklo pre nego sto je isporucilo — vrati zatecen
            # sadrzaj, da cilj ne ostane prazan zbog nase greske.
            if oznaka is not None:
                self._vrati_arhivu(koren, oznaka)
            raise DeployError(str(greska)) from greska

        return DeployResult(release_ref=oznaka,
                            detail=f"raspakovano u {koren}")

    def rollback(self, target: DeployTarget, previous: Deployment,
                 artifact_path: Path | None) -> DeployResult:
        """Vraca cilj na verziju zadate ranije isporuke.

        Povratak je nova isporuka istog artefakta, ne premestanje arhive
        unazad: arhiva pamti sta je zateceno pre jedne isporuke, pa bi njome
        mogao da se ponisti samo poslednji potez. Artefakt pamti sta je
        tacno bilo isporuceno, pa se njime moze na bilo koju raniju verziju.
        """

        if artifact_path is None:
            raise RollbackUnsupported(
                f"Artefakt isporuke {previous.id} vise ne postoji — povratak "
                "na nju nije moguc.")
        ishod = self.deploy(target, artifact_path, previous.run_id)
        return DeployResult(release_ref=ishod.release_ref,
                            detail=f"vraceno na isporuku {previous.id}")

    # ----------          POMOCNO          ----------

    def _skloni_zatecen(self, koren: Path) -> str | None:
        """Premesta zatecen sadrzaj u arhivu. Vraca oznaku, ili None ako je bilo prazno."""

        stavke = [s for s in koren.iterdir() if s.name != ARHIVA]
        if not stavke:
            return None

        oznaka = datetime.now().strftime("%Y%m%d-%H%M%S-%f")  # noqa: DTZ005
        odrediste = koren / ARHIVA / oznaka
        odrediste.mkdir(parents=True, exist_ok=True)
        for stavka in stavke:
            shutil.move(str(stavka), str(odrediste / stavka.name))
        return oznaka

    def _vrati_arhivu(self, koren: Path, oznaka: str) -> None:
        """Vraca sadrzaj iz arhive nazad u koren."""

        izvor = koren / ARHIVA / oznaka
        if not izvor.is_dir():
            return
        for stavka in izvor.iterdir():
            odrediste = koren / stavka.name
            if odrediste.exists():
                shutil.rmtree(odrediste) if odrediste.is_dir() else odrediste.unlink()
            shutil.move(str(stavka), str(odrediste))
        izvor.rmdir()
