import { useEffect, useState, type ReactNode } from "react";

import AssistantModelSelect from "../chat/AssistantModelSelect";
import { API_KEY_OPTION } from "../chat/useAssistantChat";
import {
  CHAT_POSITIONS,
  CHAT_SETTINGS,
  CORE_SCOPE,
  useChatFlag,
  useChatSetting,
  type ChatSettingId,
  type ChatSettingState,
} from "../chat/chatPrefs";
import {
  listCoreModels,
  listCorePersonas,
  type CorePersona,
} from "../../services/coreApi";
import type { CatalogModel } from "./modelPicker";
import "../../styles/settings.css";


// ==========          PODEŠAVANJA: CHAT OKVIR          ==========

/**
 * Podešavanja chat okvira za jedan opseg.
 *
 * CORE drži glavnu postavku; domen je nasleđuje dok sam ne promeni tu stavku.
 * Zato svaki red u domenu pokazuje da li prati CORE i nudi povratak — bez toga
 * bi se domen, jednom promenjen, zauvek odvojio od CORE-a.
 */
type ChatPanelProps = {
  /** „core" ili id domena. */
  scope?: string;
  subtitle?: string;
};

/**
 * Jedan red podešavanja, sa oznakom nasleđivanja i povratkom na CORE.
 *
 * Naslov i opis ne stoje ovde — dolaze iz `CHAT_SETTINGS`, jedinog spiska
 * postavki chata.
 */
function Red({
  id,
  scope,
  state,
  children,
}: {
  id: ChatSettingId;
  scope: string;
  state: ChatSettingState;
  children: ReactNode;
}) {
  const spec = CHAT_SETTINGS.find((s) => s.id === id);
  const title = spec?.title ?? id;
  const meta = spec?.meta ?? "";

  const domenski = scope !== CORE_SCOPE;

  return (
    <li className="cset-item">
      <div className="cset-item-main">
        <span className="cset-item-title">
          {title}
          {domenski && state.inherited && (
            <span className="cset-badge">prati CORE</span>
          )}
        </span>
        <span className="cset-item-meta">{meta}</span>
      </div>

      <div className="cset-item-actions">
        {domenski && !state.inherited && (
          <button type="button" className="cset-ghost" onClick={state.clear}>
            Vrati na CORE
          </button>
        )}
        {children}
      </div>
    </li>
  );
}

