// ==========          DEPLOYMENTS          ==========
// Isporuka nema svoj build: pod „Isporuci" stoje samo uspesna pokretanja koja
// su ostavila artefakt. Zato ekran nikad ne nudi da se isporuci nesto sto tek
// treba da se napravi — ono sto se salje je tacno ono sto je proslo korake.
import { useState } from "react";
import { History, Rocket, Server } from "lucide-react";

import DeployHistory from "../features/codium/deployments/DeployHistory";
import NewTarget from "../features/codium/deployments/NewTarget";
import TargetCard from "../features/codium/deployments/TargetCard";
import { useDeployments } from "../features/codium/deployments/useDeployments";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type { Deployment } from "../types/codium";
import "../styles/codium-deployments.css";

/** Poslednja uspesna isporuka po cilju — ono sto na cilju sada stoji. */
function trenutnePoCilju(deployments: Deployment[]): Map<number, Deployment> {
  const mapa = new Map<number, Deployment>();
  // Istorija stize najnovija prvo, pa prvi pogodak po cilju i jeste tekuci.
  for (const isporuka of deployments) {
    if (isporuka.status === "success" && !mapa.has(isporuka.target_id)) {
      mapa.set(isporuka.target_id, isporuka);
    }
  }
  return mapa;
}

export default function CodiumDeployments() {
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const {
    targets,
    deployments,
    deployableRuns,
    isLoading,
    error,
    createTarget,
    removeTarget,
    deploy,
    rollback,
  } = useDeployments();
  const [greskaAkcije, setGreskaAkcije] = useState("");

  const trenutne = trenutnePoCilju(deployments);
  const trenutniIds = [...trenutne.values()].map((isporuka) => isporuka.id);
  const cekaOdobrenje = new Set(
    deployments
      .filter((isporuka) => isporuka.status === "pending")
      .map((isporuka) => isporuka.target_id),
  );

  async function vrati(deploymentId: number) {
    try {
      await rollback(deploymentId);
      setGreskaAkcije("");
    } catch (problem) {
      setGreskaAkcije(problem instanceof Error ? problem.message : String(problem));
    }
  }

  async function ukloni(targetId: number) {
    try {
      await removeTarget(targetId);
      setGreskaAkcije("");
    } catch (problem) {
      setGreskaAkcije(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <div
      className={`cdep-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cdep-head">
        <p className="cdep-eyebrow">CODIUM · Kod</p>
        <h1>Deployments</h1>
        <p className="cdep-sub">
          Isporučuje se artefakt uspešnog pokretanja — tačno ono što je prošlo
          korake, bez novog build-a.
        </p>
      </header>

      {isLoading && <p className="cdep-hint">Učitavanje…</p>}
      {error && <p className="cdep-error">{error}</p>}
      {greskaAkcije && <p className="cdep-error">{greskaAkcije}</p>}

      <div className="cdep-grid smart-stack">
        <SmartFrame
          icon={<Server size={15} strokeWidth={1.8} />}
          id="ciljevi"
          layout={layout}
          title="Ciljevi isporuke"
        >
          <section className="cdep-panel">
            <h2>Ciljevi isporuke</h2>
            {targets.length === 0 ? (
              <p className="cdep-hint">
                Nijedan cilj nije definisan. Dodaj ga u okviru desno.
              </p>
            ) : (
              <div className="cdep-kartice">
                {targets.map((cilj) => (
                  <TargetCard
                    key={cilj.id}
                    target={cilj}
                    current={trenutne.get(cilj.id) ?? null}
                    awaitingApproval={cekaOdobrenje.has(cilj.id)}
                    deployableRuns={deployableRuns}
                    onDeploy={async (targetId, runId) => {
                      await deploy(targetId, runId);
                    }}
                    onRemove={ukloni}
                  />
                ))}
              </div>
            )}
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<Rocket size={15} strokeWidth={1.8} />}
          id="nov-cilj"
          layout={layout}
          title="Nov cilj"
        >
          <section className="cdep-panel">
            <h2>Nov cilj</h2>
            <NewTarget onCreate={createTarget} />
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<History size={15} strokeWidth={1.8} />}
          id="istorija"
          layout={layout}
          title="Istorija isporuka"
        >
          <section className="cdep-panel">
            <h2>Istorija isporuka</h2>
            <DeployHistory
              deployments={deployments}
              targets={targets}
              currentIds={trenutniIds}
              onRollback={vrati}
            />
          </section>
        </SmartFrame>
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
