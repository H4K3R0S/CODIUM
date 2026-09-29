# ==========          POKRETAC POSLA          ==========
# Daemon nit, isti obrazac koji projekat vec koristi (`streaming.py`,
# `installer.py`, `disk_monitor.py`). Nema reda poslova i ne uvodi se.
#
# Stanje zivi u bazi, ne u niti: zato restart API-ja ne gubi posao, a pauza na
# odobrenju ne trazi nit koja spava — nit umre, a nastavak je nova nit.
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from core.domains.codium.agents.loop import AgentLoop
from core.domains.codium.agents.models import Agent, AgentRun
from core.domains.codium.agents.repository import RunRepository

logger = logging.getLogger(__name__)

# Fabrika petlje za jedan posao: petlja zavisi od projekta (explorer), pa se
# pravi po poslu, a ne jednom za ceo proces.
LoopFactory = Callable[[Agent, AgentRun], AgentLoop]


class AgentRunner:
    """Pokrece posao u pozadini i garantuje da nece ostati bez ishoda."""

    def __init__(self, loop_factory: LoopFactory, runs: RunRepository) -> None:
        self._loop_factory = loop_factory
        self._runs = runs

    def start(self, agent: Agent, run: AgentRun) -> None:
        self._u_niti(agent, run, nastavak=False)

    def resume(self, agent: Agent, run: AgentRun) -> None:
        self._u_niti(agent, run, nastavak=True)

    def _u_niti(self, agent: Agent, run: AgentRun, *, nastavak: bool) -> None:
        def posao() -> None:
            try:
                petlja = self._loop_factory(agent, run)
                if nastavak:
                    petlja.resume(agent, run)
                else:
                    petlja.run(agent, run)
            except Exception as greska:
                # Nit koja umre bez traga ostavila bi posao zauvek u
                # „running", i GUI bi ga vecno osvezavao.
                logger.exception("Posao agenta je pukao")
                # Petlja je mogla da upise korake pre nego sto je pukla; bez
                # brojanja stvarno upisanih koraka `steps_used` bi ostao 0 i
                # GUI bi prikazao pogresan broj za posao koji je stvarno
                # radio.
                self._runs.finish(
                    run.id, status="failed",
                    result=f"Posao je pukao: {greska}",
                    steps_used=len(self._runs.steps(run.id)),
                )

        threading.Thread(target=posao, daemon=True,
                         name=f"codium-agent-{run.id}").start()
