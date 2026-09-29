// ==========          PROFILI RADNOG PROSTORA (Window Manager)          ==========
/*
 * Profil = imenovani, opisani i „scope-ovani" raspored jednog ili više prozora.
 * Zamenjuje stari slot-sistem (Shift+broj). Svaki prozor ima ulogu, ciljni
 * monitor i okvir (veličina + relativni offset na tom monitoru), uz opciju
 * centriranja. Sve mere su u fizičkim pikselima ciljnog monitora.
 *
 * Ugrađeni profili su fiksni (Default/Medium/Large). Korisnički se čuvaju u
 * localStorage. Scope kaže čemu profil služi: "core" (ceo CORE) ili konkretan
 * domen (npr. "codium"), da bi se kasnije birao po kontekstu.
 */

import type { MonitorInfo } from "./windowPlacement";
import {
  centerX,
  centerY,
  isVertical,
  type Frame,
  type MonitorMap,
  type MonitorTarget,
} from "./monitorLayout";

export type WindowRole = "main" | "terminal" | "chat" | "preview" | "logs";

/** Koliko vertikalnog monitora Main zauzima. */
export type VerticalFraction = "top-third" | "top-two-thirds" | "full";

/**
 * Adaptivna veličina Main prozora: na pejzažnom monitoru koristi `horizontal`
 * okvir; na vertikalnom bira frakciju visine (trećina/dve trećine/ceo ekran).
 */
export type AdaptiveSize = {
  horizontal: Frame;
  vertical: VerticalFraction;
};

/** "core" = globalno; bilo koji drugi string = ID domena (codium, filmium…). */
export type WorkspaceScope = "core" | string;

/** Centriranje okvira na ciljnom monitoru (poništava frame.x/y po osi). */
export type CenterMode = "x" | "y" | "both";

export type WorkspaceWindow = {
  role: WindowRole;
  monitor: MonitorTarget;
  frame: Frame;
  center?: CenterMode;
  /** Ako je zadato (samo za Main), veličina se adaptira vrsti monitora. */
  adaptive?: AdaptiveSize;
  /** Prikaz koji bare prozor renderuje (za role ≠ "main"). */
  view?: string;
  title?: string;
};

export type WorkspaceProfile = {
  id: string;
  name: string;
  description: string;
  scope: WorkspaceScope;
  builtin?: boolean;
  windows: WorkspaceWindow[];
};


// ==========          UGRAĐENI PROFILI (Central 2560×1440)          ==========

/**
 * DEFAULT — jedan prozor 1300×850, centriran na centralnom monitoru.
 */
const PROFILE_DEFAULT: WorkspaceProfile = {
  id: "default",
  name: "Default",
  description: "Glavni prozor 1300×850, gornji-levi ugao (0,0) centralnog monitora.",
  scope: "core",
  builtin: true,
  windows: [
    {
      role: "main",
      monitor: "central",
      frame: { x: 0, y: 0, width: 1300, height: 850 },
      adaptive: {
        horizontal: { x: 0, y: 0, width: 1300, height: 850 },
        vertical: "top-third",
      },
    },
  ],
};

/**
 * MEDIUM WORKSPACE — pixel-savršen grid bez preklapanja na 2560×1440:
 *  - Main 1620×1050 @ (0,0)
 *  - Terminal 1600×350 @ (0,1060)  (tačno ispod Main-a)
 *  - Chat 840×1400 @ (1720,0)      (uz desnu ivicu)
 */
