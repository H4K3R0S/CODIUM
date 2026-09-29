// ==========          PREVIEW TABOVI (opcija B — interni prikazi)          ==========
/*
 * Jedan preview host prozor sa tabovima WEB | PC | MOBI (gore-desno). Svaki tab
 * je isti URL prikazan na drugoj širini uređaja. Ovo je „opcija B" tab-merge-a:
 * bez pravog drag-spajanja OS prozora, nego interni prikazi u jednom prozoru.
 *
 * Čista logika (bez Reacta/Tauri-ja): koje širine, kako se gradi/parsira config.
 */

export type PreviewTabKind = "web" | "pc" | "mobi";

/** Širina viewport-a po tabu (px); `null` = puna širina (responsive web). */
export const TAB_WIDTH: Record<PreviewTabKind, number | null> = {
  web: null,
  pc: 1280,
  mobi: 390,
};

export const TAB_LABEL: Record<PreviewTabKind, string> = {
  web: "WEB",
  pc: "PC",
  mobi: "MOBI",
};

const TAB_ORDER: PreviewTabKind[] = ["web", "pc", "mobi"];

export type PreviewTab = {
  kind: PreviewTabKind;
  label: string;
  url: string;
  width: number | null;
};

/** Gradi listu tabova za dati URL i skup vrsta (u fiksnom redosledu). */
export function buildTabs(url: string, kinds: PreviewTabKind[]): PreviewTab[] {
  const unique = TAB_ORDER.filter((k) => kinds.includes(k));
  return unique.map((kind) => ({
    kind,
    label: TAB_LABEL[kind],
    url,
    width: TAB_WIDTH[kind],
  }));
}

/** Parsira "web,pc,mobi" u validne vrste (nepoznato se ignoriše). */
export function parseTabKinds(raw: string | null): PreviewTabKind[] {
  if (!raw) {
    return ["web"];
  }
  const parts = raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter((s): s is PreviewTabKind => TAB_ORDER.includes(s as PreviewTabKind));
  return parts.length > 0 ? parts : ["web"];
}

/** Sledeći/prethodni tab (za prečice unutar host-a). */
export function cycleTab(
  tabs: PreviewTab[],
  activeKind: PreviewTabKind,
  direction: 1 | -1,
): PreviewTabKind {
  const index = tabs.findIndex((t) => t.kind === activeKind);
  if (index < 0) {
    return tabs[0]?.kind ?? activeKind;
  }
  const next = (index + direction + tabs.length) % tabs.length;
  return tabs[next].kind;
}
