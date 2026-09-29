// ==========          PRESETI DOCKING RASPOREDA (D3/D4)          ==========
/*
 * Imenovani preseti dockview rasporeda (grid serialization) + import/export.
 * Raspored je neproziran dockview JSON (`api.toJSON()`), ovde se čuva kao
 * `unknown` — ne dira se ručno. Preseti su deljeni (ne po projektu), jer su
 * ponovo upotrebljivi obrasci rasporeda. CORE-nivo: `key` bira prostor imena
 * (npr. "core.dock.presets"), pa isti mehanizam služi svim domenima.
 */

export type DockPreset = {
  id: string;
  name: string;
  /** Neproziran dockview SerializedDockview (api.toJSON()). */
  layout: unknown;
};

export const DEFAULT_PRESETS_KEY = "core.dock.presets";

/** Čita presete iz datog prostora (tolerantno na grešku / neispravan sadržaj). */
export function readDockPresets(key: string = DEFAULT_PRESETS_KEY): DockPreset[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as DockPreset[]).filter(isPreset) : [];
  } catch {
    return [];
  }
}

/** Upisuje listu presetā u dati prostor. */
export function writeDockPresets(
  presets: DockPreset[],
  key: string = DEFAULT_PRESETS_KEY,
): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(key, JSON.stringify(presets));
  } catch {
    /* storage nedostupan */
  }
}

/**
 * Dodaje/ažurira preset po imenu (isti naziv → zamena rasporeda, bez duplikata).
 * Vraća novu listu. Prazno ime se ignoriše (vraća nepromenjeno).
 */
export function upsertDockPreset(
  presets: DockPreset[],
  name: string,
  layout: unknown,
): DockPreset[] {
  const clean = name.trim();
  if (clean === "") {
    return presets;
  }
  const existing = presets.find((p) => p.name === clean);
  if (existing) {
    return presets.map((p) => (p.id === existing.id ? { ...p, layout } : p));
  }
  return [...presets, { id: `preset-${Date.now()}`, name: clean, layout }];
}

/** Uklanja preset po ID-u. */
export function removeDockPreset(
  presets: DockPreset[],
  id: string,
): DockPreset[] {
  return presets.filter((p) => p.id !== id);
}

/** Nađe preset po ID-u. */
export function dockPresetById(
  presets: DockPreset[],
  id: string,
): DockPreset | null {
  return presets.find((p) => p.id === id) ?? null;
}

/** Serijalizuje presete u JSON string za export (fajl). */
export function exportDockPresets(presets: DockPreset[]): string {
  return JSON.stringify({ version: 1, presets }, null, 2);
}

/**
 * Parsira import JSON (iz fajla): prihvata i `{presets:[...]}` i goli niz.
 * Vraća validne presete; nevalidan ulaz → prazan niz (bez bacanja).
 */
export function parseDockPresetsImport(raw: string): DockPreset[] {
  try {
    const parsed = JSON.parse(raw);
    const list = Array.isArray(parsed)
      ? parsed
      : Array.isArray(parsed?.presets)
        ? parsed.presets
        : [];
    return (list as DockPreset[]).filter(isPreset);
  } catch {
    return [];
  }
}

/** Spaja uvezene presete sa postojećim (po imenu, uvoz ima prednost). */
export function mergeDockPresets(
  existing: DockPreset[],
  incoming: DockPreset[],
): DockPreset[] {
  let result = existing;
  for (const p of incoming) {
    result = upsertDockPreset(result, p.name, p.layout);
  }
  return result;
}

function isPreset(value: unknown): value is DockPreset {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as DockPreset).id === "string" &&
    typeof (value as DockPreset).name === "string" &&
    "layout" in (value as object)
  );
}
