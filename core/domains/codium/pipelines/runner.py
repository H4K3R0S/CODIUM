# ========== MOTOR PIPELINE-A ==========
# Pokretanje ide kao `asyncio.Task` u procesu backend-a. Motor ne zna za bazu:
# stanja prijavljuje kroz `RunStore`, redove loga kroz `LogSink`. Zato se
# testira nad laznim obema, bez SQLite-a.
from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Protocol

from core.domains.codium.pipelines.models import (
    PipelineDefinition,
    RunLogLine,
    RunStatus,
    StepDefinition,
    StepStatus,
)
from core.domains.codium.pipelines.sinks import LogSink

SEKUNDI_U_MINUTU = 60


class RunStore(Protocol):
    """Ono cime motor prijavljuje stanje pokretanja i koraka."""

    def mark_run_started(self, run_id: int) -> None: ...

    def mark_run_finished(self, run_id: int, status: str,
                          exit_code: int | None, detail: str = "") -> None: ...

    def mark_step_started(self, run_id: int, idx: int) -> None: ...

    def mark_step_finished(self, run_id: int, idx: int, status: str,
                           exit_code: int | None = None) -> None: ...


def _terminate_tree(process: asyncio.subprocess.Process) -> None:
    """Obara proces i svu njegovu decu.

    `create_subprocess_shell` na Windows-u pravi `cmd.exe`, koji pravi `npm`,
    koji pravi `node`. Gasiti samo dete znaci ostaviti unuke da rade. Isti
    obrazac koji `dev_server.py` vec koristi.
    """

    if process.returncode is not None:
        return

    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
        return

    try:
        os.killpg(os.getpgid(process.pid), 9)
    except (ProcessLookupError, PermissionError):
        process.kill()


def podrzava_podproces(loop: asyncio.AbstractEventLoop) -> bool:
    """Da li ova petlja uopste ume da pokrene podproces.

    Na Windows-u to ume samo `ProactorEventLoop`; `SelectorEventLoop` na
    `create_subprocess_shell` baca `NotImplementedError` — i to sa PRAZNOM
    porukom, pa se u istoriji pokretanja nije videlo ni sta je puklo.

    Ovo nije rubni slucaj nego podrazumevano stanje dev servera: uvicorn u
    `loops/asyncio.py` bira Proactor samo kad ne pravi podproces za sebe, a
    `--reload` i `--workers` ga bas prave — pa se dobija Selector.

    Van Windows-a svaka petlja ume podproces, pa se ne trazi nista.
    """

    if sys.platform != "win32":
        return True
    return isinstance(loop, asyncio.ProactorEventLoop)


