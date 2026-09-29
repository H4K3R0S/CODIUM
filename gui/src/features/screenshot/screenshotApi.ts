// ==========          SCREENSHOT API (Tauri most)          ==========
/*
 * Tanak omotač oko Rust komandi (`shot_*`), PathService endpointa za folder
 * snimaka i global-shortcut plugina. Sav native rad (grab, crop, upis, clipboard)
 * je u Rust-u; ovde je klijentska strana. Van Tauri-ja sve je no-op / greška.
 */

import { invoke } from "@tauri-apps/api/core";
import {
  register,
  unregisterAll,
} from "@tauri-apps/plugin-global-shortcut";

import { getApiUrl } from "../../services/httpClient";
import { isTauri } from "../window/windowManager";
import {
  clientRectToScreenPx,
  screenshotRelPath,
  type Mode,
  type Rect,
  type WindowGeom,
} from "./captureController";
import { formatExtension, type ScreenshotFormat } from "./screenshotSettings";


// ==========          TIPOVI          ==========

export type MonitorInfo = {
  id: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  is_primary: boolean;
};

export type ShotResult = {
  path: string;
  width: number;
  height: number;
  preview_base64: string;
  clipboard: boolean;
};

export type CaptureRequest = {
  mode: Mode;
  format: ScreenshotFormat;
  quality: number;
  /** Za „full": izbor monitora (podrazumevano primarni). */
  monitorId?: number;
  /** Za „region"/„element": oblast u CSS pikselima (viewport). */
  rect?: Rect;
};


// ==========          FOLDER SNIMAKA (PathService)          ==========

let cachedDir: string | null = null;

async function screenshotsDir(): Promise<string> {
  if (cachedDir) {
    return cachedDir;
  }
  const response = await fetch(getApiUrl("/api/v1/system/screenshots/dir"));
  if (!response.ok) {
    throw new Error("Nije moguće dobiti folder snimaka.");
  }
  const data = (await response.json()) as { path: string };
  cachedDir = data.path;
  return cachedDir;
}


// ==========          MONITORI          ==========

export async function listMonitors(): Promise<MonitorInfo[]> {
  if (!isTauri()) {
    return [];
  }
  try {
    return await invoke<MonitorInfo[]>("shot_monitors");
  } catch {
    return [];
  }
}

async function windowGeom(): Promise<WindowGeom> {
  const [x, y, scale] = await invoke<[number, number, number]>(
    "core_window_geom",
  );
  return { x, y, scale };
}


// ==========          SNIMANJE          ==========

export async function capture(request: CaptureRequest): Promise<ShotResult> {
  if (!isTauri()) {
    throw new Error("Snimanje ekrana radi samo u CORE desktop aplikaciji.");
  }

  const saveDir = await screenshotsDir();
  const ext = formatExtension(request.format);
  const relPath = screenshotRelPath(request.mode, ext, new Date());

  let screenRect: Rect | undefined;
  if (request.mode === "region" || request.mode === "element") {
    if (!request.rect) {
      throw new Error("Nedostaje oblast za snimak.");
    }
    const geom = await windowGeom();
    screenRect = clientRectToScreenPx(request.rect, geom);
  }

  return await invoke<ShotResult>("shot_capture", {
    params: {
      mode: request.mode,
      monitor_id: request.monitorId ?? null,
      rect: screenRect
        ? {
            x: screenRect.x,
            y: screenRect.y,
            width: screenRect.width,
            height: screenRect.height,
          }
        : null,
      format: request.format,
      quality: request.quality,
      save_dir: saveDir,
      rel_path: relPath,
    },
  });
}


// ==========          OTVORI FOLDER          ==========

export async function revealPath(path: string, select = true): Promise<void> {
  if (!isTauri()) {
    return;
  }
  try {
    await invoke("shot_reveal", { path, select });
  } catch {
    // Otvaranje foldera nije kritično — tiho preskoči.
  }
}


// ==========          GLOBALNE PREČICE          ==========

/** Veza prečice i načina snimanja. */
export type ShortcutBinding = { mode: Mode; accelerator: string };

/**
 * Registruje globalne prečice po načinu (prvo očisti sve prethodne). Prazne i
 * duplirane prečice se preskaču; nevažeća prečica ne ruši ostale.
 */
export async function registerCaptureShortcuts(
  bindings: ShortcutBinding[],
  onTrigger: (mode: Mode) => void,
): Promise<void> {
  if (!isTauri()) {
    return;
  }
  try {
    await unregisterAll();
  } catch {
    // Nebitno.
  }

  const seen = new Set<string>();
  for (const { mode, accelerator } of bindings) {
    const accel = accelerator.trim();
    if (!accel || seen.has(accel)) {
      continue;
    }
    seen.add(accel);
    try {
      await register(accel, (event) => {
        if (event.state === "Pressed") {
          onTrigger(mode);
        }
      });
    } catch {
      // Zauzeta ili nevažeća prečica — preskoči je, ostale rade.
    }
  }
}

export async function unregisterCaptureShortcuts(): Promise<void> {
  if (!isTauri()) {
    return;
  }
  try {
    await unregisterAll();
  } catch {
    // Nebitno.
  }
}
