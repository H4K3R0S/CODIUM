import { useCallback, useEffect, useState } from "react";

import {
  fetchAnalyticsSummary,
  fetchReport,
  fetchReportList,
} from "../../../services/codiumApi";
import type {
  AnalyticsReport,
  ReportSpec,
} from "../../../types/codium";

/**
 * Zbirna tabla i svi izveštaji za izabrani period.
 *
 * Izveštaji se dovlače odjednom pri promeni perioda: backend ih kešira 60 s,
 * pa je jedan nalet jeftiniji od dovlačenja po odeljku dok čovek skroluje.
 */
export function useAnalytics(period: string) {
  const [specs, setSpecs] = useState<ReportSpec[]>([]);
  const [reports, setReports] = useState<Record<string, AnalyticsReport>>({});
  const [totals, setTotals] = useState<Record<string, number>>({});
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // `josTraje` kaže da li ekran još stoji. Odgovor koji kasni ne sme da upiše
  // ništa u komponentu koje više nema.
  const ucitaj = useCallback(async (josTraje: () => boolean) => {
    try {
      const [spisak, zbir] = await Promise.all([
        fetchReportList(),
        fetchAnalyticsSummary(period),
      ]);
      if (!josTraje()) {
        return;
      }
      setSpecs(spisak.reports);
      setTotals(zbir.totals);

      const svi = await Promise.all(
        spisak.reports.map((spec) => fetchReport(spec.name, period)),
      );
      const mapa: Record<string, AnalyticsReport> = {};
      for (const izvestaj of svi) {
        mapa[izvestaj.name] = izvestaj;
      }
      setReports(mapa);
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
  }, [period]);

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

  return { specs, reports, totals, isLoading, error, refresh };
}
