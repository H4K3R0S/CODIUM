import { useState } from "react";

import type { AnalyticsReport } from "../../../types/codium";

type Props = {
  report: AnalyticsReport;
};

const SIRINA = 640;
const VISINA = 200;
const MARGINA = { levo: 46, desno: 14, gore: 14, dole: 34 };

const CRTAC = SIRINA - MARGINA.levo - MARGINA.desno;
const VISINA_CRTACA = VISINA - MARGINA.gore - MARGINA.dole;

/** Tri linije mreže dovoljne su da se pročita nivo, a ne smetaju. */
const LINIJA_MREZE = 3;

/** Preko ovoga stubac prestaje da bude oznaka vrednosti i postaje površina. */
const MAKS_SIRINA_STUPCA = 42;

/** Dve boje: akcent domena i neutralna. Više od dve serije nijedan izveštaj
 *  ne vraća — kad bude, kategorijska paleta se uvodi tada, ne unapred. */
const BOJE = ["prva", "druga"];

/** Datum (`2026-09-09`) ide kao linija; ime (korak, model) kao stupci. */
function jeDatum(x: string): boolean {
  return /^\d{4}-\d{2}-\d{2}/.test(x);
}

/** Srpski broj uz imenicu: 1 tačka, 2-4 tačke, 5+ tačaka. */
function brojTacaka(broj: number): string {
  const poslednja = broj % 10;
  const poslednje_dve = broj % 100;
  if (poslednja === 1 && poslednje_dve !== 11) {
    return `${broj} tačka`;
  }
  if (poslednja >= 2 && poslednja <= 4 && (poslednje_dve < 12 || poslednje_dve > 14)) {
    return `${broj} tačke`;
  }
  return `${broj} tačaka`;
}


function skratiOznaku(x: string): string {
  if (jeDatum(x)) {
    // `2026-09-09` -> `09-09`; godina se ne ponavlja na svakoj tački.
    return x.slice(5, 10);
  }
  return x.length > 14 ? `${x.slice(0, 13)}…` : x;
}

/**
 * Jedan grafikon za sve izveštaje.
 *
 * Moguć je samo zato što svi izveštaji imaju isti oblik odgovora. Forma se
 * bira iz podataka, ne iz imena izveštaja: dani kroz vreme su linija,
 * imenovane kategorije su stupci.
 */
