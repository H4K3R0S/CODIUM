import { useState } from "react";

import type { CommitInfo } from "../../../types/codium";
import CommitDiff from "./CommitDiff";
import CommitHistory from "./CommitHistory";
import { repoBadges } from "./repoBadges";
import { useRepositories } from "./useRepositories";

type Props = {
  projectId: number;
};

/**
 * Git uz editor: repozitorijum aktivnog projekta, stanje, istorija i razlika.
 *
 * Uži rez strane `/codium/repositories` — registracija ovde namerno ne stoji,
 * jer je registar odluka koja se donosi nad celim domenom, ne usput.
 */
export default function GitPanel({ projectId }: Props) {
  const { repositories, isLoading, error, sync } = useRepositories(projectId, {
    skipSuggestions: true,
  });
  const [izabranCommit, setIzabranCommit] = useState<CommitInfo | null>(null);
  const [greskaSinhronizacije, setGreskaSinhronizacije] = useState("");

  const repo = repositories[0] ?? null;

  async function sinhronizuj(repoId: number) {
    try {
      await sync(repoId);
      setGreskaSinhronizacije("");
    } catch (problem) {
      setGreskaSinhronizacije(
        problem instanceof Error ? problem.message : String(problem),
      );
    }
  }

  if (isLoading) {
    return <p className="crepo-hint">Učitavanje…</p>;
  }
  if (error) {
    return <p className="crepo-greska">{error}</p>;
  }
  if (repo === null) {
    return (
      <p className="crepo-hint">
        Projekat nema registrovan repozitorijum. Dodaj ga na strani Repositories.
      </p>
    );
  }

  return (
    <div className="crepo-panel">
      <header className="crepo-panel-glava">
        <strong>{repo.name}</strong>
        <div className="crepo-znacke">
          {repoBadges(repo.status).map((znacka) => (
            <span key={znacka} className="crepo-znacka">
              {znacka}
            </span>
          ))}
        </div>
        <button type="button" onClick={() => void sinhronizuj(repo.id)}>
          Sinhronizuj
        </button>
      </header>
      {greskaSinhronizacije && <p className="crepo-greska">{greskaSinhronizacije}</p>}

      <CommitHistory
        repoId={repo.id}
        onSelect={setIzabranCommit}
        selectedSha={izabranCommit?.sha ?? null}
      />
      <CommitDiff repoId={repo.id} commit={izabranCommit} />
    </div>
  );
}
