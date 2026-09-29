import { useCallback, useEffect, useState } from "react";
import { Cpu } from "lucide-react";

import {
  listCoreModels,
  setCoreModelEnabled,
} from "../../services/coreApi";
import { type CatalogModel } from "./modelPicker";

type ModelsPanelProps = {
  /** Odakle se čita katalog. Podrazumevano domenski (CODIUM). */
  load?: (scope: string) => Promise<{ models: CatalogModel[] }>;
  /** Gde se upisuje odluka. Podrazumevano domenska. */
  toggle?: (payload: {
    provider: string;
    model: string;
    enabled: boolean;
    scope?: string;
  }) => Promise<unknown>;
  /**
   * Kad je dato, panel nudi izbor opsega (globalno / CORE / po domenu).
   * Bez toga radi nad jednim, podrazumevanim opsegom.
   */
  scopes?: () => Promise<{ scopes: { id: string; label: string }[] }>;
  /** Objašnjenje ispod naslova — CORE i domen ne znače isto. */
  subtitle?: string;
};
import { groupModels, isFreeModel } from "./modelPicker";
import { DEFAULT_LIMIT, formatPrice, searchCatalog } from "./openrouterCatalog";
import "../../styles/settings.css";


// ==========          PODEŠAVANJA: MODELI          ==========

/** Detalji ispod imena modela: veličina, cena, razlog nedostupnosti. */
function opisModela(model: CatalogModel): string {
  const delovi: string[] = [];

  if (model.size_gb !== null) {
    delovi.push(`${model.size_gb} GB`);
  }
  if (model.oversized) {
    delovi.push("veći od VRAM-a");
  }
  if (!model.is_local && model.price_in_per_mtok > 0) {
    delovi.push(`$${model.price_in_per_mtok}/$${model.price_out_per_mtok} po M`);
  } else if (!model.is_local && !model.is_placeholder && !isFreeModel(model)) {
    // Prazno mesto bi se čitalo kao „besplatno" — a nijedan online poziv to
    // nije. Tabela cena je ručno održavana, pa nov model zna da izostane.
    // Besplatan model je izuzet: kod njega je nula stvarna nula, ne neznanje.
    delovi.push("cena nepoznata");
  }
  if (!model.available && model.unavailable_reason !== "") {
    delovi.push(model.unavailable_reason);
  }
  return delovi.join(" · ");
}

/**
 * Izbor modela koji se nude u CODIUM chat okviru.
 *
 * Isključivanje je deny lista: nov model koji se pojavi u Ollami je odmah
 * upotrebljiv, bez ijednog klika. Isključeni modeli ostaju ovde vidljivi —
 * inače se ne bi mogli vratiti.
 */
// Podrazumevani citac mora da bude stabilna funkcija: strelica napisana u
// listi parametara dobija novi identitet pri svakom renderu, pa bi `useCallback`
// nad njom vrteo katalog u krug i brisao stanje (npr. poruku o gresci).
const CORE_KATALOG = (scope: string) => listCoreModels(scope);

