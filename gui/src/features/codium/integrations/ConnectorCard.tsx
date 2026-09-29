import { KeyRound, Plug, Trash2, Zap } from "lucide-react";

import type {
  ConnectorDto,
  ConnectorProbe,
  ConnectorUsage,
} from "../../../services/coreApi";

interface Props {
  connector: ConnectorDto;
  kindLabel: string;
  usage: ConnectorUsage | undefined;
  probe: ConnectorProbe | undefined;
  busy: boolean;
  onTest: () => void;
  onReplaceSecret: () => void;
  onDelete: () => void;
}

const STANJE: Record<string, string> = {
  ok: "radi",
  error: "ne radi",
  unconfigured: "nije proveren",
};

/** Vreme sa servera (UTC, bez oznake zone) u čitljiv oblik. */
function vreme(sirovo: string): string {
  if (!sirovo) {
    return "nije proveravan";
  }
  const kada = new Date(`${sirovo.replace(" ", "T")}Z`);
  return Number.isNaN(kada.getTime()) ? sirovo : kada.toLocaleString("sr-RS");
}

/**
 * Kartica jednog konektora.
 *
 * Vrednost tajne se ne prikazuje — API je i ne vraća. Vidi se samo da ključ
 * postoji, uz dugme koje ga menja.
 */
export default function ConnectorCard({ connector, kindLabel, usage, probe,
                                        busy, onTest, onReplaceSecret,
                                        onDelete }: Props) {
  const koristi = usage?.items ?? [];

  return (
    <article className={`cint-kartica ${connector.status}`}>
      <header>
        <Plug size={14} strokeWidth={2} />
        <h3>{connector.name}</h3>
        <span className={`cint-znacka ${connector.status}`}>
          {STANJE[connector.status] ?? connector.status}
        </span>
      </header>

      <p className="cint-vrsta">{kindLabel}</p>
      <p className="cint-vreme">Poslednja provera: {vreme(connector.last_tested_at)}</p>

      <p className="cint-tajna">
        <KeyRound size={12} strokeWidth={2} />
        {connector.has_secret ? "••••••••" : "nema ključ"}
        <button type="button" onClick={onReplaceSecret}>Zameni</button>
      </p>

      {connector.last_error !== "" && (
        <p className="cint-greska">{connector.last_error}</p>
      )}

      {probe !== undefined && (
        <p className={`cint-proba ${probe.ok ? "ok" : "pao"}`}>
          {probe.ok ? "Veza radi" : "Veza ne radi"}
          {probe.latency_ms !== null && ` · ${probe.latency_ms} ms`}
          {probe.message !== "" && ` · ${probe.message}`}
        </p>
      )}

      {koristi.length > 0 && (
        <p className="cint-upotreba">
          Koristi: {koristi.map((s) => `${s.label} „${s.name}“`).join(", ")}
        </p>
      )}

      <footer>
        <button type="button" disabled={busy} onClick={onTest}>
          <Zap size={13} strokeWidth={2} />
          {busy ? "Testiram…" : "Testiraj vezu"}
        </button>
        <button
          type="button"
          className="cint-brisi"
          onClick={onDelete}
          aria-label={`Obriši konektor ${connector.name}`}
        >
          <Trash2 size={13} strokeWidth={2} />
        </button>
      </footer>
    </article>
  );
}
