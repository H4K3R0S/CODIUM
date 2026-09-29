import { useState } from "react";

import { fetchInfraLogs } from "../../../services/codiumApi";
import {
  canControl,
  configSummary,
  kindLabel,
  stateBadge,
} from "./serviceBadges";
import type { InfraService } from "../../../types/codium";

type Props = {
  service: InfraService;
  onControl: (
    serviceId: number,
    potez: "start" | "stop" | "restart",
  ) => Promise<void>;
  onRemove: (serviceId: number) => Promise<void>;
};

/** Koliko redova loga se traži pri otvaranju — isto koliko fazni fajl traži. */
const REDOVA = 200;

/**
 * Jedan servis: šta je, u kom je stanju, i dugmad nad njim.
 *
 * Zaustavljanje traži potvrdu, pokretanje ne: gašenje ruši ono što radi, a
 * paljenje ne ruši ništa.
 */
export default function ServiceCard({ service, onControl, onRemove }: Props) {
  const [greska, setGreska] = useState("");
  const [uToku, setUToku] = useState(false);
  const [log, setLog] = useState<string[] | null>(null);

  const znacka = stateBadge(service.status.state);
  const upravljiv = canControl(service.kind);

  async function potez(vrsta: "start" | "stop" | "restart") {
    if (vrsta !== "start") {
      const pitanje =
        vrsta === "stop"
          ? `Zaustaviti „${service.name}"?`
          : `Restartovati „${service.name}"? Ono što sada radi biće prekinuto.`;
      if (!window.confirm(pitanje)) {
        return;
      }
    }
    setUToku(true);
    try {
      await onControl(service.id, vrsta);
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    } finally {
      setUToku(false);
    }
  }

  async function ucitajLog() {
    if (log !== null) {
      setLog(null);
      return;
    }
    try {
      const odgovor = await fetchInfraLogs(service.id, REDOVA);
      setLog(odgovor.lines);
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <article className="cinf-kartica">
      <header className="cinf-kartica-glava">
        <button type="button" className="cinf-ime" onClick={() => void ucitajLog()}>
          {service.name}
        </button>
        <span className={znacka.className}>{znacka.label}</span>
        <span className="cinf-tip">{kindLabel(service.kind)}</span>
        {service.status.pid !== null && (
          <span className="cinf-pid">pid {service.status.pid}</span>
        )}
      </header>

      <p className="cinf-opis">{configSummary(service.kind, service.config)}</p>
      {service.status.detail && (
        <p className="cinf-detalj">{service.status.detail}</p>
      )}

      <div className="cinf-akcije">
        {upravljiv ? (
          <>
            <button type="button" disabled={uToku} onClick={() => void potez("start")}>
              Pokreni
            </button>
            <button type="button" disabled={uToku} onClick={() => void potez("stop")}>
              Zaustavi
            </button>
            <button
              type="button"
              disabled={uToku}
              onClick={() => void potez("restart")}
            >
              Restartuj
            </button>
          </>
        ) : (
          <span className="cinf-hint">Samo se prati — CODIUM ga nije pokrenuo.</span>
        )}
        <button
          type="button"
          className="cinf-ukloni"
          onClick={() => void onRemove(service.id)}
        >
          Ukloni
        </button>
      </div>

      {greska && <p className="cinf-greska">{greska}</p>}

      {log !== null && (
        <pre className="cinf-log">
          {log.length > 0 ? log.join("\n") : "Nema ispisa."}
        </pre>
      )}
    </article>
  );
}
