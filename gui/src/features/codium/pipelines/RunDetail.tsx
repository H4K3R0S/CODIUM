import { useEffect, useRef, useState } from "react";

import { cancelRun } from "../../../services/codiumApi";
import RunLog from "./RunLog";
import { runBadge, runDuration } from "./runBadges";
import { useRunPolling } from "./useRunPolling";

type Props = {
  runId: number | null;
  onCancelled: () => void;
  // Zove se kad pokretanje samo od sebe dođe do završnog statusa (bez klika
  // na Otkaži). Roditelj time zna da osveži broj aktivnih pokretanja koji
  // koristi useCloseGuard — bez ovoga bi brojač ostao zaglavljen na starom
  // broju posle prirodnog završetka.
  onRunEnded?: () => void;
};

/** Zaglavlje pokretanja, koraci i log. */
export default function RunDetail({ runId, onCancelled, onRunEnded }: Props) {
  const { run, steps, lines, hiddenCount, isPolling, error, showAll } =
    useRunPolling(runId);
  const [greskaAkcije, setGreskaAkcije] = useState("");
  // Sprečava dupli zahtev za otkazivanje kad se dugme klikne dva puta zaredom
  // pre nego što prvi zahtev stigne da se vrati.
  const [otkazivanjeUToku, setOtkazivanjeUToku] = useState(false);

  // Prati prelaz isPolling true -> false da bi javio roditelju samo na
  // stvarni kraj pokretanja, ne i na svaki render dok je već mirno.
  const bilaUToku = useRef(false);
  useEffect(() => {
    if (bilaUToku.current && !isPolling) {
      onRunEnded?.();
    }
    bilaUToku.current = isPolling;
  }, [isPolling, onRunEnded]);

  if (runId === null) {
    return <p className="cpipe-hint">Izaberi pokretanje.</p>;
  }
  if (error) {
    return <p className="cpipe-greska">{error}</p>;
  }
  if (run === null) {
    return <p className="cpipe-hint">Učitavanje…</p>;
  }

  const znacka = runBadge(run);

  async function otkazi(): Promise<void> {
    if (otkazivanjeUToku) {
      return;
    }
    setOtkazivanjeUToku(true);
    try {
      await cancelRun(runId as number);
      setGreskaAkcije("");
      onCancelled();
    } catch (problem) {
      setGreskaAkcije(
        problem instanceof Error ? problem.message : String(problem),
      );
    } finally {
      setOtkazivanjeUToku(false);
    }
  }

  return (
    <div className="cpipe-detalj">
      <header className="cpipe-detalj-glava">
        <span className={znacka.className}>{znacka.label}</span>
        <span className="cpipe-trajanje">{runDuration(run)}</span>
        {run.detail && <span className="cpipe-razlog">{run.detail}</span>}
        {isPolling && (
          <button
            type="button"
            disabled={otkazivanjeUToku}
            onClick={() => void otkazi()}
          >
            Otkaži
          </button>
        )}
      </header>

      {greskaAkcije && <p className="cpipe-greska">{greskaAkcije}</p>}

      <ol className="cpipe-koraci">
        {steps.map((korak) => (
          <li key={korak.idx} className={`cpipe-korak ${korak.status}`}>
            <span className="cpipe-korak-ime">{korak.name}</span>
            <span className="cpipe-korak-status">{korak.status}</span>
            {korak.exit_code !== null && (
              <span className="cpipe-korak-kod">kod {korak.exit_code}</span>
            )}
          </li>
        ))}
      </ol>

      <RunLog lines={lines} hiddenCount={hiddenCount} onShowAll={showAll} />
    </div>
  );
}
