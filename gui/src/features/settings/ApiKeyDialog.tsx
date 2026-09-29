import { useEffect, useState, type FormEvent } from "react";
import { KeyRound, Loader2, X } from "lucide-react";

import {
  createConnector,
  listConnectors,
  testConnector,
  updateConnectorSecret,
  type ConnectorDto,
} from "../../services/coreApi";
import "../../styles/assistant.css";


// ==========          UNOS API KLJUČA          ==========

// Nazivi konektora po vrsti. Ime je ono što korisnik vidi u listi konektora;
// vrsta je ono što backend zna da testira.
const NAZIVI: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  openrouter: "OpenRouter",
};

// Oblik ključa se razlikuje po provajderu; placeholder pomaže da se ne nalepi
// pogrešan ključ u pravo polje.
const PRIMERI: Record<string, string> = {
  anthropic: "sk-ant-…",
  openai: "sk-proj-…",
  openrouter: "sk-or-…",
};

type ApiKeyDialogProps = {
  kind: string;
  onClose: () => void;
  /** Poziva se tek kad je ključ sačuvan I proba prošla. */
  onSaved?: () => void;
};

/**
 * Unos API ključa za online provajdera.
 *
 * Vrednost ključa putuje samo u jednom smeru — u telu zahteva ka backend-u,
 * odakle ide u OS keychain. Nazad se ne vraća i ovde se ne pamti: čim zahtev
 * krene, polje se prazni, pa ključ ne ostaje u DOM-u.
 */
function ApiKeyDialog({ kind, onClose, onSaved }: ApiKeyDialogProps) {
  const [kljuc, setKljuc] = useState("");
  const [postojeci, setPostojeci] = useState<ConnectorDto | null>(null);
  const [radi, setRadi] = useState(false);
  const [greska, setGreska] = useState("");
  const [poruka, setPoruka] = useState("");

  const naziv = NAZIVI[kind] ?? kind;

  // Ako konektor te vrste već postoji, menja mu se ključ — nov konektor bi
  // pao na jedinstvenom imenu (HTTP 409).
  useEffect(() => {
    let otkazano = false;
    void (async () => {
      try {
        const { connectors } = await listConnectors();
        if (!otkazano) {
          setPostojeci(connectors.find((c) => c.kind === kind) ?? null);
        }
      } catch {
        // Backend nedostupan — dijalog i dalje radi, samo pravi nov konektor.
      }
    })();
    return () => {
      otkazano = true;
    };
  }, [kind]);

  async function sacuvaj(event?: FormEvent): Promise<void> {
    event?.preventDefault();
    const vrednost = kljuc.trim();
    if (vrednost === "" || radi) {
      return;
    }

    setRadi(true);
    setGreska("");
    setPoruka("");
    // Polje se prazni pre poziva: dok proba traje dijalog stoji otvoren, a
    // ključ nema razloga da i dalje bude u dokumentu.
    setKljuc("");

    try {
      const konektor = postojeci
        ? await updateConnectorSecret(postojeci.id, vrednost)
        : await createConnector({ name: naziv, kind, secret: vrednost });

      const proba = await testConnector(konektor.id);
      if (!proba.ok) {
        setGreska(proba.message || "Proba konekcije nije uspela.");
        return;
      }

      setPostojeci(konektor);
      setPoruka("Ključ je sačuvan i proveren.");
      onSaved?.();
    } catch (err) {
      setGreska(err instanceof Error ? err.message : "Backend nije dostupan.");
    } finally {
      setRadi(false);
    }
  }

  return (
    <div className="cai-dialog-backdrop" role="dialog" aria-label="Unos API ključa">
      <form className="cai-dialog" onSubmit={(event) => void sacuvaj(event)}>
        <div className="cai-dialog-head">
          <span className="cai-dialog-title">
            <KeyRound size={14} /> API ključ — {naziv}
          </span>
          <button
            type="button"
            className="cai-dialog-close"
            onClick={onClose}
            aria-label="Zatvori"
          >
            <X size={14} />
          </button>
        </div>

        {postojeci !== null && postojeci.has_secret && (
          <p className="cai-dialog-hint">
            Ključ je već sačuvan. Novi unos ga zamenjuje; postojeći se nigde ne
            prikazuje.
          </p>
        )}

        <label className="cai-dialog-label" htmlFor="cai-api-key">
          API ključ
        </label>
        <input
          id="cai-api-key"
          className="cai-dialog-input"
          type="password"
          autoComplete="off"
          value={kljuc}
          onChange={(event) => setKljuc(event.target.value)}
          placeholder={PRIMERI[kind] ?? "API ključ"}
        />

        {greska !== "" && <p className="cai-dialog-error">{greska}</p>}
        {poruka !== "" && <p className="cai-dialog-ok">{poruka}</p>}

        <div className="cai-dialog-actions">
          <button type="button" className="cai-dialog-cancel" onClick={onClose}>
            Otkaži
          </button>
          <button type="submit" className="cai-dialog-save" disabled={radi}>
            {radi && <Loader2 size={13} className="cai-spin" />}
            Proveri i sačuvaj
          </button>
        </div>
      </form>
    </div>
  );
}

export default ApiKeyDialog;
