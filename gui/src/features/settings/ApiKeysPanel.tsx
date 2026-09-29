import { useCallback, useEffect, useState } from "react";
import { KeyRound, Plug, Plus, Trash2 } from "lucide-react";

import {
  deleteConnector,
  listConnectorKinds,
  listConnectors,
  testConnector,
  type ConnectorDto,
  type ConnectorKindDto,
} from "../../services/coreApi";
import ApiKeyDialog from "./ApiKeyDialog";
import "../../styles/settings.css";


// ==========          PODEŠAVANJA: API KLJUČEVI          ==========

type Ishod = { ok: boolean; text: string };

/**
 * Spisak API ključeva za CODIUM AI modele.
 *
 * Vrednost ključa se ovde nikad ne prikazuje — backend je i ne vraća. Panel
 * zna samo da li ključ postoji, kad je poslednji put proveren i kako je prošlo.
 */
function ApiKeysPanel() {
  const [konektori, setKonektori] = useState<ConnectorDto[]>([]);
  const [ucitava, setUcitava] = useState(true);
  const [greska, setGreska] = useState("");
  const [dijalog, setDijalog] = useState<string | null>(null);
  const [ishodi, setIshodi] = useState<Record<number, Ishod>>({});
  const [zaBrisanje, setZaBrisanje] = useState<number | null>(null);
  const [vrste, setVrste] = useState<ConnectorKindDto[]>([]);
  const [novaVrsta, setNovaVrsta] = useState("");

  // Nazivi vrsta stižu sa backend-a, zajedno sa podatkom šta je podržano —
  // GUI ih ne prepisuje, da se dve liste ne raziđu.
  const naziviVrsta = new Map(vrste.map((v) => [v.id, v.label]));

  const ucitaj = useCallback(async () => {
    try {
      const { connectors } = await listConnectors();
      setKonektori(connectors);
      setGreska("");
    } catch (err) {
      setGreska(err instanceof Error ? err.message : "Backend nije dostupan.");
    } finally {
      setUcitava(false);
    }
  }, []);

  useEffect(() => {
    void ucitaj();
  }, [ucitaj]);

  useEffect(() => {
    let otkazano = false;
    void (async () => {
      try {
        const { kinds } = await listConnectorKinds();
        if (otkazano) {
          return;
        }
        // Vrsta bez provajdera je najava, ne ponuda: konektor bi se napravio,
        // a proba bi vratila „Nema provajdera za vrstu".
        const podrzane = kinds.filter((k) => k.supported);
        setVrste(podrzane);
        setNovaVrsta((trenutna) =>
          trenutna === "" ? (podrzane[0]?.id ?? "") : trenutna,
        );
      } catch {
        // Backend nedostupan — panel i dalje prikazuje postojeće konektore.
      }
    })();
    return () => {
      otkazano = true;
    };
  }, []);

  async function proveri(konektor: ConnectorDto): Promise<void> {
    try {
      const proba = await testConnector(konektor.id);
      setIshodi((prev) => ({
        ...prev,
        [konektor.id]: {
          ok: proba.ok,
          text: proba.ok
            ? `Veza radi${proba.latency_ms === null ? "" : ` (${proba.latency_ms} ms)`}.`
            : proba.message || "Proba nije uspela.",
        },
      }));
      await ucitaj();
    } catch (err) {
      setIshodi((prev) => ({
        ...prev,
        [konektor.id]: {
          ok: false,
          text: err instanceof Error ? err.message : "Backend nije dostupan.",
        },
      }));
    }
  }

  async function obrisi(konektorId: number): Promise<void> {
    setZaBrisanje(null);
    try {
      await deleteConnector(konektorId);
      await ucitaj();
    } catch (err) {
      setGreska(err instanceof Error ? err.message : "Brisanje nije uspelo.");
    }
  }

  return (
    <section className="cset-panel">
      <header className="cset-panel-head">
        <div>
          <h2 className="cset-panel-title">API ključevi</h2>
          <p className="cset-panel-sub">
            Ključevi se čuvaju u Windows Credential Manager-u, nikad u bazi ni u
            konfiguraciji. Vrednost se posle upisa ne prikazuje — može samo da se
            zameni.
          </p>
        </div>
        <div className="cset-item-actions">
          <select
            className="cset-select"
            aria-label="Vrsta konektora"
            value={novaVrsta}
            onChange={(event) => setNovaVrsta(event.target.value)}
          >
            {vrste.map((vrsta) => (
              <option key={vrsta.id} value={vrsta.id}>
                {vrsta.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="cset-primary"
            onClick={() => setDijalog(novaVrsta)}
            disabled={novaVrsta === ""}
          >
            <Plus size={14} /> Dodaj API ključ
          </button>
        </div>
      </header>

      {greska !== "" && <p className="cset-error">{greska}</p>}

      {ucitava ? (
        <p className="cset-empty">Učitavanje…</p>
      ) : konektori.length === 0 ? (
        <p className="cset-empty">
          <Plug size={15} /> Nijedan API ključ nije dodat. Lokalni modeli
          (Ollama) rade i bez ključa.
        </p>
      ) : (
        <ul className="cset-list">
          {konektori.map((konektor) => {
            const ishod = ishodi[konektor.id];
            return (
              <li key={konektor.id} className="cset-item">
                <div className="cset-item-main">
                  <span className="cset-item-title">
                    <KeyRound size={14} /> {konektor.name}
                  </span>
                  <span className="cset-item-meta">
                    {naziviVrsta.get(konektor.kind) ?? konektor.kind} ·{" "}
                    {konektor.has_secret ? "Ključ sačuvan" : "Bez ključa"}
                    {konektor.last_tested_at
                      ? ` · poslednja provera: ${konektor.last_tested_at}`
                      : " · nije proveravan"}
                  </span>
                  {ishod !== undefined && (
                    <span className={ishod.ok ? "cset-ok" : "cset-error"}>
                      {ishod.text}
                    </span>
                  )}
                  {ishod === undefined && konektor.last_error !== "" && (
                    <span className="cset-error">{konektor.last_error}</span>
                  )}
                </div>

                <div className="cset-item-actions">
                  <button
                    type="button"
                    className="cset-ghost"
                    onClick={() => void proveri(konektor)}
                  >
                    Proveri
                  </button>
                  <button
                    type="button"
                    className="cset-ghost"
                    onClick={() => setDijalog(konektor.kind)}
                  >
                    Zameni ključ
                  </button>
                  {zaBrisanje === konektor.id ? (
                    <button
                      type="button"
                      className="cset-danger"
                      onClick={() => void obrisi(konektor.id)}
                    >
                      Potvrdi brisanje
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="cset-ghost"
                      onClick={() => setZaBrisanje(konektor.id)}
                    >
                      <Trash2 size={13} /> Obriši
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {dijalog !== null && (
        <ApiKeyDialog
          kind={dijalog}
          onClose={() => setDijalog(null)}
          onSaved={() => {
            setDijalog(null);
            void ucitaj();
          }}
        />
      )}
    </section>
  );
}

export default ApiKeysPanel;
