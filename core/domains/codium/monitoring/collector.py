# ========== POZADINSKI SAKUPLJAC ==========
# Jedan zadatak koji se budi na zadatih 30 sekundi, pusti jedan krug merenja i
# vrati se na spavanje. Merenje samo po sebi je u `MonitoringService.collect_once`
# — ovde je samo raspored i uredno gasenje.
#
# Krug merenja je sinhron (SQLite upisi, podprocesi, socket-i), pa se vozi u
# niti kroz `asyncio.to_thread`: u petlji bi na svakom merenju zaustavio ceo
# API proces.
from __future__ import annotations

import asyncio
from collections.abc import Callable

# Razmak izmedju dva merenja. Kraci znaci vise redova bez vise znanja: servis
# koji padne primeti se za pola minuta, a to je granica na kojoj covek ionako
# reaguje.
RAZMAK_SEKUNDI = 30.0

# Koliko cesto se radi zadrzavanje uzoraka. Jednom dnevno je dovoljno — posao
# je jeftin, ali dira celu tabelu.
RAZMAK_ODRZAVANJA_SEKUNDI = 24 * 60 * 60.0


class MetricCollector:
    """Pozadinsko merenje, sa urednim gasenjem.

    Gasenje je vazno koliko i merenje: zadatak koji prezivi gasenje aplikacije
    nastavlja da pise u bazu koju vise niko ne gleda.
    """

    def __init__(self, collect: Callable[[], int],
                 maintain: Callable[[], dict[str, int]] | None = None,
                 interval_seconds: float = RAZMAK_SEKUNDI,
                 maintenance_seconds: float = RAZMAK_ODRZAVANJA_SEKUNDI,
                 on_error: Callable[[Exception], None] | None = None) -> None:
        self._collect = collect
        self._maintain = maintain
        self._interval = interval_seconds
        self._maintenance = maintenance_seconds
        self._on_error = on_error or (lambda _: None)
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        # Koliko je krugova zavrseno — testovi cekaju bas ovo, umesto da spavaju.
        self.rounds = 0

    # ----------          ZIVOTNI CIKLUS          ----------

    def start(self) -> None:
        """Pokrece zadatak. Ponovljen poziv ne pravi drugi."""

        if self._task is not None and not self._task.done():
            return
        self._stop = asyncio.Event()
        self.rounds = 0
        self._task = asyncio.create_task(self._vozi(), name="codium-collector")

    async def stop(self) -> None:
        """Trazi gasenje i saceka da krug u letu zavrsi."""

        if self._task is None:
            return
        self._stop.set()
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001, S110
            pass
        self._task = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    # ----------          PETLJA          ----------

    async def _vozi(self) -> None:
        od_odrzavanja = 0.0
        while not self._stop.is_set():
            await self._krug()

            od_odrzavanja += self._interval
            if self._maintain is not None and od_odrzavanja >= self._maintenance:
                od_odrzavanja = 0.0
                await self._odrzavanje()

            try:
                # Cekanje na dogadjaj, ne `sleep`: gasenje ne treba da ceka
                # ceo razmak da bi bilo primeceno.
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
            except TimeoutError:
                continue

    async def _krug(self) -> None:
        try:
            await asyncio.to_thread(self._collect)
            self.rounds += 1
        except asyncio.CancelledError:
            raise
        except Exception as greska:  # noqa: BLE001 - petlja mora da prezivi
            # Merenje koje pukne ne sme da ubije sakupljac: sledeci krug moze
            # da uspe, a mrtav sakupljac se primeti tek kad zatreba.
            self._on_error(greska)

    async def _odrzavanje(self) -> None:
        try:
            await asyncio.to_thread(self._maintain)
        except asyncio.CancelledError:
            raise
        except Exception as greska:  # noqa: BLE001 - isto pravilo kao gore
            self._on_error(greska)
