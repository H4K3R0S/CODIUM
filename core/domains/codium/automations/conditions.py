# ========== USLOVI PRAVILA ==========
# Mali izraz nad poljima dogadjaja: poredjenja, `AND`, `OR`, `contains`.
#
# Parsira se u STABLO i izvrsava sopstvenim prolaskom kroz to stablo.
# NIKADA `eval`. To je pravilo bezbednosti, ne stila: uslov pise covek u polje
# na ekranu, a `eval` nad tim poljem znaci da svako ko dodje do ekrana moze da
# pokrene bilo sta u procesu backend-a.
#
# Zato ovde nema ni `exec`, ni `compile`, ni `__import__` — parser prihvata
# tacno ono sto gramatika ispod opisuje, a sve ostalo odbija PRI PARSIRANJU,
# pre nego sto ijedna vrednost bude procitana.
#
# Gramatika:
#   izraz     := ili
#   ili       := i ( "OR" i )*
#   i         := osnovni ( "AND" osnovni )*
#   osnovni   := "(" izraz ")" | poredjenje
#   poredjenje := polje operator vrednost
#   operator  := "==" | "!=" | "<" | "<=" | ">" | ">=" | "contains"
#   vrednost  := broj | tekst u navodnicima | true | false | null
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

OPERATORI = ("==", "!=", "<=", ">=", "<", ">", "contains")

# Redosled je bitan: `<=` mora pre `<`, inace bi se `<=` procitalo kao `<`.
_TOKEN = re.compile(
    r"""
    \s*(?:
        (?P<zagrada>[()])
      | (?P<spoj>\bAND\b|\bOR\b)
      | (?P<operator><=|>=|==|!=|<|>|\bcontains\b)
      | (?P<broj>-?\d+(?:\.\d+)?)
      | (?P<tekst>"[^"]*"|'[^']*')
      | (?P<rec>[A-Za-z_][A-Za-z0-9_.]*)
    )
    """,
    re.VERBOSE,
)


class ConditionError(ValueError):
    """Uslov nije ispravan. Poruka kaze sta je zasmetalo i gde."""


@dataclass(frozen=True)
class Poredjenje:
    """List stabla: `polje operator vrednost`."""

    polje: str
    operator: str
    vrednost: Any


@dataclass(frozen=True)
class Spoj:
    """Cvor stabla: `levo AND desno` ili `levo OR desno`."""

    vrsta: str   # "AND" | "OR"
    levo: Any
    desno: Any


# ==========          PARSIRANJE          ==========

def _tokenizuj(izraz: str) -> list[tuple[str, str]]:
    tokeni: list[tuple[str, str]] = []
    mesto = 0
    while mesto < len(izraz):
        if izraz[mesto].isspace():
            mesto += 1
            continue
        pogodak = _TOKEN.match(izraz, mesto)
        if pogodak is None or pogodak.end() == mesto:
            raise ConditionError(
                f"Nerazumljiv znak na mestu {mesto}: {izraz[mesto:mesto + 12]!r}")
        vrsta = pogodak.lastgroup
        tokeni.append((vrsta, pogodak.group(vrsta).strip()))
        mesto = pogodak.end()
    return tokeni


