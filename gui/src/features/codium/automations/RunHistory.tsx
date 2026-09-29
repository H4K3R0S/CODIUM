import type { AutomationRule, AutomationRunRow } from "../../../types/codium";
import { runBadge, vreme } from "./automationLabels";

interface Props {
  runs: AutomationRunRow[];
  rules: AutomationRule[];
}

/**
 * Istorija okidanja.
 *
 * `detail` se prikazuje uvek, ne samo kod greške: kod preskočenog piše zašto
 * uslov nije prošao, kod prekoračenja zašto je pravilo ugašeno. Bez toga bi
 * čovek video „preskočeno“ i ne bi znao da li pravilo radi ili je pokvareno.
 */
export default function RunHistory({ runs, rules }: Props) {
  if (runs.length === 0) {
    return <p className="caut-prazno">Nijedno pravilo se još nije upalilo.</p>;
  }

  const imena = new Map(rules.map((p) => [p.id, p.name]));

  return (
    <ul className="caut-istorija">
      {runs.map((run) => {
        const znacka = runBadge(run);
        return (
          <li key={run.id}>
            <span className={znacka.className}>{znacka.label}</span>
            <span className="caut-istorija-ime">
              {imena.get(run.rule_id) ?? `pravilo ${run.rule_id}`}
            </span>
            <span className="caut-istorija-razlog">{run.detail}</span>
            <span className="caut-istorija-vreme">{vreme(run.at)}</span>
          </li>
        );
      })}
    </ul>
  );
}
