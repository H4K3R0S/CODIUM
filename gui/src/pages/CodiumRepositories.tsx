// ==========          REPOSITORIES          ==========
// Isti okvir kao ostale CODIUM strane (Access, Audit, AI Agents): zaglavlje sa
// eyebrow-om, okviri u `smart-stack` i CODIUM chat u dnu. Okvir strane je
// zajednicki da bi se domen citao kao jedna celina, a ne kao skup zasebnih
// alata.
import { useState } from "react";
import { FileDiff, FolderPlus, GitBranch, History } from "lucide-react";

import CommitDiff from "../features/codium/repositories/CommitDiff";
import CommitHistory from "../features/codium/repositories/CommitHistory";
import RegisterRepo from "../features/codium/repositories/RegisterRepo";
import RepoList from "../features/codium/repositories/RepoList";
import { useRepositories } from "../features/codium/repositories/useRepositories";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type { CommitInfo } from "../types/codium";
import "../styles/codium-repositories.css";

export default function CodiumRepositories() {
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const { repositories, suggestions, isLoading, error, register, remove, sync } =
    useRepositories();
  const [izabranRepo, setIzabranRepo] = useState<number | null>(null);
  const [izabranCommit, setIzabranCommit] = useState<CommitInfo | null>(null);
  const [greskaAkcije, setGreskaAkcije] = useState("");

  async function sinhronizuj(repoId: number) {
    try {
      await sync(repoId);
      setGreskaAkcije("");
    } catch (problem) {
      setGreskaAkcije(problem instanceof Error ? problem.message : String(problem));
    }
  }

  async function ukloni(repoId: number) {
    try {
      await remove(repoId);
      setGreskaAkcije("");
    } catch (problem) {
      setGreskaAkcije(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <div
      className={`crepo-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="crepo-head">
        <p className="crepo-eyebrow">CODIUM · Kod</p>
        <h1>Repositories</h1>
        <p className="crepo-sub">
          Registrovani git repozitorijumi, njihovo stanje i istorija commit-a.
        </p>
      </header>

      {isLoading && <p className="crepo-hint">Učitavanje…</p>}
      {error && <p className="crepo-error">{error}</p>}
      {greskaAkcije && <p className="crepo-error">{greskaAkcije}</p>}

      <div className="crepo-grid smart-stack">
        <SmartFrame
          icon={<FolderPlus size={15} strokeWidth={1.8} />}
          id="upis"
          layout={layout}
          title="Registruj repozitorijum"
        >
          <section className="crepo-panel">
            <h2>Registruj repozitorijum</h2>
            <RegisterRepo suggestions={suggestions} onRegister={register} />
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<GitBranch size={15} strokeWidth={1.8} />}
          id="repozitorijumi"
          layout={layout}
          title="Repozitorijumi"
        >
          <section className="crepo-panel">
            <h2>Repozitorijumi</h2>
            <RepoList
              repositories={repositories}
              selectedId={izabranRepo}
              onSelect={(repoId) => {
                setIzabranRepo(repoId);
                setIzabranCommit(null);
              }}
              onSync={(repoId) => void sinhronizuj(repoId)}
              onRemove={(repoId) => void ukloni(repoId)}
            />
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<History size={15} strokeWidth={1.8} />}
          id="istorija"
          layout={layout}
          title="Istorija commit-a"
        >
          <section className="crepo-panel">
            <h2>Istorija commit-a</h2>
            <CommitHistory
              repoId={izabranRepo}
              onSelect={setIzabranCommit}
              selectedSha={izabranCommit?.sha ?? null}
            />
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<FileDiff size={15} strokeWidth={1.8} />}
          id="razlika"
          layout={layout}
          title="Razlika"
        >
          <section className="crepo-panel crepo-panel-diff">
            <h2>Razlika</h2>
            <CommitDiff repoId={izabranRepo} commit={izabranCommit} />
          </section>
        </SmartFrame>
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