const PROFILE_MEDIUM: WorkspaceProfile = {
  id: "medium",
  name: "Medium Workspace",
  description:
    "Glavni app + CORE Terminal (ispod) + Claude Chat (desno). " +
    "Pixel grid bez preklapanja na 2560×1440.",
  scope: "core",
  builtin: true,
  windows: [
    {
      role: "main",
      monitor: "central",
      frame: { x: 0, y: 0, width: 1620, height: 1050 },
      adaptive: {
        horizontal: { x: 0, y: 0, width: 1620, height: 1050 },
        vertical: "top-two-thirds",
      },
    },
    {
      role: "terminal",
      monitor: "central",
      frame: { x: 0, y: 1060, width: 1600, height: 350 },
      view: "terminal",
      title: "CORE Terminal",
    },
    {
      role: "chat",
      monitor: "central",
      frame: { x: 1720, y: 0, width: 840, height: 1400 },
      view: "chat",
      title: "Claude Chat",
    },
  ],
};

/**
 * LARGE — glavni prozor 1720×1400, centriran na centralnom monitoru.
 */
const PROFILE_LARGE: WorkspaceProfile = {
  id: "large",
  name: "Large",
  description: "Glavni prozor 1720×1400, gornji-levi ugao (0,0) centralnog monitora.",
  scope: "core",
  builtin: true,
  windows: [
    {
      role: "main",
      monitor: "central",
      frame: { x: 0, y: 0, width: 1720, height: 1400 },
      adaptive: {
        horizontal: { x: 0, y: 0, width: 1720, height: 1400 },
        vertical: "full",
      },
    },
  ],
};

// ==========          DOMEN-SVESNI PROFILI (W2)          ==========

/**
 * FILMIUM — Main ostavlja mesta desno za Proširenu biblioteku/video (magnet).
 * Main 1500×1400 na pejzažu; na vertikali pun ekran (kolekcija Full Size).
 */
const PROFILE_FILMIUM_WORK: WorkspaceProfile = {
  id: "filmium-work",
  name: "Filmium — Biblioteka",
  description:
    "Glavni prozor levo (1500×1400); Proširena biblioteka se magnetno lepi " +
    "desno do kraja ekrana. Na vertikali kolekcija ide Full Size.",
  scope: "filmium",
  builtin: true,
  windows: [
    {
      role: "main",
      monitor: "central",
      frame: { x: 0, y: 0, width: 1500, height: 1400 },
      adaptive: {
        horizontal: { x: 0, y: 0, width: 1500, height: 1400 },
        vertical: "full",
      },
    },
  ],
};

/**
 * CODIUM — radni prostor pogodan za Phone preview desno / PC-WEB evakuaciju.
 * Main gornje dve trećine (kao Medium), jedan prozor.
 */
const PROFILE_CODIUM_WORK: WorkspaceProfile = {
  id: "codium-work",
  name: "Codium — Radni prostor",
  description:
    "Glavni prozor 1620×1050; Phone preview se dokuje desno, a PC/WEB " +
    "preview evakuiše Main na vertikalu i zauzima glavni monitor.",
  scope: "codium",
  builtin: true,
  windows: [
    {
      role: "main",
      monitor: "central",
      frame: { x: 0, y: 0, width: 1620, height: 1050 },
      adaptive: {
        horizontal: { x: 0, y: 0, width: 1620, height: 1050 },
        vertical: "top-two-thirds",
      },
    },
  ],
};

export const BUILT_IN_PROFILES: WorkspaceProfile[] = [
  PROFILE_DEFAULT,
  PROFILE_MEDIUM,
  PROFILE_LARGE,
  PROFILE_FILMIUM_WORK,
  PROFILE_CODIUM_WORK,
];


// ==========          PREVIEW NA VERTIKALNOM MONITORU (1200×1920)          ==========

export type PreviewKind = "mobile" | "pc" | "full";

/**
 * Prozori preview-a po tipu, relativno na ciljni vertikalni monitor:
 *  - mobile: 450×900, horizontalno (i vertikalno) centriran (Phone Preview);
 *  - pc: JEDAN prozor, gornje dve trećine vertikalnog monitora (1200×1280);
 *  - full: 1200×1920 (ceo ekran).
 *
 * Napomena: pc je namerno JEDAN prozor (ranije su bila dva pa je delovalo kao
 * 50/50 split). Puni „evacuation" model (Main → vertikala, PC/WEB → glavni
 * monitor + tabovi) je u planu Intelligent Window Management-a.
 */
