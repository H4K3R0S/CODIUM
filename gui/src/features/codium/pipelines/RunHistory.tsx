import { useEffect, useState } from "react";

import { fetchRuns } from "../../../services/codiumApi";
import type { PipelineRun } from "../../../types/codium";
import { runBadge, runDuration } from "./runBadges";

type Props = {
  pipelineId: number | null;
  selectedRunId: number | null;
  onSelect: (runId: number) => void;
  // Menja se kad se pokrene novo pokretanje, da se istorija osveži.
  refreshKey: number;
};

export default function RunHistory({
  pipelineId,
  selectedRunId,
  onSelect,
  refreshKey,
}: Props) {
  const [ucitana, setUcitana] = useState<PipelineRun[]>([]);
  const [greska, setGreska] = useState("");

  // Bez izabranog pipeline-a spisak je prazan — izvedeno pri crtanju, ne
  // upisano iz efekta.
  const runs = pipelineId === null ? [] : ucitana;

  useEffect(() => {
    if (pipelineId === null) {
      return;
    }
    let otkazano = false;
    fetchRuns(pipelineId, 30)
      .then((odgovor) => {
        if (!otkazano) {
          setUcitana(odgovor.runs);
          setGreska("");
        }
      })
      .catch((problem: unknown) => {
        if (!otkazano) {
          setGreska(problem instanceof Error ? problem.message : String(problem));
        }
      });
    return () => {
      otkazano = true;
    };
  }, [pipelineId, refreshKey]);

  if (pipelineId === null) {
    return <p className="cpipe-hint">Izaberi pipeline.</p>;
  }
  if (greska) {
    return <p className="cpipe-greska">{greska}</p>;
  }
  if (runs.length === 0) {
    return <p className="cpipe-hint">Ovaj pipeline još nije pokretan.</p>;
  }

  return (
    <ul className="cpipe-istorija">
      {runs.map((run) => {
        const znacka = runBadge(run);
        return (
          <li key={run.id}>
            <button
              type="button"
              className={run.id === selectedRunId ? "izabran" : ""}
              onClick={() => onSelect(run.id)}
            >
              <span className={znacka.className}>{znacka.label}</span>
              <span className="cpipe-trajanje">{runDuration(run)}</span>
              <span className="cpipe-vreme">{run.created_at}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
