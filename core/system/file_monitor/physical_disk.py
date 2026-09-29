# ========== FIZIČKA TOPOLOGIJA DISKOVA ==========
# Mapira logičke particije (E:\, G:\) na fizički disk (npr. jedan USB sa dve
# particije). Upit ka OS-u je lenj (PowerShell) i injektabilan radi testova;
# van Windows-a ili pri grešci degradira (vraća None/[]) bez pada.
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Partition:
    mount: str            # normalizovano "E:\\"
    disk_number: int
    size_bytes: int | None = None


@dataclass(frozen=True)
class PhysicalDisk:
    number: int
    model: str = ""
    serial: str = ""
    bus_type: str = ""
    size_bytes: int | None = None


@dataclass(frozen=True)
class DiskGroup:
    physical: PhysicalDisk
    partitions: tuple[Partition, ...]

    def sibling_mounts(self, mount: str) -> tuple[str, ...]:
        """Ostale particije istog fizičkog diska (bez zadatog mount-a)."""
        m = _norm(mount)
        return tuple(p.mount for p in self.partitions if p.mount != m)


# ---------- normalizacija ----------
def _norm(mount: str) -> str:
    letter = mount.strip().rstrip(":\\/").rstrip(":")
    if len(letter) == 1:
        return f"{letter.upper()}:\\"
    return mount


# ---------- PowerShell upit (default) ----------
def _default_query() -> tuple[list[dict], list[dict]]:
    parts = _run_ps(
        "Get-Partition | Where-Object DriveLetter | ForEach-Object { "
        "[pscustomobject]@{ DriveLetter=$_.DriveLetter; DiskNumber=$_.DiskNumber; "
        "Size=$_.Size } } | ConvertTo-Json -Compress"
    )
    disks = _run_ps(
        "Get-Disk | ForEach-Object { [pscustomobject]@{ Number=$_.Number; "
        "Model=$_.FriendlyName; Serial=$_.SerialNumber; BusType=[string]$_.BusType; "
        "Size=$_.Size } } | ConvertTo-Json -Compress"
    )
    return _as_list(parts), _as_list(disks)


def _run_ps(script: str) -> object:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=20, check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return json.loads(result.stdout)
    except Exception:  # noqa: BLE001
        return []  # degradacija bez pada


def _as_list(value: object) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


# ---------- javni API ----------
Query = Callable[[], tuple[list[dict], list[dict]]]


def disk_group_for(mount: str, *, query: Query | None = None) -> DiskGroup | None:
    """Vrati fizički disk i sve njegove particije za dati mount (ili None)."""
    q = query or _default_query
    parts_raw, disks_raw = q()

    partitions = [
        Partition(mount=_norm(f"{p['DriveLetter']}:"),
                  disk_number=int(p["DiskNumber"]),
                  size_bytes=_int_or_none(p.get("Size")))
        for p in parts_raw
        if p.get("DriveLetter") and p.get("DiskNumber") is not None
    ]

    target = _norm(mount)
    match = next((p for p in partitions if p.mount == target), None)
    if match is None:
        return None

    number = match.disk_number
    siblings = tuple(p for p in partitions if p.disk_number == number)
    disk_meta = next((d for d in disks_raw if int(d.get("Number", -1)) == number), {})
    physical = PhysicalDisk(
        number=number,
        model=str(disk_meta.get("Model", "") or ""),
        serial=str(disk_meta.get("Serial", "") or "").strip(),
        bus_type=str(disk_meta.get("BusType", "") or ""),
        size_bytes=_int_or_none(disk_meta.get("Size")),
    )
    return DiskGroup(physical=physical, partitions=siblings)


def physical_map(*, query: Query | None = None) -> dict[str, PhysicalDisk]:
    """Mapa svih mountova -> fizički disk kojem particija pripada."""
    q = query or _default_query
    parts_raw, disks_raw = q()

    disks: dict[int, PhysicalDisk] = {}
    for d in disks_raw:
        try:
            num = int(d.get("Number"))
        except (TypeError, ValueError):
            continue
        disks[num] = PhysicalDisk(
            number=num,
            model=str(d.get("Model", "") or ""),
            serial=str(d.get("Serial", "") or "").strip(),
            bus_type=str(d.get("BusType", "") or ""),
            size_bytes=_int_or_none(d.get("Size")),
        )

    result: dict[str, PhysicalDisk] = {}
    for p in parts_raw:
        letter = p.get("DriveLetter")
        num = p.get("DiskNumber")
        if not letter or num is None:
            continue
        num = int(num)
        result[_norm(f"{letter}:")] = disks.get(num, PhysicalDisk(number=num))
    return result


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
