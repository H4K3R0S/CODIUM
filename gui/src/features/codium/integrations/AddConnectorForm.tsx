import { useMemo, useState } from "react";
import { Plus } from "lucide-react";

import type { ConnectorKindDto } from "../../../services/coreApi";
import { describeForm, missingFields, splitPayload } from "./connectorForm";

interface Props {
  kinds: ConnectorKindDto[];
  onCreate: (payload: {
    name: string;
    kind: string;
    secret: string;
    config: Record<string, string>;
  }) => Promise<void>;
}

/**
 * Jedna forma za sve vrste konektora.
 *
 * Ime fajla je `AddConnectorForm`, a ne `ConnectorForm`, zato što bi se na
 * Windows-u sudarilo sa čistim modulom `connectorForm.ts` — datotečni sistem ne
 * razlikuje velika i mala slova, pa bi uvoz `./connectorForm` vraćao samu
 * komponentu i ona bi bila `undefined`.
 *
 * Polja se grade iz opisa vrste (`describeForm`), pa ovde nema nijednog `if`
 * po vrsti. Vrsta bez provajdera se ne nudi — ponuditi je značilo bi obećati
 * konektor koji ništa ne ume da uradi.
 */
export default function AddConnectorForm({ kinds, onCreate }: Props) {
  const [vrsta, setVrsta] = useState("");
  const [ime, setIme] = useState("");
  const [unos, setUnos] = useState<Record<string, string>>({});
  const [greska, setGreska] = useState("");
  const [snima, setSnima] = useState(false);

  const podrzane = useMemo(() => kinds.filter((k) => k.supported), [kinds]);
  const izabrana = podrzane.find((k) => k.id === vrsta) ?? null;
  const opis = izabrana === null ? null : describeForm(izabrana);

  const fale = opis === null
    ? ["kind"]
    : missingFields(opis, { name: ime, values: unos });

  async function snimi() {
    if (opis === null) {
      return;
    }
    setSnima(true);
    try {
      const { config, secret } = splitPayload(opis, { name: ime, values: unos });
      await onCreate({ name: ime.trim(), kind: opis.kind, secret, config });
      setIme("");
      setUnos({});
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    } finally {
      setSnima(false);
    }
  }

  return (
    <div className="cint-forma">
      <label>
        <span>Vrsta</span>
        <select
          aria-label="Vrsta konektora"
          value={vrsta}
          onChange={(e) => {
            setVrsta(e.target.value);
            // Polja pripadaju staroj vrsti i na novoj ne postoje.
            setUnos({});
          }}
        >
          <option value="">— izaberi vrstu —</option>
          {podrzane.map((k) => (
            <option key={k.id} value={k.id}>{k.label}</option>
          ))}
        </select>
      </label>

      {opis !== null && (
        <>
          <label>
            <span>Ime</span>
            <input
              type="text"
              aria-label="Ime konektora"
              value={ime}
              placeholder="GitHub — radni nalog"
              onChange={(e) => setIme(e.target.value)}
            />
          </label>

          {opis.fields.map((polje) => (
            <label key={polje.name}>
              <span>
                {polje.label}
                {!polje.required && <em> (nije obavezno)</em>}
              </span>
              <input
                // Tajna ide kao lozinka: vrednost se kuca jednom i posle se ne
                // prikazuje ni ovde ni u odgovoru servera.
                type={polje.secret ? "password" : "text"}
                aria-label={polje.label}
                value={unos[polje.name] ?? ""}
                placeholder={polje.placeholder}
                onChange={(e) =>
                  setUnos((staro) => ({ ...staro, [polje.name]: e.target.value }))
                }
              />
            </label>
          ))}

          <button
            type="button"
            className="cint-snimi"
            disabled={fale.length > 0 || snima}
            onClick={() => void snimi()}
          >
            <Plus size={13} strokeWidth={2} />
            Dodaj konektor
          </button>
          {greska !== "" && <p className="cint-greska">{greska}</p>}
        </>
      )}
    </div>
  );
}
