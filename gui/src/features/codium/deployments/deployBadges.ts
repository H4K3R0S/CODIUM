import type { Deployment, DeployKind } from "../../../types/codium";

// Status sa servera u srpski tekst. Nepoznat status se prikazuje kakav jeste —
// bolje sirov naziv nego prazna značka koja krije da je backend napredovao.
const TEKST: Record<string, string> = {
  pending: "čeka odobrenje",
  running: "isporučuje se",
  success: "uspeh",
  failed: "pala",
  rolled_back: "vraćena",
};

/** Tekst i CSS klasa značke za jednu isporuku. */
export function deployBadge(
  deployment: Deployment,
): { label: string; className: string } {
  const tekst = TEKST[deployment.status];
  return {
    label: tekst ?? deployment.status,
    className: `cdep-znacka ${tekst === undefined ? "nepoznato" : deployment.status}`,
  };
}

// Tip cilja u čitljiv naziv. `ssh_host` postoji u backend-u bez provajdera —
// prikazuje se, ali ekran ne nudi da se takav cilj napravi.
const TIP: Record<string, string> = {
  local_folder: "lokalni folder",
  local_docker: "lokalni Docker",
  ssh_host: "udaljeni host",
};

export function kindLabel(kind: DeployKind | string): string {
  return TIP[kind] ?? kind;
}

/**
 * Vreme isporuke u čitljivom obliku.
 *
 * Vremena sa servera su SQLite `CURRENT_TIMESTAMP` u UTC-u, bez oznake zone,
 * pa se pri čitanju dodaje `Z` — isti razlog kao u `runBadges.runDuration`.
 */
export function deployTime(deployment: Deployment): string {
  const sirovo = deployment.finished_at ?? deployment.created_at;
  if (!sirovo) {
    return "";
  }
  const kada = new Date(`${sirovo.replace(" ", "T")}Z`);
  return Number.isNaN(kada.getTime()) ? "" : kada.toLocaleString("sr-RS");
}
