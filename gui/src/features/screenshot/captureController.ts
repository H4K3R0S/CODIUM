// ==========          GEOMETRIJA I PUTANJA SNIMKA (čista logika)          ==========
/*
 * Bez Tauri poziva — samo matematika pravougaonika i gradnja imena fajla. Ceo
 * alat radi na jednom primitivu: snimak monitora + opcioni crop. Region i
 * element se biraju u CSS pikselima (viewport); pošto je CORE glavni prozor bez
 * dekoracija, gornji-levi ugao klijent-oblasti je i gornji-levi ugao prozora, pa
 * se CSS pravougaonik preslikava u ekranske (fizičke) piksele preko pozicije
 * prozora i scale faktora (`core_window_geom`).
 */

/** Tačka u CSS pikselima (viewport). */
export type Point = { x: number; y: number };

/** Pravougaonik u pikselima (CSS ili fizičkim, zavisno od koraka). */
export type Rect = { x: number; y: number; width: number; height: number };

/** Granice prozora u CSS pikselima (npr. innerWidth/innerHeight). */
export type Bounds = { width: number; height: number };

/** Geometrija klijent-oblasti prozora: pozicija (fizički px) + scale faktor. */
export type WindowGeom = { x: number; y: number; scale: number };

/** Način kadriranja (usklađeno sa `screenshotSettings.ScreenshotMode`). */
export type Mode = "full" | "window" | "region" | "element";

/**
 * Pravi normalizovan pravougaonik iz dve tačke prevlačenja — bez obzira na smer,
 * rezultat ima pozitivnu širinu i visinu.
 */
export function normalizeDragRect(start: Point, end: Point): Rect {
  const x = Math.min(start.x, end.x);
  const y = Math.min(start.y, end.y);
  return {
    x,
    y,
    width: Math.abs(end.x - start.x),
    height: Math.abs(end.y - start.y),
  };
}

/** Seče pravougaonik na granice prozora (bez negativnih koordinata). */
export function clampRectToBounds(rect: Rect, bounds: Bounds): Rect {
  const x = Math.max(0, rect.x);
  const y = Math.max(0, rect.y);
  const right = Math.min(rect.x + rect.width, bounds.width);
  const bottom = Math.min(rect.y + rect.height, bounds.height);
  return {
    x,
    y,
    width: Math.max(0, right - x),
    height: Math.max(0, bottom - y),
  };
}

/**
 * Prevodi pravougaonik iz CSS piksela (viewport) u ekranske fizičke piksele:
 * dodaje poziciju klijent-oblasti i množi scale faktorom, pa zaokružuje. Rezultat
 * ide Rust komandi kao `rect` za crop iz snimka monitora.
 */
export function clientRectToScreenPx(rect: Rect, geom: WindowGeom): Rect {
  return {
    x: Math.round(geom.x + rect.x * geom.scale),
    y: Math.round(geom.y + rect.y * geom.scale),
    width: Math.round(rect.width * geom.scale),
    height: Math.round(rect.height * geom.scale),
  };
}

/** Dva broja u dvocifren zapis (npr. 9 → "09"). */
function pad2(value: number): string {
  return value < 10 ? `0${value}` : String(value);
}

/**
 * Relativna putanja fajla snimka: `GGGG-MM-DD/HHMMSS-<mode>.<ext>`. Rust je
 * spaja sa apsolutnim folderom snimaka. Datum se prosleđuje radi determinizma u
 * testu.
 */
export function screenshotRelPath(
  mode: Mode,
  ext: string,
  when: Date,
): string {
  const day = `${when.getFullYear()}-${pad2(when.getMonth() + 1)}-${pad2(
    when.getDate(),
  )}`;
  const time = `${pad2(when.getHours())}${pad2(when.getMinutes())}${pad2(
    when.getSeconds(),
  )}`;
  return `${day}/${time}-${mode}.${ext}`;
}
