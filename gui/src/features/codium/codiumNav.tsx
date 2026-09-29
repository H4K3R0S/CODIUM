import {
  Brain,
  Activity,
  BarChart3,
  Bot,
  FolderKanban,
  GitBranch,
  LayoutDashboard,
  LayoutGrid,
  Plug,
  Rocket,
  ScrollText,
  Server,
  Settings,
  Users,
  Workflow,
  Zap,
} from "lucide-react";

import { type CellNav } from "../../cell/cellNav";
import CodiumAgentDock from "./CodiumAgentDock";
import { CodiumUiProvider } from "./workspaceUi";


// ==========          CODIUM NAVIGACIJA (ćelija)          ==========
//
// POJEDNOSTAVLJENA navigacija CODIUM domena za samostalnu ćeliju (generički
// `CellSidebar`). CORE-ov `Sidebar` zadržava BOGATU `CodiumSidebarNavigation`
// (akcije preko `CodiumUiProvider`: AI Workspace, Tasks, „uskoro" bedževi) —
// ta interaktivnost ne staje u prosti `CellNav`, pa ćelija za sada nosi samo
// rutne stavke. Ostatak (workspace/tasks akcije) se dostiže preko ruta i
// dograđuje kasnije. `Wrapper` = `CodiumUiProvider` jer CODIUM ekrani traže
// taj kontekst.

export const codiumNav: CellNav = {
  brand: "CODIUM",
  homePath: "/codium",
  settingsPath: "/codium/settings",
  Wrapper: CodiumUiProvider,
  AgentDock: CodiumAgentDock,
  railItems: [
    { label: "Overview", icon: LayoutDashboard, path: "/codium", end: true },
    { label: "Second Brain", icon: Brain, path: "/second-brain" },
    { label: "Podešavanja", icon: Settings, path: "/codium/settings" },
  ],
  sections: [
    {
      label: "CODIUM",
      items: [
        { id: "cod-overview", label: "Overview", icon: LayoutDashboard, path: "/codium" },
        { id: "cod-projects", label: "Projects", icon: FolderKanban, path: "/codium/projects" },
        { id: "cod-repos", label: "Repositories", icon: GitBranch, path: "/codium/repositories" },
        { id: "cod-workspace", label: "AI Workspace", icon: LayoutGrid, path: "/codium/workspace" },
        { id: "cod-pipelines", label: "Pipelines", icon: Workflow, path: "/codium/pipelines" },
        { id: "cod-deployments", label: "Deployments", icon: Rocket, path: "/codium/deployments" },
        { id: "cod-infra", label: "Infrastructure", icon: Server, path: "/codium/infrastructure" },
        { id: "cod-monitoring", label: "Monitoring", icon: Activity, path: "/codium/monitoring" },
        { id: "cod-analytics", label: "Analytics", icon: BarChart3, path: "/codium/analytics" },
      ],
    },
    {
      label: "AI & AUTOMATION",
      items: [
        { id: "cod-agents", label: "AI Agents", icon: Bot, path: "/codium/agents" },
        { id: "cod-automations", label: "Automations", icon: Zap, path: "/codium/automations" },
        { id: "cod-integrations", label: "Integrations", icon: Plug, path: "/codium/integrations" },
      ],
    },
    {
      label: "SYSTEM",
      items: [
        { id: "cod-access", label: "Access & Users", icon: Users, path: "/codium/access" },
        { id: "cod-audit", label: "Audit Logs", icon: ScrollText, path: "/codium/audit" },
      ],
    },
  ],
};
