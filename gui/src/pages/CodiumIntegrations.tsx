// ==========          INTEGRATIONS          ==========
// Vidljivo lice sloja iz E0. Jedno mesto gde se vidi sa čime je CODIUM povezan,
// da li veza radi, i gde se dodaje nova.
//
// Sami konektori žive u CORE-u (`/api/v1/core/ai/connectors`) jer ih dele svi
// domeni; ovaj ekran je CODIUM-ov jer je CODIUM taj koji ih troši — deploy
// ciljevi i infra node-ovi nose `connector_id`.
import { useState } from "react";
import { Plug, Plus, RefreshCw } from "lucide-react";

import ConnectorCard from "../features/codium/integrations/ConnectorCard";
import AddConnectorForm from "../features/codium/integrations/AddConnectorForm";
import { useConnectors } from "../features/codium/integrations/useConnectors";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import "../styles/codium-integrations.css";

export default function CodiumIntegrations() {
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const { connectors, kinds, usage, probes, isLoading, error, refresh, test,
          create, replaceSecret, remove } = useConnectors();
  const [uToku, setUToku] = useState<number | null>(null);
  const [poruka, setPoruka] = useState("");

  const nazivVrste = new Map(kinds.map((k) => [k.id, k.label]));

  async function testiraj(connectorId: number) {
    setUToku(connectorId);
    try {
      await test(connectorId);
      setPoruka("");
    } catch (problem) {
      setPoruka(problem instanceof Error ? problem.message : String(problem));
    } finally {
      setUToku(null);
    }
  }

  async function zameniTajnu(connectorId: number, ime: string) {
    const nova = window.prompt(`Nova vrednost ključa za „${ime}“:`);
    if (nova === null || nova.trim() === "") {
      return;
    }
    try {
      await replaceSecret(connectorId, nova.trim());
      setPoruka(`Ključ za „${ime}“ je zamenjen.`);
    } catch (problem) {
      setPoruka(problem instanceof Error ? problem.message : String(problem));
    }
  }

  async function obrisi(connectorId: number, ime: string) {
    // Potvrda navodi ŠTA konektor koristi: brisanje bez toga ostavlja deploy
    // cilj bez pristupa, a to se vidi tek na sledećoj isporuci.
    const koristi = usage[connectorId]?.items ?? [];
    const spisak = koristi.length === 0
      ? "Ništa ga trenutno ne koristi."
      : `Koristi ga: ${koristi.map((s) => `${s.label} „${s.name}“`).join(", ")}.`;
    if (!window.confirm(`Obrisati konektor „${ime}“?\n\n${spisak}`)) {
      return;
    }
    try {
      await remove(connectorId);
      setPoruka("");
    } catch (problem) {
      setPoruka(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <div
      className={`cint-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cint-head">
        <p className="cint-eyebrow">CODIUM · Kod</p>
        <h1>Integrations</h1>
        <p className="cint-sub">
          Sa čime je CODIUM povezan i da li veza radi. Vrednost ključa se ne
          prikazuje — ni ovde ni u odgovoru servera; vidi se samo da postoji.
        </p>
        <div className="cint-alat">
          <button type="button" onClick={() => void refresh()}>
            <RefreshCw size={13} strokeWidth={2} />
            Osveži
          </button>
          {isLoading && <span className="cint-hint">Učitavanje…</span>}
          {error !== "" && <span className="cint-greska">{error}</span>}
          {poruka !== "" && <span className="cint-hint">{poruka}</span>}
        </div>
      </header>

      <div className="smart-stack">
        <SmartFrame
          id="konektori"
          title="Konektori"
          icon={<Plug size={15} strokeWidth={2} />}
          layout={layout}
        >
          <section className="cint-panel">
            <h2>Konektori</h2>
            {connectors.length === 0 ? (
              <p className="cint-prazno">
                Nema konektora. Novi se dodaje ispod.
              </p>
            ) : (
              <div className="cint-mreza">
                {connectors.map((konektor) => (
                  <ConnectorCard
                    key={konektor.id}
                    connector={konektor}
                    kindLabel={nazivVrste.get(konektor.kind) ?? konektor.kind}
                    usage={usage[konektor.id]}
                    probe={probes[konektor.id]}
                    busy={uToku === konektor.id}
                    onTest={() => void testiraj(konektor.id)}
                    onReplaceSecret={() =>
                      void zameniTajnu(konektor.id, konektor.name)
                    }
                    onDelete={() => void obrisi(konektor.id, konektor.name)}
                  />
                ))}
              </div>
            )}
          </section>
        </SmartFrame>

        <SmartFrame
          id="nov"
          title="Dodaj konektor"
          icon={<Plus size={15} strokeWidth={2} />}
          layout={layout}
        >
          <section className="cint-panel">
            <h2>Dodaj konektor</h2>
            <AddConnectorForm kinds={kinds} onCreate={create} />
          </section>
        </SmartFrame>
      </div>

    </div>
  );
}
