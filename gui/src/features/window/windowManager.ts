import {
  availableMonitors,
  currentMonitor,
  getCurrentWindow,
  type Window,
} from "@tauri-apps/api/window";
import { PhysicalPosition, PhysicalSize, LogicalSize } from "@tauri-apps/api/dpi";
import { WebviewWindow } from "@tauri-apps/api/webviewWindow";

import {
  classifyMonitor,
  presetForShortcut,
  startupPlacement,
  type Orientation,
} from "./windowPlacement";
import {
  getProfileSlot,
  type WindowPane,
  type WindowProfile,
} from "./windowProfiles";


// ==========          IMPERATIVNI SLOJ (TAURI)          ==========
/*
 * Tanak omotač oko Tauri window API-ja. Sva logika izbora veličine/rasporeda
 * je u čistim modulima (windowPlacement, windowShortcuts, windowProfiles);
 * ovde se samo pozivaju Tauri komande. Van Tauri okruženja (npr. browser
 * preview) sve funkcije su no-op.
 */

/** `true` samo unutar Tauri desktop runtime-a. */
export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}


// ==========          PRECIZAN RASPORED (fizički pikseli)          ==========

/**
 * Postavlja prozor tačno na dati okvir u fizičkim pikselima i poravnava ga uz
 * ivicu monitora. Isključuje shadow (undecorated prozor na Win11 inače dobija
 * senku/zaobljene ivice — otud "malo unutra" izgled) i kompenzuje eventualni
 * nevidljivi border tako što poravna klijent oblast, ne okvir.
 */
async function applyFramePhysical(win: Window, pane: WindowPane): Promise<void> {
  try {
    await win.setShadow(false);
  } catch {
    // Neke platforme ne podržavaju setShadow — nebitno.
  }

  if (pane.fullscreen) {
    await win.setFullscreen(true);
    return;
  }

  await win.setFullscreen(false);
  await win.setSize(new PhysicalSize(pane.width, pane.height));
  await win.setPosition(new PhysicalPosition(pane.x, pane.y));

  try {
    const outer = await win.outerPosition();
    const inner = await win.innerPosition();
    const dx = inner.x - outer.x;
    const dy = inner.y - outer.y;

    if (dx !== 0 || dy !== 0) {
      await win.setPosition(new PhysicalPosition(pane.x - dx, pane.y - dy));
    }
  } catch {
    // Bez inner/outer podrške ostaje osnovno pozicioniranje.
  }
}


// ==========          PRESETI (Shift + broj)          ==========

/**
 * Postavlja veličinu trenutnog prozora prema presetu za dati monitor.
 * Preset veličine su logičke (nezavisne od skaliranja); fullscreen prelazi u
 * OS fullscreen.
 */
export async function applyPreset(index: number): Promise<void> {
  if (!isTauri()) {
    return;
  }

  const win = getCurrentWindow();
  const monitor = await currentMonitor();

  if (!monitor) {
    return;
  }

  const preset = presetForShortcut(classifyMonitor(monitor.size), index);

  if (!preset) {
    return;
  }

  if (preset === "fullscreen") {
    await win.setFullscreen(true);
    return;
  }

  await win.setFullscreen(false);
  await win.setSize(new LogicalSize(preset.width, preset.height));
}


// ==========          POČETNI RASPORED (paljenje)          ==========

/**
 * Pri pokretanju: nalazi monitor na kom je prozor, pozicionira ga u gornji
 * levi ugao tog monitora (priljubljeno) i postavlja auto veličinu (četvrtina
 * za wide, puna širina × trećina za vertikalni).
 */
export async function runStartupPlacement(): Promise<void> {
  if (!isTauri()) {
    return;
  }

  const win = getCurrentWindow();
  const monitor = await currentMonitor();

  if (!monitor) {
    return;
  }

  const place = startupPlacement({
    position: monitor.position,
    size: monitor.size,
  });

  await applyFramePhysical(win, {
    x: place.x,
    y: place.y,
    width: place.width,
    height: place.height,
  });
}


// ==========          SNIMANJE OKVIRA          ==========

/**
 * Snima trenutni okvir prozora kao pane (pozicija + veličina + fullscreen).
 * Vraća `null` van Tauri okruženja.
 */
export async function captureCurrentPane(): Promise<WindowPane | null> {
  if (!isTauri()) {
    return null;
  }

  const win = getCurrentWindow();
  const position = await win.outerPosition();
  const size = await win.outerSize();
  const fullscreen = await win.isFullscreen();

  return {
    x: position.x,
    y: position.y,
    width: size.width,
    height: size.height,
    fullscreen,
  };
}


