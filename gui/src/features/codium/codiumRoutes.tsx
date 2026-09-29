import { Route } from "react-router";

import CodiumPage from "../../pages/CodiumPage";
import CodiumOverview from "../../pages/CodiumOverview";
import CodiumSettingsPage from "../../pages/CodiumSettingsPage";
import CodiumWorkspace from "../../pages/CodiumWorkspace";
import CodiumWorkspaceEntry from "../../pages/CodiumWorkspaceEntry";
import CodiumAccess from "../../pages/CodiumAccess";
import CodiumAgents from "../../pages/CodiumAgents";
import CodiumAudit from "../../pages/CodiumAudit";
import CodiumRepositories from "../../pages/CodiumRepositories";
import CodiumPipelines from "../../pages/CodiumPipelines";
import CodiumDeployments from "../../pages/CodiumDeployments";
import CodiumInfrastructure from "../../pages/CodiumInfrastructure";
import CodiumMonitoring from "../../pages/CodiumMonitoring";
import CodiumAnalytics from "../../pages/CodiumAnalytics";
import CodiumAutomations from "../../pages/CodiumAutomations";
import CodiumIntegrations from "../../pages/CodiumIntegrations";


// ==========          CODIUM RUTE (deljeni izvor)          ==========
//
// Jedini izvor CODIUM ruta. Koristi ih i CORE `App` (kad je CODIUM aktivan
// domen) i samostalna ćelija (`CellApp` preko `cellDomain`). Vraća fragment
// `<Route>` elemenata — mesto montiranja (i eventualni `CodiumUiProvider`)
// bira roditelj (u ćeliji: `cellNav.Wrapper`).

export function codiumRoutes() {
  return (
    <>
      <Route path="/codium" element={<CodiumOverview />} />
      <Route path="/codium/settings" element={<CodiumSettingsPage />} />
      <Route path="/codium/access" element={<CodiumAccess />} />
      <Route path="/codium/agents" element={<CodiumAgents />} />
      <Route path="/codium/audit" element={<CodiumAudit />} />
      <Route path="/codium/repositories" element={<CodiumRepositories />} />
      <Route path="/codium/pipelines" element={<CodiumPipelines />} />
      <Route path="/codium/deployments" element={<CodiumDeployments />} />
      <Route path="/codium/infrastructure" element={<CodiumInfrastructure />} />
      <Route path="/codium/monitoring" element={<CodiumMonitoring />} />
      <Route path="/codium/analytics" element={<CodiumAnalytics />} />
      <Route path="/codium/automations" element={<CodiumAutomations />} />
      <Route path="/codium/integrations" element={<CodiumIntegrations />} />
      <Route path="/codium/projects" element={<CodiumPage />} />
      <Route path="/codium/workspace" element={<CodiumWorkspaceEntry />} />
      <Route path="/codium/workspace/:projectId" element={<CodiumWorkspace />} />
    </>
  );
}
