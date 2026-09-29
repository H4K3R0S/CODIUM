import type { RepoStatus } from "../../../types/codium";

/**
 * Stanje repozitorijuma u tekst značaka koje lista prikazuje.
 *
 * Čist modul bez React-a i bez mreže — zato ga test pokriva direktno.
 */
export function repoBadges(status: RepoStatus): string[] {
  // Folder koji više ne postoji nema šta drugo da kaže; grana i brojevi
  // iz keša bi bili laž.
  if (status.missing) {
    return ["nema na disku"];
  }

  const znacke: string[] = [];
  if (status.branch) {
    znacke.push(status.branch);
  }
  if (status.changed_files > 0) {
    const rec = status.changed_files === 1 ? "izmena" : "izmene";
    znacke.push(`${status.changed_files} ${rec}`);
  }
  if (status.ahead > 0) {
    znacke.push(`↑${status.ahead}`);
  }
  if (status.behind > 0) {
    znacke.push(`↓${status.behind}`);
  }
  return znacke;
}