// ==========          ČIST (BARE) PROZOR          ==========

/** URL čistog prozora: isti frontend, bare ruta bez sidebara/UX-a. */
function bareWindowUrl(pane: WindowPane): string {
  const params = new URLSearchParams();

  if (pane.view) {
    params.set("view", pane.view);
  }

  if (pane.title) {
    params.set("title", pane.title);
  }

  if (pane.query) {
    for (const [key, value] of Object.entries(pane.query)) {
      params.set(key, value);
    }
  }

  const query = params.toString();

  return `index.html#/window${query ? `?${query}` : ""}`;
}

let instanceCounter = 0;

/**
 * Otvara jedan čist prozor na okviru pane-a. Prozor učitava istu aplikaciju
 * ali u bare režimu (bez sidebara i UX elemenata — samo pozadina + titlebar
 * kontrole). Domen u njega renderuje svoj prikaz (pane.view).
 */
export function openPane(pane: WindowPane): WebviewWindow | null {
  if (!isTauri()) {
    return null;
  }

  const label = `core-${Date.now()}-${(instanceCounter += 1)}`;

  const webview = new WebviewWindow(label, {
    url: bareWindowUrl(pane),
    title: pane.title ?? "CORE",
    decorations: false,
    shadow: false,
    width: pane.width,
    height: pane.height,
  });

  // Precizan raspored (fizički pikseli) tek kad prozor postoji.
  void webview.once("tauri://created", () => {
    void applyFramePhysical(webview, pane).catch(() => {
      // Prozor je zatvoren pre nego što je raspored primenjen.
    });
  });

  return webview;
}

/** Otvara sve pane-ove profila kao čiste prozore (više prozora odjednom). */
export function openProfileWindows(profile: WindowProfile): void {
  if (!isTauri()) {
    return;
  }

  for (const pane of profile.panes) {
    openPane(pane);
  }
}

/** Menja trenutni prozor na okvir pane-a. */
export async function applyPaneToCurrent(pane: WindowPane): Promise<void> {
  if (!isTauri()) {
    return;
  }

  await applyFramePhysical(getCurrentWindow(), pane);
}


// ==========          AKTIVACIJA PROFILA          ==========

/**
 * Aktivira profil iz slota:
 *  - "resize" sa tačno jednim pane-om menja trenutni prozor;
 *  - inače otvara sve pane-ove kao nove čiste prozore.
 *
 * Koristi je i prečica Alt+Shift+slot i programski pozivi domena.
 */
export async function activateProfileSlot(slot: number): Promise<void> {
  const profile = getProfileSlot(slot);

  if (!profile || profile.panes.length === 0) {
    return;
  }

  if (profile.mode === "resize" && profile.panes.length === 1) {
    await applyPaneToCurrent(profile.panes[0]);
    return;
  }

  openProfileWindows(profile);
}

/**
 * Programski otvara sve prozore profila iz slota — namenjeno domenima (npr.
 * KALIMA: prikaz u više prozora pokretanjem profila umesto ručnog podešavanja).
 */
export function openProfileWindowsBySlot(slot: number): void {
  const profile = getProfileSlot(slot);

  if (profile) {
    openProfileWindows(profile);
  }
}


// ==========          MONITORI (za Core Settings)          ==========

export type MonitorOption = {
  index: number;
  name: string;
  orientation: Orientation;
  width: number;
  height: number;
};

/** Lista dostupnih monitora sa klasifikacijom, za izbor u podešavanjima. */
export async function listMonitors(): Promise<MonitorOption[]> {
  if (!isTauri()) {
    return [];
  }

  const monitors = await availableMonitors();

  return monitors.map((monitor, index) => ({
    index,
    name: monitor.name ?? `Monitor ${index + 1}`,
    orientation: classifyMonitor(monitor.size),
    width: monitor.size.width,
    height: monitor.size.height,
  }));
}

/**
 * Otvara jedan čist prozor sa auto rasporedom (top-left + auto veličina) na
 * izabranom monitoru — kada nema unapred snimljenog profila.
 */
export async function openWindowOnMonitor(index: number): Promise<void> {
  if (!isTauri()) {
    return;
  }

  const monitors = await availableMonitors();
  const monitor = monitors[index];

  if (!monitor) {
    return;
  }

  const place = startupPlacement({
    position: monitor.position,
    size: monitor.size,
  });

  openPane({
    x: place.x,
    y: place.y,
    width: place.width,
    height: place.height,
  });
}
