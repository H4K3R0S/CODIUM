// ==========          PAMETNO POZICIONIRANJE PREVIEW-A          ==========
/*
 * Odlučuje gde ide Codium preview prozor u odnosu na CORE Main:
 *  - AKO ima dovoljno mesta desno od Main-a (do desne ivice monitora) → preview
 *    se doka desno od Main-a (ne dira Main).
 *  - INAČE → Main migrira na drugi monitor, a preview zauzme (0,0) trenutnog
 *    monitora.
 * Čista matematika (bez Tauri-ja); imperativni sloj (launchPreview) je koristi.
 */

import type { Frame } from "./monitorLayout";
import type { MonitorInfo } from "./windowPlacement";

export type PreviewPlacement = {
  mode: "dock-right" | "evacuate";
  /** Apsolutni okvir preview prozora. */
  previewFrame: Frame;
  /** Ako mode = evacuate: novi apsolutni okvir Main-a (inače null). */
  mainTargetFrame: Frame | null;
};

/** Ograniči y tako da preview stane po visini monitora. */
function clampTop(
  preferredY: number,
  monitor: MonitorInfo,
  height: number,
): number {
  const top = monitor.position.y;
  const bottom = monitor.position.y + monitor.size.height - height;
  if (bottom < top) {
    return top;
  }
  return Math.min(Math.max(preferredY, top), bottom);
}

/** Prvi monitor različit od datog (za migraciju Main-a). */
function otherMonitor(
  current: MonitorInfo,
  monitors: MonitorInfo[],
): MonitorInfo | null {
  return monitors.find((m) => m !== current) ?? null;
}

/**
 * Planira poziciju preview-a.
 * @param main        trenutni apsolutni okvir Main prozora
 * @param mainMonitor monitor na kom je Main
 * @param monitors    svi monitori (za migraciju)
 * @param required    željena veličina preview-a (uređaj)
 */
export function planPreviewPlacement(
  main: Frame,
  mainMonitor: MonitorInfo,
  monitors: MonitorInfo[],
  required: { width: number; height: number },
): PreviewPlacement {
  const mainRight = main.x + main.width;
  const monitorRight = mainMonitor.position.x + mainMonitor.size.width;
  const rightSpace = monitorRight - mainRight;

  // Ima mesta desno od Main-a → dokuj preview tu (Main ostaje).
  if (rightSpace >= required.width) {
    return {
      mode: "dock-right",
      previewFrame: {
        x: mainRight,
        y: clampTop(main.y, mainMonitor, required.height),
        width: required.width,
        height: required.height,
      },
      mainTargetFrame: null,
    };
  }

  // Nema mesta → Main migrira na drugi monitor, preview na (0,0) ovog.
  const other = otherMonitor(mainMonitor, monitors);
  const mainTargetFrame: Frame | null = other
    ? {
        x: other.position.x,
        y: other.position.y,
        width: Math.min(main.width, other.size.width),
        height: Math.min(main.height, other.size.height),
      }
    : null;

  return {
    mode: "evacuate",
    previewFrame: {
      x: mainMonitor.position.x,
      y: mainMonitor.position.y,
      width: required.width,
      height: required.height,
    },
    mainTargetFrame,
  };
}
