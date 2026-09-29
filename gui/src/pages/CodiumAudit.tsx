// ==========          AUDIT LOGS          ==========
// Dnevnik se cita unazad u nizu, pa „Ucitaj jos" dopisuje redove umesto da
// ih zameni — zamena bi gubila mesto na kome si stao.
import { useCallback, useEffect, useRef, useState } from "react";
import { ScrollText, SlidersHorizontal } from "lucide-react";

import { relativeTime } from "../features/codium/activity";
import { getAuditLog } from "../services/codiumApi";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type { AuditEntry } from "../types/codium";
import "../styles/codium-access.css";

const STRANICA = 50;

export default function CodiumAudit() {
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [error, setError] = useState("");
  const [imaJos, setImaJos] = useState(false);
  const [ucitavanje, setUcitavanje] = useState(false);
  // Polja za kucanje (nacrt) idu odvojeno od primenjenog filtera: filter se
  // menja samo klikom na "Primeni", inace bi "Ucitaj jos" stranicirao upit
  // koji korisnik jos nije potvrdio, na offsetu racunatom za sasvim drugi
  // (neprimenjeni) upit.
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [primenjenFilter, setPrimenjenFilter] = useState({
    actor: "",
    action: "",
  });

  // Ref pored state-a: `disabled` na dugmetu sprečava sledeći klik tek posle
  // re-rendera, a dva klika u istom tiku (ili dvostruki poziv u testu) bi
  // oba prošla pre toga. Ref se postavlja odmah, sinhrono.
  const uToku = useRef(false);

  const ucitaj = useCallback(
    async (
      offset: number,
      dopuni: boolean,
      filter: typeof primenjenFilter,
      josTraje: () => boolean = () => true,
    ) => {
      if (uToku.current) {
        return;
      }
      uToku.current = true;
      setUcitavanje(true);
      try {
        const data = await getAuditLog({
          actor: filter.actor.trim() || undefined,
          action: filter.action.trim() || undefined,
          limit: STRANICA,
          offset,
        });
        if (!josTraje()) {
          return;
        }
        setEntries((prev) =>
          dopuni ? [...prev, ...data.entries] : data.entries,
        );
        setImaJos(data.entries.length === STRANICA);
        setError("");
      } catch {
        setError("Učitavanje dnevnika nije uspelo.");
      } finally {
        uToku.current = false;
        setUcitavanje(false);
      }
    },
    [],
  );

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await ucitaj(0, false, primenjenFilter, () => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
    // Namerno bez `ucitaj`/`primenjenFilter` u zavisnostima: pokrece se samo
    // pri montiranju, dalje primenu filtera pokrece dugme "Primeni".
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const primeni = () => {
    const noviFilter = { actor, action };
    setPrimenjenFilter(noviFilter);
    void ucitaj(0, false, noviFilter);
  };

  const ucitajJos = () => {
    void ucitaj(entries.length, true, primenjenFilter);
  };

  return (
    <div
      className={`cacc-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cacc-head">
        <p className="cacc-eyebrow">CODIUM · Sistem</p>
        <h1>Audit Logs</h1>
        <p className="cacc-sub">
          Šta je traženo, šta je kapija odgovorila i kako se završilo.
        </p>
      </header>

      {error && <p className="cacc-error">{error}</p>}

      <div className="smart-stack">
        <SmartFrame
          icon={<SlidersHorizontal size={15} strokeWidth={1.8} />}
          id="filteri"
          layout={layout}
          title="Filteri"
        >
          <div className="cadt-filters">
            <label htmlFor="cadt-actor">Akter</label>
            <input
              id="cadt-actor"
              onChange={(e) => setActor(e.target.value)}
              placeholder="agent:architect"
              value={actor}
            />
            <label htmlFor="cadt-action">Akcija</label>
            <input
              id="cadt-action"
              onChange={(e) => setAction(e.target.value)}
              placeholder="file.write"
              value={action}
            />
            <button disabled={ucitavanje} onClick={primeni} type="button">
              Primeni
            </button>
          </div>
        </SmartFrame>

        <SmartFrame
          icon={<ScrollText size={15} strokeWidth={1.8} />}
          id="dnevnik"
          layout={layout}
          title="Dnevnik"
        >
          {entries.length === 0 ? (
            <p className="cacc-empty">Dnevnik je prazan.</p>
          ) : (
            <table className="cacc-table cadt-table">
              <thead>
                <tr>
                  <th>Kada</th>
                  <th>Akter</th>
                  <th>Akcija</th>
                  <th>Cilj</th>
                  <th>Odgovor</th>
                  <th>Ishod</th>
                  <th>Detalj</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((unos) => (
                  <tr key={unos.id}>
                    <td>{relativeTime(unos.at)}</td>
                    <td>{unos.actor}</td>
                    <td>{unos.action}</td>
                    <td>{unos.target}</td>
                    <td className={`cacc-verdict v-${unos.verdict}`}>
                      {unos.verdict}
                    </td>
                    <td>{unos.outcome}</td>
                    <td>{unos.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {imaJos && (
            <button
              className="cadt-more"
              disabled={ucitavanje}
              onClick={ucitajJos}
              type="button"
            >
              Učitaj još
            </button>
          )}
        </SmartFrame>
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
