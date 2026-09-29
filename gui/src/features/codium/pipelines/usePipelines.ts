import { useCallback, useEffect, useState } from "react";

import {
  createPipeline,
  deletePipeline,
  fetchPipelines,
  runPipeline,
  updatePipeline,
} from "../../../services/codiumApi";
import type { Pipeline, PipelineRun } from "../../../types/codium";

/**
 * Lista pipeline-a jednog repozitorijuma, sa akcijama nad njom.
 *
 * Bez tajmera: lista se menja samo kad čovek nešto uradi. Pokretanja koja
 * traju prati `useRunPolling`, svako svoje.
 */
export function usePipelines(repositoryId?: number) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // `josTraje` kaže da li ekran još stoji. Odgovor koji kasni ne sme da upiše
  // ništa u komponentu koje više nema.
  const ucitaj = useCallback(async (josTraje: () => boolean) => {
    try {
      const odgovor = await fetchPipelines(repositoryId);
      if (!josTraje()) {
        return;
      }
      setPipelines(odgovor.pipelines);
      setError("");
    } catch (problem) {
      if (josTraje()) {
        setError(problem instanceof Error ? problem.message : String(problem));
      }
    } finally {
      if (josTraje()) {
        setLoading(false);
      }
    }
  }, [repositoryId]);

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
    async (forRepository: number, definition: string) => {
      await createPipeline({ repository_id: forRepository, definition });
      await refresh();
    },
    [refresh],
  );

  const update = useCallback(
    async (pipelineId: number, definition: string) => {
      await updatePipeline(pipelineId, { definition });
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (pipelineId: number) => {
      await deletePipeline(pipelineId);
      await refresh();
    },
    [refresh],
  );

  const start = useCallback(
    async (pipelineId: number): Promise<PipelineRun> => runPipeline(pipelineId),
    [],
  );

  return { pipelines, isLoading, error, refresh, create, update, remove, start };
}
