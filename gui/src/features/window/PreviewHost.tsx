import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";

import { registerBareView } from "./bareViews";
import {
  buildTabs,
  parseTabKinds,
  type PreviewTabKind,
} from "./previewTabs";
import "./preview-host.css";


// ==========          PREVIEW TABS (WEB | PC | MOBI)          ==========

/**
 * Prikaz preview-a sa tabovima: isti URL na različitim širinama uređaja, tabovi
 * gore-desno, iframe ka dev serveru (CSP dozvoljava localhost). Prezentaciono —
 * koristi ga i bare prozor (PreviewHost) i dockable „Preview" panel u Codium-u.
 */
export function PreviewTabsView({
  url,
  kinds,
}: {
  url: string;
  kinds?: PreviewTabKind[];
}) {
  const tabs = useMemo(
    () => buildTabs(url, kinds ?? ["web", "pc", "mobi"]),
    [url, kinds],
  );

  const [active, setActive] = useState<PreviewTabKind>(
    () => tabs[0]?.kind ?? "web",
  );
  const activeTab = tabs.find((t) => t.kind === active) ?? tabs[0];

  return (
    <div className="pvh">
      <div className="pvh-bar">
        <span className="pvh-url" title={url}>
          {url || "bez URL-a"}
        </span>
        <div className="pvh-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.kind}
              type="button"
              className={`pvh-tab ${active === tab.kind ? "active" : ""}`}
              onClick={() => setActive(tab.kind)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="pvh-stage">
        {url && activeTab ? (
          <iframe
            key={activeTab.kind}
            className="pvh-frame"
            src={activeTab.url}
            title={`preview-${activeTab.kind}`}
            style={
              activeTab.width
                ? { width: activeTab.width, maxWidth: "100%" }
                : { width: "100%" }
            }
          />
        ) : (
          <p className="pvh-empty">Nema URL-a za prikaz.</p>
        )}
      </div>
    </div>
  );
}


// ==========          PREVIEW HOST (bare prozor)          ==========

/** Bare prozor: URL i tabovi iz query-ja (`url`, `tabs=web,pc,mobi`). */
function PreviewHost() {
  const [params] = useSearchParams();
  const url = params.get("url") ?? "";
  const kinds = useMemo(() => parseTabKinds(params.get("tabs")), [params]);
  return <PreviewTabsView url={url} kinds={kinds} />;
}

// Registruj kao bare view „preview-host" (učitava se sa BareWindowShell-om).
registerBareView("preview-host", () => <PreviewHost />);

export default PreviewHost;
