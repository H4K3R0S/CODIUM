// ==========          KORISNIČKI PROFILI PROZORA          ==========
/*
 * Profil je imenovani skup "pane"-ova — svaki pane je zapamćen okvir prozora
 * (pozicija + veličina + fullscreen, uz opcioni prikaz). Korisnik ga pravi u
 * Core Settings snimanjem trenutnog prozora (jedan ili više puta). Aktivira
 * se prečicom Alt+Shift+slot ili programski: domen (npr. KALIMA) pokrene
 * profil i time odjednom otvori sve predefinisane prozore, pa u njih prikazuje
 * šta mu treba.
 *
 * Čuva se kao JSON lista u localStorage, pa i ne-React kod (windowManager)
 * može da je čita. Sve mere su apsolutni fizički pikseli (uključuju offset
 * monitora), onako kako ih vraća Tauri outerPosition/outerSize.
 */

export type WindowProfileMode = "resize" | "open";

/** Jedan prozor u profilu: okvir + opcioni prikaz koji se u njemu otvara. */
export type WindowPane = {
  x: number;
  y: number;
  width: number;
  height: number;
  fullscreen?: boolean;
  /** Ključ prikaza koji čist prozor renderuje (npr. domen postavi svoj). */
  view?: string;
  /** Naslov prikaza (informativno). */
  title?: string;
  /** Dodatni query parametri za prikaz (npr. preview-host: url, tabs). */
  query?: Record<string, string>;
};

export type WindowProfile = {
  /** Slot 1–3 (mapiran na Alt+Shift+1..3). */
  slot: number;
  /** Naziv koji korisnik vidi. */
  name: string;
  /**
   * "resize" (uz tačno jedan pane) menja trenutni prozor; inače se svi
   * pane-ovi otvaraju kao novi čisti prozori.
   */
  mode: WindowProfileMode;
  panes: WindowPane[];
};

export const WINDOW_PROFILES_KEY = "core.window.profiles";


// ==========          ČITANJE / UPIS          ==========

/**
 * Čita listu profila iz localStorage. Tolerantno na nedostupan ili oštećen
 * storage — u tom slučaju vraća praznu listu.
 */
export function readProfiles(): WindowProfile[] {
  if (typeof window === "undefined") {
    return [];
  }

  const raw = window.localStorage.getItem(WINDOW_PROFILES_KEY);

  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);

    if (!Array.isArray(parsed)) {
      return [];
    }

    // Tolerantno na profile bez panes polja (preskoči neispravne).
    return (parsed as WindowProfile[]).filter(
      (profile) => Array.isArray(profile?.panes),
    );
  } catch {
    return [];
  }
}

/** Upisuje celu listu profila. */
export function writeProfiles(profiles: WindowProfile[]): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(WINDOW_PROFILES_KEY, JSON.stringify(profiles));
}

/** Vraća profil u datom slotu ili `null`. */
export function getProfileSlot(slot: number): WindowProfile | null {
  return readProfiles().find((profile) => profile.slot === slot) ?? null;
}

/**
 * Ubacuje ili zamenjuje profil za njegov slot i vraća novu listu.
 */
export function upsertProfile(profile: WindowProfile): WindowProfile[] {
  const others = readProfiles().filter(
    (existing) => existing.slot !== profile.slot,
  );

  const next = [...others, profile].sort((a, b) => a.slot - b.slot);

  writeProfiles(next);

  return next;
}

/** Briše profil u datom slotu i vraća novu listu. */
export function clearProfileSlot(slot: number): WindowProfile[] {
  const next = readProfiles().filter((profile) => profile.slot !== slot);

  writeProfiles(next);

  return next;
}

/**
 * Dodaje pane u profil datog slota (pravi profil ako ne postoji) i vraća novu
 * listu. Koristi se pri snimanju trenutnog prozora u profil.
 */
export function addPaneToSlot(
  slot: number,
  pane: WindowPane,
  meta?: { name?: string; mode?: WindowProfileMode },
): WindowProfile[] {
  const existing = getProfileSlot(slot);

  const profile: WindowProfile = existing
    ? {
        ...existing,
        name: meta?.name ?? existing.name,
        mode: meta?.mode ?? existing.mode,
        panes: [...existing.panes, pane],
      }
    : {
        slot,
        name: meta?.name?.trim() || `Profil ${slot}`,
        mode: meta?.mode ?? "open",
        panes: [pane],
      };

  return upsertProfile(profile);
}

/** Briše pane po indeksu iz profila slota i vraća novu listu. */
export function removePaneFromSlot(
  slot: number,
  paneIndex: number,
): WindowProfile[] {
  const existing = getProfileSlot(slot);

  if (!existing) {
    return readProfiles();
  }

  const panes = existing.panes.filter((_, index) => index !== paneIndex);

  if (panes.length === 0) {
    return clearProfileSlot(slot);
  }

  return upsertProfile({ ...existing, panes });
}
