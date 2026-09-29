import { useCallback, useEffect, useState } from "react";

import {
  collectMetricsNow,
  fetchAlerts,
  fetchMonitoringOverview,
} from "../../../services/codiumApi";
import type { AlertRow, ServiceOverviewRow } from "../../../types/codium";

/**
 * Zid pločica i traka alarma.
 *
 * Bez polling-a u pregledaču: sakupljač na serveru meri na 30 s, pa bi tajmer
 * u GUI-ju samo ponavljao isti odgovor. „Izmeri sada" postoji za slučaj kad
 * čovek ne želi da čeka sledeći krug.
 */
export function useMonitoring() {
  const [services, setServices] = useState<ServiceOverviewRow[]>([]);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // `josTraje` kaže da li ekran još stoji. Odgovor koji kasni ne sme da upiše
  // ništa u komponentu koje više nema — bez toga svaki brz odlazak sa strane
  // ostavlja upis u prazno.
  const ucitaj = useCallback(async (josTraje: () => boolean) => {
    try {
      const [pregled, upaljeni] = await Promise.all([
        fetchMonitoringOverview(),
        fetchAlerts("firing"),
      ]);
      if (!josTraje()) {
        return;
      }
      setServices(pregled.services);
      setAlerts(upaljeni.alerts);
      setError("");
    } catch (greska) {
      if (josTraje()) {
        setError(greska instanceof Error ? greska.message : String(greska));
      }
    } finally {
      if (josTraje()) {
        setLoading(false);
      }
    }
  }, []);

  /** Ručno osvežavanje: ekran je tu, pa je odgovor uvek relevantan. */
  const refresh = useCallback(async () => {
    setLoading(true);
    await ucitaj(() => true);
  }, [ucitaj]);

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await ucitaj(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [ucitaj]);

  const collectNow = useCallback(async () => {
    await collectMetricsNow();
    await refresh();
  }, [refresh]);

  return { services, alerts, isLoading, error, refresh, collectNow };
}
