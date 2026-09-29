// ==========          RASPORED PROZORA PO MONITORU          ==========
/*
 * Čista logika (bez Tauri poziva) koja određuje veličine prozora po tipu
 * monitora i početni raspored pri paljenju. Sve mere su u fizičkim pikselima
 * monitora; imperativni sloj (windowManager) ih prevodi u Tauri pozive.
 */

export type MonitorSize = {
  width: number;
  height: number;
};

export type MonitorInfo = {
  position: { x: number; y: number };
  size: MonitorSize;
};

/** Tip monitora prema orijentaciji/aspektu. */
export type Orientation = "wide" | "wide-ultra" | "vertical";

export type PresetSize = {
  width: number;
  height: number;
};

/** Fiksna veličina ili prelazak u OS fullscreen. */
export type Preset = PresetSize | "fullscreen";

/** Preko kog aspekta se pejzažni monitor smatra ekstra širokim. */
const ULTRA_WIDE_ASPECT = 2.1;


// ==========          PRESETI (Shift + broj)          ==========

/**
 * Fiksni preseti veličine prozora po grupi monitora. wide-ultra deli presete
 * sa wide grupom.
 */
export const WINDOW_PRESETS: Record<"wide" | "vertical", Preset[]> = {
  wide: [
    { width: 1300, height: 850 },
    { width: 1620, height: 1050 },
    { width: 1720, height: 1400 },
    "fullscreen",
  ],
  vertical: [
    { width: 1200, height: 700 },
    { width: 1200, height: 1250 },
    "fullscreen",
  ],
};


// ==========          KLASIFIKACIJA          ==========

/**
 * Svrstava monitor u wide / wide-ultra / vertical na osnovu dimenzija.
 */
export function classifyMonitor({ width, height }: MonitorSize): Orientation {
  if (height > width) {
    return "vertical";
  }

  return width / height >= ULTRA_WIDE_ASPECT ? "wide-ultra" : "wide";
}

/** Grupa presета kojoj orijentacija pripada. */
function presetGroup(orientation: Orientation): "wide" | "vertical" {
  return orientation === "vertical" ? "vertical" : "wide";
}

/**
 * Vraća preset za `Shift + (index + 1)` na datom tipu monitora, ili `null`
 * ako indeks izlazi iz opsega presета tog monitora.
 */
export function presetForShortcut(
  orientation: Orientation,
  index: number,
): Preset | null {
  return WINDOW_PRESETS[presetGroup(orientation)][index] ?? null;
}


// ==========          POČETNI RASPORED (paljenje)          ==========

export type StartupPlacement = {
  x: number;
  y: number;
  width: number;
  height: number;
};

/**
 * Računa početnu poziciju (top-left datog monitora) i veličinu prozora pri
 * paljenju:
 *  - vertikalni monitor: puna širina × trećina visine;
 *  - ekstra širok: trećina širine × pola visine;
 *  - normalan wide: četvrtina (½ širine × ½ visine).
 */
export function startupPlacement(monitor: MonitorInfo): StartupPlacement {
  const { position, size } = monitor;
  const orientation = classifyMonitor(size);

  let width: number;
  let height: number;

  if (orientation === "vertical") {
    width = size.width;
    height = Math.round(size.height / 3);
  } else if (orientation === "wide-ultra") {
    width = Math.round(size.width / 3);
    height = Math.round(size.height / 2);
  } else {
    width = Math.round(size.width / 2);
    height = Math.round(size.height / 2);
  }

  return { x: position.x, y: position.y, width, height };
}
