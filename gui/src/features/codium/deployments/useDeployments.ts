import { useCallback, useEffect, useState } from "react";

import {
  createDeployTarget,
  deleteDeployTarget,
  deployRun,
  fetchDeployableRuns,
  fetchDeployTargets,
  fetchDeployments,
  rollbackDeployment,
} from "../../../services/codiumApi";
import type {
  Deployment,
  DeployTargetCreateRequest,
  DeployTarget,
} from "../../../types/codium";

/**
 * Ciljevi isporuke, istorija i pokretanja koja se uopšte mogu isporučiti.
 *
 * Bez polling-a: isporuka je sinhrona (raspakivanje ili `docker` poziv), pa se
 * ishod zna čim poziv vrati odgovor — nema stanja koje bi tajmer pratio, za
 * razliku od pipeline pokretanja.
 */
export function useDeployments() {
  const [targets, setTargets] = useState<DeployTarget[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [deployableRuns, setDeployableRuns] = useState<number[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // `josTraje` kaže da li ekran još stoji. Odgovor koji kasni ne sme da upiše
  // ništa u komponentu koje više nema.
  const ucitaj = useCallback(async (josTraje: () => boolean) => {
    try {
      const [ciljevi, istorija, pokretanja] = await Promise.all([
        fetchDeployTargets(),
        fetchDeployments(),
        fetchDeployableRuns(),
      ]);
      if (!josTraje()) {
        return;
      }
      setTargets(ciljevi.targets);
      setDeployments(istorija.deployments);
      setDeployableRuns(pokretanja.run_ids);
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

  const createTarget = useCallback(
    async (zahtev: DeployTargetCreateRequest) => {
      await createDeployTarget(zahtev);
      await refresh();
    },
    [refresh],
  );

  const removeTarget = useCallback(
    async (targetId: number) => {
      await deleteDeployTarget(targetId);
      await refresh();
    },
    [refresh],
  );

  const deploy = useCallback(
    async (targetId: number, runId: number) => {
      const isporuka = await deployRun(targetId, runId);
      await refresh();
      return isporuka;
    },
    [refresh],
  );

  const rollback = useCallback(
    async (deploymentId: number) => {
      const isporuka = await rollbackDeployment(deploymentId);
      await refresh();
      return isporuka;
    },
    [refresh],
  );

  return {
    targets,
    deployments,
    deployableRuns,
    isLoading,
    error,
    refresh,
    createTarget,
    removeTarget,
    deploy,
    rollback,
  };
}
