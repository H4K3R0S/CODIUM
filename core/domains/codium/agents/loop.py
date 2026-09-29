# ==========          PETLJA AGENTA          ==========
# Cista petlja: sve zavisnosti su ubrizgane, pa se testira laznim modelom bez
# ijednog pravog poziva.
#
# Istorija razgovora se gradi iz koraka zapisanih u bazi, ne iz promenljive u
# memoriji. To je isti izvor iz kojeg `resume` krece dalje posle odobrenja, pa
# pauza ne trazi nit koja spava — nit umre, a nastavak je nova nit.
from __future__ import annotations

import hashlib
import json
import posixpath
from collections.abc import Callable

from core.domains.codium.agents.models import Agent, AgentRun, AgentStep
from core.domains.codium.agents.protocol import ToolCall, parse_move, system_prompt
from core.domains.codium.agents.repository import RunRepository
from core.domains.codium.agents.tools.registry import ToolRegistry, ToolSpec
from core.domains.codium.audit import (
    Approval,
    ApprovalRepository,
    AuditEntry,
    AuditRepository,
)
from core.security.scope_gate import ALLOW, DENY, NEEDS_APPROVAL, ScopeGate

# Poruke -> tekst modela. Ubrizgano da bi petlja bila testabilna bez provajdera.
Chat = Callable[[list[dict[str, str]]], str]

# Ko odgovara: (provajder, model, da li je lokalan). Ubrizgano, jer petlja ne
# sme da zna kako se model bira — to je posao rutera.
ModelResolver = Callable[[], tuple[str, str, bool]]

# Akcija kapije za online poziv. Lokalni model ne pita nista — ne trosi novac.
ONLINE_ACTION = "ai.call_online"

# Model koji dva puta zaredom napravi istu gresku ne ume da se popravi. Bez
# ovoga bi vrteo krug do `max_steps` i trosio na svakom.
MAX_PONOVLJENIH_GRESAKA = 2


