# ========== KES IZVESTAJA ==========
# Agregat preko devedeset dana nije jeftin, a ekran se cesto ponovo iscrtava
# (promena taba, povratak na stranu). Zato rezultat po kljucu stoji u memoriji
# 60 sekundi.
#
# Kes je u memoriji, ne u bazi: izvestaj je izveden podatak, a izvedeni podatak
# koji se cuva postaje drugo skladiste koje moze da se razidje sa izvorom.
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

TRAJANJE_SEKUNDI = 60.0


class ReportCache:
    """Kljuc -> (vreme upisa, vrednost), sa istekom."""

    def __init__(self, ttl_seconds: float = TRAJANJE_SEKUNDI,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._zapisi: dict[str, tuple[float, Any]] = {}

    def get_or_compute(self, key: str, compute: Callable[[], Any]) -> Any:
        """Vraca zapamceno ako je sveze, inace racuna i pamti."""

        sada = self._clock()
        zapamceno = self._zapisi.get(key)
        if zapamceno is not None and sada - zapamceno[0] < self._ttl:
            return zapamceno[1]

        vrednost = compute()
        self._zapisi[key] = (sada, vrednost)
        return vrednost

    def invalidate(self) -> None:
        """Prazni kes. Postoji za testove i za rucno osvezavanje."""

        self._zapisi.clear()

    def __len__(self) -> int:
        return len(self._zapisi)
