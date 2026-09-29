// ==========          GRUPE PANOVA TERMINALA          ==========
//
// Čista logika (bez React-a) za spajanje panova u obojene grupe. Prevlačenjem se
// jedan pan „ubaci" u grupu drugog; grupisani panovi dobijaju istu boju ivice, pa
// se vizuelno razlikuju kao zajednička celina (kao tab-grupe).

/** Bilo koji objekat sa id-jem i opcionom grupom. */
export type Groupable = { id: string; groupId?: string };

// Paleta boja grupa — po grupi se deterministički bira (hash id-ja).
const GROUP_PALETTE = [
  "#4a9ce6",
  "#3fb58b",
  "#d9a441",
  "#c05bd6",
  "#e0693b",
  "#5fae63",
  "#d64b8a",
  "#5c6ffb",
];

function hashIndex(text: string, modulo: number): number {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return hash % modulo;
}

/** Boja ivice grupe (stabilna po id-ju grupe). */
export function groupColor(groupId: string): string {
  return GROUP_PALETTE[hashIndex(groupId, GROUP_PALETTE.length)];
}

/**
 * Spoji pan `srcId` u grupu pana `targetId`: dodeli mu ciljnu grupu (ako cilj još
 * nije grupisan, i cilj i izvor dobijaju novu grupu `freshId`) i premesti izvor na
 * KRAJ te grupe (tako postaje vidljiv pan stacka). Vraća nov niz (bez mutacije).
 */
export function mergePanes<T extends Groupable>(
  panes: T[],
  srcId: string,
  targetId: string,
  freshId: string,
): T[] {
  if (srcId === targetId) {
    return panes;
  }
  const target = panes.find((p) => p.id === targetId);
  const src = panes.find((p) => p.id === srcId);
  if (!target || !src) {
    return panes;
  }
  const groupId = target.groupId ?? freshId;

  // Dodeli grupu izvoru (i cilju ako je bio bez grupe).
  const relabeled = panes.map((p) => {
    if (p.id === srcId) {
      return { ...p, groupId };
    }
    if (p.id === targetId && target.groupId === undefined) {
      return { ...p, groupId };
    }
    return p;
  });

  // Ubaci izvor na kraj neprekidnog run-a te grupe (postaje vidljiv u stacku).
  const without = relabeled.filter((p) => p.id !== srcId);
  const moved = relabeled.find((p) => p.id === srcId)!;
  let insertAt = without.findIndex((p) => p.id === targetId);
  for (let i = insertAt + 1; i < without.length; i += 1) {
    if (without[i].groupId === groupId) {
      insertAt = i;
    } else {
      break;
    }
  }
  without.splice(insertAt + 1, 0, moved);
  return without;
}

/** Neprekidan „run" panova iste grupe (ili pojedinačan pan bez grupe). */
export type PaneSegment<T> = { groupId?: string; panes: T[] };

/**
 * Grupiše panove u segmente: uzastopni panovi iste (definisane) grupe čine jedan
 * segment; panovi bez grupe su svaki svoj segment. Segment sa više panova se u
 * UI-ju prikazuje kao stack (tabovi), a segmenti se ređaju jedan uz drugi (split).
 */
export function segmentByGroup<T extends Groupable>(panes: T[]): PaneSegment<T>[] {
  const segments: PaneSegment<T>[] = [];
  for (const pane of panes) {
    const last = segments[segments.length - 1];
    if (pane.groupId !== undefined && last && last.groupId === pane.groupId) {
      last.panes.push(pane);
    } else {
      segments.push({ groupId: pane.groupId, panes: [pane] });
    }
  }
  return segments;
}

/**
 * Premesti pan na kraj svog grupnog run-a (klik na tab u stacku ga čini vidljivim).
 * Nema efekta ako pan nije grupisan.
 */
export function bringPaneToGroupEnd<T extends Groupable>(
  panes: T[],
  paneId: string,
): T[] {
  const pane = panes.find((p) => p.id === paneId);
  if (!pane || pane.groupId === undefined) {
    return panes;
  }
  const without = panes.filter((p) => p.id !== paneId);
  let insertAt = -1;
  for (let i = 0; i < without.length; i += 1) {
    if (without[i].groupId === pane.groupId) {
      insertAt = i;
    }
  }
  if (insertAt === -1) {
    return panes;
  }
  without.splice(insertAt + 1, 0, pane);
  return without;
}

/** Izbaci pan iz njegove grupe (raspusti vezu). */
export function ungroupPane<T extends Groupable>(panes: T[], id: string): T[] {
  return panes.map((p) => (p.id === id ? stripGroup(p) : p));
}

function stripGroup<T extends Groupable>(pane: T): T {
  const { groupId: _groupId, ...rest } = pane;
  return rest as T;
}

/**
 * Ukloni grupe koje su ostale sa samo jednim panom (nakon zatvaranja/premeštanja) —
 * grupa od jednog nema smisla, pa se boja ivice sklanja.
 */
export function pruneSingletonGroups<T extends Groupable>(panes: T[]): T[] {
  const counts = new Map<string, number>();
  for (const p of panes) {
    if (p.groupId) {
      counts.set(p.groupId, (counts.get(p.groupId) ?? 0) + 1);
    }
  }
  return panes.map((p) =>
    p.groupId && counts.get(p.groupId) === 1 ? stripGroup(p) : p,
  );
}
