import { getJson, postJson, putJson } from "../services/httpClient";


// ==========          ĆELIJSKI API (generički)          ==========
//
// Domen-agnostičan klijent ćelije: stanje ćelije, persone i asistent. Nijedna
// domenska ruta nije zakucana — asistent gađa generički `/cell/assistant/ask`
// koji cell API nudi samo ako domen ima asistenta; ako ga nema, poziv padne i
// `CellAssistantChat` prikaže razumljivu poruku.

export type CellAssistantAnswer = {
  answer: string;
  sources: string[];
  is_fallback: boolean;
};

export type CellStatus = {
  domain_id: string;
  name: string;
  domain_version: string;
  kernel_version: string;
  port: number;
  operating_system: string;
  node_name: string;
  database_path: string;
  rag_enabled: boolean;
  rag_namespace: string;
  pending_upgrades: number;
  ai_endpoint: string;
  ai_assistant_model: string | null;
};

export type CellPersona = {
  id: string;
  name: string;
  markdown: string;
  customized: boolean;
};

/** Pitanje asistentu domena nad lokalnom Ollamom ćelije (ako domen ima asistenta). */
export function askCellAssistant(question: string): Promise<CellAssistantAnswer> {
  return postJson<CellAssistantAnswer, { question: string }>(
    "/cell/assistant/ask",
    { question },
  );
}

/** Stanje ćelije, uključujući Ollama model i adresu iz cell.json. */
export function getCellStatus(): Promise<CellStatus> {
  return getJson<CellStatus>("/cell/status");
}

/** Persone domena ćelije. */
export function listCellPersonas(): Promise<CellPersona[]> {
  return getJson<CellPersona[]>("/cell/personas");
}

/** Upisuje izmenjen tekst persone. */
export function saveCellPersona(id: string, markdown: string): Promise<CellPersona> {
  return putJson<CellPersona, { markdown: string }>(
    `/cell/personas/${encodeURIComponent(id)}`,
    { markdown },
  );
}

export type CellAiConfig = {
  assistant_model: string | null;
  endpoint: string;
  default_endpoint: string;
  available_models: string[];
};

export type CellAtom = { path: string; content: string };

/** AI podešavanja ćelije (lokalni model + adresa + dostupni modeli). */
export function getCellAiConfig(): Promise<CellAiConfig> {
  return getJson<CellAiConfig>("/cell/ai-config");
}

/** Upisuje model i adresu u cell.json (primenjuje se po ponovnom pokretanju). */
export function saveCellAiConfig(
  assistantModel: string | null,
  endpoint: string | null,
): Promise<CellAiConfig> {
  return putJson<CellAiConfig, { assistant_model: string | null; endpoint: string | null }>(
    "/cell/ai-config",
    { assistant_model: assistantModel, endpoint },
  );
}

/** Uređivi atom fajlovi asistenta (persona.md, tools, commands). */
export function listCellAtoms(): Promise<CellAtom[]> {
  return getJson<CellAtom[]>("/cell/atoms");
}

/** Upisuje sadržaj jednog atoma. `path` je relativan (npr. "tools/pretraga.md"). */
export function saveCellAtom(path: string, content: string): Promise<CellAtom> {
  const delovi = path.split("/").map(encodeURIComponent).join("/");
  return putJson<CellAtom, { content: string }>(`/cell/atoms/${delovi}`, { content });
}


// ==========          ASISTENT KOMANDE (CODIUM)          ==========
//
// Klijent za asistent komande: prepoznavanje namere, potvrda upisa,
// opovrgavanje. Po uzoru na FILMIUM klijent, ali gađa CODIUM rutu
// i telo `command` zahteva nosi i `persona_id` (CODIUM ima 12 persona, ne
// jednu podrazumevanu kao FILMIUM).

export type AssistantResult = {
  kind: "answer" | "proposal" | "navigate";
  intent: string;
  params: Record<string, unknown>;
  reply: string;
  preview: Record<string, unknown> | null;
  confirm_token: string | null;
  sources: string[];
  log_id: string | null;
};

/** Šalje komandu asistentu (prepoznaje nameru) za izabranu personu. */
export function sendCommand(message: string, personaId: string): Promise<AssistantResult> {
  return postJson<AssistantResult, { message: string; persona_id: string }>(
    "/api/v1/codium/assistant/command",
    { message, persona_id: personaId },
  );
}

/**
 * Potvrđuje predlog (upisuje promenu) po tokenu iz `AssistantResult.confirm_token`.
 * Odgovor zavisi od namere (`{ synced: true, ... }` / `{ started: true, ... }`),
 * ali uvek nosi i `reply` (tekst za dock), pa je tip namerno labav.
 */
export function confirmAction(token: string): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>, { token: string }>(
    "/api/v1/codium/assistant/confirm",
    { token },
  );
}

/** Odbacuje predlog (bez upisa), po potrebi uz `log_id` radi revizije. */
export function refuteAction(logId?: string): Promise<{ refuted: boolean }> {
  return postJson<{ refuted: boolean }, { log_id: string | null }>(
    "/api/v1/codium/assistant/refute",
    { log_id: logId ?? null },
  );
}
