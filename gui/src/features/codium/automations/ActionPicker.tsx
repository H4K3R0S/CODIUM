import { ShieldAlert } from "lucide-react";

import type { AutomationActionSpec } from "../../../types/codium";

interface Props {
  actions: AutomationActionSpec[];
  izabrane: string[];
  onToggle: (name: string) => void;
}

/**
 * Treći korak: akcije.
 *
 * Uz svaku odmah piše da li traži odobrenje. To se vidi PRE snimanja, ne kad
 * se pravilo prvi put upali i stane na redu za odobrenje.
 */
export default function ActionPicker({ actions, izabrane, onToggle }: Props) {
  return (
    <ul className="caut-akcije">
      {actions.map((akcija) => (
        <li key={akcija.name}>
          <label>
            <input
              type="checkbox"
              checked={izabrane.includes(akcija.name)}
              onChange={() => onToggle(akcija.name)}
            />
            <span className="caut-akcija-ime">{akcija.label}</span>
            {akcija.requires_approval && (
              <span className="caut-odobrenje">
                <ShieldAlert size={12} strokeWidth={2} />
                traži odobrenje
              </span>
            )}
          </label>
          <p className="caut-akcija-opis">{akcija.description}</p>
        </li>
      ))}
    </ul>
  );
}
