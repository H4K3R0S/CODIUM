import { useCallback, useEffect, useState } from "react";

import {
  createConnector,
  deleteConnector,
  fetchConnectorUsage,
  listConnectorKinds,
  listConnectors,
  testConnector,
  updateConnectorSecret,
} from "../../../services/coreApi";
import type {
  ConnectorDto,
  ConnectorKindDto,
  ConnectorProbe,
  ConnectorUsage,
} from "../../../services/coreApi";

/**
 * Konektori, vrste i njihova upotreba u CODIUM-u.
 *
 * Upotreba se učitava zajedno sa spiskom, a ne tek pred brisanje: dijalog koji
 * mora da čeka mrežu da bi rekao šta će se pokvariti stiže prekasno.
 */
export function useConnectors() {
  const [connectors, setConnectors] = useState<ConnectorDto[]>([]);
  const [kinds, setKinds] = useState<ConnectorKindDto[]>([]);
  const [usage, setUsage] = useState<Record<number, ConnectorUsage>>({});
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [probes, setProbes] = useState<Record<number, ConnectorProbe>>({});

  // `josTraje` kaže da li ekran još stoji. Odgovor koji kasni ne sme da upiše
  // ništa u komponentu koje više nema.
  const ucitaj = useCallback(async (josTraje: () => boolean) => {
    try {
      const [spisak, vrste] = await Promise.all([
        listConnectors(),
        listConnectorKinds(),
      ]);
      if (!josTraje()) {
        return;
      }
      setConnectors(spisak.connectors);
      setKinds(vrste.kinds);
      setError("");
      try {
        const upotreba = await fetchConnectorUsage();
        setUsage(Object.fromEntries(
          upotreba.usage.map((u) => [u.connector_id, u]),
        ));
      } catch {
        // Bez ove rute konektori se i dalje vide; samo upozorenje pred
        // brisanje ostaje bez sadržaja.
        setUsage({});
      }
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

  const test = useCallback(async (connectorId: number) => {
    const ishod = await testConnector(connectorId);
    setProbes((staro) => ({ ...staro, [connectorId]: ishod }));
    // Proba upisuje `status` i `last_tested_at`, pa se kartica osvežava.
    await refresh();
    return ishod;
  }, [refresh]);

  const create = useCallback(async (payload: {
    name: string;
    kind: string;
    secret: string;
    config: Record<string, string>;
  }) => {
    await createConnector(payload);
    await refresh();
  }, [refresh]);

  const replaceSecret = useCallback(async (connectorId: number,
                                           secret: string) => {
    await updateConnectorSecret(connectorId, secret);
    await refresh();
  }, [refresh]);

  const remove = useCallback(async (connectorId: number) => {
    await deleteConnector(connectorId);
    await refresh();
  }, [refresh]);

  return { connectors, kinds, usage, probes, isLoading, error, refresh, test,
           create, replaceSecret, remove };
}
