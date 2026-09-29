import {
  chatModels,
  formatModelLabel,
  groupModels,
  isFreeModel,
  needsApiKey,
  shortModelLabel,
  type CatalogModel,
} from "../settings/modelPicker";
import { API_KEY_OPTION } from "./useAssistantChat";
import ChatSelect, {
  type ChatSelectGroup,
} from "../../components/chat/ChatSelect";


// ==========          IZBORNIK MODELA (deljen)          ==========
// Isti izbornik u dashboard chatu i u AI Workspace-u. Dve kopije bi se
// razišle — ranije jesu: Workspace je imao izbor modela, dashboard nije.

type AssistantModelSelectProps = {
  models: CatalogModel[];
  value: string;
  onChange: (next: string) => void;
  className?: string;
  /**
   * Kratko ime modela umesto punog natpisa. Uz polje za unos nema mesta za
   * cenu i velicinu, a i izbor se donosi u podesavanjima, gde pun natpis
   * ostaje.
   */
  compact?: boolean;
};

function AssistantModelSelect({
  models,
  value,
  onChange,
  className = "cai-model",
  compact = false,
}: AssistantModelSelectProps) {
  const vidljivi = chatModels(models);
  const natpis = compact ? shortModelLabel : formatModelLabel;

  // Uz polje za unos ide izbornik koji se crta u stranici: spisak `<select>`-a
  // crta operativni sistem, pa je uvek neprozirno beo i iskace iz providnog
  // okvira. U podesavanjima, na punoj podlozi, `<select>` je i dalje u redu.
  if (compact) {
    const grupe: ChatSelectGroup[] = groupModels(vidljivi).map((group) => ({
      title: group.title,
      options: group.models.map((m) => ({
        value: m.id,
        label: natpis(m),
        disabled: !m.available,
        free: isFreeModel(m),
      })),
    }));
    if (needsApiKey(vidljivi)) {
      grupe.push({
        options: [{ value: API_KEY_OPTION, label: "Potreban API ključ…" }],
      });
    }

    return (
      <ChatSelect
        ariaLabel="Model"
        className={className}
        value={value}
        groups={grupe}
        onChange={onChange}
        placeholder="Model"
      />
    );
  }

  return (
    <select
      className={className}
      aria-label="Model"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onClick={(event) => event.stopPropagation()}
    >
      {/* Prazan izbor: ruter bira po registru. Kratak natpis jer izbornik
          stoji uz polje za unos, gde je prostor uzak. */}
      <option value="">Model</option>
      {groupModels(vidljivi).map((group) => (
        <optgroup key={group.title} label={group.title}>
          {group.models.map((m) => (
            // Izvorni `<select>` crta operativni sistem i ne prima okvir na
            // pojedinacnoj stavci, pa zelene trake ovde nema. Oznaka svejedno
            // stoji: ovaj oblik izbornika koristi `formatModelLabel`, koji
            // besplatan model vec ispisuje kao takav.
            <option key={`${m.provider}:${m.id}`} value={m.id} disabled={!m.available}>
              {natpis(m)}
            </option>
          ))}
        </optgroup>
      ))}
      {needsApiKey(vidljivi) && (
        <option value={API_KEY_OPTION}>Potreban API ključ…</option>
      )}
    </select>
  );
}

export default AssistantModelSelect;
