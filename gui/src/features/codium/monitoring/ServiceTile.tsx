import { useEffect, useState } from "react";

import { fetchMetricSeries } from "../../../services/codiumApi";
import Sparkline from "./Sparkline";
import { tileState, uptimeLabel } from "./monitoringLabels";
import type { SeriesPoint, ServiceOverviewRow } from "../../../types/codium";

type Props = {
  row: ServiceOverviewRow;
  selected: boolean;
  onSelect: (serviceId: number) => void;
};

/**
 * Jedna pločica: servis, stanje, dostupnost u 24 sata i oblik ponašanja.
 *
 * Sparkline se dovlači po pločici, ne u zbirnom pozivu: pregled bi inače
 * nosio niz tačaka po servisu, a najveći deo ekrana su servisi koje čovek u
 * tom trenutku i ne gleda.
 */
export default function ServiceTile({ row, selected, onSelect }: Props) {
  const [tacke, setTacke] = useState<SeriesPoint[]>([]);

  useEffect(() => {
    let otkazano = false;
    fetchMetricSeries(row.service_id, "up", "hour", 24)
      .then((odgovor) => {
        if (!otkazano) {
          setTacke(odgovor.points);
        }
      })
      // Grafikon je dodatak — pločica bez njega i dalje kaže sve bitno.
      .catch(() => setTacke([]));
    return () => {
      otkazano = true;
    };
  }, [row.service_id]);

  const znacka = tileState(row);

  return (
    <button
      type="button"
      className={`cmon-plocica ${selected ? "izabrana" : ""}`}
      onClick={() => onSelect(row.service_id)}
    >
      <span className="cmon-plocica-glava">
        <span className="cmon-ime">{row.name}</span>
        <span className={znacka.className}>{znacka.label}</span>
      </span>

      <Sparkline
        points={tacke}
        min={0}
        max={1}
        label={`Dostupnost servisa ${row.name} u poslednja 24 sata`}
      />

      <span className="cmon-brojevi">
        <span>
          dostupnost <strong>{uptimeLabel(row.uptime_24h)}</strong>
        </span>
        {row.latency_ms !== null && (
          <span>
            odziv <strong>{row.latency_ms}</strong> ms
          </span>
        )}
        {row.cpu_percent !== null && (
          <span>
            procesor <strong>{row.cpu_percent}</strong> %
          </span>
        )}
        {row.memory_mb !== null && (
          <span>
            memorija <strong>{row.memory_mb}</strong> MB
          </span>
        )}
      </span>
    </button>
  );
}
