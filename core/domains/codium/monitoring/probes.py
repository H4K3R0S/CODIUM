# ========== PROBE ==========
# Cist modul: ulaz je konfiguracija, izlaz su uzorci. Bez baze, bez kapije,
# bez dnevnika — zato se svaka proba testira nad laznim izvrsiocem, bez mreze
# i bez Docker-a.
#
# Svaka proba UVEK vraca `up` (0 ili 1). To je jedina metrika koja postoji za
# sve tipove servisa, pa je i jedina nad kojom pravilo alarma sme da racuna da
# ce je dobiti.
from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from core.domains.codium.command import (
    CommandError,
    CommandResult,
    ToolMissing,
    run_command,
)
from core.domains.codium.monitoring.models import Metric, MetricSample, ProbeResult

# Koliko dugo se ceka odgovor pre nego sto se proba smatra neuspelom.
ROK_SEKUNDI = 5.0

# Bajtova u megabajtu — merenja se prijavljuju u MB, jer je to jedinica koju
# covek cita na ekranu.
_MB = 1024 * 1024


def _uzorak(metric: str, value: float, service_id: int | None) -> MetricSample:
    return MetricSample(metric=metric, value=value, service_id=service_id)


def probe_tcp(host: str, port: int, *, service_id: int | None = None,
              timeout: float = ROK_SEKUNDI) -> ProbeResult:
    """Da li neko slusa na portu, i koliko je trebalo da se veza otvori."""

    pocetak = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            trajanje = (time.monotonic() - pocetak) * 1000
    except OSError as greska:
        return ProbeResult([_uzorak(Metric.UP, 0.0, service_id)], str(greska))

    return ProbeResult(
        [
            _uzorak(Metric.UP, 1.0, service_id),
            _uzorak(Metric.LATENCY_MS, round(trajanje, 1), service_id),
        ],
        f"{host}:{port} odgovara",
    )


def probe_http(url: str, *, expected_status: int = 200,
               service_id: int | None = None,
               timeout: float = ROK_SEKUNDI,
               opener: Callable[..., object] | None = None) -> ProbeResult:
    """Da li URL odgovara ocekivanim statusom, i za koliko.

    Status koji nije ocekivan je `up = 0`, ali se latencija svejedno belezi:
    server koji vraca 500 za dve sekunde nije isto sto i server koji cuti.
    """

    otvori = opener or urllib.request.urlopen
    pocetak = time.monotonic()
    try:
        odgovor = otvori(url, timeout=timeout)
        status = getattr(odgovor, "status", None) or odgovor.getcode()
        zatvori = getattr(odgovor, "close", None)
        if callable(zatvori):
            zatvori()
    except urllib.error.HTTPError as greska:
        # HTTP greska JESTE odgovor — server radi, samo ne vraca ono sto se
        # ocekuje. Zato se meri i latencija.
        trajanje = (time.monotonic() - pocetak) * 1000
        return ProbeResult(
            [
                _uzorak(Metric.UP, 1.0 if greska.code == expected_status else 0.0,
                        service_id),
                _uzorak(Metric.LATENCY_MS, round(trajanje, 1), service_id),
            ],
            f"HTTP {greska.code}",
        )
    except Exception as greska:  # noqa: BLE001 - mreza puca na mnogo nacina
        return ProbeResult([_uzorak(Metric.UP, 0.0, service_id)], str(greska))

    trajanje = (time.monotonic() - pocetak) * 1000
    return ProbeResult(
        [
            _uzorak(Metric.UP, 1.0 if status == expected_status else 0.0,
                    service_id),
            _uzorak(Metric.LATENCY_MS, round(trajanje, 1), service_id),
        ],
        f"HTTP {status}",
    )


