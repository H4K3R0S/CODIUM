import { useCallback, useEffect, useState } from "react";
import { RotateCcw, Save } from "lucide-react";

import {
  listCorePersonas,
  readPersona,
  resetPersona,
  savePersona,
  type CorePersona,
} from "../../services/coreApi";
import "../../styles/settings.css";


// ==========          PODEŠAVANJA: PERSONE          ==========

/**
 * Izbor persone i uređivanje njenog teksta.
 *
 * Persona je .md datoteka: prvi naslov je naziv, ostatak je sistemski prompt
 * koji ide modelu. Ovde se menja ceo taj tekst — bez skrivenog uvoda, da ono
 * što korisnik vidi bude tačno ono što model dobija.
 *
 * Svaki opseg ima svog „Opšteg pomoćnika" — podrazumevani režim razgovora.
 * Uloga mu je ista svuda, tekst nije: CORE-ov govori o sistemu, CODIUM-ov o
 * razvoju, i uređuju se svaki u svom opsegu.
 */
type PersonaPanelProps = {
  /** Opseg čije se persone prikazuju: „core", „codium", ... */
  scope: string;
  subtitle?: string;
};

function PersonaPanel({ scope, subtitle }: PersonaPanelProps) {
  const [persone, setPersone] = useState<CorePersona[]>([]);
  const [izabrana, setIzabrana] = useState("");
  const [tekst, setTekst] = useState("");
  const [sacuvan, setSacuvan] = useState("");
  const [izmenjena, setIzmenjena] = useState(false);
  const [greska, setGreska] = useState("");
  const [poruka, setPoruka] = useState("");
  const [radi, setRadi] = useState(false);

  const aktivna = persone.find((p) => p.id === izabrana);

  useEffect(() => {
    let otkazano = false;
    void (async () => {
      try {
        const { personas } = await listCorePersonas(scope);
        if (otkazano) {
          return;
        }
        setPersone(personas);
        setIzabrana((prethodna) =>
          personas.some((p) => p.id === prethodna)
            ? prethodna
            : personas[0]?.id ?? "",
        );
      } catch {
        setGreska("Spisak persona nije dostupan.");
      }
    })();
    return () => {
      otkazano = true;
    };
  }, [scope]);

  const ucitaj = useCallback(async (josTraje: () => boolean = () => true) => {
    if (aktivna === undefined) {
      return;
    }
    try {
      const doc = await readPersona(aktivna.scope, aktivna.id);
      if (!josTraje()) {
        return;
      }
      setTekst(doc.markdown);
      setSacuvan(doc.markdown);
      setIzmenjena(doc.customized);
      setGreska("");
    } catch {
      setGreska("Tekst persone nije dostupan.");
    }
  }, [aktivna]);

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      // Poruka o snimanju pripada prethodnoj personi, pa se gasi pre učitavanja.
      setPoruka("");
      await ucitaj(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [ucitaj]);

  async function sacuvaj(): Promise<void> {
    if (aktivna === undefined) {
      return;
    }
    setRadi(true);
    try {
      const doc = await savePersona(aktivna.scope, aktivna.id, tekst);
      setSacuvan(doc.markdown);
      setIzmenjena(true);
      // Naziv se čita iz naslova, pa spisak mora da prati izmenu.
      setPersone((prethodne) =>
        prethodne.map((p) =>
          p.id === doc.id && p.scope === doc.scope
            ? { ...p, name: doc.name, customized: true }
            : p,
        ),
      );
      setGreska("");
      setPoruka("Sačuvano. Važi od sledeće poruke.");
    } catch {
      setGreska("Čuvanje nije uspelo.");
    } finally {
      setRadi(false);
    }
  }

  async function vrati(): Promise<void> {
    if (aktivna === undefined) {
      return;
    }
    setRadi(true);
    try {
      const doc = await resetPersona(aktivna.scope, aktivna.id);
      setTekst(doc.markdown);
      setSacuvan(doc.markdown);
      setIzmenjena(false);
      setPersone((prethodne) =>
        prethodne.map((p) =>
          p.id === doc.id && p.scope === doc.scope
            ? { ...p, name: doc.name, customized: false }
            : p,
        ),
      );
      setGreska("");
      setPoruka("Vraćeno na podrazumevani tekst.");
    } catch {
      setGreska("Povratak na podrazumevano nije uspeo.");
    } finally {
      setRadi(false);
    }
  }

  return (
    <section className="cset-panel">
      <header className="cset-panel-head">
        <div>
          <h2 className="cset-panel-title">Persone</h2>
          <p className="cset-panel-sub">
            {subtitle ??
              "Persona je režim razgovora: tekst ispod je sistemski prompt koji ide modelu. Prvi naslov (# ...) je naziv persone."}
          </p>
        </div>
      </header>

      <ul className="cset-list">
        <li className="cset-item">
          <div className="cset-item-main">
            <span className="cset-item-title">
              Persona
              {aktivna?.id === "global" && (
                <span className="cset-badge">podrazumevana</span>
              )}
              {izmenjena && <span className="cset-badge free">izmenjena</span>}
            </span>
            <span className="cset-item-meta">
              {aktivna?.id === "global"
                ? "Opšti pomoćnik: režim sa kojim chat počinje."
                : "Uža uloga; bira se izričito u chatu."}
            </span>
          </div>

          <select
            className="cset-select"
            aria-label="Persona za uređivanje"
            value={izabrana}
            onChange={(event) => setIzabrana(event.target.value)}
          >
            {persone.map((p) => (
              <option key={`${p.scope}:${p.id}`} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </li>
      </ul>

      <textarea
        className="cset-editor"
        aria-label="Tekst persone (.md)"
        spellCheck={false}
        value={tekst}
        onChange={(event) => {
          setTekst(event.target.value);
          setPoruka("");
        }}
      />

      {greska !== "" && <p className="cset-error">{greska}</p>}

      <div className="cset-item-actions">
        <button
          type="button"
          className="cset-primary"
          disabled={radi || tekst === sacuvan || tekst.trim() === ""}
          onClick={() => void sacuvaj()}
        >
          <Save size={13} />
          Sačuvaj
        </button>

        <button
          type="button"
          className="cset-ghost"
          disabled={radi || !izmenjena}
          onClick={() => void vrati()}
        >
          <RotateCcw size={13} />
          Vrati podrazumevano
        </button>

        {poruka !== "" && <span className="cset-ok">{poruka}</span>}
      </div>
    </section>
  );
}

export default PersonaPanel;
