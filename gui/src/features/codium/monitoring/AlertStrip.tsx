import { TriangleAlert } from "lucide-react";

import { alertTime } from "./monitoringLabels";
import type { AlertRow, ServiceOverviewRow } from "../../../types/codium";
import "../../../styles/codium-alerts.css";

type Props = {
  alerts: AlertRow[];
  /** Za prevođenje `rule_id` u ime servisa; prazno je dozvoljeno. */
  services?: ServiceOverviewRow[];
  ruleServiceIds?: Record<number, number>;
};

/**
 * Traka aktivnih alarma.
 *
 * Prazna traka znači da je sve u redu — i to se izgovara, umesto da traka
 * nestane. Nestala traka i traka koja nije stigla izgledaju isto.
 */
export default function AlertStrip({
  alerts,
  services = [],
  ruleServiceIds = {},
}: Props) {
  if (alerts.length === 0) {
    return <p className="cmon-mirno">Nema aktivnih alarma.</p>;
  }

  const imeServisa = (ruleId: number): string => {
    const serviceId = ruleServiceIds[ruleId];
    const servis = services.find((s) => s.service_id === serviceId);
    return servis?.name ?? `pravilo ${ruleId}`;
  };

  return (
    <ul className="cmon-alarmi">
      {alerts.map((alarm) => (
        <li key={alarm.id}>
          <TriangleAlert size={14} strokeWidth={2} aria-hidden="true" />
          <span className="cmon-alarm-cilj">{imeServisa(alarm.rule_id)}</span>
          {alarm.value !== null && (
            <span className="cmon-alarm-vrednost">izmereno {alarm.value}</span>
          )}
          <span className="cmon-alarm-vreme">
            od {alertTime(alarm.started_at)}
          </span>
        </li>
      ))}
    </ul>
  );
}
