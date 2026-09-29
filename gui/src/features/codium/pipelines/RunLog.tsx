import { useEffect, useRef, useState } from "react";

import type { RunLogLine } from "../../../types/codium";
import { parseAnsi } from "./ansi";

type Props = {
  lines: RunLogLine[];
  hiddenCount: number;
  onShowAll: () => void;
};

// Koliko piksela od dna se i dalje računa kao „na dnu".
const PRAG_DNA = 40;

/**
 * Log jednog pokretanja, sa bojama i granicom prikaza.
 *
 * Automatski skrol radi SAMO dok je čovek na dnu. Čim odskroluje gore, skrol
 * se ne pomera pod njim — prikaz koji otima skrol dok čitaš grešku je gori od
 * prikaza bez skrola.
 */
export default function RunLog({ lines, hiddenCount, onShowAll }: Props) {
  const okvir = useRef<HTMLDivElement | null>(null);
  const [prati, setPrati] = useState(true);

  useEffect(() => {
    const element = okvir.current;
    if (element === null || !prati) {
      return;
    }
    element.scrollTop = element.scrollHeight;
  }, [lines, prati]);

  function naSkrol(): void {
    const element = okvir.current;
    if (element === null) {
      return;
    }
    const odDna = element.scrollHeight - element.scrollTop - element.clientHeight;
    setPrati(odDna <= PRAG_DNA);
  }

  return (
    <div className="cpipe-log-okvir">
      {hiddenCount > 0 && (
        <div className="cpipe-log-traka">
          <span>Starijih redova sakriveno: {hiddenCount}</span>
          <button type="button" onClick={onShowAll}>
            Učitaj sve
          </button>
        </div>
      )}

      <div className="cpipe-log" ref={okvir} onScroll={naSkrol}>
        {lines.length === 0 ? (
          <p className="cpipe-hint">Još nema ispisa.</p>
        ) : (
          lines.map((red) => (
            <div key={red.seq} className={`cpipe-log-red ${red.stream}`}>
              {parseAnsi(red.line).map((komad, redni) => (
                <span
                  key={redni}
                  className={[
                    komad.color ? `ansi-${komad.color}` : "",
                    komad.bold ? "ansi-bold" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  {komad.text}
                </span>
              ))}
            </div>
          ))
        )}
      </div>

      {!prati && (
        <button
          type="button"
          className="cpipe-na-dno"
          onClick={() => setPrati(true)}
        >
          Na dno
        </button>
      )}
    </div>
  );
}
