import { useCallback, useEffect, useState } from "react";

import {
  createAutomationRule,
  deleteAutomationRule,
  fetchAutomationActions,
  fetchAutomationEvents,
  fetchAutomationRules,
  fetchAutomationRuns,
  updateAutomationRule,
} from "../../../services/codiumApi";
import type {
  AutomationActionSpec,
  AutomationEventSpec,
  AutomationRule,
  AutomationRuleCreateRequest,
  AutomationRunRow,
} from "../../../types/codium";

/**
 * Pravila, dostupni događaji i akcije, i istorija okidanja.
 *
 * Događaji i akcije dolaze sa servera, ne iz konstante u GUI-ju: spisak živi
 * na jednom mestu, pa nova akcija u backend-u odmah stoji u uređivaču.
 */
export function useAutomations() {
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [events, setEvents] = useState<AutomationEventSpec[]>([]);
  const [actions, setActions] = useState<AutomationActionSpec[]>([]);
  const [runs, setRuns] = useState<AutomationRunRow[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // `josTraje` kaže da li ekran još stoji. Odgovor koji kasni ne sme da upiše
  // ništa u komponentu koje više nema.
  const ucitaj = useCallback(async (josTraje: () => boolean) => {
    try {
      const [pravila, dogadjaji, akcije, okidanja] = await Promise.all([
        fetchAutomationRules(),
        fetchAutomationEvents(),
        fetchAutomationActions(),
        fetchAutomationRuns(undefined, 30),
      ]);
      if (!josTraje()) {
        return;
      }
      setRules(pravila.rules);
      setEvents(dogadjaji.events);
      setActions(akcije.actions);
      setRuns(okidanja.runs);
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

  const create = useCallback(
    async (zahtev: AutomationRuleCreateRequest) => {
      await createAutomationRule(zahtev);
      await refresh();
    },
    [refresh],
  );

  const toggle = useCallback(
    async (rule: AutomationRule) => {
      await updateAutomationRule(rule.id, {
        name: rule.name,
        condition_expr: rule.condition_expr,
        actions: rule.actions,
        enabled: !rule.enabled,
        rate_limit_n: rule.rate_limit_n,
        rate_limit_seconds: rule.rate_limit_seconds,
      });
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (ruleId: number) => {
      await deleteAutomationRule(ruleId);
      await refresh();
    },
    [refresh],
  );

  return { rules, events, actions, runs, isLoading, error, refresh, create,
           toggle, remove };
}
