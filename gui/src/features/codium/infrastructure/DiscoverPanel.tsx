import { useState } from "react";

import { kindLabel, stateBadge } from "./serviceBadges";
import type {
  DiscoveredService,
  InfraServiceCreateRequest,
} from "../../../types/codium";

type Props = {
  nodeId: number;
  onDiscover: (nodeId: number) => Promise<DiscoveredService[]>;
  onAdd: (zahtev: InfraServiceCreateRequest) => Promise<void>;
};

/**
 * „Pronađi servise" — popis zatečenog, sa čekiranjem šta ulazi u registar.
 *
 * Ništa se ne upisuje samo: mašina puna tuđih kontejnera ne sme sama sebe da
 * upiše. Ono što je već u registru dolazi odčekirano i ugašeno.
 */
export default function DiscoverPanel({ nodeId, onDiscover, onAdd }: Props) {
  const [nadjeni, setNadjeni] = useState<DiscoveredService[] | null>(null);
  const [izabrani, setIzabrani] = useState<Set<string>>(new Set());
  const [greska, setGreska] = useState("");
  const [uToku, setUToku] = useState(false);

  async function pronadji() {
    setUToku(true);
    try {
      const lista = await onDiscover(nodeId);
      setNadjeni(lista);
      setIzabrani(new Set());
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    } finally {
      setUToku(false);
    }
  }

  function prebaci(ime: string) {
    setIzabrani((prethodni) => {
      const noviSkup = new Set(prethodni);
      if (noviSkup.has(ime)) {
        noviSkup.delete(ime);
      } else {
        noviSkup.add(ime);
      }
      return noviSkup;
    });
  }

  async function upisi() {
    if (nadjeni === null) {
      return;
    }
    setUToku(true);
    try {
      for (const predlog of nadjeni.filter((n) => izabrani.has(n.name))) {
        await onAdd({
          node_id: nodeId,
          name: predlog.name,
          kind: predlog.kind,
          config: predlog.config,
        });
      }
      setNadjeni(null);
      setIzabrani(new Set());
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    } finally {
      setUToku(false);
    }
  }

  return (
    <div className="cinf-pronadji">
      <button type="button" disabled={uToku} onClick={() => void pronadji()}>
        Pronađi servise
      </button>

      {greska && <p className="cinf-greska">{greska}</p>}

      {nadjeni !== null && nadjeni.length === 0 && (
        <p className="cinf-hint">Ništa nije nađeno na ovom node-u.</p>
      )}

      {nadjeni !== null && nadjeni.length > 0 && (
        <>
          <ul className="cinf-predlozi">
            {nadjeni.map((predlog) => {
              const znacka = stateBadge(predlog.state);
              return (
                <li key={`${predlog.kind}:${predlog.name}`}>
                  <label>
                    <input
                      type="checkbox"
                      disabled={predlog.already_registered}
                      checked={izabrani.has(predlog.name)}
                      onChange={() => prebaci(predlog.name)}
                    />
                    <span className="cinf-predlog-ime">{predlog.name}</span>
                    <span className="cinf-tip">{kindLabel(predlog.kind)}</span>
                    <span className={znacka.className}>{znacka.label}</span>
                    {predlog.already_registered && (
                      <span className="cinf-hint">već u registru</span>
                    )}
                  </label>
                </li>
              );
            })}
          </ul>
          <button
            type="button"
            disabled={izabrani.size === 0 || uToku}
            onClick={() => void upisi()}
          >
            Upiši izabrane ({izabrani.size})
          </button>
        </>
      )}
    </div>
  );
}
