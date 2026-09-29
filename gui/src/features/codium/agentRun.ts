// ==========          PRIKAZ POSLA AGENTA          ==========
// Cist modul bez ijednog uvoza — prevod stanja sa servera u ono sto se vidi.

export type StepTone = "thought" | "call" | "result" | "answer" | "blocked";

const TON_PO_VRSTI: Record<string, StepTone> = {
  tool_call: "call",
  tool_result: "result",
  answer: "answer",
  thought: "thought",
};

/** Ton jednog koraka; nepoznata vrsta se crta kao misao, ne kao greska. */
export function stepTone(step: { kind: string; payload: string }): StepTone {
  if (step.kind === "tool_result" && /^(Odbijeno|Ceka odobrenje)/i.test(step.payload)) {
    // Odbijanje i cekanje na coveka nisu obican rezultat alata.
    return "blocked";
  }
  return TON_PO_VRSTI[step.kind] ?? "thought";
}

const NAZIV_STANJA: Record<string, string> = {
  running: "Radi",
  waiting_approval: "Čeka odobrenje",
  done: "Gotovo",
  failed: "Neuspeh",
  cancelled: "Prekinuto",
};

/** Citljiv naziv stanja; nepoznato stanje se prikazuje kakvo jeste. */
export function runLabel(status: string): string {
  return NAZIV_STANJA[status] ?? status;
}

/**
 * Da li posao još traje, pa prikaz treba osvežavati.
 *
 * Nepoznato stanje vraća `false`: greška na serveru bi inače značila poll
 * koji nikad ne prestaje.
 */
export function isRunLive(status: string): boolean {
  return status === "running" || status === "waiting_approval";
}
