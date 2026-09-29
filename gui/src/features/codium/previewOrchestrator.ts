// ==========          PREVIEW ORKESTRATOR (Tauri sloj)          ==========
/*
 * Otvara/gasi preview prozor projekta kao zaseban Tauri prozor koji učitava
 * spoljni URL (dev server / staging / live). Van Tauri runtime-a (browser
 * preview) sve funkcije su no-op — čista logika veličina je u previewProfiles.
 *
 * F7 MVP: dev server pokreće korisnik ručno, ovde se samo prikazuje URL u
 * prozoru izabrane veličine na izabranom monitoru. Screenshot/auto-detekcija
 * komande dolaze kasnije.
 */
import { availableMonitors } from "@tauri-apps/api/window";
import { WebviewWindow } from "@tauri-apps/api/webviewWindow";

import { isTauri } from "../window/windowManager";
import {
  previewWindowLabel,
  type PreviewSize,
} from "./previewProfiles";


export type PreviewMonitor = {
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
};

export type OpenPreviewOptions = {
  projectId: number;
  url: string;
  size: PreviewSize;
  title?: string;
  /** Ime monitora (iz listPreviewMonitors); bez njega ide na primarni. */
  monitorName?: string;
  /**
   * Eksplicitan apsolutni okvir (fizički pikseli). Ako je zadat, koristi se
   * tačna pozicija i veličina (za pametno dokovanje/evakuaciju), a `size` i
   * `monitorName` se ignorišu.
   */
  frame?: { x: number; y: number; width: number; height: number };
};

/** Lista dostupnih monitora (prazna van Tauri-ja). */
export async function listPreviewMonitors(): Promise<PreviewMonitor[]> {
  if (!isTauri()) {
    return [];
  }
  try {
    const monitors = await availableMonitors();
    return monitors.map((monitor, index) => ({
      name: monitor.name ?? `Monitor ${index + 1}`,
      x: monitor.position.x,
      y: monitor.position.y,
      width: monitor.size.width,
      height: monitor.size.height,
    }));
  } catch {
    return [];
  }
}

/** Zatvara preview prozor projekta (ako postoji). */
export async function closePreview(projectId: number): Promise<void> {
  if (!isTauri()) {
    return;
  }
  try {
    const existing = await WebviewWindow.getByLabel(
      previewWindowLabel(projectId),
    );
    if (existing) {
      await existing.close();
    }
  } catch {
    // Prozor je već zatvoren ili nedostupan — nebitno.
  }
}

/**
 * Otvara (ili ponovo otvara) preview prozor projekta na zadatom URL-u i
 * veličini. Prethodni prozor istog projekta se prvo zatvara, pa je ista
 * funkcija i „reload" (ponovno učitavanje spoljne strane).
 */
export async function openPreview(
  options: OpenPreviewOptions,
): Promise<WebviewWindow | null> {
  if (!isTauri()) {
    return null;
  }

  await closePreview(options.projectId);

  // Eksplicitan okvir (pametno dokovanje) ima prednost nad monitorName/size.
  let position: { x: number; y: number } | undefined;
  let width = options.size.width;
  let height = options.size.height;

  if (options.frame) {
    position = { x: options.frame.x, y: options.frame.y };
    width = options.frame.width;
    height = options.frame.height;
  } else if (options.monitorName) {
    const monitors = await listPreviewMonitors();
    const target = monitors.find((m) => m.name === options.monitorName);
    if (target) {
      position = { x: target.x + 40, y: target.y + 40 };
    }
  }

  const webview = new WebviewWindow(previewWindowLabel(options.projectId), {
    url: options.url,
    title: options.title ?? "CODIUM Preview",
    width,
    height,
    ...(position ? { x: position.x, y: position.y } : {}),
    resizable: true,
  });

  return webview;
}
