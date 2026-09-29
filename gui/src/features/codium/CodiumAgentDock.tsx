import { useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { Bug, FolderPlus, Rocket, ScanSearch } from "lucide-react";

import type { ChatSuggestion } from "../../components/chat/CoreChat";
import CellAssistantChat, { type CellChatHandle } from "../../cell/CellAssistantChat";
import {
  confirmAction,
  refuteAction,
  sendCommand,
  type AssistantResult,
} from "../../cell/cellApi";
import "../../styles/codium-hub-chat.css";
import "../../styles/codium-assistant-chat.css";


// ==========          CODIUM AGENT (globalni dock)          ==========
/*
 * Globalni Agent dock CODIUM ćelije, vidljiv na svim stranicama (montiran kroz
 * `codiumNav.AgentDock`). Koristi deljeni `CellAssistantChat` (ChatDock: položaj
 * dole/desno, minimize, glatki prelazi, smart reflow) — donese komandni `onSend`
 * (asistent backend), izbor od 12 persona i traku predloga.
 *
 * `sendCommand` vraća kind answer/proposal/navigate — `navigate` navlači rutu,
 * `proposal` traka „Potvrdi/Otkaži" (upis tek na potvrdu), `answer` u balončić.
 */

/** Persone CODIUM Agenta — id (šalje se backend-u) → prikazno ime. */
const PERSONE: { id: string; ime: string }[] = [
  { id: "opsti", ime: "Opšti" },
  { id: "arhitekta", ime: "Arhitekta" },
  { id: "graditelj", ime: "Graditelj" },
  { id: "recenzent", ime: "Recenzent" },
  { id: "dizajner", ime: "Dizajner" },
  { id: "menadzer", ime: "Menadžer" },
  { id: "debager", ime: "Debager" },
  { id: "pisac", ime: "Pisac" },
  { id: "bezbednjak", ime: "Bezbednjak" },
  { id: "devops", ime: "DevOps" },
  { id: "tester", ime: "Tester" },
  { id: "data-engineer", ime: "Data Engineer" },
];

/** Brze akcije u praznom stanju chata. */
const CODIUM_SUGGESTIONS: ChatSuggestion[] = [
  {
    id: "new-project",
    label: "Napravi projekat",
    icon: <FolderPlus size={16} />,
    prompt: "Pomozi mi da napravim nov projekat — predloži strukturu i stack.",
  },
  {
    id: "analyze-project",
    label: "Analiziraj projekat",
    icon: <ScanSearch size={16} />,
    prompt: "Analiziraj aktivan projekat i predloži šta da poboljšam.",
  },
  {
    id: "debug-problem",
    label: "Debaguj problem",
    icon: <Bug size={16} />,
    prompt: "Pomozi mi da debagujem problem u kodu.",
  },
  {
    id: "deploy-project",
    label: "Deploy projekat",
    icon: <Rocket size={16} />,
    prompt: "Vodi me kroz deploy aktivnog projekta.",
  },
];


/** Predlog koji čeka potvrdu (upis) — od poslednjeg `sendCommand`. */
type PredlogUpisa = {
  linije: string[];
  token: string | null;
  logId: string | null;
};

/** Čitljive linije `preview` objekta za traku predloga. */
function opisiPredlog(preview: Record<string, unknown> | null): string[] {
  if (preview === null) {
    return [];
  }
  const linije: string[] = [];
  const naslov = preview.title ?? preview.name ?? preview.path;
  if (naslov !== undefined && naslov !== null) {
    linije.push(`Predmet: ${String(naslov)}`);
  }
  const promene = preview.changes;
  if (promene !== null && typeof promene === "object") {
    for (const [polje, vrednost] of Object.entries(promene as Record<string, unknown>)) {
      linije.push(`${polje}: ${String(vrednost)}`);
    }
  }
  for (const [kljuc, vrednost] of Object.entries(preview)) {
    if (kljuc === "title" || kljuc === "name" || kljuc === "path" || kljuc === "changes") {
      continue;
    }
    linije.push(`${kljuc}: ${String(vrednost)}`);
  }
  return linije;
}

/** Dodaje izvore odgovoru. */
function formatOdgovor(reply: string, sources: string[]): string {
  if (sources.length === 0) {
    return reply;
  }
  return `${reply}\n\nIzvori: ${sources.join(", ")}`;
}


function CodiumAgentDock() {
  const [persona, setPersona] = useState(PERSONE[0].id);
  const [predlog, setPredlog] = useState<PredlogUpisa | null>(null);
  const [predlogBusy, setPredlogBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const chatRef = useRef<CellChatHandle>(null);

  // AI Workspace ima svoj ugrađeni asistent (deli okvir sa terminalom / desni
  // panel / odvojen prozor). Globalni lebdeći dock bi tu bio drugi chat na istoj
  // stranici, pa se na workspace ruti ne prikazuje. Svuda drugde ostaje.
  if (location.pathname.startsWith("/codium/workspace")) {
    return null;
  }

  async function posaljiKomandu(text: string): Promise<string> {
    let rezultat: AssistantResult;
    try {
      rezultat = await sendCommand(text, persona);
    } catch (error) {
      console.error("CODIUM Agent nije dostupan:", error);
      return (
        "Agent nije dostupan u ovoj ćeliji. Proveri da li Ollama radi i da "
        + "li je model upisan u cell.json (ai.assistant_model)."
      );
    }

    if (rezultat.kind === "navigate") {
      setPredlog(null);
      const ruta = rezultat.preview?.route;
      if (typeof ruta === "string" && ruta !== "") {
        navigate(ruta);
      }
      return rezultat.reply !== "" ? rezultat.reply : "Otvaram...";
    }

    if (rezultat.kind === "proposal") {
      setPredlog({
        linije: opisiPredlog(rezultat.preview),
        token: rezultat.confirm_token,
        logId: rezultat.log_id,
      });
      return rezultat.reply !== "" ? rezultat.reply : "Predlog čeka potvrdu.";
    }

    setPredlog(null);
    return formatOdgovor(rezultat.reply, rezultat.sources);
  }

  async function potvrdiPredlog(): Promise<void> {
    const token = predlog?.token;
    if (token === null || token === undefined) {
      return;
    }
    setPredlogBusy(true);
    try {
      const rezultat = await confirmAction(token);
      const odgovor = rezultat.reply;
      if (typeof odgovor === "string" && odgovor !== "") {
        chatRef.current?.appendReply(odgovor);
      }
    } catch (error) {
      console.error("Potvrda predloga nije uspela:", error);
    } finally {
      setPredlogBusy(false);
      setPredlog(null);
    }
  }

  async function otkaziPredlog(): Promise<void> {
    if (predlog === null) {
      return;
    }
    setPredlogBusy(true);
    try {
      await refuteAction(predlog.logId ?? undefined);
    } catch (error) {
      console.error("Otkazivanje predloga nije uspelo:", error);
    } finally {
      setPredlogBusy(false);
      setPredlog(null);
    }
  }

  return (
    <CellAssistantChat
      ref={chatRef}
      scope="codium"
      title="Codium"
      variant="is-codium"
      suggestions={CODIUM_SUGGESTIONS}
      onSend={posaljiKomandu}
      personaPicker={(
        <label className="ckc-persona-picker">
          <span>Persona</span>
          <select onChange={(event) => setPersona(event.target.value)} value={persona}>
            {PERSONE.map((p) => (
              <option key={p.id} value={p.id}>{p.ime}</option>
            ))}
          </select>
        </label>
      )}
      footer={predlog !== null ? (
        <div className="ckc-proposal">
          {predlog.linije.map((linija, indeks) => (
            <p key={indeks} className="ckc-proposal-text">{linija}</p>
          ))}
          <div className="ckc-proposal-actions">
            <button
              type="button"
              className="ckc-proposal-confirm"
              onClick={() => void potvrdiPredlog()}
              disabled={predlogBusy || predlog.token === null}
            >
              Potvrdi
            </button>
            <button
              type="button"
              className="ckc-proposal-cancel"
              onClick={() => void otkaziPredlog()}
              disabled={predlogBusy}
            >
              Otkaži
            </button>
          </div>
        </div>
      ) : undefined}
    />
  );
}

export default CodiumAgentDock;
