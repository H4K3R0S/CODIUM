/** Periodi koje backend prihvata. Malo izbora — svaki je jedan klik. */
export const PERIODI = [
  { id: "7d", label: "7 dana" },
  { id: "30d", label: "30 dana" },
  { id: "90d", label: "90 dana" },
];

/** Odeljci ekrana, redom kojim se čitaju. */
export const ODELJCI = [
  { id: "razvoj", label: "Razvoj" },
  { id: "isporuka", label: "Isporuka" },
  { id: "sistem", label: "Rad sistema" },
  { id: "ai", label: "AI" },
];

type Plocica = {
  key: string;
  label: string;
  /** Ključ prethodnog perioda, ako pločica ume da pokaže promenu. */
  prevKey?: string;
  format: "broj" | "procenat" | "novac";
};

/** Šta stoji u gornjem redu. Namerno malo — pločica koja se ne čita je buka. */
export const PLOCICE: Plocica[] = [
  { key: "runs", label: "Pokretanja", prevKey: "runs_prev", format: "broj" },
  { key: "success_rate", label: "Uspešnost", format: "procenat" },
  { key: "deploys", label: "Isporuka", prevKey: "deploys_prev", format: "broj" },
  { key: "rollback_rate", label: "Vraćeno unazad", format: "procenat" },
  { key: "avg_uptime", label: "Dostupnost", format: "procenat" },
  { key: "ai_calls", label: "AI pozivi", prevKey: "ai_calls_prev", format: "broj" },
  {
    key: "ai_cost_usd",
    label: "AI trošak",
    prevKey: "ai_cost_usd_prev",
    format: "novac",
  },
];

export function formatiraj(vrednost: number, format: Plocica["format"]): string {
  if (format === "procenat") {
    return `${(vrednost * 100).toFixed(1)} %`;
  }
  if (format === "novac") {
    return `$${vrednost.toFixed(2)}`;
  }
  return String(Math.round(vrednost));
}

/**
 * Promena u odnosu na prethodni period.
 *
 * Vraća `null` kada poređenja nema — a ne nulu: „bez promene" i „nema sa čim
 * da se uporedi" nisu isto, i ne smeju da izgledaju isto.
 */
export function promena(
  sada: number | undefined,
  pre: number | undefined,
): { text: string; smer: "gore" | "dole" | "isto" } | null {
  if (sada === undefined || pre === undefined) {
    return null;
  }
  const razlika = sada - pre;
  if (Math.abs(razlika) < 1e-9) {
    return { text: "bez promene", smer: "isto" };
  }
  const znak = razlika > 0 ? "+" : "−";
  const prikaz = Math.abs(razlika) < 1 ? Math.abs(razlika).toFixed(2)
                                       : String(Math.round(Math.abs(razlika)));
  return {
    text: `${znak}${prikaz} u odnosu na prethodni period`,
    smer: razlika > 0 ? "gore" : "dole",
  };
}
