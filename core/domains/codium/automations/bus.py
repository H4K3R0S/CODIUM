# ========== RAZGLAS DOGADJAJA ==========
# Jednostavan SINHRONI razglas u procesu. Nema reda poruka, nema spoljne
# infrastrukture — jedan proces, jedan pretplatnik po pravilu.
#
# Modul je namerno bez teskih uvoza (samo modeli): podsistemi koji objavljuju
# dogadjaje (pipeline, isporuka, infrastruktura, merenje) uvoze bas njega, pa
# bi svaki tezi uvoz ovde zatvorio krug kroz pola domena.
from __future__ import annotations

import threading
from collections.abc import Callable

from core.domains.codium.automations.models import Event

Pretplatnik = Callable[[Event], None]


class EventBus:
    """Objavi dogadjaj, stigne svima koji slusaju.

    Sinhrono: objavljivanje se vraca tek kad su svi pretplatnici zavrsili.
    To je namerno — dogadjaj koji je proizvela akcija mora da bude vidljiv u
    istom potezu, inace zastita od petlje ne bi imala sta da broji.
    """

    def __init__(self) -> None:
        self._pretplatnici: list[Pretplatnik] = []
        self._brava = threading.Lock()
        # Greske pretplatnika se ne gutaju tiho nego prijavljuju ovde.
        self._na_gresku: Callable[[Exception], None] = lambda _: None

    def subscribe(self, handler: Pretplatnik) -> None:
        with self._brava:
            if handler not in self._pretplatnici:
                self._pretplatnici.append(handler)

    def unsubscribe(self, handler: Pretplatnik) -> None:
        with self._brava:
            if handler in self._pretplatnici:
                self._pretplatnici.remove(handler)

    def on_error(self, handler: Callable[[Exception], None]) -> None:
        self._na_gresku = handler

    def publish(self, event: Event) -> int:
        """Salje dogadjaj svim pretplatnicima. Vraca koliko ih je primilo.

        Pretplatnik koji pukne NE prekida ostale: automatizacija koja se
        sapletla ne sme da obori pipeline koji je dogadjaj objavio.
        """

        with self._brava:
            primaoci = list(self._pretplatnici)

        for pretplatnik in primaoci:
            try:
                pretplatnik(event)
            except Exception as greska:  # noqa: BLE001 - objavljivac mora da prezivi
                self._na_gresku(greska)
        return len(primaoci)

    def clear(self) -> None:
        """Skida sve pretplatnike (koristi se u testovima i pri gasenju)."""

        with self._brava:
            self._pretplatnici.clear()

    def __len__(self) -> int:
        return len(self._pretplatnici)


# Jedan proces = jedan razglas. Podsistemi objavljuju OVDE.
event_bus = EventBus()


def publish(name: str, payload: dict | None = None, *, origin: str = "",
            depth: int = 0) -> None:
    """Kratica za objavljivanje sa deljenog razglasa.

    Postoji da pozivalac (pipeline, isporuka…) ne mora da uvozi ni `Event` ni
    sam razglas — jedan poziv, jedan uvoz.
    """

    event_bus.publish(Event(name=name, payload=payload or {}, origin=origin,
                            depth=depth))