export default function ReportChart({ report }: Props) {
  const [preko, setPreko] = useState<number | null>(null);

  const serije = report.series.filter((s) => s.points.length > 0);
  if (serije.length === 0) {
    return <p className="cana-hint">Za ovaj period nema podataka.</p>;
  }

  // Sve serije jednog izveštaja dele istu osu x — backend ih tako i vraća.
  const oznake = serije[0].points.map((t) => t.x);
  const linijski = oznake.every(jeDatum);

  const sveVrednosti = serije.flatMap((s) => s.points.map((t) => t.y));
  const najveca = Math.max(...sveVrednosti);
  // Osa uvek počinje od nule; ona koja ne počinje preuveličava male razlike.
  // Kad su SVE vrednosti nula, osa ide do jedan — inače bi sva četiri broja
  // na njoj bila `0.00`, što ne kaže ništa.
  const vrh = najveca > 0 ? najveca * 1.1 : 1;

  const x = (redni: number) =>
    MARGINA.levo +
    (oznake.length === 1
      ? CRTAC / 2
      : (redni / (oznake.length - 1)) * CRTAC);
  const y = (vrednost: number) =>
    MARGINA.gore + VISINA_CRTACA - (vrednost / vrh) * VISINA_CRTACA;

  // Stupci: širina po grupi, pa po seriji unutar grupe. Gornja granica
  // postoji jer bi jedna jedina kategorija inače dobila stubac preko celog
  // grafikona — zid, ne podatak.
  const sirinaGrupe = CRTAC / Math.max(oznake.length, 1);
  const sirinaStupca = Math.min(
    MAKS_SIRINA_STUPCA,
    Math.max(2, (sirinaGrupe * 0.7) / serije.length),
  );
  // Grupa se centrira u svom pojasu; sa širokim pojasom i uskim stupcem
  // levo poravnanje bi ostavilo rupu pored oznake na osi.
  const sirinaGrupeStubaca = sirinaStupca * serije.length + (serije.length - 1) * 2;
  const stubX = (redni: number, serijaRedni: number) =>
    MARGINA.levo +
    redni * sirinaGrupe +
    (sirinaGrupe - sirinaGrupeStubaca) / 2 +
    serijaRedni * (sirinaStupca + 2);

  return (
    <div className="cana-grafikon">
      {/* Za dve i više serija legenda je uvek tu — identitet ne sme da zavisi
          samo od boje. */}
      {serije.length > 1 && (
        <ul className="cana-legenda">
          {serije.map((serija, redni) => (
            <li key={serija.label}>
              <span className={`cana-uzorak ${BOJE[redni % BOJE.length]}`} />
              {serija.label}
            </li>
          ))}
        </ul>
      )}

      <svg
        viewBox={`0 0 ${SIRINA} ${VISINA}`}
        role="img"
        aria-label={`Izveštaj ${report.name}`}
        onMouseLeave={() => setPreko(null)}
      >
        {Array.from({ length: LINIJA_MREZE + 1 }, (_, red) => {
          const vrednost = (vrh * red) / LINIJA_MREZE;
          const linijaY = y(vrednost);
          return (
            <g key={red}>
              <line
                className="cana-mreza"
                x1={MARGINA.levo}
                x2={SIRINA - MARGINA.desno}
                y1={linijaY}
                y2={linijaY}
              />
              <text className="cana-osa-y" x={MARGINA.levo - 6} y={linijaY + 3}>
                {vrh >= 10 ? vrednost.toFixed(0) : vrednost.toFixed(2)}
              </text>
            </g>
          );
        })}

        {linijski
          ? serije.map((serija, serijaRedni) => (
              <polyline
                key={serija.label}
                className={`cana-linija ${BOJE[serijaRedni % BOJE.length]}`}
                points={serija.points
                  .map((t, redni) => `${x(redni).toFixed(1)},${y(t.y).toFixed(1)}`)
                  .join(" ")}
              />
            ))
          : serije.map((serija, serijaRedni) =>
              serija.points.map((tacka, redni) => (
                <rect
                  key={`${serija.label}-${tacka.x}`}
                  className={`cana-stub ${BOJE[serijaRedni % BOJE.length]}`}
                  x={stubX(redni, serijaRedni)}
                  y={y(tacka.y)}
                  width={sirinaStupca}
                  height={Math.max(0, y(0) - y(tacka.y))}
                  rx={2}
                />
              )),
            )}

        {preko !== null && linijski && (
          <line
            className="cana-nisan"
            x1={x(preko)}
            x2={x(preko)}
            y1={MARGINA.gore}
            y2={MARGINA.gore + VISINA_CRTACA}
          />
        )}

        {/* Meta za prelaz mišem je široka koliko razmak, ne koliko tačka. */}
        {oznake.map((oznaka, redni) => (
          <rect
            key={oznaka}
            className="cana-meta"
            x={MARGINA.levo + redni * sirinaGrupe}
            y={MARGINA.gore}
            width={sirinaGrupe}
            height={VISINA_CRTACA}
            onMouseEnter={() => setPreko(redni)}
          />
        ))}

        {/* Oznake ose x: prva, srednja i poslednja — sve bi se preklopile. */}
        {[0, Math.floor((oznake.length - 1) / 2), oznake.length - 1]
          .filter((redni, mesto, svi) => svi.indexOf(redni) === mesto)
          .map((redni) => (
            <text
              key={redni}
              className="cana-osa-x"
              x={
                linijski
                  ? x(redni)
                  : MARGINA.levo + redni * sirinaGrupe + sirinaGrupe / 2
              }
              y={VISINA - 12}
            >
              {skratiOznaku(oznake[redni])}
            </text>
          ))}
      </svg>

      <p className="cana-ocitavanje">
        {preko === null ? (
          <>{brojTacaka(oznake.length)}</>
        ) : (
          <>
            <strong>{oznake[preko]}</strong>
            {serije.map((serija) => (
              <span key={serija.label} className="cana-ocitana">
                {serija.label}: <strong>{serija.points[preko]?.y ?? "—"}</strong>
              </span>
            ))}
          </>
        )}
      </p>
    </div>
  );
}
