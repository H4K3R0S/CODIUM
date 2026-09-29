// ==========          ODVOJENI AI PROZOR (detach)          ==========
// Otvara AI asistenta u čistom prozoru prilepljenom uz desnu ivicu ekrana, pune
// visine. Van Tauri-ja (browser) je no-op i vraća false.

import { openScreenRightEdge } from "../window/gridSnap";

// Širina odvojenog AI prozora (fizički pikseli).
const AI_WINDOW_WIDTH = 480;

/**
 * Otvori AI chat u odvojenom prozoru uz desnu ivicu ekrana (pun visina).
 * Vraća `true` ako je prozor otvoren (samo u desktop/Tauri okruženju).
 */
export async function openAiChatWindow(projectId: number): Promise<boolean> {
  const win = await openScreenRightEdge(AI_WINDOW_WIDTH, {
    view: "codium-ai",
    title: "CODIUM AI",
    query: { project: String(projectId) },
  });
  return win !== null;
}
