import { Trash2 } from "lucide-react";

import type { AutomationRule } from "../../../types/codium";
import { eventLabel, vreme } from "./automationLabels";

interface Props {
  rule: AutomationRule;
  /** Ime akcije u čitljiv naziv; nepoznato ostaje kako jeste. */
  actionLabels: Record<string, string>;
  onToggle: () => void;
  onDelete: () => void;
  onTest: () => void;
}

/** Jedan red spiska: prekidač, tri dela pravila, vreme poslednjeg okidanja. */
export default function RuleRow({ rule, actionLabels, onToggle, onDelete,
                                  onTest }: Props) {
  return (
    <li className={`caut-red ${rule.enabled ? "" : "ugaseno"}`}>
      <label className="caut-prekidac">
        <input
          type="checkbox"
          checked={rule.enabled}
          aria-label={`Uključi pravilo ${rule.name}`}
          onChange={onToggle}
        />
        <span />
      </label>

      <div className="caut-red-telo">
        <p className="caut-red-ime">{rule.name}</p>
        <p className="caut-red-opis">
          <span className="caut-kad">KADA</span> {eventLabel(rule.event)}
          {rule.condition_expr !== "" && (
            <>
              {" "}
              <span className="caut-kad">AKO</span>{" "}
              <code>{rule.condition_expr}</code>
            </>
          )}{" "}
          <span className="caut-kad">ONDA</span>{" "}
          {rule.actions.map((a) => actionLabels[a.name] ?? a.name).join(", ")}
        </p>
        <p className="caut-red-vreme">Poslednje okidanje: {vreme(rule.last_run_at)}</p>
      </div>

      <div className="caut-red-alat">
        <button type="button" onClick={onTest}>Probaj</button>
        <button type="button" className="caut-brisi" onClick={onDelete}
                aria-label={`Obriši pravilo ${rule.name}`}>
          <Trash2 size={13} strokeWidth={2} />
        </button>
      </div>
    </li>
  );
}
