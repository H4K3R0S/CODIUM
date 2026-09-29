// ==========          PRIKAZ STAVKE AKTIVNOSTI          ==========
// Čist modul bez ijednog uvoza — prevod podataka sa servera u ono što se vidi.

/** Ton reda: običan, greška, ili odbijeno pravilom. */
export type ActivityTone = "ok" | "error" | "blocked";

/**
 * Odbijanje nije kvar nego sistem koji radi svoj posao, pa nosi svoj ton —
 * inače bi na ekranu izgledalo isto kao pad poziva.
 */
export function activityTone(item: { outcome: string; kind: string }): ActivityTone {
  if (item.outcome === "blocked") {
    return "blocked";
  }
  if (item.outcome === "error") {
    return "error";
  }
  return "ok";
}

const MINUT = 60_000;
const SAT = 60 * MINUT;
const DAN = 24 * SAT;

/**
 * „pre 15 min“ umesto pune vremenske oznake.
 *
 * Kolona `at` je `CURRENT_TIMESTAMP`, dakle UTC bez oznake zone; bez dodatog
 * „Z“ bi je pregledač čitao kao lokalno vreme i svaki red bi izgledao pomeren
 * za onoliko sati koliko zona odstupa.
 */
export function relativeTime(at: string, now: Date = new Date()): string {
  const normalized = at.includes("T") ? at : at.replace(" ", "T");
  const utc = /[Zz]|[+-]\d{2}:?\d{2}$/.test(normalized)
    ? normalized
    : `${normalized}Z`;

  const trenutak = Date.parse(utc);
  if (Number.isNaN(trenutak)) {
    return "";
  }

  const razlika = now.getTime() - trenutak;
  if (razlika < MINUT) {
    return "upravo";
  }
  if (razlika < SAT) {
    return `pre ${Math.floor(razlika / MINUT)} min`;
  }
  if (razlika < DAN) {
    return `pre ${Math.floor(razlika / SAT)} h`;
  }
  return `pre ${Math.floor(razlika / DAN)} d`;
}
