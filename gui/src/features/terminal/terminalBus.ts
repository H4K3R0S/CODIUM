// ==========          TERMINAL BUS (cwd sync)          ==========
/*
 * Lagani most za „Otvori terminal ovde": Explorer (ili bilo ko) traži nov
 * terminal u datom folderu, a TerminalPanel to hvata i otvara tab sa tim cwd-om.
 * Decoupled preko CustomEvent-a na window-u — radi i kad su paneli razdvojeni
 * (docking). Van browsera (SSR/test bez window-a) je no-op.
 */

const EVENT = "core:terminal-here";

/** Zatraži nov terminal u datom radnom direktorijumu. */
export function requestTerminalHere(cwd: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { cwd } }));
}

/** Pretplata na zahteve „Otvori terminal ovde"; vraća funkciju za odjavu. */
export function subscribeTerminalHere(cb: (cwd: string) => void): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }
  const handler = (event: Event): void => {
    const detail = (event as CustomEvent<{ cwd?: string }>).detail;
    if (detail?.cwd) {
      cb(detail.cwd);
    }
  };
  window.addEventListener(EVENT, handler);
  return () => window.removeEventListener(EVENT, handler);
}
