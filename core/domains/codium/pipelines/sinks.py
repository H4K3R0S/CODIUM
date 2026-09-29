# ========== SERIJSKI UPIS LOGA ==========
# Hiljadu redova loga ne sme da znaci hiljadu transakcija. Serije zive ovde,
# a ne u motoru — tako se motor testira sa sink-om koji samo skuplja, a
# serije se testiraju laznim satom, bez cekanja.
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from core.domains.codium.pipelines.models import RunLogLine

# Koliko redova ide u jednu transakciju i koliko dugo se ceka na dopunu.
VELICINA_SERIJE = 50
PROZOR_SEKUNDI = 0.2


class LogWriter(Protocol):
    """Ono sto sink zove da bi red stvarno zavrsio u bazi."""

    def append(self, lines: list[RunLogLine]) -> None: ...


class LogSink(Protocol):
    """Ono sto motor zove za svaki red."""

    def write(self, line: RunLogLine) -> None: ...

    def flush(self) -> None: ...


class BatchingLogSink:
    """Skuplja redove i salje ih u serijama.

    Serija odlazi kad se napuni ili kad prozor istekne. Prozor se proverava
    pri upisu, ne tajmerom u pozadini: tajmer bi trazio svoj zadatak, svoje
    gasenje i svoj skup gresaka, a `flush()` na kraju koraka i na kraju
    pokretanja ionako zatvara rep.
    """

    def __init__(self, writer: LogWriter,
                 clock: Callable[[], float] = time.monotonic,
                 batch_size: int = VELICINA_SERIJE,
                 window_seconds: float = PROZOR_SEKUNDI) -> None:
        self._writer = writer
        self._clock = clock
        self._batch_size = batch_size
        self._window = window_seconds
        self._buffer: list[RunLogLine] = []
        self._prvi_u_seriji: float | None = None

    def write(self, line: RunLogLine) -> None:
        if self._prvi_u_seriji is None:
            self._prvi_u_seriji = self._clock()
        self._buffer.append(line)

        napunjena = len(self._buffer) >= self._batch_size
        istekla = self._clock() - self._prvi_u_seriji >= self._window
        if napunjena or istekla:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        self._writer.append(self._buffer)
        self._buffer = []
        self._prvi_u_seriji = None


class CollectingLogSink:
    """Sink koji nista ne upisuje — skuplja u listu, za testove motora."""

    def __init__(self) -> None:
        self.lines: list[RunLogLine] = []

    def write(self, line: RunLogLine) -> None:
        self.lines.append(line)

    def flush(self) -> None:
        return None
