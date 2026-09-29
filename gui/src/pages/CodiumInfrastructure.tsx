// ==========          INFRASTRUCTURE          ==========
// Popis svega sto negde radi i sto CODIUM ume da upali, ugasi i proveri.
// Grupisano po node-u, jer je node mesto — a sta gde radi je prvo pitanje kad
// nesto ne odgovara.
import { Plus, RefreshCw, Search, Server } from "lucide-react";

import DiscoverPanel from "../features/codium/infrastructure/DiscoverPanel";
import NewService from "../features/codium/infrastructure/NewService";
import ServiceCard from "../features/codium/infrastructure/ServiceCard";
import { useInfrastructure } from "../features/codium/infrastructure/useInfrastructure";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import "../styles/codium-infrastructure.css";

export default function CodiumInfrastructure() {
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const {
    nodes,
    services,
    isLoading,
    error,
    refresh,
    createService,
    removeService,
    discover,
    control,
  } = useInfrastructure();

  // `localhost` uvek postoji (upisan migracijom), ali dok lista jos stize
  // nemamo id — obrasci se do tada ne crtaju.
  const prviNode = nodes.length > 0 ? nodes[0] : null;

  return (
    <div
      className={`cinf-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cinf-head">
        <p className="cinf-eyebrow">CODIUM · Kod</p>
        <h1>Infrastructure</h1>
        <p className="cinf-sub">
          Šta gde radi — procesi, kontejneri i portovi koje CODIUM ume da upali,
          ugasi i proveri.
        </p>
        <div className="cinf-alat">
          <button type="button" onClick={() => void refresh()}>
            <RefreshCw size={13} strokeWidth={2} />
            Osveži
          </button>
          {isLoading && <span className="cinf-hint">Učitavanje…</span>}
        </div>
      </header>

      {error && <p className="cinf-error">{error}</p>}

      <div className="cinf-grid smart-stack">
        {nodes.map((node) => (
          <SmartFrame
            icon={<Server size={15} strokeWidth={1.8} />}
            id={`node-${node.id}`}
            key={node.id}
            layout={layout}
            title={node.name}
          >
            <section className="cinf-panel">
              <h2>{node.name}</h2>
              {services.filter((s) => s.node_id === node.id).length === 0 ? (
                <p className="cinf-hint">
                  Na ovom node-u nema upisanih servisa. Pronađi ih ili upiši
                  ručno, u okvirima desno.
                </p>
              ) : (
                <div className="cinf-kartice">
                  {services
                    .filter((s) => s.node_id === node.id)
                    .map((servis) => (
                      <ServiceCard
                        key={servis.id}
                        service={servis}
                        onControl={control}
                        onRemove={removeService}
                      />
                    ))}
                </div>
              )}
            </section>
          </SmartFrame>
        ))}

        <SmartFrame
          icon={<Search size={15} strokeWidth={1.8} />}
          id="pronadji"
          layout={layout}
          title="Pronađi servise"
        >
          <section className="cinf-panel">
            <h2>Pronađi servise</h2>
            {prviNode === null ? (
              <p className="cinf-hint">Učitavanje node-ova…</p>
            ) : (
              <DiscoverPanel
                nodeId={prviNode.id}
                onDiscover={discover}
                onAdd={createService}
              />
            )}
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<Plus size={15} strokeWidth={1.8} />}
          id="nov-servis"
          layout={layout}
          title="Nov servis"
        >
          <section className="cinf-panel">
            <h2>Nov servis</h2>
            {prviNode === null ? (
              <p className="cinf-hint">Učitavanje node-ova…</p>
            ) : (
              <NewService nodeId={prviNode.id} onCreate={createService} />
            )}
          </section>
        </SmartFrame>
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
