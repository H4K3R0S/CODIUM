import { useCallback, useEffect, useState } from "react";

import {
  deleteRepository,
  fetchRepoSuggestions,
  fetchRepositories,
  registerRepository,
  syncRepository,
} from "../../../services/codiumApi";
import type {
  RepositoryWithStatus,
  RepoSuggestion,
} from "../../../types/codium";

/**
 * Registar repozitorijuma i ponuda iz projekata, sa osvežavanjem.
 *
 * Bez polling-a: lista se osvežava na akciju korisnika. Stanje ionako ima
 * keš od 10 s u servisu, pa bi tajmer samo trošio procese.
 */
type Opcije = {
  // `GitPanel` prikazuje samo repozitorijum aktivnog projekta i nikad ne
  // čita `suggestions` — svaki mount i svaka akcija bi inače pokrenuli
  // `provider.detect()` za sve projekte uzalud.
  skipSuggestions?: boolean;
};

export function useRepositories(projectId?: number, opcije?: Opcije) {
  const [repositories, setRepositories] = useState<RepositoryWithStatus[]>([]);
  const [suggestions, setSuggestions] = useState<RepoSuggestion[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const preskociPonude = opcije?.skipSuggestions ?? false;

  // `josTraje` kaže da li ekran još stoji. Odgovor koji kasni ne sme da upiše
  // ništa u komponentu koje više nema.
  const ucitaj = useCallback(async (josTraje: () => boolean) => {
    try {
      const [lista, ponude] = await Promise.all([
        fetchRepositories(projectId),
        preskociPonude
          ? Promise.resolve({ suggestions: [] as RepoSuggestion[] })
          : fetchRepoSuggestions(),
      ]);
      if (!josTraje()) {
        return;
      }
      setRepositories(lista.repositories);
      setSuggestions(ponude.suggestions);
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
  }, [projectId, preskociPonude]);

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

  const register = useCallback(
    async (localPath: string, forProject?: number | null) => {
      await registerRepository({ local_path: localPath, project_id: forProject });
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (repoId: number) => {
      await deleteRepository(repoId);
      await refresh();
    },
    [refresh],
  );

  const sync = useCallback(
    async (repoId: number) => {
      await syncRepository(repoId);
      await refresh();
    },
    [refresh],
  );

  return { repositories, suggestions, isLoading, error, refresh, register, remove, sync };
}
