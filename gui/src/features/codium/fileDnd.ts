// ==========          DRAG-DROP PREMEŠTANJE FAJLOVA          ==========
//
// Čista logika za prevlačenje stavki stabla u foldere. Odlučuje da li je drop
// dozvoljen; samo premeštanje ide kroz `moveFileNode` (API). Putanje su relativne
// u „/" separatoru (kao u FileNode.path).

/** Roditeljski folder date putanje („" za koren). */
export function parentDir(path: string): string {
  const parts = path.split("/");
  parts.pop();
  return parts.join("/");
}

/**
 * Da li se `srcPath` sme prevući u folder `destDir`.
 * Zabranjeno: u samog sebe, u svoje podstablo, i u trenutni roditelj (bez efekta).
 */
export function canDropInto(srcPath: string, destDir: string): boolean {
  if (srcPath === "") {
    return false; // koren se ne prevlači
  }
  if (destDir === srcPath) {
    return false; // u samog sebe
  }
  if (destDir.startsWith(`${srcPath}/`)) {
    return false; // u sopstveno podstablo
  }
  if (destDir === parentDir(srcPath)) {
    return false; // već je tu — nema pomeranja
  }
  return true;
}