class _Parser:
    def __init__(self, tokeni: list[tuple[str, str]]) -> None:
        self._tokeni = tokeni
        self._mesto = 0

    def _gledaj(self) -> tuple[str, str] | None:
        return (self._tokeni[self._mesto]
                if self._mesto < len(self._tokeni) else None)

    def _uzmi(self) -> tuple[str, str]:
        if self._mesto >= len(self._tokeni):
            raise ConditionError("Uslov se prekida ranije nego sto bi trebalo.")
        token = self._tokeni[self._mesto]
        self._mesto += 1
        return token

    def parsiraj(self):
        stablo = self._ili()
        if self._mesto != len(self._tokeni):
            visak = self._tokeni[self._mesto][1]
            raise ConditionError(f"Visak u uslovu, pocev od: {visak!r}")
        return stablo

    def _ili(self):
        levo = self._i()
        while (token := self._gledaj()) and token == ("spoj", "OR"):
            self._uzmi()
            levo = Spoj("OR", levo, self._i())
        return levo

    def _i(self):
        levo = self._osnovni()
        while (token := self._gledaj()) and token == ("spoj", "AND"):
            self._uzmi()
            levo = Spoj("AND", levo, self._osnovni())
        return levo

    def _osnovni(self):
        token = self._gledaj()
        if token is None:
            raise ConditionError("Uslov je prazan tamo gde se ocekuje poredjenje.")

        if token == ("zagrada", "("):
            self._uzmi()
            unutra = self._ili()
            zatvorena = self._uzmi()
            if zatvorena != ("zagrada", ")"):
                raise ConditionError("Nedostaje zatvorena zagrada.")
            return unutra

        return self._poredjenje()

    def _poredjenje(self) -> Poredjenje:
        vrsta, polje = self._uzmi()
        if vrsta != "rec":
            raise ConditionError(
                f"Na mestu polja stoji {polje!r}, a ocekuje se ime polja.")

        vrsta_op, operator = self._uzmi()
        if vrsta_op != "operator":
            raise ConditionError(
                f"Posle polja `{polje}` ocekuje se operator, a stoji {operator!r}. "
                f"Dozvoljeni: {', '.join(OPERATORI)}.")

        return Poredjenje(polje, operator, self._vrednost(polje))

    def _vrednost(self, polje: str) -> Any:
        vrsta, sirovo = self._uzmi()
        if vrsta == "broj":
            return float(sirovo) if "." in sirovo else int(sirovo)
        if vrsta == "tekst":
            return sirovo[1:-1]
        if vrsta == "rec":
            if sirovo == "true":
                return True
            if sirovo == "false":
                return False
            if sirovo == "null":
                return None
            # Ovde se odbija i `f(x)`: `f` bi bilo `rec`, a zatim `(` — poziv
            # funkcije nikad ne prodje kroz gramatiku.
            raise ConditionError(
                f"Vrednost uz `{polje}` mora biti broj, tekst u navodnicima, "
                f"`true`, `false` ili `null` — a stoji {sirovo!r}.")
        raise ConditionError(
            f"Vrednost uz `{polje}` nije prepoznata: {sirovo!r}.")


def parse(izraz: str):
    """Cita uslov u stablo. Prazan uslov znaci „uvek".

    Raises:
        ConditionError: Uslov nije ispravan. Odbija se PRI PARSIRANJU, pre nego
            sto ijedna vrednost bude procitana.
    """

    ociscen = (izraz or "").strip()
    if not ociscen:
        return None
    return _Parser(_tokenizuj(ociscen)).parsiraj()


# ==========          OCENA          ==========

def _uporedi(levo: Any, operator: str, desno: Any) -> bool:
    if operator == "==":
        return levo == desno
    if operator == "!=":
        return levo != desno
    if operator == "contains":
        # `contains` radi i nad tekstom i nad listom; nad nicim je netacno,
        # ne greska — polje koje dogadjaj nije doneo prosto ne sadrzi nista.
        if levo is None:
            return False
        try:
            return desno in levo
        except TypeError:
            return False

    # Poredjenja po velicini nad nicim su NETACNA, ne greska: dogadjaj koji
    # nije doneo polje ne sme da obori celo pravilo.
    if levo is None or desno is None:
        return False
    try:
        if operator == "<":
            return levo < desno
        if operator == "<=":
            return levo <= desno
        if operator == ">":
            return levo > desno
        if operator == ">=":
            return levo >= desno
    except TypeError:
        return False

    raise ConditionError(f"Nepoznat operator: {operator}")


def evaluate(stablo, payload: dict) -> bool:
    """Ocenjuje stablo nad poljima dogadjaja. Prazno stablo je „tacno"."""

    if stablo is None:
        return True

    if isinstance(stablo, Spoj):
        levo = evaluate(stablo.levo, payload)
        # Kratak spoj: `AND` sa netacnom levom stranom ne ocenjuje desnu.
        if stablo.vrsta == "AND":
            return levo and evaluate(stablo.desno, payload)
        return levo or evaluate(stablo.desno, payload)

    if isinstance(stablo, Poredjenje):
        return _uporedi(payload.get(stablo.polje), stablo.operator,
                        stablo.vrednost)

    raise ConditionError(f"Nepoznat cvor u uslovu: {stablo!r}")


def matches(izraz: str, payload: dict) -> bool:
    """Parsira i ocenjuje u jednom potezu. Za probu i za ocenu u letu."""

    return evaluate(parse(izraz), payload)


def polja_u_izrazu(stablo) -> set[str]:
    """Koja polja uslov cita. Sluzi proveri da pravilo gleda svoj dogadjaj."""

    if stablo is None:
        return set()
    if isinstance(stablo, Spoj):
        return polja_u_izrazu(stablo.levo) | polja_u_izrazu(stablo.desno)
    if isinstance(stablo, Poredjenje):
        return {stablo.polje}
    return set()
