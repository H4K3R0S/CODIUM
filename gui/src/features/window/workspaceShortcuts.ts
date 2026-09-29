// ==========          PREČICE RADNOG PROSTORA (Alt)          ==========
/*
 * Čisto mapiranje tastature u akciju Window Manager-a. Alt-bazirano, da ne
 * otima kucanje simbola ('#', '$'…) kao stari Shift+broj sistem. Bez Tauri
 * poziva i DOM efekata — lako se testira. Koristi `event.code` (fizička tipka),
 * pa radi nezavisno od rasporeda tastature.
 *
 *   Alt + 1 → Default        Alt + F → Fullscreen toggle
 *   Alt + 2 → Medium         Alt + M → Mobile preview (levi vertikalni)
 *   Alt + 3 → Large          Alt + P → PC preview  (levi vertikalni)
 *   Alt + R → Panic reset (zatvori satelite, Main → central 0,0, default)
 */

import type { MonitorTarget } from "./monitorLayout";
import type { PreviewKind } from "./workspaceProfiles";

export type WorkspaceAction =
  | { type: "profile"; id: string }
  | { type: "fullscreen" }
  | { type: "preview"; kind: PreviewKind; target: MonitorTarget }
  | { type: "evacuate"; kind: "pc" | "web" }
  | { type: "panic" };

type ShortcutEvent = {
  code: string;
  altKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
};

/**
 * Mapira kombinaciju u akciju. Zahteva Alt bez Ctrl/Shift/Meta — sve ostalo
 * vraća `null` (ne otima druge kombinacije).
 */
export function resolveWorkspaceShortcut(
  event: ShortcutEvent,
): WorkspaceAction | null {
  if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
    return null;
  }

  switch (event.code) {
    case "Digit1":
      return { type: "profile", id: "default" };
    case "Digit2":
      return { type: "profile", id: "medium" };
    case "Digit3":
      return { type: "profile", id: "large" };
    case "KeyF":
      return { type: "fullscreen" };
    case "KeyM":
      return { type: "preview", kind: "mobile", target: "left-vertical" };
    case "KeyP":
      // PC preview = evakuacija: Main → vertikala, preview → glavni monitor.
      return { type: "evacuate", kind: "pc" };
    case "KeyR":
      // Panic: zatvori sve satelite, Main → central (0,0), default veličina.
      return { type: "panic" };
    default:
      return null;
  }
}