def probe_process(pid: int | None, *, service_id: int | None = None,
                  psutil_module=None) -> ProbeResult:
    """Da li proces zivi, i koliko trosi.

    Bez `psutil`-a ostaje samo `up` — merenje potrosnje nije uslov da se vidi
    da li servis radi, pa se odsustvo biblioteke ne pretvara u kvar.
    """

    if pid is None:
        return ProbeResult([_uzorak(Metric.UP, 0.0, service_id)], "nema PID-a")

    if psutil_module is None:
        try:
            import psutil as psutil_module
        except ImportError:
            return ProbeResult([_uzorak(Metric.UP, 1.0, service_id)],
                               "psutil nedostupan — samo `up`")

    try:
        proces = psutil_module.Process(pid)
        cpu = float(proces.cpu_percent(interval=None))
        memorija = float(proces.memory_info().rss) / _MB
    except Exception as greska:  # noqa: BLE001 - psutil puca na mnogo nacina
        return ProbeResult([_uzorak(Metric.UP, 0.0, service_id)], str(greska))

    return ProbeResult(
        [
            _uzorak(Metric.UP, 1.0, service_id),
            _uzorak(Metric.CPU_PERCENT, round(cpu, 1), service_id),
            _uzorak(Metric.MEMORY_MB, round(memorija, 1), service_id),
        ],
        f"pid {pid}",
    )


def probe_docker(container: str, *, service_id: int | None = None,
                 runner: Callable[..., CommandResult] = run_command) -> ProbeResult:
    """Stanje kontejnera i njegova potrosnja.

    `docker stats --no-stream` je jedan poziv koji vraca i procesor i memoriju;
    razdvajati ih na dva poziva znacilo bi dva podprocesa po uzorku.
    """

    try:
        stanje = runner(["docker", "inspect", "-f", "{{.State.Running}}",
                         container], timeout=int(ROK_SEKUNDI) + 5)
    except ToolMissing as greska:
        return ProbeResult([_uzorak(Metric.UP, 0.0, service_id)], str(greska))
    except CommandError as greska:
        # Ugasen Docker Desktop nije isto sto i neinstaliran Docker; kontejner
        # je i dalje `up = 0`, ali razlog mora da kaze sta da se uradi.
        return ProbeResult([_uzorak(Metric.UP, 0.0, service_id)],
                           f"Docker ne odgovara (da li je pokrenut?): {greska}")

    radi = stanje.exit_code == 0 and stanje.output.strip().lower() == "true"
    if not radi:
        return ProbeResult([_uzorak(Metric.UP, 0.0, service_id)],
                           stanje.output.strip()[:200])

    uzorci = [_uzorak(Metric.UP, 1.0, service_id)]
    try:
        potrosnja = runner(
            ["docker", "stats", "--no-stream",
             "--format", "{{.CPUPerc}}\t{{.MemUsage}}", container],
            timeout=int(ROK_SEKUNDI) + 5,
        )
    except CommandError:
        # Kontejner radi — to je vec izmereno. Potrosnja je dodatak, ne uslov.
        return ProbeResult(uzorci, "radi (bez potrosnje)")

    if potrosnja.exit_code == 0:
        cpu, memorija = _procitaj_stats(potrosnja.output)
        if cpu is not None:
            uzorci.append(_uzorak(Metric.CPU_PERCENT, cpu, service_id))
        if memorija is not None:
            uzorci.append(_uzorak(Metric.MEMORY_MB, memorija, service_id))

    return ProbeResult(uzorci, "radi")


# ==========          CITANJE `docker stats`          ==========

_JEDINICE = {"b": 1 / _MB, "kib": 1 / 1024, "mib": 1.0, "gib": 1024.0,
             "kb": 1 / 1024, "mb": 1.0, "gb": 1024.0}


def _procitaj_stats(izlaz: str) -> tuple[float | None, float | None]:
    """Cita `12.34%\tab45.6MiB / 1.9GiB` u procenat i megabajte."""

    delovi = izlaz.strip().split("\t")
    if len(delovi) < 2:
        return (None, None)

    cpu = None
    sirov_cpu = delovi[0].strip().rstrip("%")
    try:
        cpu = round(float(sirov_cpu), 1)
    except ValueError:
        cpu = None

    memorija = _u_megabajte(delovi[1].split("/")[0].strip())
    return (cpu, memorija)


def _u_megabajte(vrednost: str) -> float | None:
    """`45.6MiB` u broj megabajta. Nepoznata jedinica vraca None."""

    broj = ""
    jedinica = ""
    for znak in vrednost:
        if znak.isdigit() or znak == ".":
            broj += znak
        elif not znak.isspace():
            jedinica += znak

    if not broj:
        return None
    faktor = _JEDINICE.get(jedinica.lower())
    if faktor is None:
        return None
    try:
        return round(float(broj) * faktor, 1)
    except ValueError:
        return None