def _otisak(content: str) -> str:
    """Otisak sadrzaja koji se pise.

    Ne dokazuje da je covek video bas ovaj tekst — samo da se `content` u
    molbi nije promenio izmedju podnosenja i nastavka posla.
    """

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AgentLoop:
    """Vodi jedan posao agenta od zadatka do ishoda."""

    def __init__(self, *, runs: RunRepository, tools: ToolRegistry,
                 gate: ScopeGate, approvals: ApprovalRepository,
                 audit: AuditRepository, chat: Chat,
                 resolve_model: ModelResolver | None = None) -> None:
        self._runs = runs
        self._tools = tools
        self._gate = gate
        self._approvals = approvals
        self._audit = audit
        self._chat = chat
        self._resolve_model = resolve_model

    # ----------          ULAZI          ----------

    def run(self, agent: Agent, run: AgentRun) -> AgentRun:
        return self._vrti(agent, run, koraka=0, poslednja_greska="",
                          ponovljeno=0)

    def resume(self, agent: Agent, run: AgentRun) -> AgentRun:
        """Nastavlja posao posle odluke coveka o molbi."""

        # BEZBEDNOSNA PRETPOSTAVKA na koju se ova metoda oslanja: alat se
        # ovde izvrsava PRE nego sto bilo koja atomska provera potvrdi da je
        # ovo jedini put kad se ova molba obradjuje. Danas to vazi zato sto
        # je `ApprovalRepository.decide()` jedini poziv koji menja status
        # molbe, sa `WHERE status='pending'` — druga odluka nad istom molbom
        # je nemoguca, pa je i drugo izvrsavanje alata nemoguce. Ako se ikad
        # doda novi put do `resume` (npr. oporavak posle pada procesa) koji
        # ne prolazi kroz taj isti atomski `decide()`, ova pretpostavka puca
        # i alat moze da se izvrsi dvaput nad istom molbom. Svaki novi put
        # mora da sacuva to svojstvo — jednokratnu, atomsku odluku pre nego
        # sto se stigne dovde.

        # `run` je zamrznut dataclass koji je pozivalac mogao da drzi u ruci
        # jos od pauze. `_vrti` cita stanje iz baze na svakom koraku; `resume`
        # mora isto — inace drugi poziv sa istim zastarelim objektom ponovo
        # izvrsi potez nad poslom koji je vec zavrsen.
        sveze = self._runs.get(run.id)
        if sveze is None:
            return run
        run = sveze

        if run.status != "waiting_approval" or run.pending_approval_id is None:
            return run

        molba = self._approvals.get(run.pending_approval_id)
        if molba is None or molba.status == "pending":
            # Jos se ceka; posao ostaje kakav jeste.
            return run

        payload = self._procitaj_payload(molba.payload)

        if payload.get("kind") == "model":
            # Molba za online model nema alat da se izvrsi — odobrenje samo
            # pusta posao da krene.
            cilj = f"{payload.get('provider', '')}/{payload.get('model', '')}"
            if molba.status != "approved":
                razlog = molba.note or "bez obrazlozenja"
                self._korak(run.id, "note", "",
                            f"Online model odbijen: {razlog}")
                return self._runs.finish(
                    run.id, status="cancelled",
                    result=f"Covek je odbio online model `{cilj}`: {razlog}",
                    steps_used=self._broj_poteza(run.id),
                )
            # Model se ponovo razresava, isto kao otisak sadrzaja kod
            # `write_file` ispod: molba je odobrena za cilj `cilj`, ali ako se
            # medjuvremenu `codium_model_prefs` ili `agent.model` promenio,
            # odobrenje coveka vazi za model koji vise nije taj koji bi se
            # pozvao — nastavak bi platio drugi model bez ijedne provere.
            if self._resolve_model is not None:
                try:
                    novi_provajder, novi_model, _ = self._resolve_model()
                except Exception:  # noqa: BLE001 — ruter puca na svoj nacin
                    novi_provajder, novi_model = None, None
                if (novi_provajder != payload.get("provider")
                        or novi_model != payload.get("model")):
                    self._korak(run.id, "note", "",
                                f"Model promenjen posle odobrenja: bilo je "
                                f"`{cilj}`.")
                    return self._runs.finish(
                        run.id, status="failed",
                        result=f"Model se promenio posle odobrenja online "
                               f"poziva `{cilj}`.",
                        steps_used=self._broj_poteza(run.id),
                    )

            self._audit.record(AuditEntry(
                actor=f"agent:{agent.slug}", action=ONLINE_ACTION,
                verdict="approved", target=cilj, outcome="ok",
                detail=f"odobreno molbom {molba.id}",
                project_id=run.project_id,
            ))
            # Pamti se isti marker koji `_proveri_online` trazi, da `_vrti`
            # ne otvori novu molbu za cilj koji je covek vec odobrio.
            self._korak(run.id, "note", "", f"online:{cilj}")
            nastavljen = self._runs.resume(run.id)
            if nastavljen is None:
                return self._runs.get(run.id)
            return self._vrti(agent, nastavljen,
                              koraka=self._broj_poteza(run.id),
                              poslednja_greska="", ponovljeno=0)

        ime_alata = str(payload.get("tool", ""))

        if molba.status != "approved":
            razlog = molba.note or "bez obrazlozenja"
            self._korak(run.id, "tool_result", ime_alata,
                        f"Odbijeno: {razlog}")
            return self._runs.finish(
                run.id, status="cancelled",
                result=f"Covek je odbio potez `{ime_alata}`: {razlog}",
                steps_used=self._broj_poteza(run.id),
            )

        spec = self._tools.get(ime_alata)
        if spec is None:
            self._korak(run.id, "tool_result", ime_alata,
                        f"Alat `{ime_alata}` vise ne postoji.")
            return self._runs.finish(
                run.id, status="failed",
                result=f"Odobren alat `{ime_alata}` vise ne postoji.",
                steps_used=self._broj_poteza(run.id),
            )

        argumenti = payload.get("args") or {}
        if not isinstance(argumenti, dict):
            argumenti = {}
        poziv = ToolCall(tool=ime_alata, args=argumenti)

        # Isti uslov kao u `_vrti`: agent sme samo ono sto mu je upisano u
        # `tools`, bez obzira sta je kapija rekla kad je molba podneta. Alat
        # je mogao da bude uklonjen agentu dok je posao cekao na coveka.
        if ime_alata not in agent.tools:
            self._korak(run.id, "tool_result", ime_alata,
                        f"Alat `{ime_alata}` nije vise dozvoljen ovom agentu.")
            return self._runs.finish(
                run.id, status="failed",
                result=f"Alat `{ime_alata}` nije vise dozvoljen ovom agentu.",
                steps_used=self._broj_poteza(run.id),
            )

        # Kapija se pita ponovo jer su se pravila mogla promeniti dok se
        # cekalo na coveka. Ovde vazi samo `deny` — `needs_approval` bi
        # otvorio novu molbu za istu stvar i petlja bi cekala samu sebe u
        # krug, a odobrenje koje vec postoji je tacno odgovor na to pitanje.
        # Svaki drugi verdikt (`allow`, ili nepoznat) pusta potez dalje, jer
        # je covek vec dao svoju saglasnost.
        odluka = self._gate.check(
            actor=f"agent:{agent.slug}", action=spec.action,
            target=self._meta(poziv),
        )
        if odluka.verdict == DENY:
            self._trag(agent, run, spec, poziv, "deny", "blocked",
                       odluka.reason)
            self._korak(run.id, "tool_result", ime_alata,
                        f"Odbijeno pravilom: {odluka.reason}")
            return self._runs.finish(
                run.id, status="failed",
                result=f"Kapija je odbila `{spec.action}`: {odluka.reason}",
                steps_used=self._broj_poteza(run.id),
            )

        if spec.writes_content:
            sada = _otisak(str(argumenti.get("content", "")))
            if sada != payload.get("content_hash"):
                # Ovo NE dokazuje da je covek video bas ove bajtove — oba
                # broja dolaze iz istog upisanog payload-a. Hvata samo slucaj
                # kad je neko izmenio `args` u molbi a nije dirao
                # `content_hash`, sto znaci da se sadrzaj promenio izmedju
                # podnosenja molbe i nastavka.
                self._korak(run.id, "tool_result", ime_alata,
                            "Sadrzaj se promenio posle odobrenja; potez pada.")
                return self._runs.finish(
                    run.id, status="failed",
                    result="Otisak sadrzaja se ne poklapa sa odobrenim.",
                    steps_used=self._broj_poteza(run.id),
                )

        izlaz, greska = self._izvrsi(spec, argumenti)
        self._korak(run.id, "tool_result", ime_alata, izlaz)
        # Za razliku od `_vrti`, ovde je potez zaista izvrsen posle ljudskog
        # odobrenja — to je tacno dogadjaj koji revizor trazi u dnevniku, pa
        # se ovde, jedini put u petlji, upisuje trag. `outcome` prati stvarni
        # ishod izvrsavanja: dozvoljen potez i dalje moze da pukne (npr.
        # doznaka za pisanje, ili putanja koja izleti iz korena), pa lazno
        # "ok" na neuspesnom pisanju bi prijavilo uspeh koji se nije desio.
        self._audit.record(AuditEntry(
            actor=f"agent:{agent.slug}", action=spec.action, verdict="approved",
            target=self._meta(poziv), outcome="error" if greska else "ok",
            detail=f"odobreno molbom {molba.id}", project_id=run.project_id,
        ))

        nastavljen = self._runs.resume(run.id)
        if nastavljen is None:
            return self._runs.get(run.id)
        return self._vrti(agent, nastavljen,
                          koraka=self._broj_poteza(run.id),
                          poslednja_greska="", ponovljeno=0)

    # ----------          JEZGRO          ----------

    def _vrti(self, agent: Agent, run: AgentRun, *, koraka: int,
              poslednja_greska: str, ponovljeno: int) -> AgentRun:
        while True:
            # Prekid je zapis, ne signal: nit ga vidi pre sledeceg poteza.
            tekuci = self._runs.get(run.id)
            if tekuci is None or tekuci.status != "running":
                return tekuci if tekuci is not None else run

            # Model se razresava iznova na svakom koraku (ispod, kroz
            # ubrizgani `chat`), pa i provera sme samo jednom da pusti posao
            # dalje: promena modela izmedju dva koraka ne sme da preskoci
            # kapiju.
            prepreka = self._proveri_online(agent, run)
            if prepreka is not None:
                return prepreka

            if koraka >= agent.max_steps:
                return self._runs.finish(
                    run.id, status="failed",
                    result=f"Dostignut limit od {agent.max_steps} koraka.",
                    steps_used=koraka,
                )

            sirovo = self._chat(self._poruke(agent, run))
            potez = parse_move(sirovo)
            koraka += 1

            # Proza bez poziva alata je konacan odgovor.
            if potez.call is None and not potez.error:
                self._korak(run.id, "answer", "", potez.answer)
                return self._runs.finish(run.id, status="done",
                                         result=potez.answer,
                                         steps_used=koraka)

            if potez.error:
                # Bez ovoga bi transkript imao dve uzastopne `user` poruke
                # (rezultat prethodnog koraka, pa opet greska) i model ne bi
                # video sta je zapravo napisao kad je pogresio. Stroga API
                # pravila providera odbijaju dve uzastopne poruke iste uloge.
                self._korak(run.id, "thought", "", sirovo)
                ishod = self._greska(run.id, "", potez.error,
                                     poslednja_greska, ponovljeno, koraka)
                if ishod is not None:
                    return ishod
                poslednja_greska, ponovljeno = potez.error, (
                    ponovljeno + 1 if potez.error == poslednja_greska else 1)
                continue

            call = potez.call
            self._korak(run.id, "tool_call", call.tool,
                        json.dumps({"tool": call.tool, "args": call.args},
                                   ensure_ascii=False))

            # Agent sme samo ono sto mu je upisano, bez obzira na kapiju.
            if call.tool not in agent.tools:
                poruka = f"Alat `{call.tool}` nije dozvoljen ovom agentu."
            else:
                spec = self._tools.get(call.tool)
                poruka = (f"Alat `{call.tool}` ne postoji."
                          if spec is None else "")

            if poruka:
                ishod = self._greska(run.id, call.tool, poruka,
                                     poslednja_greska, ponovljeno, koraka)
                if ishod is not None:
                    return ishod
                ponovljeno = (ponovljeno + 1
                              if poruka == poslednja_greska else 1)
                poslednja_greska = poruka
                continue

            spec = self._tools.get(call.tool)
            odluka = self._gate.check(
                actor=f"agent:{agent.slug}", action=spec.action,
                target=self._meta(call),
            )

            if odluka.verdict == DENY:
                self._trag(agent, run, spec, call, "deny", "blocked",
                           odluka.reason)
                self._korak(run.id, "tool_result", call.tool,
                            f"Odbijeno pravilom: {odluka.reason}")
                return self._runs.finish(
                    run.id, status="failed",
                    result=f"Kapija je odbila `{spec.action}`: {odluka.reason}",
                    steps_used=koraka,
                )

            if odluka.verdict == NEEDS_APPROVAL:
                molba = self._zatrazi_odobrenje(agent, run, spec, call)
                self._trag(agent, run, spec, call, NEEDS_APPROVAL, "pending",
                           f"molba {molba.id}")
                self._korak(run.id, "tool_result", call.tool,
                            f"Ceka odobrenje coveka (molba {molba.id}).")
                pauziran = self._runs.wait_for_approval(run.id, molba.id)
                return pauziran if pauziran is not None else self._runs.get(run.id)

            if odluka.verdict != ALLOW:
                # Nepoznat verdikt se ponasa kao odbijanje. Tiho izvrsavanje
                # onoga sto kapija nije izricito dozvolila je rupa.
                self._trag(agent, run, spec, call, odluka.verdict, "blocked",
                           odluka.reason)
                self._korak(run.id, "tool_result", call.tool,
                            f"Nepoznat odgovor kapije: {odluka.verdict}")
                return self._runs.finish(
                    run.id, status="failed",
                    result=f"Kapija je vratila nepoznat verdikt "
                           f"`{odluka.verdict}`.",
                    steps_used=koraka,
                )

            # Citanja se ne upisuju u dnevnik — vec stoje kao koraci posla, a
            # dnevnik bi se ugusio u njima.
            izlaz, greska = self._izvrsi(spec, call.args)
            self._korak(run.id, "tool_result", call.tool, izlaz)

            if greska:
                ishod = self._greska(run.id, call.tool, izlaz,
                                     poslednja_greska, ponovljeno, koraka,
                                     vec_upisano=True)
                if ishod is not None:
                    return ishod
                ponovljeno = (ponovljeno + 1
                              if izlaz == poslednja_greska else 1)
                poslednja_greska = izlaz
            else:
                poslednja_greska, ponovljeno = "", 0

    # ----------          POMOCNO          ----------

    def _poruke(self, agent: Agent, run: AgentRun) -> list[dict[str, str]]:
        poruke = [
            {"role": "system",
             "content": system_prompt(agent.system_prompt,
                                      self._tools.describe(agent.tools))},
            {"role": "user", "content": run.task},
        ]
        for step in self._runs.steps(run.id):
            if step.kind in ("tool_call", "thought"):
                self._dodaj(poruke, "assistant", step.payload)
            elif step.kind == "tool_result":
                self._dodaj(poruke, "user", step.payload)
        return poruke

    def _dodaj(self, poruke: list[dict[str, str]], role: str,
               content: str) -> None:
        """Dodaje poruku, spajajuci je sa prethodnom ako je ista uloga.

        Namerno opsti mehanizam, ne zakrpa za jedan put kroz petlju: `resume`
        upisuje pauzu kao jedan `tool_result` ("Ceka odobrenje...") pa posle
        odobrenja izvrsen potez kao drugi `tool_result` — bez spajanja to su
        dve uzastopne `user` poruke, a Anthropic (i svaki strogi provajder)
        odbija transkript sa dve poruke iste uloge zaredom (HTTP 400). Isti
        rizik postoji svuda gde se dva koraka istog smera upisu jedan za
        drugim — spajanje ovde pokriva sve te puteve, ukljucujuci one koji
        jos nisu napisani, a ne samo slucaj koji je do sada uocen (greska
        parsiranja, gde je `thought` korak vec resio problem umetanjem
        `assistant` poruke izmedju dve `user` poruke).
        """

        if poruke and poruke[-1]["role"] == role:
            poruke[-1]["content"] = f"{poruke[-1]['content']}\n\n{content}"
        else:
            poruke.append({"role": role, "content": content})

    def _korak(self, run_id: int, kind: str, tool: str, payload: str) -> None:
        self._runs.append_step(AgentStep(
            run_id=run_id, idx=self._sledeci_idx(run_id), kind=kind,
            tool=tool, payload=payload,
        ))

    def _sledeci_idx(self, run_id: int) -> int:
        koraci = self._runs.steps(run_id)
        return koraci[-1].idx + 1 if koraci else 0

    def _broj_poteza(self, run_id: int) -> int:
        return sum(1 for s in self._runs.steps(run_id) if s.kind == "tool_call")

    def _meta(self, call: ToolCall) -> str:
        """Cilj koji ide kapiji: putanja kad je ima, inace prazno.

        Kapija poredi ciljeve kao gole nizove (tacno ili prefiksno), a
        istrazivac normalizuje putanju pre nego sto je upise na disk. Bez
        normalizacije ovde, dva razlicita niza (npr. `api.py`, `./api.py`,
        `/api.py`) gadjaju isti fajl, a pravilo kapije pogadja samo jedan od
        njih. Mora da prati isto skidanje kao `CodiumExplorer._safe`
        (ukljucujuci `lstrip("/")`, inace vodeca kosa crta zaobidje pravilo).
        Cisto normalizacija teksta — bez doticanja fajl-sistema.
        """

        rel = call.args.get("rel")
        if not isinstance(rel, str):
            return ""
        ociscen = rel.strip().replace("\\", "/")
        ociscen = ociscen.removeprefix("./")
        ociscen = ociscen.lstrip("/")
        return posixpath.normpath(ociscen) if ociscen else ""

    def _izvrsi(self, spec: ToolSpec, args: dict) -> tuple[str, bool]:
        """Pokrece alat; izuzetak postaje rezultat koraka, ne pad petlje."""

        try:
            return str(spec.run(**args)), False
        except TypeError as greska:
            return f"Pogresni argumenti za `{spec.name}`: {greska}", True
        except Exception as greska:  # noqa: BLE001 - alat sme da pukne bilo cime
            return f"Greska alata `{spec.name}`: {greska}", True

    def _greska(self, run_id: int, tool: str, poruka: str,
                poslednja: str, ponovljeno: int, koraka: int,
                *, vec_upisano: bool = False) -> AgentRun | None:
        """Upisuje gresku kao rezultat koraka i gasi petlju na ponavljanju."""

        if not vec_upisano:
            self._korak(run_id, "tool_result", tool, poruka)
        if poruka == poslednja and ponovljeno + 1 >= MAX_PONOVLJENIH_GRESAKA:
            return self._runs.finish(
                run_id, status="failed",
                result=f"Ista greska dva puta zaredom: {poruka}",
                steps_used=koraka,
            )
        return None

    def _zatrazi_odobrenje(self, agent: Agent, run: AgentRun, spec: ToolSpec,
                           call: ToolCall) -> Approval:
        payload: dict[str, object] = {"tool": call.tool, "args": call.args}
        if spec.writes_content:
            payload["content_hash"] = _otisak(str(call.args.get("content", "")))
        return self._approvals.request(Approval(
            actor=f"agent:{agent.slug}", action=spec.action,
            target=self._meta(call),
            payload=json.dumps(payload, ensure_ascii=False),
        ))

    def _proveri_online(self, agent: Agent, run: AgentRun) -> AgentRun | None:
        """Pita kapiju sme li ovaj posao da koristi online model.

        Pita se pred SVAKI poziv modela — model se moze promeniti izmedju dva
        koraka (podesavanja, izmena `agent.model`), pa provera na pocetku
        posla ne bi uhvatila promenu na putu. Da isti odobreni cilj ne bi
        pitao kapiju iznova na svakom koraku, odobrenje se pamti kao korak
        `note` u bazi (`f"online:{cilj}"`) — u bazi, ne u polju objekta, jer
        se posle pauze petlja nastavlja iz nove niti sa novim primerkom
        `AgentLoop`-a. Bez `resolve_model` (stariji pozivaoci i testovi)
        provera se preskace.
        """

        if self._resolve_model is None:
            return None
        try:
            provajder, model, lokalan = self._resolve_model()
        except Exception:  # noqa: BLE001 — ruter puca na svoj nacin
            # Nepoznat model se ponasa kao lokalan: ako razresavanje modela
            # puca, i sam poziv modela ce pasti iz istog uzroka, pa kapija
            # nema sta da stiti — a obarati posao zbog kvara rutera bi
            # znacilo kazniti korisnika za tudju gresku.
            return None
        if lokalan:
            return None

        cilj = f"{provajder}/{model}"
        marker = f"online:{cilj}"
        if any(step.kind == "note" and step.payload == marker
               for step in self._runs.steps(run.id)):
            # Ovaj cilj je vec odobren za ovaj posao — kapija se ne pita
            # drugi put za istu stvar.
            return None

        odluka = self._gate.check(actor=f"agent:{agent.slug}",
                                  action=ONLINE_ACTION, target=cilj)

        if odluka.verdict == ALLOW:
            # Pravilom dozvoljen cilj se pamti isto kao odobren molbom, da se
            # kapija ne pita ponovo na sledecem koraku. Trag u dnevniku ovde
            # nedostajao je pre ove izmene: chat ruta ostavlja trag za isti
            # dogadjaj, petlja agenta nije.
            self._korak(run.id, "note", "", marker)
            self._audit.record(AuditEntry(
                actor=f"agent:{agent.slug}", action=ONLINE_ACTION,
                verdict=ALLOW, target=cilj, outcome="ok",
                detail=odluka.reason, project_id=run.project_id,
            ))
            return None

        if odluka.verdict == NEEDS_APPROVAL:
            molba = self._approvals.request(Approval(
                actor=f"agent:{agent.slug}", action=ONLINE_ACTION, target=cilj,
                payload=json.dumps({"kind": "model", "provider": provajder,
                                    "model": model}, ensure_ascii=False),
            ))
            self._audit.record(AuditEntry(
                actor=f"agent:{agent.slug}", action=ONLINE_ACTION,
                verdict=NEEDS_APPROVAL, target=cilj, outcome="pending",
                detail=f"molba {molba.id}", project_id=run.project_id,
            ))
            # Vrsta koraka je `note`, ne `tool_result`: pauza pred prvi poziv
            # nije rezultat alata i ne sme da udje u transkript kao poruka
            # korisnika (`_poruke` je namerno ne prepoznaje).
            self._korak(run.id, "note", "",
                        f"Ceka odobrenje coveka za online model {cilj} "
                        f"(molba {molba.id}).")
            pauziran = self._runs.wait_for_approval(run.id, molba.id)
            return pauziran if pauziran is not None else self._runs.get(run.id)

        # `deny` i svaki nepoznat verdikt obaraju posao. Tiho placanje onoga
        # sto kapija nije izricito dozvolila je rupa.
        self._audit.record(AuditEntry(
            actor=f"agent:{agent.slug}", action=ONLINE_ACTION,
            verdict=odluka.verdict, target=cilj, outcome="blocked",
            detail=odluka.reason, project_id=run.project_id,
        ))
        self._korak(run.id, "note", "",
                    f"Online model odbijen: {odluka.reason}")
        return self._runs.finish(
            run.id, status="failed",
            result=f"Kapija je odbila online model `{cilj}`: {odluka.reason}",
            steps_used=self._broj_poteza(run.id),
        )

    def _trag(self, agent: Agent, run: AgentRun, spec: ToolSpec,
              call: ToolCall, verdict: str, outcome: str, detail: str) -> None:
        self._audit.record(AuditEntry(
            actor=f"agent:{agent.slug}", action=spec.action, verdict=verdict,
            target=self._meta(call), outcome=outcome, detail=detail,
            project_id=run.project_id,
        ))

    def _procitaj_payload(self, sirovo: str) -> dict:
        try:
            podaci = json.loads(sirovo or "{}")
        except ValueError:
            return {}
        return podaci if isinstance(podaci, dict) else {}