function ModelsPanel({
  load = CORE_KATALOG,
  toggle = setCoreModelEnabled,
  scopes,
  subtitle = "Isključeni modeli se ne nude u chat okviru, ali ostaju ovde da bi mogli da se vrate. Nov model se pojavljuje uključen.",
}: ModelsPanelProps = {}) {
  const [modeli, setModeli] = useState<CatalogModel[]>([]);
  const [ucitava, setUcitava] = useState(true);
  const [greska, setGreska] = useState("");
  const [opsezi, setOpsezi] = useState<{ id: string; label: string }[]>([]);
  const [opseg, setOpseg] = useState("global");
  const [upit, setUpit] = useState("");

  useEffect(() => {
    if (scopes === undefined) {
      return;
    }
    let otkazano = false;
    void (async () => {
      try {
        const { scopes: lista } = await scopes();
        if (!otkazano) {
          setOpsezi(lista);
        }
      } catch {
        // Bez spiska opsega panel radi nad globalnim.
      }
    })();
    return () => {
      otkazano = true;
    };
  }, [scopes]);

  // `josTraje` kaze da li ekran jos stoji: odgovor koji kasni ne sme da
  // upise nista u komponentu koje vise nema.
  const ucitaj = useCallback(async (josTraje: () => boolean = () => true) => {
    try {
      const { models } = await load(opseg);
      if (!josTraje()) {
        return;
      }
      setModeli(models);
      setGreska("");
    } catch (err) {
      setGreska(err instanceof Error ? err.message : "Backend nije dostupan.");
    } finally {
      setUcitava(false);
    }
  }, [load, opseg]);

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await ucitaj(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [ucitaj]);

  async function prebaci(model: CatalogModel): Promise<void> {
    const novo = !model.enabled;
    // Prekidač se okreće odmah; ako upis padne, vraća se nazad. Bez toga bi
    // prekidač stajao u starom stanju dok mreža ne odgovori i delovao pokvareno.
    setModeli((prev) =>
      prev.map((m) =>
        m.id === model.id && m.provider === model.provider
          ? { ...m, enabled: novo }
          : m,
      ),
    );

    try {
      await toggle({
        provider: model.provider, model: model.id, enabled: novo,
        ...(scopes === undefined ? {} : { scope: opseg }),
      });
      setGreska("");
    } catch (err) {
      setModeli((prev) =>
        prev.map((m) =>
          m.id === model.id && m.provider === model.provider
            ? { ...m, enabled: !novo }
            : m,
        ),
      );
      setGreska(err instanceof Error ? err.message : "Upis nije uspeo.");
    }
  }

  // Provajder sa allow listom ima 300+ modela i ide u svoju sekciju sa
  // pretragom; ostali idu u obicne grupe „Lokalno" / „Online".
  const obicni = modeli.filter((m) => !m.needs_allowlist);
  const izKataloga = modeli.filter((m) => m.needs_allowlist);
  const pretraga = searchCatalog(izKataloga, upit, DEFAULT_LIMIT);
  const cuvar = izKataloga.find((m) => m.is_placeholder);

  return (
    <section className="cset-panel">
      <header className="cset-panel-head">
        <div>
          <h2 className="cset-panel-title">Modeli</h2>
          <p className="cset-panel-sub">{subtitle}</p>
        </div>

        {scopes !== undefined && (
          <select
            className="cset-select"
            aria-label="Opseg podešavanja"
            value={opseg}
            onChange={(event) => setOpseg(event.target.value)}
          >
            {opsezi.map((stavka) => (
              <option key={stavka.id} value={stavka.id}>
                {stavka.label}
              </option>
            ))}
          </select>
        )}
      </header>

      {greska !== "" && <p className="cset-error">{greska}</p>}

      {ucitava ? (
        <p className="cset-empty">Učitavanje…</p>
      ) : obicni.length === 0 && izKataloga.length === 0 ? (
        <p className="cset-empty">
          <Cpu size={15} /> Katalog je prazan. Pokreni Ollama server ili dodaj
          API ključ.
        </p>
      ) : (
        groupModels(obicni).map((grupa) => (
          <div key={grupa.title} className="cset-group">
            <h3 className="cset-group-title">{grupa.title}</h3>
            <ul className="cset-list">
              {grupa.models.map((model) => {
                const opis = opisModela(model);
                return (
                  <li
                    key={`${model.provider}:${model.id}`}
                    className={`cset-item ${isFreeModel(model) ? "is-free" : ""}`}
                  >
                    <div className="cset-item-main">
                      <span className="cset-item-title">
                        {model.label}
                        {!model.is_placeholder && (
                          // Znacka prati CENU, ne mesto gde model zivi:
                          // besplatan online model nije „placa se".
                          <span
                            className={`cset-badge ${
                              isFreeModel(model) ? "free" : "paid"
                            }`}
                          >
                            {isFreeModel(model) ? "besplatno" : "plaća se"}
                          </span>
                        )}
                      </span>
                      {opis !== "" && (
                        <span className="cset-item-meta">{opis}</span>
                      )}
                    </div>

                    {model.is_placeholder ? (
                      // Nije model nego poruka o provajderu — nema sta da se
                      // ukljuci ni iskljuci.
                      <span className="cset-item-note">nije model</span>
                    ) : model.disabled_globally ? (
                      // CORE ga je iskljucio za sve domene. Prekidac ovde bi
                      // obecao nesto sto ruter nece ispuniti.
                      <span className="cset-item-note">isključen u CORE-u</span>
                    ) : (
                    <button
                      type="button"
                      role="switch"
                      aria-checked={model.enabled}
                      aria-label={`Model ${model.id} u chatu`}
                      className={`cset-switch ${model.enabled ? "on" : ""}`}
                      onClick={() => void prebaci(model)}
                    >
                      <span className="cset-switch-knob" />
                    </button>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))
      )}

      {izKataloga.length > 0 && (
        <div className="cset-group">
          <h3 className="cset-group-title">OpenRouter katalog</h3>
          <p className="cset-panel-sub">
            Ovaj provajder ima preko 300 modela, pa se u chatu nudi samo ono
            što ovde uključiš.
          </p>

          {cuvar !== undefined ? (
            // Bez ključa katalog ne postoji — red-čuvar nosi razlog.
            <p className="cset-empty">{cuvar.unavailable_reason}</p>
          ) : (
            <>
              <input
                className="set-orc-search"
                aria-label="Pretraga OpenRouter kataloga"
                placeholder="Pretraga po nazivu modela…"
                value={upit}
                onChange={(event) => setUpit(event.target.value)}
              />

              <ul className="cset-list">
                {pretraga.shown.map((model) => (
                  <li
                    key={`${model.provider}:${model.id}`}
                    className={`cset-item set-orc-row ${
                      isFreeModel(model) ? "is-free" : ""
                    }`}
                  >
                    <div className="cset-item-main">
                      <span className="cset-item-title">{model.id}</span>
                      <span className="cset-item-meta set-orc-meta">
                        {formatPrice(model)} ·{" "}
                        {Math.round(model.context_window / 1000)}k konteksta
                      </span>
                    </div>

                    {model.disabled_globally ? (
                      // Allow lista je globalna: u opsegu domena prekidac bi
                      // pisao u DENY listu, a model bi i dalje bio nepusten.
                      // Obecanje koje ruter ne ispunjava.
                      <span className="cset-item-note">
                        pušta se u CORE podešavanjima
                      </span>
                    ) : (
                      <button
                        type="button"
                        role="switch"
                        aria-checked={model.enabled}
                        aria-label={`Model ${model.id} u chatu`}
                        className={`cset-switch ${model.enabled ? "on" : ""}`}
                        onClick={() => void prebaci(model)}
                      >
                        <span className="cset-switch-knob" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>

              {pretraga.hidden > 0 && (
                <p className="set-orc-more">
                  Još {pretraga.hidden} modela — suzi pretragu.
                </p>
              )}
              {pretraga.shown.length === 0 && (
                <p className="cset-empty">Nijedan model se ne poklapa.</p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}

export default ModelsPanel;
