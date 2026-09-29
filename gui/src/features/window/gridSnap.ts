// ==========          GRID SNAPPING (magnetno lepljenje)          ==========
/*
 * Filmium magnet: pomoćni prozor (npr. Proširena biblioteka / video) lepi se uz
 * DESNU ivicu Main prozora i puni prostor do kraja ekrana, punom visinom. Kada
 * se Main pomeri ili promeni veličinu, prilepljeni prozor se dinamički prati.
 *
 * Čista matematika (`computeRightSnapFrame`) je testabilna; imperativni sloj
 * kači Tauri onMoved/onResized listenere i repozicionira prilepljeni prozor.
 */

import { getCurrentWindow } from "@tauri-apps/api/window";
import { PhysicalPosition, PhysicalSize } from "@tauri-apps/api/dpi";
import type { WebviewWindow } from "@tauri-apps/api/webviewWindow";

import { isTauri, openPane } from "./windowManager";
import { loadMonitorMap } from "./workspaceManager";
import { monitorAtPoint, type Frame } from "./monitorLayout";
import type { MonitorInfo } from "./windowPlacement";


/**
 * Okvir prilepljenog prozora desno od Main-a: x = desna ivica Main-a, širina do
 * kraja monitora, puna visina monitora. Sve apsolutni fizički pikseli.
 */
export function computeRightSnapFrame(
  mainAbs: Frame,
  monitor: MonitorInfo,
): Frame {
  const mainRight = mainAbs.x + mainAbs.width;
  const monitorRight = monitor.position.x + monitor.size.width;
  return {
    x: mainRight,
    y: monitor.position.y,
    width: Math.max(0, monitorRight - mainRight),
    height: monitor.size.height,
  };
}

/**
 * Fiksna veličina prilepljena uz desnu ivicu Main-a (npr. Phone Preview
 * 450×900): x = desna ivica Main-a, ali stegnuto tako da ceo prozor stane u
 * monitor (ako nema mesta, priljubi se uz desnu ivicu monitora). y = centriran
 * po visini Main-a, takođe stegnut u granice monitora.
 */
export function computeFixedRightFrame(
  mainAbs: Frame,
  monitor: MonitorInfo,
  size: { width: number; height: number },
): Frame {
  const monitorLeft = monitor.position.x;
  const monitorTop = monitor.position.y;
  const monitorRight = monitorLeft + monitor.size.width;
  const monitorBottom = monitorTop + monitor.size.height;

  const desiredX = mainAbs.x + mainAbs.width;
  const maxX = monitorRight - size.width;
  const x = Math.max(monitorLeft, Math.min(desiredX, maxX));

  const desiredY = mainAbs.y + Math.round((mainAbs.height - size.height) / 2);
  const maxY = monitorBottom - size.height;
  const y = Math.max(monitorTop, Math.min(desiredY, maxY));

  return { x, y, width: size.width, height: size.height };
}


/**
 * Okvir prilepljen uz DESNU IVICU MONITORA (ne uz Main), fiksne širine, pune
 * visine — od gornje do donje ivice ekrana. Za odvojeni AI chat prozor.
 */
export function computeScreenRightEdgeFrame(
  monitor: MonitorInfo,
  width: number,
): Frame {
  const monitorRight = monitor.position.x + monitor.size.width;
  const clampedWidth = Math.min(width, monitor.size.width);
  return {
    x: monitorRight - clampedWidth,
    y: monitor.position.y,
    width: clampedWidth,
    height: monitor.size.height,
  };
}


// ==========          IMPERATIVNI SLOJ (Tauri)          ==========

/** Trenutni apsolutni okvir Main prozora + monitor na kom je. */
async function mainFrameAndMonitor(): Promise<{
  frame: Frame;
  monitor: MonitorInfo;
} | null> {
  const win = getCurrentWindow();
  const pos = await win.outerPosition();
  const size = await win.outerSize();
  const map = await loadMonitorMap();
  const all = [
    map.central,
    map["left-vertical"],
    map["right-vertical"],
    ...map.others,
  ].filter((m): m is MonitorInfo => m !== null);
  const monitor =
    monitorAtPoint(all, pos.x + size.width / 2, pos.y + size.height / 2) ??
    map.central;
  if (!monitor) {
    return null;
  }
  return {
    frame: { x: pos.x, y: pos.y, width: size.width, height: size.height },
    monitor,
  };
}

/** Funkcija koja iz okvira Main-a i monitora računa okvir satelita. */
type SnapComputer = (mainAbs: Frame, monitor: MonitorInfo) => Frame;

