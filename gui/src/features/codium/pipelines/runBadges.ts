import type { PipelineRun } from "../../../types/codium";

// Status sa servera u srpski tekst. Nepoznat status se prikazuje kakav jeste —
// bolje sirov naziv nego prazna značka koja krije da je backend napredovao.
const TEKST: Record<string, string> = {
  queued: "u redu",
  running: "radi",
  success: "uspeh",
  failed: "pao",
  cancelled: "otkazano",
  timeout: "istekao",
};

/** Tekst i CSS klasa značke za jedno pokretanje. */
export function runBadge(run: PipelineRun): { label: string; className: string } {
  const tekst = TEKST[run.status];
  return {
    label: tekst ?? run.status,
    className: `cpipe-znacka ${tekst === undefined ? "nepoznato" : run.status}`,
  };
}

/**
 * Trajanje pokretanja u čitljivom obliku.
 *
 * Vremena sa servera su SQLite `CURRENT_TIMESTAMP` u UTC-u, bez oznake zone,
 * pa se razlika računa tako što se obema stranama doda `Z`. Bez toga bi ih
 * pregledač čitao kao lokalna vremena i razlika bi i dalje bila tačna, ali
 * samo slučajno — dok jedno od njih ne dođe iz drugog izvora.
 */
export function runDuration(run: PipelineRun): string {
  if (!run.started_at) {
    return "";
  }
  if (!run.finished_at) {
    return "u toku";
  }

  const pocetak = Date.parse(`${run.started_at.replace(" ", "T")}Z`);
  const kraj = Date.parse(`${run.finished_at.replace(" ", "T")}Z`);
  if (Number.isNaN(pocetak) || Number.isNaN(kraj)) {
    return "";
  }

  const sekundi = Math.max(0, Math.round((kraj - pocetak) / 1000));
  if (sekundi < 60) {
    return `${sekundi} s`;
  }
  return `${Math.floor(sekundi / 60)} min ${sekundi % 60} s`;
}
