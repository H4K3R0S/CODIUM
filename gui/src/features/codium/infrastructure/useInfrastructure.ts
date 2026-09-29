import { useCallback, useEffect, useState } from "react";

import {
  createInfraService,
  deleteInfraService,
  discoverInfraServices,
  fetchInfraNodes,
  fetchInfraServices,
  restartInfraService,
  startInfraService,
  stopInfraService,
} from "../../../services/codiumApi";
import type {
  DiscoveredService,
  InfraNode,
  InfraService,
  InfraServiceCreateRequest,
} from "../../../types/codium";

/**
 * Node-ovi, registar servisa i potezi nad njima.
 *
 * Bez polling-a: stanje se osvežava na akciju i na ručno „Osveži". Servis na
 * serveru već drži keš od 5 s, pa bi tajmer ionako vraćao isto — a svaki
 * promašaj keša je podproces ili socket po servisu.
 */
export function useInfrastructure() {
  const [nodes, setNodes] = useState<InfraNode[]>([]);
  const [services, setServices] = useState<InfraService[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // `josTraje` kaže da li ekran još stoji. Odgovor koji kasni ne sme da upiše
  // ništa u komponentu koje više nema.
  const ucitaj = useCallback(async (josTraje: () => boolean) => {
    try {
      const [popisNodova, popisServisa] = await Promise.all([
        fetchInfraNodes(),
        fetchInfraServices(),
      ]);
      if (!josTraje()) {
        return;
      }
      setNodes(popisNodova.nodes);
      setServices(popisServisa.services);
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

  const createService = useCallback(
    async (zahtev: InfraServiceCreateRequest) => {
      await createInfraService(zahtev);
      await refresh();
    },
    [refresh],
  );

  const removeService = useCallback(
    async (serviceId: number) => {
      await deleteInfraService(serviceId);
      await refresh();
    },
    [refresh],
  );

  const discover = useCallback(
    async (nodeId: number): Promise<DiscoveredService[]> => {
      const odgovor = await discoverInfraServices(nodeId);
      return odgovor.found;
    },
    [],
  );

  const control = useCallback(
    async (serviceId: number, potez: "start" | "stop" | "restart") => {
      if (potez === "start") {
        await startInfraService(serviceId);
      } else if (potez === "stop") {
        await stopInfraService(serviceId);
      } else {
        await restartInfraService(serviceId);
      }
      await refresh();
    },
    [refresh],
  );

  return {
    nodes,
    services,
    isLoading,
    error,
    refresh,
    createService,
    removeService,
    discover,
    control,
  };
}
