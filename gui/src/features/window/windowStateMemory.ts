// ==========          MEMORIJA STANJA PROZORA          ==========
/*
 * Pamti apsolutni okvir Main prozora pre „evacuation"-a (kad PC/WEB preview
 * preuzme glavni monitor), da bi se Main vratio na tačno isto mesto kad se
 * preview zatvori. Čuva se u localStorage (preživi i restart), uz in-memory keš.
 */

import type { Frame } from "./monitorLayout";

const MEMORY_KEY = "core.window.mainStateBeforeEvacuation";

let cached: Frame | null | undefined; // undefined = nije čitано

/** Snimi apsolutni okvir Main prozora (fizički pikseli). */
export function saveMainFrame(frame: Frame): void {
  cached = frame;
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(MEMORY_KEY, JSON.stringify(frame));
  } catch {
    /* storage nedostupan — ostaje in-memory */
  }
}

/** Pročitaj zapamćeni okvir (ili null ako ga nema). */
export function readMainFrame(): Frame | null {
  if (cached !== undefined) {
    return cached;
  }
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(MEMORY_KEY);
    cached = raw ? (JSON.parse(raw) as Frame) : null;
  } catch {
    cached = null;
  }
  return cached;
}

/** Obriši zapamćeno stanje (posle uspešnog vraćanja). */
export function clearMainFrame(): void {
  cached = null;
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(MEMORY_KEY);
  } catch {
    /* nebitno */
  }
}

/** Ima li zapamćeno stanje (za „vrati Main" dugme/logiku). */
export function hasSavedMainFrame(): boolean {
  return readMainFrame() !== null;
}
