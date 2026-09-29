// ==========          DOMEN-SVESNO PONAŠANJE PROZORA (W2)          ==========
/*
 * Deklarativna mapa: aktivni domen → podrazumevani raspored i strategija
 * pomoćnih prozora. Čisto (bez Tauri) — imperativni sloj (`workspaceManager`)
 * je čita i bira konkretnu akciju (magnet desno / evakuacija / ništa).
 *
 *   FILMIUM  → Main levo, Biblioteka magnetno desno; kolekcija na vertikali Full.
 *   CODIUM   → Phone preview desno; PC/WEB evakuacija (Main → vertikala).
 *   CORE/IMPERIUM/KALIMA → bez posebnog satelita (Kalima dolazi u W6).
 */

import type { DomainId } from "../../lib/domainTheme";

/** Kako se otvara glavni pomoćni prozor domena. */
export type PreviewStrategy = "none" | "snap-right" | "evacuate";

export type DomainWindowBehavior = {
  domain: DomainId;
  /** Profil za Main pri ulasku u domen. */
  defaultProfileId: string;
  /** Strategija glavnog pomoćnog prozora (preview/biblioteka). */
  previewStrategy: PreviewStrategy;
  /** Filmium: Proširena biblioteka se magnetno lepi desno od Main-a. */
  librarySnapsRight: boolean;
  /** Filmium: kolekcija na vertikalnom monitoru ide preko celog ekrana. */
  verticalCollectionFullscreen: boolean;
};

const CORE_BEHAVIOR: DomainWindowBehavior = {
  domain: "core",
  defaultProfileId: "default",
  previewStrategy: "none",
  librarySnapsRight: false,
  verticalCollectionFullscreen: false,
};

export const BEHAVIOR_BY_DOMAIN: Record<DomainId, DomainWindowBehavior> = {
  core: CORE_BEHAVIOR,
  filmium: {
    domain: "filmium",
    defaultProfileId: "filmium-work",
    previewStrategy: "snap-right",
    librarySnapsRight: true,
    verticalCollectionFullscreen: true,
  },
  codium: {
    domain: "codium",
    defaultProfileId: "codium-work",
    previewStrategy: "evacuate",
    librarySnapsRight: false,
    verticalCollectionFullscreen: false,
  },
  imperium: { ...CORE_BEHAVIOR, domain: "imperium" },
  kalima: { ...CORE_BEHAVIOR, domain: "kalima" },
};

/** Ponašanje za dati domen; nepoznat → CORE podrazumevano. */
export function behaviorForDomain(domain: string): DomainWindowBehavior {
  return (
    BEHAVIOR_BY_DOMAIN[domain as DomainId] ?? {
      ...CORE_BEHAVIOR,
      domain: "core",
    }
  );
}
