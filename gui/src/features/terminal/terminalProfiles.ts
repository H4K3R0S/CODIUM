// ==========          PROFILI TERMINALA (T6)          ==========
/*
 * Imenovani preseti terminala: shell + radni direktorijum + env promenljive.
 * Klik na profil otvara tab sa tim podešavanjima. Čista CRUD logika nad
 * localStorage (`core.term.profiles`), deljeno za sve domene.
 */

import type { EnvPair } from "./terminalApi";

export type TermProfile = {
  id: string;
  name: string;
  /** ID shell-a iz kataloga (`term_list_shells`). */
  shellId: string;
  cwd?: string;
  /** Env promenljive kao parovi [ključ, vrednost]. */
  env?: EnvPair[];
};

export const TERM_PROFILES_KEY = "core.term.profiles";

/** Čita profile (tolerantno na grešku / neispravan sadržaj). */
export function readProfiles(key: string = TERM_PROFILES_KEY): TermProfile[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as TermProfile[]).filter(isProfile) : [];
  } catch {
    return [];
  }
}

/** Upisuje profile (prazna lista briše ključ). */
export function writeProfiles(
  profiles: TermProfile[],
  key: string = TERM_PROFILES_KEY,
): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (profiles.length === 0) {
      window.localStorage.removeItem(key);
      return;
    }
    window.localStorage.setItem(key, JSON.stringify(profiles));
  } catch {
    /* storage nedostupan */
  }
}

/**
 * Dodaje nov ili ažurira postojeći profil (po `id` ako je zadat). Prazno ime
 * ili shell → vraća nepromenjeno. Vraća novu listu.
 */
export function upsertProfile(
  profiles: TermProfile[],
  draft: Omit<TermProfile, "id"> & { id?: string },
): TermProfile[] {
  if (draft.name.trim() === "" || draft.shellId === "") {
    return profiles;
  }
  const clean: TermProfile = {
    id: draft.id ?? `tprof-${Date.now()}`,
    name: draft.name.trim(),
    shellId: draft.shellId,
    cwd: draft.cwd?.trim() ? draft.cwd.trim() : undefined,
    env: normalizeEnv(draft.env),
  };
  const exists = draft.id && profiles.some((p) => p.id === draft.id);
  return exists
    ? profiles.map((p) => (p.id === draft.id ? clean : p))
    : [...profiles, clean];
}

/** Uklanja profil po ID-u. */
export function removeProfile(
  profiles: TermProfile[],
  id: string,
): TermProfile[] {
  return profiles.filter((p) => p.id !== id);
}

/** Zadržava samo env parove sa nepraznim ključem; prazna lista → undefined. */
export function normalizeEnv(env?: EnvPair[]): EnvPair[] | undefined {
  if (!env) {
    return undefined;
  }
  const clean = env
    .map(([k, v]) => [k.trim(), v] as EnvPair)
    .filter(([k]) => k !== "");
  return clean.length > 0 ? clean : undefined;
}

function isProfile(value: unknown): value is TermProfile {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as TermProfile).id === "string" &&
    typeof (value as TermProfile).name === "string" &&
    typeof (value as TermProfile).shellId === "string"
  );
}