class PipelineRunner:
    """Pokrece definiciju nad korenom repozitorijuma."""

    def __init__(self, runs: RunStore, sink: LogSink,
                 timeout_seconds_override: int | None = None) -> None:
        self._runs = runs
        self._sink = sink
        # Samo za testove: pravi istek od minuta bi test drzao ceo minut.
        self._timeout_override = timeout_seconds_override
        self._tasks: dict[int, asyncio.Task[None] | concurrent.futures.Future] = {}
        self._processes: dict[int, asyncio.subprocess.Process] = {}
        self._cancelled: set[int] = set()
        self._seq: dict[int, int] = {}
        # Koji je korak trenutno u letu — treba ga i isteku i neocekivanoj
        # gresci da bi znali gde da stanu, a da ne prepisu vec zavrsene korake.
        self._trenutni_korak: dict[int, int] = {}
        # Petlja API procesa. `start()` je pozvan i iz asinhronih ruta (gde
        # vec postoji petlja u trenutnoj niti) i iz niti agenta
        # (`AgentRunner._u_niti`, obicna `threading.Thread` bez ikakve
        # petlje) — tada je ovo jedan od nacina da se `_vozi` uopste zakaze.
        self._main_loop: asyncio.AbstractEventLoop | None = None
        # Sopstvena petlja, u svojoj niti, za slucaj da nijedna zatecena ne
        # ume podproces (vidi `podrzava_podproces`). Pravi se tek kad zatreba
        # — masina bez tog problema nikad ne dobije ni nit.
        self._own_loop: asyncio.AbstractEventLoop | None = None
        self._own_thread: threading.Thread | None = None
        self._own_lock = threading.Lock()

    # ----------          JAVNO          ----------

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Upamti glavnu petlju API procesa za pozive bez sopstvene petlje."""

        self._main_loop = loop

    def start(self, run_id: int, definition: PipelineDefinition,
              root: Path) -> None:
        """Pokrece pokretanje. Ne blokira.

        Petlja se bira po jednom pitanju — ume li podproces:

        1. petlja OVE niti, ako je ima i ako ume (asinhrona ruta na Proactor-u);
        2. povezana petlja API procesa, ako ume (nit agenta, server bez `--reload`);
        3. sopstvena petlja motora, uvek.

        Zato pokretanje vise ne zavisi od toga kako je server pokrenut.
        """

        self._seq[run_id] = 0
        korutina = self._vozi(run_id, definition, root)

        try:
            trenutna = asyncio.get_running_loop()
        except RuntimeError:
            trenutna = None

        if trenutna is not None and podrzava_podproces(trenutna):
            self._tasks[run_id] = asyncio.create_task(korutina)
            return

        self._tasks[run_id] = asyncio.run_coroutine_threadsafe(
            korutina, self._petlja_za_podproces(),
        )

    def is_running(self, run_id: int) -> bool:
        zadatak = self._tasks.get(run_id)
        return zadatak is not None and not zadatak.done()

    def cancel(self, run_id: int) -> bool:
        """Gasi stablo procesa. Status upisuje sama petlja, ne ovaj poziv."""

        if not self.is_running(run_id):
            return False
        self._cancelled.add(run_id)
        proces = self._processes.get(run_id)
        if proces is not None:
            _terminate_tree(proces)
        return True

    def wait_blocking(self, run_id: int, timeout: float | None = None) -> None:
        """Ceka kraj iz niti koja nema svoju petlju (nit agenta, test).

        `wait()` je korutina i trazi petlju u pozivajucoj niti; ovde je nema.
        """

        zadatak = self._tasks.get(run_id)
        if isinstance(zadatak, concurrent.futures.Future):
            zadatak.result(timeout)

    def shutdown(self) -> None:
        """Gasi sopstvenu petlju i njenu nit, ako su uopste napravljene.

        Backend je dugovecan proces i nit je `daemon`, pa ovo nije uslov za
        uredno gasenje — postoji da testovi ne ostavljaju nit za sobom.
        """

        with self._own_lock:
            petlja, nit = self._own_loop, self._own_thread
            self._own_loop, self._own_thread = None, None

        if petlja is None:
            return
        petlja.call_soon_threadsafe(petlja.stop)
        if nit is not None:
            nit.join(timeout=5)
        petlja.close()

    def _petlja_za_podproces(self) -> asyncio.AbstractEventLoop:
        """Petlja na koju sme da se zakaze pokretanje.

        Prvo povezana petlja API procesa — ako ume podproces, nema razloga
        praviti drugu. Inace sopstvena, napravljena pri prvom pokretanju i
        posle toga deljena; svako pokretanje sa svojom niti bilo bi nit po
        pokretanju na dugovecnom procesu.
        """

        if self._main_loop is not None and podrzava_podproces(self._main_loop):
            return self._main_loop

        with self._own_lock:
            if self._own_loop is None:
                # Na Windows-u izricito Proactor; drugde podrazumevana petlja.
                self._own_loop = (
                    asyncio.ProactorEventLoop() if sys.platform == "win32"
                    else asyncio.new_event_loop()
                )
                self._own_thread = threading.Thread(
                    target=self._own_loop.run_forever,
                    name="codium-pipeline-loop",
                    daemon=True,
                )
                self._own_thread.start()
            return self._own_loop

    async def wait(self, run_id: int) -> None:
        """Ceka kraj pokretanja. Za testove i za uredno gasenje."""

        zadatak = self._tasks.get(run_id)
        if zadatak is None:
            return
        if isinstance(zadatak, asyncio.Task):
            await asyncio.gather(zadatak, return_exceptions=True)
        else:
            # `concurrent.futures.Future` (zakazano preko
            # `run_coroutine_threadsafe`) — `asyncio.gather` ga ne prihvata
            # direktno, pa se prvo umota u pravi `asyncio.Future`.
            await asyncio.gather(asyncio.wrap_future(zadatak), return_exceptions=True)

    # ----------          PETLJA          ----------

    async def _vozi(self, run_id: int, definition: PipelineDefinition,
                    root: Path) -> None:
        self._runs.mark_run_started(run_id)
        istek = (
            self._timeout_override if self._timeout_override is not None
            else definition.timeout_minutes * SEKUNDI_U_MINUTU
        )

        try:
            try:
                status, kod = await asyncio.wait_for(
                    self._koraci(run_id, definition, root), timeout=istek,
                )
                detalj = ""
            except TimeoutError:
                await self._ubij_i_zavrsi_trenutni(run_id, definition)
                status, kod = RunStatus.TIMEOUT, None
                detalj = f"istek od {definition.timeout_minutes} min"
            except Exception as greska:  # noqa: BLE001 - svaki kvar mora zavrsiti run
                # `working_dir` dolazi iz JSON definicije koju je covek napisao;
                # los koren, na primer, obara `create_subprocess_shell`. Run ne
                # sme ostati zaglavljen u `running` samo zato sto je pukao ovde.
                await self._ubij_i_zavrsi_trenutni(run_id, definition)
                status, kod = RunStatus.FAILED, None
                detalj = str(greska)

            if run_id in self._cancelled:
                status, kod, detalj = RunStatus.CANCELLED, None, "otkazano"

            self._runs.mark_run_finished(run_id, status, kod, detalj)
        finally:
            self._sink.flush()
            # Backend je dugovecan proces — ne sme svako zavrseno pokretanje
            # da ostavi zauvek zivu referencu (Task, brojac, itd.) iza sebe.
            self._processes.pop(run_id, None)
            self._cancelled.discard(run_id)
            self._trenutni_korak.pop(run_id, None)
            self._tasks.pop(run_id, None)
            self._seq.pop(run_id, None)

    async def _koraci(self, run_id: int, definition: PipelineDefinition,
                      root: Path) -> tuple[str, int | None]:
        """Vozi korake redom. Vraca konacni status i izlazni kod."""

        for redni, korak in enumerate(definition.steps):
            if run_id in self._cancelled:
                # Otkazano pre nego sto je ovaj korak i krenuo — bilo pre
                # prvog koraka, bilo u pauzi izmedju dva koraka.
                self._preskoci_ostatak(run_id, definition, od_koraka=redni)
                return (RunStatus.CANCELLED, None)

            self._trenutni_korak[run_id] = redni
            self._runs.mark_step_started(run_id, redni)
            kod = await self._korak(run_id, redni, korak, definition, root)
            self._trenutni_korak.pop(run_id, None)

            if run_id in self._cancelled:
                # Otkazano dok je bas ovaj korak radio — obaranje procesa
                # (u `cancel()`) mu je vec dalo izlazni kod, ali otkazivanje
                # mora da pobedi `continue_on_error`, ne da ga on progutaj.
                self._runs.mark_step_finished(run_id, redni, StepStatus.FAILED, kod)
                self._preskoci_ostatak(run_id, definition, od_koraka=redni + 1)
                return (RunStatus.CANCELLED, None)

            if kod == 0:
                self._runs.mark_step_finished(run_id, redni, StepStatus.SUCCESS, 0)
                continue

            self._runs.mark_step_finished(run_id, redni, StepStatus.FAILED, kod)
            if korak.continue_on_error:
                # Korak sme da padne — pokretanje ide dalje i moze da uspe.
                continue

            self._preskoci_ostatak(run_id, definition, od_koraka=redni + 1)
            return (RunStatus.FAILED, kod)

        return (RunStatus.SUCCESS, 0)

    async def _korak(self, run_id: int, idx: int, korak: StepDefinition,
                     definition: PipelineDefinition, root: Path) -> int:
        """Pokrece jedan korak i vraca njegov izlazni kod."""

        radni = root / korak.working_dir if korak.working_dir else root
        okruzenje = {**os.environ, **definition.env}

        dodatno: dict[str, object] = {}
        if sys.platform == "win32":
            dodatno["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            # Svoja grupa procesa, da `killpg` obori i decu.
            dodatno["start_new_session"] = True

        proces = await asyncio.create_subprocess_shell(
            korak.run,
            cwd=str(radni),
            env=okruzenje,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **dodatno,
        )
        self._processes[run_id] = proces

        await asyncio.gather(
            self._citaj(run_id, idx, proces.stdout, "stdout"),
            self._citaj(run_id, idx, proces.stderr, "stderr"),
        )
        kod = await proces.wait()
        self._sink.flush()
        return kod

    async def _citaj(self, run_id: int, idx: int,
                     stream: asyncio.StreamReader | None, ime: str) -> None:
        """Cita jedan tok red po red i salje ga sink-u."""

        if stream is None:
            return
        async for sirovo in stream:
            linija = sirovo.decode("utf-8", "replace").rstrip("\r\n")
            self._seq[run_id] = self._seq.get(run_id, 0) + 1
            self._sink.write(RunLogLine(
                run_id=run_id, step_idx=idx, seq=self._seq[run_id],
                stream=ime, line=linija,
            ))

    # ----------          POMOCNO          ----------

    def _preskoci_ostatak(self, run_id: int, definition: PipelineDefinition,
                          od_koraka: int) -> None:
        """Koraci koji nisu stigli na red nose `skipped`, ne `queued`."""

        for redni in range(od_koraka, len(definition.steps)):
            self._runs.mark_step_finished(run_id, redni, StepStatus.SKIPPED, None)

    async def _ubij_i_zavrsi_trenutni(self, run_id: int,
                                      definition: PipelineDefinition) -> None:
        """Gasi proces u letu i zatvara racune za istek i za gresku.

        Korak koji je bio u letu dobija svoj zavrsni status (FAILED) umesto
        da ostane zauvek "pokrenut a nikad zavrsen"; tek koraci POSLE njega
        postaju SKIPPED. Koraci koji su vec uspeli pre isteka/greske se ne
        diraju — prepisivanje njihovog statusa bi unistilo bas onu razliku
        (SKIPPED naspram vec-zavrseno) radi koje SKIPPED i postoji.
        """

        proces = self._processes.get(run_id)
        if proces is not None:
            _terminate_tree(proces)
            # `wait_for` je otkazao korutinu usred `await proces.wait()`, pa
            # taj poziv nikad nije zavrsen — bez novog await-a ostaje
            # nezatvoren transport (ResourceWarning pri gasenju petlje).
            with contextlib.suppress(Exception):
                await proces.wait()

        trenutni = self._trenutni_korak.get(run_id)
        if trenutni is not None:
            self._runs.mark_step_finished(run_id, trenutni, StepStatus.FAILED, None)
            self._preskoci_ostatak(run_id, definition, od_koraka=trenutni + 1)
        else:
            self._preskoci_ostatak(run_id, definition, od_koraka=0)
