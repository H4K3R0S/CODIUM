import { useState } from "react";

import type { SeriesPoint } from "../../../types/codium";

type Props = {
  points: SeriesPoint[];
  metric: string;
  /** Jedinica uz vrednost u opisu (`ms`, `%`, `MB`). Prazno za `up`. */
  unit?: string;
};

const SIRINA = 640;
const VISINA = 180;
const MARGINA = { levo: 44, desno: 12, gore: 12, dole: 22 };

const CRTAC = SIRINA - MARGINA.levo - MARGINA.desno;
const VISINA_CRTACA = VISINA - MARGINA.gore - MARGINA.dole;

/** Koliko linija mreze — tri su dovoljne da se procita nivo, a ne smetaju. */
const LINIJA_MREZE = 3;


function skrati(bucket: string): string {
  // `2026-09-03 14:00` -> `14:00`; `2026-09-03` ostaje kakav jeste.
  const deo = bucket.split(" ")[1];
  return deo ?? bucket;
}


/**
 * Jedna serija kroz vreme, sa mrežom, osom i tooltipom na prelaz mišem.
 *
 * Jedna serija znači da legenda ne treba — naslov iznad grafikona već kaže
 * šta se crta. Brojevi stoje na osi i u tooltipu, ne na svakoj tački.
 */
export default function MetricChart({ points, metric, unit = "" }: Props) {
  const [preko, setPreko] = useState<number | null>(null);

  if (points.length === 0) {
    return <p className="cmon-hint">Za ovaj period nema merenja.</p>;
  }

  const vrednosti = points.map((t) => t.value);
  // `up` je uvek 0..1; ostale metrike se skaliraju po izmerenom, uz nulu kao
  // dno — grafikon koji ne počinje od nule preuveličava male razlike.
  const vrh = metric === "up" ? 1 : Math.max(...vrednosti, 0.001) * 1.1;
  const dno = 0;
  const raspon = vrh - dno || 1;

  const x = (redni: number) =>
    MARGINA.levo +
    (points.length === 1 ? CRTAC / 2 : (redni / (points.length - 1)) * CRTAC);
  const y = (vrednost: number) =>
    MARGINA.gore + VISINA_CRTACA - ((vrednost - dno) / raspon) * VISINA_CRTACA;

  const linija = points
    .map((tacka, redni) => `${x(redni).toFixed(1)},${y(tacka.value).toFixed(1)}`)
    .join(" ");

  const izabrana = preko === null ? null : points[preko];

  return (
    <div className="cmon-grafikon">
      <svg
        viewBox={`0 0 ${SIRINA} ${VISINA}`}
        role="img"
        aria-label={`${metric} kroz vreme`}
        onMouseLeave={() => setPreko(null)}
      >
        {/* Mreza i osa su recesivni — podaci su ono sto se cita. */}
        {Array.from({ length: LINIJA_MREZE + 1 }, (_, red) => {
          const vrednost = dno + (raspon * red) / LINIJA_MREZE;
          const linijaY = y(vrednost);
          return (
            <g key={red}>
              <line
                className="cmon-mreza"
                x1={MARGINA.levo}
                x2={SIRINA - MARGINA.desno}
                y1={linijaY}
                y2={linijaY}
              />
              <text className="cmon-osa" x={MARGINA.levo - 6} y={linijaY + 3}>
                {vrednost >= 10 ? vrednost.toFixed(0) : vrednost.toFixed(2)}
              </text>
            </g>
          );
        })}

        <polygon
          className="cmon-ispuna"
          points={
            `${x(0)},${y(dno)} ${linija} ` +
            `${x(points.length - 1)},${y(dno)}`
          }
        />
        <polyline className="cmon-linija" points={linija} />

        {izabrana !== null && preko !== null && (
          <>
            <line
              className="cmon-nisan"
              x1={x(preko)}
              x2={x(preko)}
              y1={MARGINA.gore}
              y2={MARGINA.gore + VISINA_CRTACA}
            />
            <circle
              className="cmon-tacka"
              cx={x(preko)}
              cy={y(izabrana.value)}
              r={4}
            />
          </>
        )}

        {/* Nevidljive trake za prelaz misem: meta je siroka koliko i razmak
            izmedju tacaka, ne koliko sama tacka. */}
        {points.map((tacka, redni) => (
          <rect
            key={tacka.bucket}
            className="cmon-meta"
            x={x(redni) - CRTAC / (points.length * 2)}
            y={MARGINA.gore}
            width={CRTAC / points.length || 8}
            height={VISINA_CRTACA}
            onMouseEnter={() => setPreko(redni)}
          />
        ))}

        <text className="cmon-osa" x={MARGINA.levo} y={VISINA - 6}>
          {skrati(points[0].bucket)}
        </text>
        <text
          className="cmon-osa cmon-osa-desno"
          x={SIRINA - MARGINA.desno}
          y={VISINA - 6}
        >
          {skrati(points[points.length - 1].bucket)}
        </text>
      </svg>

      <p className="cmon-ocitavanje">
        {izabrana === null ? (
          <>
            poslednje: <strong>{points[points.length - 1].value}</strong>
            {unit}
          </>
        ) : (
          <>
            {izabrana.bucket}: <strong>{izabrana.value}</strong>
            {unit} <span className="cmon-hint">({izabrana.samples} uzoraka)</span>
          </>
        )}
      </p>
    </div>
  );
}
