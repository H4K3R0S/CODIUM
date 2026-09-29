import type { InfraServiceKind, InfraServiceState } from "../../../types/codium";

// Stanje sa servera u srpski tekst. Nepoznato stanje se prikazuje kakvo jeste —
// bolje sirov naziv nego prazna značka koja krije da je backend napredovao.
const STANJE: Record<string, string> = {
  running: "radi",
  stopped: "ugašen",
  unknown: "nepoznato",
  error: "greška",
};

export function stateBadge(
  state: InfraServiceState | string,
): { label: string; className: string } {
  const tekst = STANJE[state];
  return {
    label: tekst ?? state,
    className: `cinf-znacka ${tekst === undefined ? "unknown" : state}`,
  };
}

const TIP: Record<string, string> = {
  local_process: "proces",
  local_docker: "Docker",
  port_probe: "port",
};

export function kindLabel(kind: InfraServiceKind | string): string {
  return TIP[kind] ?? kind;
}

/**
 * Kratak opis servisa iz njegove konfiguracije.
 *
 * Svaki tip nosi drugo polje, a kartica ima jedan red za to — bez ovoga bi
 * ekran morao da zna oblik konfiguracije svakog provajdera.
 */
export function configSummary(
  kind: InfraServiceKind | string,
  config: Record<string, string>,
): string {
  if (kind === "local_docker") {
    return config.container ?? "";
  }
  if (kind === "port_probe") {
    const host = config.host ?? "127.0.0.1";
    return config.port ? `${host}:${config.port}` : "";
  }
  const port = config.port ? ` · port ${config.port}` : "";
  return `${config.command ?? ""}${port}`;
}

/** Da li ovaj tip uopšte ume da se pokreće iz CODIUM-a. */
export function canControl(kind: InfraServiceKind | string): boolean {
  return kind !== "port_probe";
}