export const PREVIEW_SPECS: Record<PreviewKind, WorkspaceWindow[]> = {
  mobile: [
    {
      role: "preview",
      monitor: "left-vertical",
      frame: { x: 0, y: 0, width: 450, height: 900 },
      center: "both",
    },
  ],
  pc: [
    {
      role: "preview",
      monitor: "left-vertical",
      frame: { x: 0, y: 0, width: 1200, height: 1280 },
    },
  ],
  full: [
    {
      role: "preview",
      monitor: "left-vertical",
      frame: { x: 0, y: 0, width: 1200, height: 1920 },
    },
  ],
};


// ==========          RAZREŠAVANJE OKVIRA (uz centriranje)          ==========

/**
 * Vraća stvarni relativni okvir prozora na datom monitoru: ako je zadato
 * centriranje, x/y se računaju iz veličine monitora, inače ostaju iz `frame`.
 */
export function resolveFrame(window: WorkspaceWindow, monitor: MonitorInfo): Frame {
  const { frame, center } = window;
  const x =
    center === "x" || center === "both" ? centerX(monitor, frame.width) : frame.x;
  const y =
    center === "y" || center === "both" ? centerY(monitor, frame.height) : frame.y;
  return { x, y, width: frame.width, height: frame.height };
}


// ==========          VERTIKALNA ADAPTACIJA (konfigurabilno)          ==========

/**
 * Podešavanje kako se Main adaptira na vertikalnom monitoru:
 *  - mode "manual": frakcija po presetu (Alt+1 trećina, Alt+2 dve trećine,
 *    Alt+3 pun) — korisnik bira presetom;
 *  - mode "auto": frakcija po REZOLUCIJI (visini) monitora, uz granice.
 * Frakcije su konfigurabilne.
 */
export type VerticalAdaptationConfig = {
  mode: "manual" | "auto";
  thirdBelow: number; // auto: visina < thirdBelow → trećina
  twoThirdsBelow: number; // auto: visina < twoThirdsBelow → dve trećine; inače pun
  thirdFraction: number;
  twoThirdsFraction: number;
};

export const DEFAULT_VERTICAL_ADAPTATION: VerticalAdaptationConfig = {
  mode: "manual",
  thirdBelow: 1300,
  twoThirdsBelow: 2100,
  thirdFraction: 1 / 3,
  twoThirdsFraction: 2 / 3,
};

export const VERTICAL_ADAPTATION_KEY = "core.window.verticalAdaptation";

export function readVerticalAdaptation(): VerticalAdaptationConfig {
  if (typeof window === "undefined") {
    return DEFAULT_VERTICAL_ADAPTATION;
  }
  try {
    const raw = window.localStorage.getItem(VERTICAL_ADAPTATION_KEY);
    if (!raw) {
      return DEFAULT_VERTICAL_ADAPTATION;
    }
    return { ...DEFAULT_VERTICAL_ADAPTATION, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_VERTICAL_ADAPTATION;
  }
}

export function writeVerticalAdaptation(config: VerticalAdaptationConfig): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(VERTICAL_ADAPTATION_KEY, JSON.stringify(config));
  } catch {
    /* storage nedostupan */
  }
}

/** Frakcija visine za datu kategoriju/rezoluciju po configu. */
function verticalFractionValue(
  category: VerticalFraction,
  monitor: MonitorInfo,
  config: VerticalAdaptationConfig,
): number {
  if (config.mode === "auto") {
    const h = monitor.size.height;
    if (h < config.thirdBelow) return config.thirdFraction;
    if (h < config.twoThirdsBelow) return config.twoThirdsFraction;
    return 1;
  }
  if (category === "top-third") return config.thirdFraction;
  if (category === "top-two-thirds") return config.twoThirdsFraction;
  return 1;
}

