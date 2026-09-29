// ==========          ANALYTICS          ==========
// Odgovara na pitanja koja se ne vide iz pojedinacnog ekrana: gde odlazi vreme,
// sta se najcesce kvari, koliko kosta AI, da li se stanje popravlja.
//
// Ova strana ne pravi nijedan nov podatak — cita ono sto E2, E3, E4, E6 i AI
// blok vec upisuju.
import { useState } from "react";
import { BarChart3, Download, RefreshCw } from "lucide-react";

import ReportChart from "../features/codium/analytics/ReportChart";
import {
  ODELJCI,
  PERIODI,
  PLOCICE,
  formatiraj,
  promena,
} from "../features/codium/analytics/analyticsLabels";
import { useAnalytics } from "../features/codium/analytics/useAnalytics";
import { reportExportUrl } from "../services/codiumApi";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import "../styles/codium-analytics.css";

export default function CodiumAnalytics() {
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  // Jedan prekidac perioda, na vrhu, vazi za CELU stranu — dva bi znacila da
  // dva grafikona pored sebe mogu da pokazuju razlicite raspone.
  const [period, setPeriod] = useState("30d");
  const { specs, reports, totals, isLoading, error, refresh } =
    useAnalytics(period);

  return (
    <div
      className={`cana-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cana-head">
        <p className="cana-eyebrow">CODIUM · Kod</p>
        <h1>Analytics</h1>
        <p className="cana-sub">
          Gde odlazi vreme, šta se najčešće kvari i koliko košta AI — spojeno iz
          onoga što ostali ekrani već beleže.
        </p>
        <div className="cana-alat">
          <div className="cana-tabovi" role="group" aria-label="Period">
            {PERIODI.map((stavka) => (
              <button
                key={stavka.id}
                type="button"
                className={stavka.id === period ? "izabran" : ""}
                onClick={() => setPeriod(stavka.id)}
              >
                {stavka.label}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => void refresh()}>
            <RefreshCw size={13} strokeWidth={2} />
            Osveži
          </button>
          {isLoading && <span className="cana-hint">Učitavanje…</span>}
        </div>
      </header>

      {error && <p className="cana-error">{error}</p>}

      {/* Zbirni brojevi za period, sa promenom u odnosu na prethodni. */}
      <section className="cana-plocice" aria-label="Ključni brojevi">
        {PLOCICE.map((plocica) => {
          const vrednost = totals[plocica.key];
          const razlika = plocica.prevKey
            ? promena(vrednost, totals[plocica.prevKey])
            : null;
          return (
            <article className="cana-plocica" key={plocica.key}>
              <p className="cana-plocica-ime">{plocica.label}</p>
              <p className="cana-plocica-broj">
                {vrednost === undefined
                  ? "—"
                  : formatiraj(vrednost, plocica.format)}
              </p>
              {razlika && (
                <p className={`cana-promena ${razlika.smer}`}>{razlika.text}</p>
              )}
            </article>
          );
        })}
      </section>

      <div className="cana-grid smart-stack">
        {ODELJCI.map((odeljak) => {
          const uOdeljku = specs.filter((s) => s.section === odeljak.id);
          if (uOdeljku.length === 0) {
            return null;
          }
          return (
            <SmartFrame
              icon={<BarChart3 size={15} strokeWidth={1.8} />}
              id={`odeljak-${odeljak.id}`}
              key={odeljak.id}
              layout={layout}
              title={odeljak.label}
            >
              <section className="cana-panel">
                <h2>{odeljak.label}</h2>
                {uOdeljku.map((spec) => (
                  <article className="cana-izvestaj" key={spec.name}>
                    <header className="cana-izvestaj-glava">
                      <h3>{spec.label}</h3>
                      <a
                        className="cana-izvoz"
                        href={reportExportUrl(spec.name, period)}
                        title="Preuzmi kao CSV"
                      >
                        <Download size={13} strokeWidth={2} />
                        CSV
                      </a>
                    </header>
                    <p className="cana-opis">{spec.description}</p>
                    {reports[spec.name] ? (
                      <ReportChart report={reports[spec.name]} />
                    ) : (
                      <p className="cana-hint">Učitavanje…</p>
                    )}
                  </article>
                ))}
              </section>
            </SmartFrame>
          );
        })}
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
