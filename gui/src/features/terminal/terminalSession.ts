// ==========          PERSIST SESIJA TERMINALA (T3)          ==========
/*
 * Pamti KOJI su tabovi bili otvoreni (po shell-u) za dati kontekst (npr.
 * projekat), da se pri ponovnom otvaranju workspace-a respawn-uju isti shell-ovi.
 * PTY procesi ne preživljavaju restart — čuva se samo opis tabova, ne sadržaj.
 * Čista logika nad localStorage; ključ bira prostor imena (`codium.term.<id>`).
 */

import type { ShellInfo } from "./terminalApi";
import type { SplitDirection } from "./TerminalSplit";

/** Zapamćen pan u tabu: shell + (opciono) grupa. */
export type SavedPane = { shellId: string; groupId?: string };

/**
 * Opis jednog zapamćenog taba. `shellId` je glavni shell (kompatibilnost sa
 * starim zapisima); `panes`/`direction` pamte pun split raspored kad postoji.
 */
export type SavedTab = {
  shellId: string;
  title?: string;
  direction?: SplitDirection;
  color?: string;
  panes?: SavedPane[];
};

/** Rekonstruisan pan (shell iz kataloga + grupa). */
export type RestoredPane = { shell: ShellInfo; groupId?: string };

/** Rekonstruisan tab (naslov, smer, panovi) — spreman za mapiranje na TermTab. */
export type RestoredTab = {
  title?: string;
  direction: SplitDirection;
  color?: string;
  panes: RestoredPane[];
};

const PREFIX = "core.term.session.";

/** Pun localStorage ključ za dati kontekst. */
export function sessionKey(context: string): string {
  return `${PREFIX}${context}`;
}

/** Čita zapamćene tabove (tolerantno na grešku / neispravan sadržaj). */
export function readSession(context: string): SavedTab[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(sessionKey(context));
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as SavedTab[]).filter(isSavedTab) : [];
  } catch {
    return [];
  }
}

/** Upisuje zapamćene tabove (prazna lista briše ključ). */
export function writeSession(context: string, tabs: SavedTab[]): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (tabs.length === 0) {
      window.localStorage.removeItem(sessionKey(context));
      return;
    }
    window.localStorage.setItem(sessionKey(context), JSON.stringify(tabs));
  } catch {
    /* storage nedostupan */
  }
}

/**
 * Mapira zapamćene tabove na trenutno dostupne shell-ove (po `shellId`).
 * Nepoznati shell-ovi (npr. deinstaliran) se preskaču. Vraća shell-ove u
 * zapamćenom redosledu — svaki je jedan tab za respawn.
 */
export function restoreTabs(
  saved: SavedTab[],
  shells: ShellInfo[],
): ShellInfo[] {
  const byId = new Map(shells.map((s) => [s.id, s]));
  const result: ShellInfo[] = [];
  for (const tab of saved) {
    const shell = byId.get(tab.shellId);
    if (shell) {
      result.push(shell);
    }
  }
  return result;
}

/**
 * Rekonstruiše pun raspored (panovi + grupe + smer) iz zapamćenih tabova, mapiran
 * na trenutno dostupne shell-ove. Nepoznati shell-ovi se preskaču; ako tab nema
 * `panes` (stari zapis), pravi se jedan pan iz `shellId`. Tabovi bez ijednog
 * validnog pana se izostavljaju.
 */
export function restoreLayout(
  saved: SavedTab[],
  shells: ShellInfo[],
): RestoredTab[] {
  const byId = new Map(shells.map((s) => [s.id, s]));
  const tabs: RestoredTab[] = [];
  for (const tab of saved) {
    const rawPanes =
      tab.panes && tab.panes.length > 0 ? tab.panes : [{ shellId: tab.shellId }];
    const panes: RestoredPane[] = [];
    for (const pane of rawPanes) {
      const shell = byId.get(pane.shellId);
      if (shell) {
        panes.push({ shell, groupId: pane.groupId });
      }
    }
    if (panes.length > 0) {
      tabs.push({
        title: tab.title,
        direction: tab.direction ?? "row",
        color: tab.color,
        panes,
      });
    }
  }
  return tabs;
}

function isSavedTab(value: unknown): value is SavedTab {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as SavedTab).shellId === "string"
  );
}
