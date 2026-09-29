# ========== OCENA PRAVILA ALARMA ==========
# Cist modul: ulaz je pravilo i poslednji uzorci, izlaz je odluka. Bez baze i
# bez notifikacija — zato se ceo raspored „dva prekrsaja ne pale, tri pale"
# testira nad listama brojeva, bez ijednog reda u SQLite-u.
from __future__ import annotations

from core.domains.codium.monitoring.models import (
    AlertRule,
    AlertState,
    Comparison,
    MetricSample,
)


def krsi(value: float, comparison: str, threshold: float) -> bool:
    """Da li jedna izmerena vrednost krsi prag.

    Jednakost nad brojevima sa pokretnim zarezom je namerno tolerantna: prag
    `1` i izmereno `0.9999999` su isto za coveka koji je pravilo pisao.
    """

    if comparison == Comparison.LT:
        return value < threshold
    if comparison == Comparison.GT:
        return value > threshold
    if comparison == Comparison.EQ:
        return abs(value - threshold) < 1e-9
    # Nepoznat uslov ne sme tiho da prodje kao „ne krsi" — pravilo koje niko
    # ne razume je pravilo koje nikad nece upaliti alarm, a covek ce misliti
    # da ga cuva.
    raise ValueError(f"Nepoznat uslov poredjenja: {comparison}")


def oceni(rule: AlertRule, samples: list[MetricSample],
          *, alarm_gori: bool) -> str:
    """Odlucuje sta pravilo trazi nad zadatim uzorcima.

    Args:
        rule: Pravilo koje se ocenjuje.
        samples: Poslednji uzorci te metrike, NAJNOVIJI PRVI.
        alarm_gori: Da li za ovo pravilo vec postoji upaljen alarm.

    Returns:
        `FIRING` — treba upaliti (jos ne gori),
        `RESOLVED` — treba ugasiti (gori, a vrednost se vratila),
        `OK` — ne treba nista.

    Prag mora da bude prekrsen `for_samples` puta ZAREDOM. Bez toga jedan
    promasen uzorak (mreza zatreperi) pali alarm, pa alarmi prestanu da znace
    isto — a onda i da se citaju.
    """

    if not rule.enabled or not samples:
        return AlertState.OK

    potrebno = max(1, rule.for_samples)
    poslednji = samples[:potrebno]

    if alarm_gori:
        # Za gasenje je dovoljan JEDAN uzorak u opsegu: kvar koji je prosao
        # prosao je, a cekanje jos dva uzorka bi drzalo laznu uzbunu.
        if not krsi(poslednji[0].value, rule.comparison, rule.threshold):
            return AlertState.RESOLVED
        return AlertState.OK

    if len(poslednji) < potrebno:
        # Jos nema dovoljno merenja da se odluci — servis je tek dodat.
        return AlertState.OK

    svi_krse = all(
        krsi(uzorak.value, rule.comparison, rule.threshold)
        for uzorak in poslednji
    )
    return AlertState.FIRING if svi_krse else AlertState.OK


def opis(rule: AlertRule, value: float | None) -> str:
    """Recenica za notifikaciju i dnevnik."""

    cilj = f"servis {rule.service_id}" if rule.service_id else "node"
    izmereno = "nepoznato" if value is None else f"{value:g}"
    return (f"{cilj}: {rule.metric} {rule.comparison} {rule.threshold:g} "
            f"(izmereno {izmereno})")