/** Postavi prilepljeni prozor na izračunati okvir (jednom). */
async function reposition(
  satellite: WebviewWindow,
  compute: SnapComputer,
): Promise<void> {
  const info = await mainFrameAndMonitor();
  if (!info) {
    return;
  }
  const snap = compute(info.frame, info.monitor);
  try {
    await satellite.setPosition(new PhysicalPosition(snap.x, snap.y));
    await satellite.setSize(new PhysicalSize(snap.width, snap.height));
  } catch {
    /* prozor zatvoren pre repozicioniranja */
  }
}

/**
 * Uključi magnet sa datom funkcijom okvira: prilepljeni prozor prati Main
 * (pomeranje + resize). Vraća funkciju za isključivanje. Van Tauri-ja no-op.
 */
export async function attachSnap(
  satellite: WebviewWindow,
  compute: SnapComputer,
): Promise<() => void> {
  if (!isTauri()) {
    return () => {};
  }
  const main = getCurrentWindow();

  await reposition(satellite, compute); // početno poravnanje

  const unMoved = await main.onMoved(() => void reposition(satellite, compute));
  const unResized = await main.onResized(
    () => void reposition(satellite, compute),
  );

  return () => {
    unMoved();
    unResized();
  };
}

/** Magnet za prozor koji PUNI prostor desno od Main-a (Filmium biblioteka). */
export async function attachRightSnap(
  satellite: WebviewWindow,
): Promise<() => void> {
  return attachSnap(satellite, computeRightSnapFrame);
}

/**
 * Otvara prilepljeni prozor desno od Main-a i uključuje magnet. Namena:
 * Filmium proširena biblioteka/video. Vraća funkciju za isključivanje magneta
 * (auto se skida i kad se prozor zatvori).
 */
export async function openSnappedRight(opts?: {
  view?: string;
  title?: string;
  query?: Record<string, string>;
}): Promise<() => void> {
  if (!isTauri()) {
    return () => {};
  }
  const info = await mainFrameAndMonitor();
  if (!info) {
    return () => {};
  }
  const snap = computeRightSnapFrame(info.frame, info.monitor);
  const satellite = openPane({
    x: snap.x,
    y: snap.y,
    width: snap.width,
    height: snap.height,
    view: opts?.view,
    title: opts?.title ?? "Biblioteka",
    query: opts?.query,
  });
  if (!satellite) {
    return () => {};
  }
  const detach = await attachRightSnap(satellite);
  void satellite.once("tauri://destroyed", () => detach());
  return detach;
}

/**
 * Otvara čist prozor prilepljen uz DESNU IVICU MONITORA, pune visine (od vrha do
 * dna ekrana), zadate širine. Nezavisan od Main-a (ne prati ga) — namena: odvojeni
 * AI chat prozor. Vraća otvoreni prozor (ili null van Tauri-ja).
 */
export async function openScreenRightEdge(
  width: number,
  opts?: { view?: string; title?: string; query?: Record<string, string> },
): Promise<WebviewWindow | null> {
  if (!isTauri()) {
    return null;
  }
  const info = await mainFrameAndMonitor();
  if (!info) {
    return null;
  }
  const frame = computeScreenRightEdgeFrame(info.monitor, width);
  return openPane({
    x: frame.x,
    y: frame.y,
    width: frame.width,
    height: frame.height,
    view: opts?.view,
    title: opts?.title ?? "CORE",
    query: opts?.query,
  });
}

/**
 * Otvara prozor FIKSNE veličine prilepljen uz desnu ivicu Main-a i uključuje
 * magnet (Codium Phone Preview 450×900). Vraća funkciju za isključivanje magneta.
 */
export async function openSnappedFixedRight(
  size: { width: number; height: number },
  opts?: { view?: string; title?: string; query?: Record<string, string> },
): Promise<() => void> {
  if (!isTauri()) {
    return () => {};
  }
  const info = await mainFrameAndMonitor();
  if (!info) {
    return () => {};
  }
  const snap = computeFixedRightFrame(info.frame, info.monitor, size);
  const satellite = openPane({
    x: snap.x,
    y: snap.y,
    width: snap.width,
    height: snap.height,
    view: opts?.view,
    title: opts?.title ?? "Phone Preview",
    query: opts?.query,
  });
  if (!satellite) {
    return () => {};
  }
  const compute: SnapComputer = (mainAbs, monitor) =>
    computeFixedRightFrame(mainAbs, monitor, size);
  const detach = await attachSnap(satellite, compute);
  void satellite.once("tauri://destroyed", () => detach());
  return detach;
}
