import { deployBadge, deployTime } from "./deployBadges";
import type { Deployment, DeployTarget } from "../../../types/codium";

type Props = {
  deployments: Deployment[];
  targets: DeployTarget[];
  /** Isporuka koja trenutno stoji na cilju — na nju se nema šta vraćati. */
  currentIds: number[];
  onRollback: (deploymentId: number) => Promise<void>;
};

/**
 * Istorija isporuka, najnovija prvo.
 *
 * „Vrati" stoji samo na ranijim uspešnim isporukama: neuspela nikad nije
 * stigla na cilj, a tekuća je već tamo.
 */
export default function DeployHistory({
  deployments,
  targets,
  currentIds,
  onRollback,
}: Props) {
  if (deployments.length === 0) {
    return <p className="cdep-hint">Još nema nijedne isporuke.</p>;
  }

  const imeCilja = (targetId: number) =>
    targets.find((cilj) => cilj.id === targetId)?.name ?? `cilj ${targetId}`;

  return (
    <ul className="cdep-istorija">
      {deployments.map((isporuka) => {
        const znacka = deployBadge(isporuka);
        const moze =
          isporuka.status === "success" && !currentIds.includes(isporuka.id);
        return (
          <li key={isporuka.id} className="cdep-stavka">
            <span className={znacka.className}>{znacka.label}</span>
            <span className="cdep-cilj">{imeCilja(isporuka.target_id)}</span>
            <span className="cdep-run">pokretanje #{isporuka.run_id ?? "—"}</span>
            <span className="cdep-vreme">{deployTime(isporuka)}</span>
            {isporuka.detail && (
              <span className="cdep-detalj" title={isporuka.detail}>
                {isporuka.detail}
              </span>
            )}
            {moze && (
              <button type="button" onClick={() => void onRollback(isporuka.id)}>
                Vrati
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
