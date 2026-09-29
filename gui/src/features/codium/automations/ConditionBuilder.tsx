import type { AutomationEventSpec } from "../../../types/codium";

// Operatori koje razume parser na serveru. Spisak je ovde namerno kratak:
// uređivač nudi samo ono što gramatika prima, pa čovek ne može da sastavi
// uslov koji server odbija.
const OPERATORI = ["==", "!=", ">", ">=", "<", "<=", "contains"] as const;

interface Props {
  event: AutomationEventSpec | null;
  polje: string;
  operator: string;
  vrednost: string;
  onChange: (polje: string, operator: string, vrednost: string) => void;
}

/**
 * Drugi korak: uslov nad poljima izabranog događaja.
 *
 * Polja se biraju iz spiska koji je doneo događaj — čovek ne pogađa imena, i
 * ne može da napiše uslov nad poljem koje taj događaj nikad ne nosi.
 */
export default function ConditionBuilder({ event, polje, operator, vrednost,
                                           onChange }: Props) {
  if (event === null) {
    return <p className="caut-prazno">Prvo izaberi događaj.</p>;
  }

  return (
    <div className="caut-uslov">
      <select
        aria-label="Polje"
        value={polje}
        onChange={(e) => onChange(e.target.value, operator, vrednost)}
      >
        <option value="">— bez uslova (uvek) —</option>
        {event.fields.map((ime) => (
          <option key={ime} value={ime}>{ime}</option>
        ))}
      </select>

      <select
        aria-label="Operator"
        value={operator}
        disabled={polje === ""}
        onChange={(e) => onChange(polje, e.target.value, vrednost)}
      >
        {OPERATORI.map((znak) => (
          <option key={znak} value={znak}>{znak}</option>
        ))}
      </select>

      <input
        aria-label="Vrednost"
        type="text"
        value={vrednost}
        disabled={polje === ""}
        placeholder="failed"
        onChange={(e) => onChange(polje, operator, e.target.value)}
      />
    </div>
  );
}
