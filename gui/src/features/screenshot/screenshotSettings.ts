// ==========          PODEŠAVANJA SCREENSHOT ALATA          ==========
/*
 * Jedinstven izvor ključeva i podrazumevanih vrednosti za screenshot alat —
 * dele ga panel podešavanja (CORE Settings → Alati) i hook za prečice. Vrednosti
 * se pamte u localStorage preko `useCoreSetting` / `useCoreStringSetting`.
 */

import type { Mode } from "./captureController";

/** Podržani formati fajla. Clipboard uvek dobija sirovu sliku, nezavisno. */
export type ScreenshotFormat = "png" | "jpg" | "webp";

/** Način kadriranja jednog snimka (isti tip kao `captureController.Mode`). */
export type ScreenshotMode = Mode;

/** Redosled načina u podešavanjima i menijima. */
export const MODES: Mode[] = ["full", "window", "region", "element"];

/** Srpski nazivi načina — deljeni izvor za meni, panel i podešavanja. */
export const MODE_LABELS: Record<Mode, string> = {
  full: "Ceo ekran",
  window: "Aktivan prozor",
  region: "Region",
  element: "Element",
};

// ==========          KLJUČEVI (localStorage)          ==========

/** Zaseban ključ prečice po načinu — svaki mod ima svoju prečicu. */
export const SHORTCUT_KEYS: Record<Mode, string> = {
  full: "core.screenshot.shortcut.full",
  window: "core.screenshot.shortcut.window",
  region: "core.screenshot.shortcut.region",
  element: "core.screenshot.shortcut.element",
};

export const FORMAT_KEY = "core.screenshot.format";
export const QUALITY_KEY = "core.screenshot.quality";

// ==========          PODRAZUMEVANE VREDNOSTI          ==========

/**
 * Podrazumevane prečice po načinu. Samo Element ima podrazumevanu (`Alt+Insert`);
 * ostali su prazni dok im korisnik ne dodeli prečicu u Podešavanjima.
 */
export const DEFAULT_SHORTCUTS: Record<Mode, string> = {
  full: "",
  window: "",
  region: "",
  element: "Alt+Insert",
};

export const DEFAULT_FORMAT: ScreenshotFormat = "png";
export const DEFAULT_QUALITY = 90;

/** Formati za padajući izbor u podešavanjima. */
export const FORMATS: { id: ScreenshotFormat; label: string; ext: string }[] = [
  { id: "png", label: "PNG (bez gubitaka)", ext: "png" },
  { id: "jpg", label: "JPG (manji fajl)", ext: "jpg" },
  { id: "webp", label: "WebP", ext: "webp" },
];

/** Ekstenzija fajla za dati format. */
export function formatExtension(format: ScreenshotFormat): string {
  const found = FORMATS.find((f) => f.id === format);
  return found ? found.ext : "png";
}

/** Da li format ima gubitke (pa kvalitet ima smisla). */
export function isLossyFormat(format: ScreenshotFormat): boolean {
  return format === "jpg" || format === "webp";
}

/** Svodi proizvoljan string na podržan format; nepoznato → PNG. */
export function normalizeFormat(value: string): ScreenshotFormat {
  return FORMATS.some((f) => f.id === value)
    ? (value as ScreenshotFormat)
    : DEFAULT_FORMAT;
}
