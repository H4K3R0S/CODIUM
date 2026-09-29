import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Bot, Send, User } from "lucide-react";

import ApiKeyDialog from "../settings/ApiKeyDialog";
import AssistantCost from "./AssistantCost";
import AssistantModelSelect from "./AssistantModelSelect";
import { useAssistantChat } from "./useAssistantChat";
import "../../styles/codium-ai.css";


// ==========          AI ASISTENT (F9) — uski prikaz          ==========

type AiAssistantProps = {
  projectId: number;
};

/**
 * CODIUM AI asistent (F9): chat po personi (Arhitekta/Graditelj/Recenzent…),
 * sa kontekstom projekta. Sav rad (persone, izbor modela, istorija, trošak)
 * živi u `useAssistantChat`, isti hook koji koristi i chat na dashboard-u —
 * zato se dva ekrana ne mogu raziću u ponašanju.
 */
function AiAssistant({ projectId }: AiAssistantProps) {
  const chat = useAssistantChat(projectId);
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [chat.messages, chat.sending]);

  async function send(): Promise<void> {
    const text = draft.trim();
    if (text === "" || chat.sending) {
      return;
    }
    setDraft("");
    await chat.ask(text);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <div className="cai">
      <div className="cai-head">
        <span className="cai-head-label">
          <Bot size={14} /> AI asistent
        </span>
        <select
          className="cai-persona"
          value={chat.persona}
          onChange={(event) => chat.setPersona(event.target.value)}
          aria-label="Persona (chat mod)"
        >
          {chat.personas.length === 0 && (
            <option value="architect">Arhitekta</option>
          )}
          {chat.personas.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <AssistantModelSelect
          models={chat.models}
          value={chat.model}
          onChange={chat.chooseModel}
        />
      </div>

      <div className="cai-thread">
        {chat.messages.length === 0 ? (
          <div className="cai-empty">
            <Bot size={26} />
            <p>Pitaj asistenta o projektu.</p>
            <p className="cai-hint">Persona bira ton i fokus odgovora.</p>
          </div>
        ) : (
          chat.messages.map((message) => (
            <div key={message.id} className={`cai-msg ${message.author}`}>
              <span className="cai-avatar">
                {message.author === "me" ? <User size={13} /> : <Bot size={13} />}
              </span>
              <div className={`cai-bubble ${message.fallback ? "fallback" : ""}`}>
                {message.text}
              </div>
            </div>
          ))
        )}
        {chat.sending && (
          <div className="cai-msg assistant">
            <span className="cai-avatar">
              <Bot size={13} />
            </span>
            <div className="cai-bubble cai-typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <AssistantCost merenje={chat.merenje} />

      <div className="cai-input">
        <textarea
          className="cai-textarea"
          placeholder="Poruka asistentu… (Enter šalje, Shift+Enter nov red)"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          rows={2}
          aria-label="Poruka asistentu"
        />
        <button
          type="button"
          className="cai-send"
          onClick={() => void send()}
          disabled={draft.trim() === "" || chat.sending}
          aria-label="Pošalji"
        >
          <Send size={15} />
        </button>
      </div>

      {chat.kljucDijalog && (
        <ApiKeyDialog
          kind="anthropic"
          onClose={() => chat.setKljucDijalog(false)}
          onSaved={() => {
            chat.setKljucDijalog(false);
            void chat.osveziKatalog();
          }}
        />
      )}
    </div>
  );
}

export default AiAssistant;
