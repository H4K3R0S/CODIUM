// ==========          RASPORED MONITORA (dinamička detekcija)          ==========
/*
 * Čista logika (bez Tauri poziva) koja iz liste monitora — onako kako ih vraća
 * Tauri `monitors()` (globalna pozicija + veličina u fizičkim pikselima) —
 * određuje koji je CENTRALNI, LEVI VERTIKALNI i DESNI VERTIKALNI monitor.
 *
 * Oslanja se na GLOBALNE pozicije (position.x), pa mapiranje radi bez obzira
 * kako je Windows složio virtuelni ekran (levi monitor može imati negativan x,
 * ili biti „ispod" centralnog). Ne pretpostavlja redosled iz `monitors()`.
 */

import type { MonitorInfo } from "./windowPlacement";

export type MonitorRole =
  | "central"
  | "left-vertical"
  | "right-vertical"
  | "other";

/** Rezultat mapiranja: monitor po ulozi (nedostajući = null). */
export type MonitorMap = {
  central: MonitorInfo | null;
  "left-vertical": MonitorInfo | null;
  "right-vertical": MonitorInfo | null;
  others: MonitorInfo[];
};

/**
 * Cilj na koji se šalje prozor (uloga monitora). `aux-N` (1-baziran) su dodatni
 * monitori za setup sa 3–5 ekrana.
 */
export type MonitorTarget =
  | "central"
  | "left-vertical"
  | "right-vertical"
  | `aux-${number}`;

/** Monitor je vertikalan ako je viši nego širi. */
export function isVertical(monitor: MonitorInfo): boolean {
  return monitor.size.height > monitor.size.width;
}

/** Površina ekrana (za izbor „glavnog" pejzažnog kao centralnog). */
function area(monitor: MonitorInfo): number {
  return monitor.size.width * monitor.size.height;
}

/**
 * Mapira monitore u uloge:
 *  - CENTRALNI = najveći pejzažni (width ≥ height) po površini;
 *  - VERTIKALNI se dele po x koordinati u odnosu na centralni:
 *      x < centar.x → levi; inače → desni. Kad centralni ne postoji,
 *      dele se međusobno (najmanji x = levi, najveći x = desni).
 */
export function mapMonitors(monitors: MonitorInfo[]): MonitorMap {
  const landscape = monitors.filter((m) => !isVertical(m));
  const vertical = monitors.filter((m) => isVertical(m));

  // Centralni = najveći pejzažni monitor.
  const central =
    landscape.length > 0
      ? landscape.reduce((best, m) => (area(m) > area(best) ? m : best))
      : null;

  let left: MonitorInfo | null = null;
  let right: MonitorInfo | null = null;

  if (vertical.length > 0) {
    const sorted = [...vertical].sort((a, b) => a.position.x - b.position.x);
    if (central) {
      const lefts = sorted.filter((m) => m.position.x < central.position.x);
      const rights = sorted.filter((m) => m.position.x >= central.position.x);
      // Najbliži centru sa svake strane.
      left = lefts.length ? lefts[lefts.length - 1] : null;
      right = rights.length ? rights[0] : null;
    } else {
      left = sorted[0] ?? null;
      right = sorted.length > 1 ? sorted[sorted.length - 1] : null;
    }
  }

  const claimed = new Set<MonitorInfo>();
  if (central) claimed.add(central);
  if (left) claimed.add(left);
  if (right) claimed.add(right);

  return {
    central,
    "left-vertical": left,
    "right-vertical": right,
    others: monitors.filter((m) => !claimed.has(m)),
  };
}

/** Vraća monitor za traženu ulogu (uz fallback na centralni pa prvi). */
export function monitorForTarget(
  map: MonitorMap,
  target: MonitorTarget,
): MonitorInfo | null {
  // Dodatni monitori: "aux-1", "aux-2"… → 1-baziran indeks u others.
  const auxMatch = /^aux-(\d+)$/.exec(target);
  if (auxMatch) {
    const index = Number(auxMatch[1]) - 1;
    return map.others[index] ?? map.central ?? null;
  }
  return map[target as "central" | "left-vertical" | "right-vertical"]
    ?? map.central
    ?? null;
}

/** Uloga (target) datog monitora unutar mape — za snimanje/detekciju. */
export function targetOfMonitor(
  map: MonitorMap,
  monitor: MonitorInfo,
): MonitorTarget {
  if (monitor === map.central) return "central";
  if (monitor === map["left-vertical"]) return "left-vertical";
  if (monitor === map["right-vertical"]) return "right-vertical";
  const auxIndex = map.others.indexOf(monitor);
  if (auxIndex >= 0) return `aux-${auxIndex + 1}`;
  return "central";
}

/** Nalazi monitor koji sadrži tačku (x,y); null ako nijedan. */
export function monitorAtPoint(
  monitors: MonitorInfo[],
  x: number,
  y: number,
): MonitorInfo | null {
  for (const m of monitors) {
    if (
      x >= m.position.x &&
      x < m.position.x + m.size.width &&
      y >= m.position.y &&
      y < m.position.y + m.size.height
    ) {
      return m;
    }
  }
  return null;
}


// ==========          APSOLUTNI OKVIR NA MONITORU          ==========

/** Okvir prozora relativno na gornji-levi ugao ciljnog monitora. */
export type Frame = {
  x: number;
  y: number;
  width: number;
  height: number;
};

/** Apsolutni fizički okvir = pozicija monitora + relativni offset okvira. */
export function absoluteFrame(monitor: MonitorInfo, frame: Frame): Frame {
  return {
    x: monitor.position.x + frame.x,
    y: monitor.position.y + frame.y,
    width: frame.width,
    height: frame.height,
  };
}

/** X offset koji horizontalno centrira širinu `width` na monitoru. */
export function centerX(monitor: MonitorInfo, width: number): number {
  return Math.max(0, Math.round((monitor.size.width - width) / 2));
}

/** Y offset koji vertikalno centrira visinu `height` na monitoru. */
export function centerY(monitor: MonitorInfo, height: number): number {
  return Math.max(0, Math.round((monitor.size.height - height) / 2));
}
