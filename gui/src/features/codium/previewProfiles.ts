// ==========          PREVIEW PROFILI (čista logika)          ==========
/*
 * Uređajni profili za preview prozor (F7). Bez Tauri poziva — samo veličine i
 * validacija, da bi bilo testabilno nezavisno od desktop runtime-a.
 */

export type PreviewDevice = "desktop" | "mobile" | "tablet" | "custom";

export type PreviewSize = { width: number; height: number };

/** Standardne veličine po uređaju (logički pikseli). Custom se zadaje ručno. */
export const PREVIEW_DEVICE_SIZES: Record<
  Exclude<PreviewDevice, "custom">,
  PreviewSize
> = {
  desktop: { width: 1280, height: 800 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 375, height: 812 },
};

export const PREVIEW_DEVICES: { id: PreviewDevice; label: string }[] = [
  { id: "desktop", label: "Desktop" },
  { id: "tablet", label: "Tablet" },
  { id: "mobile", label: "Mobilni" },
  { id: "custom", label: "Prilagođeno" },
];

// Granice custom veličine (spreči 0 i besmisleno velike prozore).
const MIN_DIMENSION = 200;
const MAX_DIMENSION = 7680;

/** Ograniči dimenziju na razuman opseg; NaN → minimum. */
function clampDimension(value: number): number {
  if (!Number.isFinite(value)) {
    return MIN_DIMENSION;
  }
  return Math.max(MIN_DIMENSION, Math.min(MAX_DIMENSION, Math.round(value)));
}

/**
 * Rešava konačnu veličinu preview prozora. Za `custom` koristi zadate dimenzije
 * (uz clamp); za ostale uzima standardnu veličinu uređaja.
 */
export function resolvePreviewSize(
  device: PreviewDevice,
  custom?: Partial<PreviewSize>,
): PreviewSize {
  if (device === "custom") {
    return {
      width: clampDimension(custom?.width ?? PREVIEW_DEVICE_SIZES.desktop.width),
      height: clampDimension(
        custom?.height ?? PREVIEW_DEVICE_SIZES.desktop.height,
      ),
    };
  }
  return PREVIEW_DEVICE_SIZES[device];
}

/**
 * Normalizuje URL koji je korisnik uneo za preview. Dodaje http:// ako nema
 * šeme (localhost/IP obično ide bez nje). Prazan/nevalidan → null.
 */
export function normalizePreviewUrl(raw: string): string | null {
  const trimmed = raw.trim();
  if (trimmed === "") {
    return null;
  }
  const withScheme = /^[a-z]+:\/\//i.test(trimmed)
    ? trimmed
    : `http://${trimmed}`;
  try {
    // Konstruktor baca na potpuno neispravan unos.
    const url = new URL(withScheme);
    return url.toString();
  } catch {
    return null;
  }
}

/** Stabilan label Tauri prozora za preview datog projekta (jedan po projektu). */
export function previewWindowLabel(projectId: number): string {
  return `codium-preview-${projectId}`;
}
