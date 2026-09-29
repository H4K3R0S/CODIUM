// ==========          PANIC LAYOUT RESET (W7)          ==========
/*
 * Čista logika za „paniku": iz svih labela prozora izdvaja satelite (sve osim
 * Main-a) koje treba zatvoriti, i računa ciljni okvir Main-a na centralnom
 * monitoru (default profil, adaptivno). Bez Tauri poziva — lako se testira.
 */

import type { Frame } from "./monitorLayout";
import type { MonitorInfo } from "./windowPlacement";
import { profileById, resolveFrame, resolveMainFrame } from "./workspaceProfiles";

/**
 * Labeli satelita za zatvaranje = svi osim onog koji zadržavamo (Main). Prazan
 * `keep` ne zadržava ništa (ne bi trebalo da se desi u praksi).
 */
export function labelsToClose(all: string[], keep: string): string[] {
  return all.filter((label) => label !== keep);
}

/**
 * Ciljni (relativni) okvir Main-a pri panici: default profil na centralnom
 * monitoru. Adaptira se vrsti monitora (pejzaž → horizontalni okvir; vertikala
 * → gornja frakcija). Fallback 1300×850 ako default profil nedostaje.
 */
export function panicMainFrame(central: MonitorInfo): Frame {
  const profile = profileById("default");
  const main = profile?.windows.find((w) => w.role === "main");
  if (!main) {
    return { x: 0, y: 0, width: 1300, height: 850 };
  }
  if (main.adaptive) {
    return resolveMainFrame(main.adaptive, central);
  }
  return resolveFrame(main, central);
}