function ChatPanel({ scope = CORE_SCOPE, subtitle }: ChatPanelProps) {
  const [personas, setPersonas] = useState<CorePersona[]>([]);
  const [models, setModels] = useState<CatalogModel[]>([]);

  // Podrazumevane vrednosti dolaze iz `CHAT_SETTINGS`.
  const [persona, setPersona, personaStanje] = useChatSetting(scope, "persona");
  const [model, setModel, modelStanje] = useChatSetting(scope, "model");
  const [pozicija, setPozicija, pozicijaStanje] = useChatSetting(scope, "pos");
  const [akcije, setAkcije, akcijeStanje] = useChatFlag(scope, "suggestions");
  const [trosak, setTrosak, trosakStanje] = useChatFlag(scope, "cost");
  const [glas, setGlas, glasStanje] = useChatFlag(scope, "voice");
  const [razumeJezik, setRazumeJezik, razumeStanje] = useChatSetting(scope, "understandLang");
  const [odgovorJezik, setOdgovorJezik, odgovorStanje] = useChatSetting(scope, "replyLang");
  const [izgovorJezik, setIzgovorJezik, izgovorStanje] = useChatSetting(scope, "speakLang");
  const [glasIme, setGlasIme, glasImeStanje] = useChatSetting(scope, "speakVoice");

  useEffect(() => {
    let otkazano = false;
    void (async () => {
      try {
        const [{ personas: lista }, { models: katalog }] = await Promise.all([
          listCorePersonas(scope),
          listCoreModels(scope, true),
        ]);
        if (!otkazano) {
          setPersonas(lista);
          setModels(katalog);
        }
      } catch {
        // Backend nedostupan — ostaju podrazumevane vrednosti.
      }
    })();
    return () => {
      otkazano = true;
    };
  }, [scope]);

  return (
    <section className="cset-panel">
      <header className="cset-panel-head">
        <div>
          <h2 className="cset-panel-title">Chat okvir</h2>
          <p className="cset-panel-sub">
            {subtitle ??
              "Sistemski chat na dashboard-u: sa kim razgovara, čime odgovara i gde okvir stoji. Isti izbor persone i modela stoji i u samom chatu."}
          </p>
        </div>
      </header>

      <ul className="cset-list">
        <Red id="persona" scope={scope} state={personaStanje}>
          <select
            className="cset-select"
            aria-label="Persona chata"
            value={persona}
            onChange={(event) => setPersona(event.target.value)}
          >
            {personas.length === 0 && (
              <option value="global">Opšti pomoćnik</option>
            )}
            {personas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </Red>

        <Red id="model" scope={scope} state={modelStanje}>
          <AssistantModelSelect
            className="cset-select"
            models={models}
            value={model}
            onChange={(next) => {
              // Red za unos ključa nije model; u podešavanjima nema šta da
              // otvori, pa se ignoriše.
              if (next !== API_KEY_OPTION) {
                setModel(next);
              }
            }}
          />
        </Red>

        <Red id="pos" scope={scope} state={pozicijaStanje}>
          <select
            className="cset-select"
            aria-label="Položaj chat okvira"
            value={pozicija}
            onChange={(event) => setPozicija(event.target.value)}
          >
            {CHAT_POSITIONS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </Red>

        <Red id="suggestions" scope={scope} state={akcijeStanje}>
          <button
            type="button"
            role="switch"
            aria-checked={akcije}
            aria-label="Brze akcije"
            className={`cset-switch ${akcije ? "on" : ""}`}
            onClick={() => setAkcije(!akcije)}
          >
            <span aria-hidden="true" className="cset-switch-knob" />
          </button>
        </Red>

        <Red id="cost" scope={scope} state={trosakStanje}>
          <button
            type="button"
            role="switch"
            aria-checked={trosak}
            aria-label="Prikaz troška"
            className={`cset-switch ${trosak ? "on" : ""}`}
            onClick={() => setTrosak(!trosak)}
          >
            <span aria-hidden="true" className="cset-switch-knob" />
          </button>
        </Red>

        <Red id="voice" scope={scope} state={glasStanje}>
          <button
            type="button"
            role="switch"
            aria-checked={glas}
            aria-label="Glasovni odgovori (TTS)"
            className={`cset-switch ${glas ? "on" : ""}`}
            onClick={() => setGlas(!glas)}
          >
            <span aria-hidden="true" className="cset-switch-knob" />
          </button>
        </Red>

        <Red id="understandLang" scope={scope} state={razumeStanje}>
          <select className="cset-select" aria-label="Jezik razumevanja"
            value={razumeJezik} onChange={(e) => setRazumeJezik(e.target.value)}>
            <option value="auto">Automatski (sr + en)</option>
            <option value="sr">Srpski</option>
            <option value="en">Engleski</option>
          </select>
        </Red>

        <Red id="replyLang" scope={scope} state={odgovorStanje}>
          <select className="cset-select" aria-label="Jezik odgovora"
            value={odgovorJezik} onChange={(e) => setOdgovorJezik(e.target.value)}>
            <option value="en">Engleski</option>
            <option value="sr">Srpski</option>
          </select>
        </Red>

        <Red id="speakLang" scope={scope} state={izgovorStanje}>
          <select className="cset-select" aria-label="Jezik izgovora"
            value={izgovorJezik} onChange={(e) => setIzgovorJezik(e.target.value)}>
            <option value="auto">Prema tekstu</option>
            <option value="en">Engleski</option>
            <option value="sr">Srpski</option>
          </select>
        </Red>

        <Red id="speakVoice" scope={scope} state={glasImeStanje}>
          <input className="cset-select" type="text" aria-label="Glas (TTS)"
            placeholder="automatski" value={glasIme}
            onChange={(e) => setGlasIme(e.target.value)} />
        </Red>
      </ul>
    </section>
  );
}

export default ChatPanel;
