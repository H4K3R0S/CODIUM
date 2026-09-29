import { createContext, useContext, useMemo } from "react";
import type { DockviewApi, IDockviewPanelProps } from "dockview-react";
import {
  Bot,
  BrainCircuit,
  FolderTree,
  GitBranch,
  Info,
  ListTodo,
  Monitor,
  SquareTerminal,
} from "lucide-react";

import type { Project } from "../../types/codium";
import FileExplorer from "./FileExplorer";
import CodeEditorPanel from "./CodeEditorPanel";
import { ProjectWorkContent } from "./ProjectWorkModal";
import { BrainContent } from "./BrainModal";
import AiAssistant from "./AiAssistant";
import GitPanel from "./repositories/GitPanel";
import { projectPreviewUrl } from "./launchPreview";
import { PreviewTabsView } from "../window/PreviewHost";
import TerminalPanel from "../terminal/TerminalPanel";
import CoreDockLayout, {
  type DockPanelMeta,
} from "../window/CoreDockLayout";


// ==========          DELJENO STANJE PANELA (kontekst)          ==========

type DockContextValue = {
  project: Project;
  openFile: string | null;
  setOpenFile: (path: string) => void;
};

const DockContext = createContext<DockContextValue | null>(null);

function useDock(): DockContextValue {
  const ctx = useContext(DockContext);
  if (!ctx) {
    throw new Error("DockContext nije dostupan.");
  }
  return ctx;
}


// ==========          POJEDINAČNI PANELI          ==========

function ExplorerPanel(_props: IDockviewPanelProps) {
  const { project, openFile, setOpenFile } = useDock();
  if (!project.local_path) {
    return (
      <div className="cdk-placeholder">
        <p>Projekat nema lokalnu putanju.</p>
        <p className="cdk-hint">Dodaj `local_path` da se prikaže stablo.</p>
      </div>
    );
  }
  return (
    <FileExplorer
      projectId={project.id}
      onOpenFile={setOpenFile}
      activePath={openFile}
      localPath={project.local_path}
    />
  );
}

function EditorPanel(_props: IDockviewPanelProps) {
  const { project, openFile } = useDock();
  return <CodeEditorPanel projectId={project.id} fileToOpen={openFile} />;
}

function InfoPanel(_props: IDockviewPanelProps) {
  const { project } = useDock();
  return (
    <div className="cdk-info">
      <dl>
        <dt>Slug</dt>
        <dd>{project.slug}</dd>
        <dt>Status</dt>
        <dd>{project.status}</dd>
        <dt>Prioritet</dt>
        <dd>{project.priority}</dd>
        {project.repository_url && (
          <>
            <dt>Repo</dt>
            <dd className="cdk-truncate">{project.repository_url}</dd>
          </>
        )}
      </dl>
      <p className="cdk-hint">AI asistent je u panelu „AI".</p>
    </div>
  );
}

function TerminalDockPanel(_props: IDockviewPanelProps) {
  const { project } = useDock();
  return (
    <TerminalPanel
      cwd={project.local_path ?? undefined}
      persistKey={`codium.${project.id}`}
    />
  );
}

function PreviewPanel(_props: IDockviewPanelProps) {
  const { project } = useDock();
  const url = projectPreviewUrl(project);
  if (!url) {
    return (
      <div className="cdk-placeholder">
        <p>Projekat nema preview URL.</p>
        <p className="cdk-hint">Dodaj `dev_port` ili `preview_url`.</p>
      </div>
    );
  }
  return <PreviewTabsView url={url} kinds={["web", "pc", "mobi"]} />;
}

function TasksPanel(_props: IDockviewPanelProps) {
  const { project } = useDock();
  return (
    <div className="cdk-panel-scroll">
      <ProjectWorkContent projectId={project.id} />
    </div>
  );
}

function BrainPanel(_props: IDockviewPanelProps) {
  const { project } = useDock();
  return (
    <div className="cdk-panel-scroll">
      <BrainContent projectId={project.id} />
    </div>
  );
}

function AiPanel(_props: IDockviewPanelProps) {
  const { project } = useDock();
  return (
    <div className="cdk-panel-scroll">
      <AiAssistant projectId={project.id} />
    </div>
  );
}

function GitDockPanel(_props: IDockviewPanelProps) {
  const { project } = useDock();
  return (
    <div className="cdk-panel-scroll">
      <GitPanel projectId={project.id} />
    </div>
  );
}

const DOCK_COMPONENTS = {
  explorer: ExplorerPanel,
  editor: EditorPanel,
  info: InfoPanel,
  terminal: TerminalDockPanel,
  preview: PreviewPanel,
  tasks: TasksPanel,
  brain: BrainPanel,
  ai: AiPanel,
  git: GitDockPanel,
};

// Naslov + ikonica po ključu panela (za re-dodavanje).
const PANEL_META: Record<string, DockPanelMeta> = {
  explorer: { title: "Explorer", icon: <FolderTree size={13} /> },
  editor: { title: "Editor", icon: <SquareTerminal size={13} /> },
  info: { title: "Info", icon: <Info size={13} /> },
  terminal: { title: "Terminal", icon: <SquareTerminal size={13} /> },
  preview: { title: "Preview", icon: <Monitor size={13} /> },
  tasks: { title: "Tasks", icon: <ListTodo size={13} /> },
  brain: { title: "Brain", icon: <BrainCircuit size={13} /> },
  ai: { title: "AI", icon: <Bot size={13} /> },
  git: { title: "Git", icon: <GitBranch size={13} /> },
};


// ==========          PODRAZUMEVANI RASPORED          ==========

function buildDefaultLayout(api: DockviewApi): void {
  api.clear();
  api.addPanel({ id: "explorer", component: "explorer", title: "Explorer" });
  api.addPanel({
    id: "editor",
    component: "editor",
    title: "Editor",
    position: { referencePanel: "explorer", direction: "right" },
  });
  api.addPanel({
    id: "info",
    component: "info",
    title: "Info",
    position: { referencePanel: "editor", direction: "right" },
  });
  api.addPanel({
    id: "terminal",
    component: "terminal",
    title: "Terminal",
    position: { referencePanel: "editor", direction: "below" },
  });
}


// ==========          CODIUM DOCKING (omotač oko CoreDockLayout)          ==========

type CodiumDockLayoutProps = {
  project: Project;
  openFile: string | null;
  setOpenFile: (path: string) => void;
};

/**
 * Docking radni prostor CODIUM-a: domenske panel-komponente (Explorer/Editor/
 * Info/Terminal/Preview/Tasks/Brain/AI) + deljeno stanje (kontekst) predate
 * generičkom `CoreDockLayout`-u (D4), koji nosi mehaniku (dodavanje panela,
 * Float, Reset, preseti + import/export, serijalizacija po projektu).
 */
function CodiumDockLayout({
  project,
  openFile,
  setOpenFile,
}: CodiumDockLayoutProps) {
  const ctx = useMemo<DockContextValue>(
    () => ({ project, openFile, setOpenFile }),
    [project, openFile, setOpenFile],
  );

  return (
    <DockContext.Provider value={ctx}>
      <CoreDockLayout
        storageKey={`codium.dock.${project.id}`}
        presetsKey="codium.dock.presets"
        components={DOCK_COMPONENTS}
        panelMeta={PANEL_META}
        buildDefaultLayout={buildDefaultLayout}
      />
    </DockContext.Provider>
  );
}

export default CodiumDockLayout;
