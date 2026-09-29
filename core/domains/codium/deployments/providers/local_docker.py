# ========== PROVIDER: LOKALNI DOCKER ==========
# Dva nacina rada, jer se u praksi javljaju oba:
#
# - `compose` — artefakt se raspakuje u folder sa `compose` fajlom, pa ide
#   `docker compose up -d --build`. Povratak je nova isporuka ranijeg
#   artefakta, isto kao kod foldera.
# - `image`  — artefakt je build kontekst; pravi se slika sa oznakom po
#   pokretanju (`<slika>:run-<id>`), stari kontejner se gasi i pokrece nov.
#   Povratak je pokretanje prethodne oznake, bez ponovnog build-a.
#
# Komande idu kroz ubrizganog izvrsioca, pa se ceo provider testira bez
# instaliranog Docker-a.
from __future__ import annotations

import tempfile
from pathlib import Path

from core.domains.codium.command import (
    ROK_KRATKO,
    CommandError,
    CommandResult,
    CommandRunner,
    ToolMissing,
    run_command,
)
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

NACIN_COMPOSE = "compose"
NACIN_IMAGE = "image"
NACINI = (NACIN_COMPOSE, NACIN_IMAGE)

# Build ume da traje; provera prisustva Docker-a mora da bude brza.
_ROK_BUILD = 900
_ROK_KRATKO = ROK_KRATKO


class LocalDockerProvider:
    """Isporuka u Docker na istoj masini."""

    kind = DeployKind.LOCAL_DOCKER

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self._run = runner

    # ----------          PROVERE          ----------

    def validate(self, target: DeployTarget) -> None:
        nacin = target.config.get("mode", NACIN_COMPOSE)
        if nacin not in NACINI:
            raise TargetConfigError(
                f"Polje `mode` mora biti `{NACIN_COMPOSE}` ili `{NACIN_IMAGE}`.")

        if nacin == NACIN_COMPOSE:
            folder = target.config.get("compose_dir", "")
            if not folder.strip():
                raise TargetConfigError(
                    "Nacin `compose` trazi polje `compose_dir`.")
            if not Path(folder).is_absolute():
                raise TargetConfigError(
                    f"Polje `compose_dir` mora biti apsolutna putanja: {folder}")
            return

        if not target.config.get("image", "").strip():
            raise TargetConfigError("Nacin `image` trazi polje `image`.")
        if not target.config.get("container", "").strip():
            raise TargetConfigError("Nacin `image` trazi polje `container`.")

    def health(self, target: DeployTarget) -> HealthResult:
        try:
            self.validate(target)
        except TargetConfigError as greska:
            return HealthResult(healthy=False, detail=str(greska))

        try:
            ishod = self._run(["docker", "version", "--format", "{{.Server.Version}}"],
                              timeout=_ROK_KRATKO)
        except ToolMissing as greska:
            return HealthResult(healthy=False, detail=str(greska))
        except (CommandError, DeployError) as greska:
            return HealthResult(
                healthy=False,
                detail=f"Docker ne odgovara (da li je pokrenut?): {greska}")

        if ishod.exit_code != 0:
            return HealthResult(healthy=False,
                                detail=ishod.output.strip() or "docker ne odgovara")
        return HealthResult(healthy=True,
                            detail=f"docker {ishod.output.strip()}")

    # ----------          ISPORUKA          ----------

    def deploy(self, target: DeployTarget, artifact_path: Path,
               run_id: int | None) -> DeployResult:
        self.validate(target)
        if target.config.get("mode", NACIN_COMPOSE) == NACIN_COMPOSE:
            return self._compose(target, artifact_path)
        return self._image(target, artifact_path, run_id)

    def rollback(self, target: DeployTarget, previous: Deployment,
                 artifact_path: Path | None) -> DeployResult:
        self.validate(target)

        if target.config.get("mode", NACIN_COMPOSE) == NACIN_IMAGE:
            # Slika sa prethodnom oznakom jos stoji lokalno — povratak je samo
            # pokretanje te oznake, bez ponovnog build-a.
            if not previous.release_ref:
                raise RollbackUnsupported(
                    f"Isporuka {previous.id} nema zapamcenu oznaku slike.")
            self._pokreni_kontejner(target, previous.release_ref)
            return DeployResult(release_ref=previous.release_ref,
                                detail=f"vraceno na sliku {previous.release_ref}")

        if artifact_path is None:
            raise RollbackUnsupported(
                f"Artefakt isporuke {previous.id} vise ne postoji — povratak "
                "na nju nije moguc.")
        ishod = self._compose(target, artifact_path)
        return DeployResult(release_ref=ishod.release_ref,
                            detail=f"vraceno na isporuku {previous.id}")

    # ----------          NACINI          ----------

    def _compose(self, target: DeployTarget, artifact_path: Path) -> DeployResult:
        folder = Path(target.config["compose_dir"])
        folder.mkdir(parents=True, exist_ok=True)
        artifacts.unpack(archive=artifact_path, destination=folder)

        ishod = self._izvrsi(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=str(folder), timeout=_ROK_BUILD,
        )
        return DeployResult(release_ref=None, detail=ishod.output.strip()[:500])

    def _image(self, target: DeployTarget, artifact_path: Path,
               run_id: int | None) -> DeployResult:
        oznaka = f"{target.config['image']}:run-{run_id if run_id else 'manual'}"

        # Build kontekst je sadrzaj artefakta; raspakuje se u privremen folder
        # da se ne ostavlja trag na masini posle isporuke.
        with tempfile.TemporaryDirectory(prefix="codium-deploy-") as privremen:
            kontekst = Path(privremen)
            artifacts.unpack(archive=artifact_path, destination=kontekst)
            self._izvrsi(["docker", "build", "-t", oznaka, str(kontekst)],
                         timeout=_ROK_BUILD)

        self._pokreni_kontejner(target, oznaka)
        return DeployResult(release_ref=oznaka, detail=f"pokrenuta slika {oznaka}")

    def _pokreni_kontejner(self, target: DeployTarget, oznaka: str) -> None:
        ime = target.config["container"]
        # Gasenje starog sme da ne uspe — kontejner mozda ne postoji (prva
        # isporuka). Zato se ishod ove komande namerno ne proverava.
        self._run(["docker", "rm", "-f", ime], timeout=_ROK_KRATKO)

        komanda = ["docker", "run", "-d", "--name", ime]
        port = target.config.get("port", "").strip()
        if port:
            komanda += ["-p", port]
        komanda.append(oznaka)
        self._izvrsi(komanda, timeout=_ROK_KRATKO)

    def _izvrsi(self, args: list[str], cwd: str | None = None,
                timeout: int = _ROK_KRATKO) -> CommandResult:
        """Pokrece komandu i pretvara nenulti kod u urednu gresku isporuke."""

        try:
            ishod = self._run(args, cwd=cwd, timeout=timeout)
        except CommandError as greska:
            # Nema odgovora (nema alata, ili je istekao) — za isporuku je to
            # isto sto i neuspeh, samo sa drugim uzrokom.
            raise DeployError(str(greska)) from greska
        if ishod.exit_code != 0:
            raise DeployError(
                f"`{' '.join(args)}` je vratila kod {ishod.exit_code}: "
                f"{ishod.output.strip()[:500]}")
        return ishod
