// ==========          AUTOMATIZACIJA          ==========
// Sve prethodne faze rade kad ih čovek pozove. Ovde sistem sam reaguje, pa
// ekran mora da bude čitljiv i onome ko pravilo nije pisao: KADA, AKO, ONDA
// stoje ispisani u svakom redu.
//
// Uređivač ide u tri koraka i svaki sledeći zavisi od prethodnog — polja za
// uslov zna tek izabrani događaj.
import { useState } from "react";
import { History, ListChecks, Plus, RefreshCw, Zap } from "lucide-react";

import ActionPicker from "../features/codium/automations/ActionPicker";
import ConditionBuilder from "../features/codium/automations/ConditionBuilder";
import { sastaviUslov } from "../features/codium/automations/conditionExpression";
import RuleRow from "../features/codium/automations/RuleRow";
import RunHistory from "../features/codium/automations/RunHistory";
import { eventLabel } from "../features/codium/automations/automationLabels";
import { useAutomations } from "../features/codium/automations/useAutomations";
import { testAutomationRule } from "../services/codiumApi";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type { AutomationTestResponse } from "../types/codium";
import "../styles/codium-automations.css";

export default function CodiumAutomations() {
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const { rules, events, actions, runs, isLoading, error, refresh, create,
          toggle, remove } = useAutomations();

  const [ime, setIme] = useState("");
  const [dogadjaj, setDogadjaj] = useState("");
  const [polje, setPolje] = useState("");
  const [operator, setOperator] = useState("==");
  const [vrednost, setVrednost] = useState("");
  const [izabraneAkcije, setIzabraneAkcije] = useState<string[]>([]);
  const [greskaUpisa, setGreskaUpisa] = useState("");
  const [proba, setProba] = useState<
    { id: number; ishod: AutomationTestResponse } | null
  >(null);

  const izabranDogadjaj = events.find((d) => d.name === dogadjaj) ?? null;
  // Pravilo pamti ime akcije, a čovek u spisku čita naziv sa ekrana.
  const nazivAkcije = Object.fromEntries(actions.map((a) => [a.name, a.label]));
  const uslov = sastaviUslov(polje, operator, vrednost);
  const mozeUpis = ime.trim() !== "" && dogadjaj !== "" &&
    izabraneAkcije.length > 0;

  function prebaciAkciju(name: string) {
    setIzabraneAkcije((staro) =>
      staro.includes(name) ? staro.filter((x) => x !== name) : [...staro, name],
    );
  }

  async function snimi() {
    try {
      await create({
        name: ime.trim(),
        event: dogadjaj,
        condition_expr: uslov,
        actions: izabraneAkcije.map((name) => ({ name, params: {} })),
      });
      setIme("");
      setPolje("");
      setVrednost("");
      setIzabraneAkcije([]);
      setGreskaUpisa("");
    } catch (problem) {
      setGreskaUpisa(problem instanceof Error ? problem.message : String(problem));
    }
  }

  async function probaj(ruleId: number) {
    try {
      // Prazan izmišljen događaj: server javlja da uslov nije prošao, što je
      // tačan odgovor. Proba nikada ne izvršava akcije.
      const ishod = await testAutomationRule(ruleId, {});
      setProba({ id: ruleId, ishod });
    } catch (problem) {
      setGreskaUpisa(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <div
      className={`caut-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="caut-head">
        <p className="caut-eyebrow">CODIUM · Kod</p>
        <h1>Automations</h1>
        <p className="caut-sub">
          Pravila reaguju sama. Ono što traži odobrenje i dalje čeka čoveka —
          automatizacija ubrzava odluku, ne zaobilazi je.
        </p>
        <div className="caut-alat">
          <button type="button" onClick={() => void refresh()}>
            <RefreshCw size={13} strokeWidth={2} />
            Osveži
          </button>
          {isLoading && <span className="caut-hint">Učitavanje…</span>}
          {error !== "" && <span className="caut-greska">{error}</span>}
        </div>
      </header>

      <div className="smart-stack">
        <SmartFrame
          id="pravila"
          title="Pravila"
          icon={<Zap size={15} strokeWidth={2} />}
          layout={layout}
        >
          <section className="caut-panel">
            <h2>Pravila</h2>
            {rules.length === 0 ? (
            <p className="caut-prazno">Nema pravila. Novo se sastavlja ispod.</p>
          ) : (
            <ul className="caut-spisak">
              {rules.map((pravilo) => (
                <RuleRow
                  key={pravilo.id}
                  rule={pravilo}
                  actionLabels={nazivAkcije}
                  onToggle={() => void toggle(pravilo)}
                  onDelete={() => void remove(pravilo.id)}
                  onTest={() => void probaj(pravilo.id)}
                />
              ))}
            </ul>
          )}
          {proba !== null && (
            <p className="caut-proba">
              Proba: {proba.ishod.matched ? "pravilo bi se upalilo" : "ne pali se"}
              {" — "}
              {proba.ishod.reason}
              {proba.ishod.would_run.length > 0 && (
                <> Izvršilo bi: {proba.ishod.would_run.join(", ")}.</>
              )}
            </p>
            )}
          </section>
        </SmartFrame>

        <SmartFrame
          id="novo"
          title="Novo pravilo"
          icon={<ListChecks size={15} strokeWidth={2} />}
          layout={layout}
        >
          <section className="caut-panel">
            <h2>Novo pravilo</h2>
            <div className="caut-korak">
            <p className="caut-korak-naslov">1 · Kada</p>
            <input
              type="text"
              aria-label="Ime pravila"
              placeholder="Ime pravila"
              value={ime}
              onChange={(e) => setIme(e.target.value)}
            />
            <select
              aria-label="Događaj"
              value={dogadjaj}
              onChange={(e) => {
                setDogadjaj(e.target.value);
                // Polje pripada starom događaju i na novom ne postoji.
                setPolje("");
                setVrednost("");
              }}
            >
              <option value="">— izaberi događaj —</option>
              {events.map((d) => (
                <option key={d.name} value={d.name}>{eventLabel(d.name)}</option>
              ))}
            </select>
          </div>

          <div className="caut-korak">
            <p className="caut-korak-naslov">2 · Ako</p>
            <ConditionBuilder
              event={izabranDogadjaj}
              polje={polje}
              operator={operator}
              vrednost={vrednost}
              onChange={(p, o, v) => {
                setPolje(p);
                setOperator(o);
                setVrednost(v);
              }}
            />
            {uslov !== "" && <code className="caut-izraz">{uslov}</code>}
          </div>

          <div className="caut-korak">
            <p className="caut-korak-naslov">3 · Onda</p>
            <ActionPicker
              actions={actions}
              izabrane={izabraneAkcije}
              onToggle={prebaciAkciju}
            />
          </div>

          <button
            type="button"
            className="caut-snimi"
            disabled={!mozeUpis}
            onClick={() => void snimi()}
          >
            <Plus size={13} strokeWidth={2} />
            Napravi pravilo
          </button>
            {greskaUpisa !== "" && <p className="caut-greska">{greskaUpisa}</p>}
          </section>
        </SmartFrame>

        <SmartFrame
          id="istorija"
          title="Istorija okidanja"
          icon={<History size={15} strokeWidth={2} />}
          layout={layout}
        >
          <section className="caut-panel">
            <h2>Istorija okidanja</h2>
            <RunHistory runs={runs} rules={rules} />
          </section>
        </SmartFrame>
      </div>

    </div>
  );
}
