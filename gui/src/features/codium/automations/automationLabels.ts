import type { AutomationRunRow } from "../../../types/codium";

// Ishod okidanja u srpski tekst. `skipped` i `rate_limited` nisu isto: prvo
// znači da uslov nije prošao (pravilo radi kako treba), drugo da je pravilo
// ugašeno jer se otelo.
const ISHOD: Record<string, string> = {
  done: "izvršeno",
  skipped: "preskočeno",
  waiting_approval: "čeka odobrenje",
  failed: "greška",
  rate_limited: "ugašeno zbog učestalosti",
};

export function runBadge(
  run: AutomationRunRow,
): { label: string; className: string } {
  const tekst = ISHOD[run.status];
  return {
    label: tekst ?? run.status,
    className: `caut-znacka ${tekst === undefined ? "nepoznato" : run.status}`,
  };
}

/** Čitljivo ime događaja; nepoznato ostaje kakvo jeste. */
const DOGADJAJ: Record<string, string> = {
  "repo.commit.detected": "nov commit",
  "repo.branch.changed": "promena grane",
  "pipeline.run.finished": "pipeline završio",
  "deployment.finished": "isporuka završila",
  "service.state.changed": "servis promenio stanje",
  "alert.fired": "alarm upaljen",
  "alert.resolved": "alarm razrešen",
  "schedule.tick": "po rasporedu",
};

export function eventLabel(event: string): string {
  return DOGADJAJ[event] ?? event;
}

/** Vreme sa servera (SQLite UTC, bez oznake zone) u čitljiv oblik. */
export function vreme(sirovo: string | null): string {
  if (!sirovo) {
    return "još se nije palilo";
  }
  const kada = new Date(`${sirovo.replace(" ", "T")}Z`);
  return Number.isNaN(kada.getTime()) ? sirovo : kada.toLocaleString("sr-RS");
}