/**
 * Okvir Main prozora na datom monitoru: pejzažni → `horizontal`; vertikalni →
 * gornji deo visine po frakciji (manual po presetu ili auto po rezoluciji).
 */
export function resolveMainFrame(
  adaptive: AdaptiveSize,
  monitor: MonitorInfo,
  config: VerticalAdaptationConfig = readVerticalAdaptation(),
): Frame {
  if (!isVertical(monitor)) {
    return adaptive.horizontal;
  }
  const fraction = verticalFractionValue(adaptive.vertical, monitor, config);
  return {
    x: 0,
    y: 0,
    width: monitor.size.width,
    height: Math.round(monitor.size.height * fraction),
  };
}


// ==========          EVACUATION (Codium PC/WEB preview)          ==========

/**
 * Plan „evakuacije" za veliki preview (PC/WEB):
 *  - Main → vrh VERTIKALNOG monitora (gornje dve trećine);
 *  - Preview → GLAVNI (centralni) monitor, ceo prostor, na (0,0).
 * Central je glavni ekran (odluka projekta). Ako nema vertikalnog, Main se ne
 * seli (mainFrame = null), preview svejedno ide na central.
 */
export type EvacuationPlan = {
  central: MonitorInfo;
  vertical: MonitorInfo | null;
  mainTarget: MonitorTarget | null;
  mainFrame: Frame | null; // relativno na vertical
  previewFrame: Frame; // relativno na central (0,0, ceo ekran)
};

export function planEvacuation(
  map: MonitorMap,
  config: VerticalAdaptationConfig = readVerticalAdaptation(),
): EvacuationPlan | null {
  const central = map.central;
  if (!central) {
    return null;
  }

  const vertical = map["left-vertical"] ?? map["right-vertical"] ?? null;
  const mainTarget: MonitorTarget | null = vertical
    ? vertical === map["left-vertical"]
      ? "left-vertical"
      : "right-vertical"
    : null;

  const mainFrame = vertical
    ? resolveMainFrame(
        {
          horizontal: { x: 0, y: 0, width: 0, height: 0 },
          vertical: "top-two-thirds",
        },
        vertical,
        config,
      )
    : null;

  return {
    central,
    vertical,
    mainTarget,
    mainFrame,
    previewFrame: {
      x: 0,
      y: 0,
      width: central.size.width,
      height: central.size.height,
    },
  };
}


// ==========          PERSISTENCIJA (korisnički profili)          ==========

export const WORKSPACE_PROFILES_KEY = "core.window.workspaceProfiles";

/** Čita korisničke profile iz localStorage (tolerantno na grešku). */
export function readUserProfiles(): WorkspaceProfile[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(WORKSPACE_PROFILES_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as WorkspaceProfile[];
    return Array.isArray(parsed) ? parsed.filter((p) => !p.builtin) : [];
  } catch {
    return [];
  }
}

/** Upisuje korisničke profile (ugrađeni se nikad ne snimaju). */
export function writeUserProfiles(profiles: WorkspaceProfile[]): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    const clean = profiles.filter((p) => !p.builtin);
    window.localStorage.setItem(WORKSPACE_PROFILES_KEY, JSON.stringify(clean));
  } catch {
    /* storage nedostupan — profili se ne pamte */
  }
}

/** Svi profili: ugrađeni + korisnički. */
export function allProfiles(): WorkspaceProfile[] {
  return [...BUILT_IN_PROFILES, ...readUserProfiles()];
}

/** Nađe profil po ID-u (ugrađeni pa korisnički). */
export function profileById(id: string): WorkspaceProfile | null {
  return allProfiles().find((p) => p.id === id) ?? null;
}

/**
 * Profili relevantni za dati domen: CORE (globalni) + oni sa scope tog domena.
 * Osnov za domen-svesnu primenu (W2).
 */
export function profilesForScope(scope: WorkspaceScope): WorkspaceProfile[] {
  return allProfiles().filter((p) => p.scope === "core" || p.scope === scope);
}
