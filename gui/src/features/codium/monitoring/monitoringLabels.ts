import type { ServiceOverviewRow } from "../../../types/codium";

/** Metrike koje ekran nudi, sa jedinicom i čitljivim imenom. */
export const METRIKE: { metric: string; label: string; unit: string }[] = [
  { metric: "up", label: "Dostupnost", unit: "" },
  { metric: "latency_ms", label: "Odziv", unit: " ms" },
  { metric: "cpu_percent", label: "Procesor", unit: " %" },
  { metric: "memory_mb", label: "Memorija", unit: " MB" },
];

/** Periodi iz faznog fajla: 1 sat, 24 sata, 7 dana. */
export const PERIODI: { id: string; label: string; bucket: string }[] = [
  { id: "1h", label: "1 sat", bucket: "minute" },
  { id: "24h", label: "24 sata", bucket: "hour" },
  { id: "7d", label: "7 dana", bucket: "day" },
];

/**
 * Stanje pločice: iz poslednje `up` vrednosti, ne iz stanja registra.
 *
 * Merenje i registar mogu da se razilaze — registar zna šta je CODIUM
 * pokrenuo, merenje zna šta stvarno odgovara. Na ekranu merenja pobeđuje
 * merenje.
 */
export function tileState(red: ServiceOverviewRow): {
  label: string;
  className: string;
} {
  if (red.firing_alerts > 0) {
    return { label: "alarm", className: "cmon-znacka alarm" };
  }
  if (red.up === null) {
    return { label: "nije mereno", className: "cmon-znacka nemereno" };
  }
  if (red.up >= 1) {
    return { label: "radi", className: "cmon-znacka radi" };
  }
  return { label: "ne odgovara", className: "cmon-znacka pao" };
}

/** Dostupnost u procentima, ili crtica ako još nije merena. */
export function uptimeLabel(uptime: number | null): string {
  if (uptime === null) {
    return "—";
  }
  return `${(uptime * 100).toFixed(1)} %`;
}

/** Vreme sa servera (SQLite UTC, bez oznake zone) u čitljiv oblik. */
export function alertTime(sirovo: string): string {
  if (!sirovo) {
    return "";
  }
  const kada = new Date(`${sirovo.replace(" ", "T")}Z`);
  return Number.isNaN(kada.getTime()) ? sirovo : kada.toLocaleString("sr-RS");
}
