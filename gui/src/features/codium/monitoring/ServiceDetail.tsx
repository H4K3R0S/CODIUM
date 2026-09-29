import { useEffect, useState } from "react";

import { fetchMetricSeries } from "../../../services/codiumApi";
import MetricChart from "./MetricChart";
import { METRIKE, PERIODI } from "./monitoringLabels";
import type { SeriesPoint, ServiceOverviewRow } from "../../../types/codium";

type Props = {
  row: ServiceOverviewRow;
};

/**
 * Detalj jednog servisa: jedan grafikon po metrici, sa izborom perioda.
 *
 * Period bira i veličinu kante — dan u minutnim kantama je 1440 tačaka, a
 * nijedan grafikon toliko ne prikazuje. Zato se biraju zajedno.
 */
export default function ServiceDetail({ row }: Props) {
  const [period, setPeriod] = useState(PERIODI[1]);
  const [metrika, setMetrika] = useState(METRIKE[0]);
  // Podaci nose ključ upita kome pripadaju, pa se „učitava se" i sadržaj
  // IZVODE pri crtanju. Ranije je efekat sinhrono palio indikator na svaku
  // promenu metrike ili perioda — to je bio dodatni crtež, a između njih se
  // nakratko video grafikon prethodne metrike kao da je nov.
  const kljuc = `${row.service_id}|${metrika.metric}|${period.bucket}`;
  const [ucitano, setUcitano] = useState<{
    kljuc: string;
    tacke: SeriesPoint[];
  } | null>(null);

  const ucitavanje = ucitano?.kljuc !== kljuc;
  const tacke = ucitano?.kljuc === kljuc ? ucitano.tacke : [];

  useEffect(() => {
    let otkazano = false;
    fetchMetricSeries(row.service_id, metrika.metric, period.bucket, 200)
      .then((odgovor) => {
        if (!otkazano) {
          setUcitano({ kljuc, tacke: odgovor.points });
        }
      })
      .catch(() => {
        if (!otkazano) {
          setUcitano({ kljuc, tacke: [] });
        }
      });
    return () => {
      otkazano = true;
    };
  }, [kljuc, row.service_id, metrika, period]);

  return (
    <div className="cmon-detalj">
      <div className="cmon-izbor">
        <div className="cmon-tabovi" role="group" aria-label="Metrika">
          {METRIKE.map((stavka) => (
            <button
              key={stavka.metric}
              type="button"
              className={stavka.metric === metrika.metric ? "izabran" : ""}
              onClick={() => setMetrika(stavka)}
            >
              {stavka.label}
            </button>
          ))}
        </div>
        <div className="cmon-tabovi" role="group" aria-label="Period">
          {PERIODI.map((stavka) => (
            <button
              key={stavka.id}
              type="button"
              className={stavka.id === period.id ? "izabran" : ""}
              onClick={() => setPeriod(stavka)}
            >
              {stavka.label}
            </button>
          ))}
        </div>
      </div>

      {ucitavanje ? (
        <p className="cmon-hint">Učitavanje…</p>
      ) : (
        <MetricChart
          points={tacke}
          metric={metrika.metric}
          unit={metrika.unit}
        />
      )}
    </div>
  );
}
