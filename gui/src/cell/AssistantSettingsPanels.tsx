import { useEffect, useState } from "react";

import {
  getCellAiConfig,
  listCellAtoms,
  saveCellAiConfig,
  saveCellAtom,
  type CellAiConfig,
  type CellAtom,
} from "./cellApi";


// ==========          KANONSKI ASISTENT PANELI (generički)          ==========
//
// Reusable paneli za domenske CellSettingsPage stranice: `ModelPanel` (izbor
// lokalnog Ollama modela i adrese) i `AtomiPanel` (editor Agent atoma).
// Naslovi i opisi se parametrizuju kroz `brand` prop (npr. "FILMIUM", "IMPERIUM").

export function ModelPanel({ brand }: { brand: string }) {
  const [config, setConfig] = useState<CellAiConfig | null>(null);
  const [model, setModel] = useState("");
  const [adresa, setAdresa] = useState("");
  const [poruka, setPoruka] = useState<string | null>(null);

  useEffect(() => {
    getCellAiConfig()
      .then((cfg) => {
        setConfig(cfg);
        setModel(cfg.assistant_model ?? "");
        setAdresa(cfg.endpoint);
      })
      .catch(() => setPoruka("Podešavanja nisu dostupna."));
  }, []);

  async function sacuvaj(): Promise<void> {
    try {
      const cfg = await saveCellAiConfig(model.trim() || null, adresa.trim() || null);
      setConfig(cfg);
      setModel(cfg.assistant_model ?? "");
      setAdresa(cfg.endpoint);
      setPoruka("Sačuvano u cell.json. Ponovo pokreni ćeliju da bi se primenilo.");
    } catch {
      setPoruka("Čuvanje nije uspelo.");
    }
  }

  // Ponuđeni modeli: instalirani (Ollama) + trenutni ako nije na listi.
  const modeli = config
    ? Array.from(new Set([...config.available_models, ...(model ? [model] : [])]))
    : [];

  return (
    <section className="cset-panel">
      <header className="cset-panel-head">
        <div>
          <h2 className="cset-panel-title">{brand} Agent</h2>
          <p className="cset-panel-sub">
            {brand} radi nad lokalnom Ollamom. Izaberi model i adresu; upisuje se
            u cell.json i primenjuje po ponovnom pokretanju ćelije.
          </p>
        </div>
      </header>
      {config && (
        <div className="cset-field-group">
          <label className="cset-field">
            <span>Model</span>
            {modeli.length > 0 ? (
              <select value={model} onChange={(event) => setModel(event.target.value)}>
                <option value="">— nije izabran —</option>
                {modeli.map((ime) => (
                  <option key={ime} value={ime}>
                    {ime}
                  </option>
                ))}
              </select>
            ) : (
              <input
                onChange={(event) => setModel(event.target.value)}
                placeholder="npr. qwen2.5"
                value={model}
              />
            )}
            {config.available_models.length === 0 && (
              <small>Ollama nije dostupna na datoj adresi — upiši ime modela ručno.</small>
            )}
          </label>
          <label className="cset-field">
            <span>Ollama adresa</span>
            <input
              onChange={(event) => setAdresa(event.target.value)}
              placeholder={config.default_endpoint}
              value={adresa}
            />
            <small>Prazno = podrazumevano ({config.default_endpoint}).</small>
          </label>
          <button onClick={() => void sacuvaj()} type="button">
            Sačuvaj
          </button>
        </div>
      )}
      {poruka && <p>{poruka}</p>}
    </section>
  );
}

export function AtomiPanel({ brand }: { brand: string }) {
  const [atomi, setAtomi] = useState<CellAtom[]>([]);
  const [izabran, setIzabran] = useState<string | null>(null);
  const [tekst, setTekst] = useState("");
  const [poruka, setPoruka] = useState<string | null>(null);

  useEffect(() => {
    listCellAtoms()
      .then((lista) => {
        setAtomi(lista);
        const prvi = lista[0] ?? null;
        setIzabran(prvi?.path ?? null);
        setTekst(prvi?.content ?? "");
      })
      .catch(() => setPoruka("Atomi nisu dostupni."));
  }, []);

  function izaberi(path: string): void {
    const atom = atomi.find((a) => a.path === path) ?? null;
    setIzabran(atom?.path ?? null);
    setTekst(atom?.content ?? "");
    setPoruka(null);
  }

  async function sacuvaj(): Promise<void> {
    if (!izabran) {
      return;
    }
    try {
      const nov = await saveCellAtom(izabran, tekst);
      setAtomi((prethodni) => prethodni.map((a) => (a.path === nov.path ? nov : a)));
      setPoruka("Sačuvano. Važi od sledeće komande Agentu.");
    } catch {
      setPoruka("Čuvanje nije uspelo (prazan tekst ili nedozvoljena putanja).");
    }
  }

  return (
    <section className="cset-panel">
      <header className="cset-panel-head">
        <div>
          <h2 className="cset-panel-title">Atomi</h2>
          <p className="cset-panel-sub">
            Uputstva i komande Agenta {brand} ćelije — persona, alati i katalog
            komandi. Uredi i sačuvaj po fajlu.
          </p>
        </div>
      </header>
      {atomi.length > 0 && (
        <label className="cset-field">
          <span>Fajl</span>
          <select value={izabran ?? ""} onChange={(event) => izaberi(event.target.value)}>
            {atomi.map((a) => (
              <option key={a.path} value={a.path}>
                {a.path}
              </option>
            ))}
          </select>
        </label>
      )}
      <textarea
        aria-label="Sadržaj atoma"
        onChange={(event) => setTekst(event.target.value)}
        rows={16}
        value={tekst}
      />
      <button disabled={!izabran} onClick={() => void sacuvaj()} type="button">
        Sačuvaj
      </button>
      {poruka && <p>{poruka}</p>}
    </section>
  );
}
