// ==========          KATALOG SHELL-OVA (čisto)          ==========
/*
 * Pomoćna, testabilna logika oko liste shell-ova koju vraća Rust: izbor
 * podrazumevanog i kratke labele za tab. Bez Tauri poziva.
 */

import type { ShellInfo } from "./terminalApi";

// Prioritet podrazumevanog shell-a (Windows-first, pa Unix).
const DEFAULT_PRIORITY = ["pwsh", "powershell", "bash", "zsh", "cmd", "sh"];

/**
 * Bira podrazumevani shell: po prioritetu (pwsh > powershell > bash…), a ako
 * nijedan iz liste nije prisutan → prvi dostupan; prazna lista → null.
 */
export function pickDefaultShell(shells: ShellInfo[]): ShellInfo | null {
  if (shells.length === 0) {
    return null;
  }
  for (const id of DEFAULT_PRIORITY) {
    const found = shells.find((s) => s.id === id);
    if (found) {
      return found;
    }
  }
  return shells[0];
}

/** Kratka labela taba: ime shell-a + redni broj instance (1-baziran). */
export function shellTabTitle(shell: ShellInfo, index: number): string {
  return index <= 1 ? shell.name : `${shell.name} ${index}`;
}

/** Koliko instanci datog shell-a već postoji (za numeraciju taba). */
export function shellInstanceIndex(
  openShellIds: string[],
  shellId: string,
): number {
  return openShellIds.filter((id) => id === shellId).length + 1;
}
