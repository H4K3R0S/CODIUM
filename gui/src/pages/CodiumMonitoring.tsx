// ==========          MONITORING          ==========
// Infrastructure pokazuje trenutak; ovde se vidi ponasanje kroz vreme.
// Traka alarma stoji na vrhu jer je jedina stvar zbog koje covek otvara ovaj
// ekran kad NESTO nije u redu.
import { useEffect, useState } from "react";
import { Activity, RefreshCw, TriangleAlert } from "lucide-react";

import AlertStrip from "../features/codium/monitoring/AlertStrip";
import ServiceDetail from "../features/codium/monitoring/ServiceDetail";
import ServiceTile from "../features/codium/monitoring/ServiceTile";
import { useMonitoring } from "../features/codium/monitoring/useMonitoring";
import { fetchAlertRules } from "../services/codiumApi";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import "../styles/codium-monitoring.css";

export default function CodiumMonitoring() {
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const { services, alerts, isLoading, error, refresh, collectNow } =
    useMonitoring();
  const [izabran, setIzabran] = useState<number | null>(null);
  // Alarm nosi `rule_id`, a covek cita ime servisa — pravila su jedini most
  // izmedju to dvoje.
  const [pravilaPoServisu, setPravilaPoServisu] = useState<
    Record<number, number>
  >({});
  const [greskaAkcije, setGreskaAkcije] = useState("");

  useEffect(() => {
    fetchAlertRules()
      .then((odgovor) => {
        const mapa: Record<number, number> = {};
        for (const pravilo of odgovor.rules) {
          if (pravilo.service_id !== null) {
            mapa[pravilo.id] = pravilo.service_id;
          }
        }
        setPravilaPoServisu(mapa);
      })
      // Bez mape se alarm i dalje vidi, samo pod brojem pravila.
      .catch(() => setPravilaPoServisu({}));
  }, [alerts.length]);

  const izabranRed =
    services.find((s) => s.service_id === izabran) ?? null;

  async function izmeriSada() {
    try {
      await collectNow();
      setGreskaAkcije("");
    } catch (problem) {
      setGreskaAkcije(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <div
      className={`cmon-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cmon-head">
        <p className="cmon-eyebrow">CODIUM · Kod</p>
        <h1>Monitoring</h1>
        <p className="cmon-sub">
          Servisi se mere na 30 sekundi. Ovde se vidi kako su se ponašali, ne
          samo kako stoje sada.
        </p>
        <div className="cmon-alat">
          <button type="button" onClick={() => void refresh()}>
            <RefreshCw size={13} strokeWidth={2} />
            Osveži
          </button>
          <button type="button" onClick={() => void izmeriSada()}>
            <Activity size={13} strokeWidth={2} />
            Izmeri sada
          </button>
          {isLoading && <span className="cmon-hint">Učitavanje…</span>}
        </div>
      </header>

      {error && <p className="cmon-error">{error}</p>}
      {greskaAkcije && <p className="cmon-error">{greskaAkcije}</p>}

      <div className="cmon-grid smart-stack">
        <SmartFrame
          icon={<TriangleAlert size={15} strokeWidth={1.8} />}
          id="alarmi"
          layout={layout}
          title="Aktivni alarmi"
        >
          <section className="cmon-panel">
            <h2>Aktivni alarmi</h2>
            <AlertStrip
              alerts={alerts}
              services={services}
              ruleServiceIds={pravilaPoServisu}
            />
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<Activity size={15} strokeWidth={1.8} />}
          id="servisi"
          layout={layout}
          title="Servisi"
        >
          <section className="cmon-panel">
            <h2>Servisi</h2>
            {services.length === 0 ? (
              <p className="cmon-hint">
                Nema servisa za merenje. Upiši ih na strani Infrastructure.
              </p>
            ) : (
              <div className="cmon-zid">
                {services.map((red) => (
                  <ServiceTile
                    key={red.service_id}
                    row={red}
                    selected={red.service_id === izabran}
                    onSelect={(serviceId) =>
                      setIzabran(serviceId === izabran ? null : serviceId)
                    }
                  />
                ))}
              </div>
            )}
          </section>
        </SmartFrame>

        {izabranRed !== null && (
          <SmartFrame
            icon={<Activity size={15} strokeWidth={1.8} />}
            id="detalj"
            layout={layout}
            title={izabranRed.name}
          >
            <section className="cmon-panel">
              <h2>{izabranRed.name}</h2>
              <ServiceDetail row={izabranRed} />
            </section>
          </SmartFrame>
        )}
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
