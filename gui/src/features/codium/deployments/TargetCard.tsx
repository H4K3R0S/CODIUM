import { useEffect, useState } from "react";

import { fetchDeployHealth } from "../../../services/codiumApi";
import { deployBadge, deployTime, kindLabel } from "./deployBadges";
import type { Deployment, DeployHealth, DeployTarget } from "../../../types/codium";

type Props = {
  target: DeployTarget;
  /** Poslednja uspešna isporuka na ovaj cilj — ono što tamo sada stoji. */
  current: Deployment | null;
  /** Da li neka isporuka na ovaj cilj čeka ljudsku odluku (E1). */
  awaitingApproval: boolean;
  deployableRuns: number[];
  onDeploy: (targetId: number, runId: number) => Promise<void>;
  onRemove: (targetId: number) => Promise<void>;
};

/**
 * Jedan cilj isporuke: šta na njemu stoji, da li je zdrav, i dugme „Isporuči".
 *
 * Zdravlje se čita pri prikazu, ne u listi ciljeva — provera dodiruje disk
 * (ili Docker demon), pa bi jedan spor cilj zadržao celu listu.
 */
export default function TargetCard({
  target,
  current,
  awaitingApproval,
  deployableRuns,
  onDeploy,
  onRemove,
}: Props) {
  const [zdravlje, setZdravlje] = useState<DeployHealth | null>(null);
  const [izabranoPokretanje, setIzabranoPokretanje] = useState<number | "">("");
  const [greska, setGreska] = useState("");
  const [uToku, setUToku] = useState(false);

  useEffect(() => {
    let otkazano = false;
    fetchDeployHealth(target.id)
      .then((ishod) => {
        if (!otkazano) {
          setZdravlje(ishod);
        }
      })
      // Neuspela provera zdravlja ne sme da obori karticu — cilj i dalje
      // može da primi isporuku, samo mu stanje nije poznato.
      .catch(() => setZdravlje(null));
    return () => {
      otkazano = true;
    };
  }, [target.id]);

  async function isporuci() {
    if (izabranoPokretanje === "") {
      return;
    }
    setUToku(true);
    try {
      await onDeploy(target.id, Number(izabranoPokretanje));
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    } finally {
      setUToku(false);
    }
  }

  const znacka = current ? deployBadge(current) : null;

  return (
    <article className="cdep-kartica">
      <header className="cdep-kartica-glava">
        <h3>{target.name}</h3>
        <span className="cdep-tip">{kindLabel(target.kind)}</span>
        {zdravlje && (
          <span
            className={`cdep-zdravlje ${zdravlje.healthy ? "zdrav" : "bolestan"}`}
            title={zdravlje.detail}
          >
            {zdravlje.healthy ? "dostupan" : "nedostupan"}
          </span>
        )}
      </header>

      {current ? (
        <p className="cdep-trenutno">
          <span className={znacka!.className}>{znacka!.label}</span>
          <span>pokretanje #{current.run_id ?? "—"}</span>
          {current.commit_sha && (
            <span className="cdep-sha">{current.commit_sha.slice(0, 7)}</span>
          )}
          <span className="cdep-vreme">{deployTime(current)}</span>
        </p>
      ) : (
        <p className="cdep-hint">Na ovaj cilj još nije ništa isporučeno.</p>
      )}

      {awaitingApproval && (
        <p className="cdep-ceka">
          Isporuka čeka odobrenje — potvrdi je na strani Access &amp; Users.
        </p>
      )}

      <div className="cdep-akcije">
        <label className="cdep-skriveno" htmlFor={`cdep-run-${target.id}`}>
          Pokretanje za isporuku
        </label>
        <select
          id={`cdep-run-${target.id}`}
          value={izabranoPokretanje}
          onChange={(dogadjaj) =>
            setIzabranoPokretanje(
              dogadjaj.target.value === "" ? "" : Number(dogadjaj.target.value),
            )
          }
        >
          <option value="">Izaberi pokretanje…</option>
          {deployableRuns.map((runId) => (
            <option key={runId} value={runId}>
              pokretanje #{runId}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={izabranoPokretanje === "" || uToku}
          onClick={() => void isporuci()}
        >
          Isporuči
        </button>
        <button
          type="button"
          className="cdep-ukloni"
          onClick={() => void onRemove(target.id)}
        >
          Ukloni
        </button>
      </div>

      {deployableRuns.length === 0 && (
        <p className="cdep-hint">
          Nijedno pokretanje nema artefakt. Dodaj polje <code>artifact</code> u
          definiciju pipeline-a i pokreni ga.
        </p>
      )}

      {greska && <p className="cdep-greska">{greska}</p>}
    </article>
  );
}
