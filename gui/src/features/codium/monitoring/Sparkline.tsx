import type { SeriesPoint } from "../../../types/codium";

type Props = {
  points: SeriesPoint[];
  /** Opseg vrednosti; za `up` je uvek 0..1, pa se ne izvodi iz podataka. */
  min?: number;
  max?: number;
  label: string;
};

const SIRINA = 120;
const VISINA = 28;

/**
 * Jedna serija, bez osa i bez brojeva — sparkline.
 *
 * Namerno nije pun grafikon: pločica servisa pokazuje oblik ponašanja, a
 * tačne vrednosti stoje kao tekst pored nje. Broj na svakoj tački bio bi
 * nečitljiv na 120 piksela.
 */
export default function Sparkline({ points, min, max, label }: Props) {
  if (points.length < 2) {
    return <div className="cmon-spark cmon-spark-prazan">nema merenja</div>;
  }

  const vrednosti = points.map((t) => t.value);
  const dno = min ?? Math.min(...vrednosti);
  const vrh = max ?? Math.max(...vrednosti);
  const raspon = vrh - dno || 1;

  const tacke = points.map((tacka, redni) => {
    const x = (redni / (points.length - 1)) * SIRINA;
    const y = VISINA - ((tacka.value - dno) / raspon) * VISINA;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <svg
      className="cmon-spark"
      viewBox={`0 0 ${SIRINA} ${VISINA}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      {/* Ispuna nosi oblik, linija nosi vrednost — 2px, kako i treba. */}
      <polygon
        className="cmon-spark-ispuna"
        points={`0,${VISINA} ${tacke.join(" ")} ${SIRINA},${VISINA}`}
      />
      <polyline className="cmon-spark-linija" points={tacke.join(" ")} />
    </svg>
  );
}
