// ==========          TERMINAL API (Tauri most)          ==========
/*
 * Tanak omotač oko Rust PTY komandi (`term_*`) i event stream-a. Sav OS pristup
 * (spawn shell, ulaz/izlaz, resize, kill) ide kroz Tauri — ovo je klijentska
 * strana. Van Tauri-ja (browser preview) sve je no-op / prazno.
 */

import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import { isTauri } from "../window/windowManager";

export type ShellInfo = {
  id: string;
  name: string;
  path: string;
  args: string[];
};

/** Par [ključ, vrednost] env promenljive (iz profila). */
export type EnvPair = [string, string];

type SpawnOptions = {
  id: string;
  shell: string;
  args: string[];
  cwd?: string;
  env?: EnvPair[];
  cols: number;
  rows: number;
};

/** Dostupni shell-ovi na mašini (za drop meni). */
export async function listShells(): Promise<ShellInfo[]> {
  if (!isTauri()) {
    return [];
  }
  try {
    return await invoke<ShellInfo[]>("term_list_shells");
  } catch {
    return [];
  }
}

/** Pokreće PTY sesiju; baca ako Rust vrati grešku (GUI je prikaže). */
export async function spawnTerminal(opts: SpawnOptions): Promise<void> {
  if (!isTauri()) {
    return;
  }
  await invoke("term_spawn", {
    id: opts.id,
    shell: opts.shell,
    args: opts.args,
    cwd: opts.cwd ?? null,
    env: opts.env ?? null,
    cols: opts.cols,
    rows: opts.rows,
  });
}

/** Šalje korisnički unos u shell. */
export async function writeTerminal(id: string, data: string): Promise<void> {
  if (!isTauri()) {
    return;
  }
  try {
    await invoke("term_write", { id, data });
  } catch {
    /* sesija zatvorena */
  }
}

/** Menja dimenzije PTY-a. */
export async function resizeTerminal(
  id: string,
  cols: number,
  rows: number,
): Promise<void> {
  if (!isTauri()) {
    return;
  }
  try {
    await invoke("term_resize", { id, cols, rows });
  } catch {
    /* sesija zatvorena */
  }
}

/** Gasi sesiju (zatvaranje taba/prozora). */
export async function killTerminal(id: string): Promise<void> {
  if (!isTauri()) {
    return;
  }
  try {
    await invoke("term_kill", { id });
  } catch {
    /* već zatvorena */
  }
}

/** Pretplata na izlaz PTY-a; poziva `cb` sa (id, bajtovi). */
export async function onTermData(
  cb: (id: string, bytes: Uint8Array) => void,
): Promise<UnlistenFn> {
  if (!isTauri()) {
    return () => {};
  }
  return listen<{ id: string; bytes: number[] }>("term://data", (event) => {
    cb(event.payload.id, Uint8Array.from(event.payload.bytes));
  });
}

/** Pretplata na kraj procesa (shell izašao). */
export async function onTermExit(
  cb: (id: string) => void,
): Promise<UnlistenFn> {
  if (!isTauri()) {
    return () => {};
  }
  return listen<{ id: string }>("term://exit", (event) => {
    cb(event.payload.id);
  });
}
