import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import {
  ArrowLeft,
  Bot,
  ChevronRight,
  Columns3,
  Globe,
  LayoutGrid,
  Monitor,
  PanelBottom,
  Smartphone,
  SquareArrowOutUpRight,
} from "lucide-react";

import { getProject } from "../services/codiumApi";
import { launchPreview, launchPreviewTabs } from "../features/codium/launchPreview";
import type { PreviewDevice, PreviewSize } from "../features/codium/previewProfiles";
import { useCoreStringSetting } from "../lib/useCoreSetting";
import { useCodiumUi } from "../features/codium/useCodiumUi";
import type { Project } from "../types/codium";
import AiAssistant from "../features/codium/AiAssistant";
import { openAiChatWindow } from "../features/codium/aiWindow";
import BrainModal from "../features/codium/BrainModal";
import ProjectWorkModal from "../features/codium/ProjectWorkModal";
import CodiumFixedLayout from "../features/codium/CodiumFixedLayout";
import CodiumDockLayout from "../features/codium/CodiumDockLayout";
import ScreenshotToolbarButton from "../features/screenshot/ScreenshotToolbarButton";
import "../styles/codium-hub.css";
import "../styles/codium-workspace.css";
import "../styles/codium-hub-chat.css";


// ==========          POMOĆNE          ==========

const STATUS_LABELS: Record<string, string> = {
  active: "Aktivan",
  paused: "Pauziran",
  done: "Završen",
  archived: "Arhiviran",
};

function stackChips(stack: string): string[] {
  return stack
    .split(/[,;]/)
    .map((part) => part.trim())
    .filter((part) => part !== "");
}


// ==========          AI KOLONA (desni vertikalni panel)          ==========

type AiColumnProps = {
  projectId: number;
  width: number;
  onWidth: (px: number) => void;
  onClose: () => void;
  onDetach: () => void;
  onDock: () => void;
};

/**
 * Desni vertikalni AI panel u workspace-u: naslov + prebaci-dole + „Odvoji" (u
 * zaseban prozor) + minimizuj (u tab uz ivicu), pa AiAssistant. Levom ivicom se
 * prevlači širina (clamp 300–900).
 */
function WorkspaceAiColumn({
  projectId,
  width,
  onWidth,
  onClose,
  onDetach,
  onDock,
}: AiColumnProps) {
  function startResize(event: React.MouseEvent): void {
    event.preventDefault();
    const startX = event.clientX;
    const base = width;
    function onMove(moveEvent: MouseEvent): void {
      // Prevlačenje ulevo = širi panel.
      const next = Math.min(Math.max(base + (startX - moveEvent.clientX), 300), 900);
      onWidth(next);
    }
    function onUp(): void {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  return (
    <aside className="cdw-ai-col" style={{ width }} aria-label="AI asistent">
      <div
        className="cdw-ai-resizer"
        role="separator"
        aria-orientation="vertical"
        title="Prevuci za širinu"
        onMouseDown={startResize}
      />
      <div className="cdw-ai-inner">
        <div className="cdw-ai-head">
          <span className="cdw-ai-title">
            <Bot size={14} /> AI asistent
          </span>
          <div className="cdw-ai-actions">
            <button
              type="button"
              className="cdw-ai-btn"
              onClick={onDock}
              title="Prebaci dole (deli okvir sa terminalom)"
              aria-label="Prebaci asistenta dole"
            >
              <PanelBottom size={14} />
            </button>
            <button
              type="button"
              className="cdw-ai-btn"
              onClick={onDetach}
              title="Odvoji u zaseban prozor (uz desnu ivicu ekrana)"
              aria-label="Odvoji u prozor"
            >
              <SquareArrowOutUpRight size={14} />
            </button>
            <button
              type="button"
              className="cdw-ai-btn"
              onClick={onClose}
              title="Minimizuj (skloni uz desnu ivicu)"
              aria-label="Minimizuj AI panel"
            >
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
        <div className="cdw-ai-body">
          <AiAssistant projectId={projectId} />
        </div>
      </div>
    </aside>
  );
}


// ==========          CODIUM WORKSPACE SHELL          ==========

/**
 * Radno okruženje jednog projekta (F4 ljuska): gornji toolbar, Explorer (F5),
 * Editor (F6 Monaco), opcioni desni INFO panel i donji panel. Navigacija alatki
 * (Tasks/Beleške/Brain, „uskoro" alatke, Info toggle) živi u CORE sidebaru i
 * deli stanje kroz CodiumUi kontekst.
 */
function CodiumWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const id = Number(projectId);

  const { panel, openPanel, soon, showSoon, showInfo } = useCodiumUi();

  // Raspored: "fixed" (default, svi okviri na mestu) ili "dock" (prilagodljiv).
  const [layoutMode, setLayoutMode] = useCoreStringSetting(
    "codium.layoutMode",
    "fixed",
  );

  // AI panel (desna kolona) — uvek dostupan; stanje i širina se pamte.
  const [aiOpen, setAiOpen] = useCoreStringSetting("codium.aiOpen", "");
  const [aiWidth, setAiWidth] = useCoreStringSetting("codium.aiWidth", "380");
  const aiWidthPx = Number(aiWidth) || 380;

  // Položaj asistenta (deljeno sa dashboard chatom): "bottom" | "right".
  // U fiksnom rasporedu "bottom" deli donji okvir sa terminalom (terminal levo,
  // asistent desno, zajednički collapse); "right" je bočni panel/tab.
  const [chatPosSetting, setChatPosSetting] = useCoreStringSetting(
    "codium.chat.pos",
    "bottom",
  );
  const chatPos = chatPosSetting === "right" ? "right" : "bottom";

  // Pri izlasku iz workspace-a zatvori zaostale panele/dijaloge iz konteksta.
  useEffect(() => {
    return () => {
      openPanel(null);
      showSoon(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [project, setProject] = useState<Project | null>(null);
  const [ucitava, setLoading] = useState(true);
  const [nijeNadjen, setMissing] = useState(false);

  // Neispravan id iz rute nije stanje koje se upisuje nego činjenica koja se
  // vidi odmah: „nema projekta", bez učitavanja i bez dodatnog crteža.
  const idNijeBroj = Number.isNaN(id);
  const missing = idNijeBroj || nijeNadjen;
  const loading = !idNijeBroj && ucitava;
  const [openFile, setOpenFile] = useState<string | null>(null);
  const [previewMsg, setPreviewMsg] = useState<string | null>(null);

  const [, setActiveProjectId] = useCoreStringSetting(
    "codium.activeProjectId",
    "",
  );

  const load = useCallback(async (josTraje: () => boolean = () => true) => {
    setLoading(true);
    try {
      const data = await getProject(id);
      if (!josTraje()) {
        return;
      }
      setProject(data);
      // Ulazak u workspace = ovaj projekat je aktivan (kontekst za beleške).
      setActiveProjectId(String(data.id));
    } catch {
      setMissing(true);
    } finally {
      setLoading(false);
    }
    // setActiveProjectId je stabilan (useCallback u hook-u).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (idNijeBroj) {
      return;
    }
    let ziv = true;
    async function pokreni() {
      await load(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [id, idNijeBroj, load]);

  if (loading) {
    return <div className="cdw-message">Učitavam projekat…</div>;
  }

  if (missing || !project) {
    return (
      <div className="cdw-message">
        <p>Projekat nije pronađen.</p>
        <button
          type="button"
          className="cd-btn-primary"
          onClick={() => navigate("/codium")}
        >
          Nazad na projekte
        </button>
      </div>
    );
  }

  const activeProject = project;

  // Asistent deli donji okvir sa terminalom samo u fiksnom rasporedu + „bottom".
  const chatInBottom = layoutMode === "fixed" && chatPos === "bottom";

  // Brzo pokretanje preview-a: WEB (desktop), MOBI (telefon), PC (Full HD).
  async function quickPreview(
    label: string,
    device: PreviewDevice,
    customSize?: Partial<PreviewSize>,
  ): Promise<void> {
    setPreviewMsg(`Otvaram preview (${label})…`);
    const result = await launchPreview(activeProject, device, customSize);
    setPreviewMsg(result.message);
  }

  async function quickPreviewTabs(): Promise<void> {
    setPreviewMsg("Otvaram tab preview (WEB|PC|MOBI)…");
    const result = await launchPreviewTabs(activeProject);
    setPreviewMsg(result.message);
  }

  return (
    <div className="cdw-shell-dock">
      {/* ==========          GORNJI TOOLBAR          ========== */}
      <header className="cdw-toolbar">
        <button
          type="button"
          className="cdw-back"
          onClick={() => navigate("/codium")}
          aria-label="Nazad na projekte"
        >
          <ArrowLeft size={16} />
        </button>
        <h1 className="cdw-project-name">{project.name}</h1>
        <span className={`cd-badge ${project.visibility}`}>
          {project.visibility === "client" ? "Klijent" : "Privatno"}
        </span>
        <span className={`cdw-status cd-status-${project.status}`}>
          {STATUS_LABELS[project.status] ?? project.status}
        </span>
        <div className="cdw-stack">
          {stackChips(project.stack).map((chip) => (
            <span key={chip} className="cd-chip">
              {chip}
            </span>
          ))}
        </div>
        <div className="cdw-toolbar-spacer" />

        {/* AI panel toggle: relevantno kad asistent nije u donjem deljenom okviru. */}
        {!chatInBottom && (
          <button
            type="button"
            className={`cdw-layout-toggle ${aiOpen ? "active" : ""}`}
            onClick={() => setAiOpen(aiOpen ? "" : "1")}
            title={
              aiOpen ? "Minimizuj AI panel" : "Prikaži AI asistenta (desni panel)"
            }
          >
            <Bot size={14} />
            AI
          </button>
        )}

        {/* Snimak ekrana: ceo ekran / prozor / region / element. */}
        <ScreenshotToolbarButton />

        {/* Prekidač rasporeda: fiksno (default) ↔ docking (prilagodljivo). */}
        <button
          type="button"
          className={`cdw-layout-toggle ${layoutMode === "dock" ? "active" : ""}`}
          onClick={() =>
            setLayoutMode(layoutMode === "dock" ? "fixed" : "dock")
          }
          title={
            layoutMode === "dock"
              ? "Docking uključen — klik za fiksni raspored"
              : "Fiksni raspored — klik za docking (prevlačenje panela)"
          }
        >
          <LayoutGrid size={14} />
          {layoutMode === "dock" ? "Docking" : "Fiksno"}
        </button>

        {/* Brzi preview: desni ćošak toolbara — odmah otvara preview prozor. */}
        <div className="cdw-preview-quick" role="group" aria-label="Brzi preview">
          {previewMsg && <span className="cdw-preview-msg">{previewMsg}</span>}
          <button
            type="button"
            className="cdw-preview-btn"
            onClick={() => void quickPreview("WEB", "desktop")}
            title="Preview — web (desktop veličina)"
          >
            <Globe size={14} /> WEB
          </button>
          <button
            type="button"
            className="cdw-preview-btn"
            onClick={() => void quickPreview("MOBI", "mobile")}
            title="Preview — mobilni"
          >
            <Smartphone size={14} /> MOBI
          </button>
          <button
            type="button"
            className="cdw-preview-btn"
            onClick={() =>
              void quickPreview("PC", "custom", { width: 1920, height: 1080 })
            }
            title="Preview — PC (Full HD)"
          >
            <Monitor size={14} /> PC
          </button>
          <button
            type="button"
            className="cdw-preview-btn"
            onClick={() => void quickPreviewTabs()}
            title="Preview u jednom prozoru sa tabovima WEB | PC | MOBI"
          >
            <Columns3 size={14} /> TABS
          </button>
        </div>
      </header>

      {/* ==========          RADNI PROSTOR (fiksno / docking) + AI kolona          ========== */}
      <div className="cdw-work-row">
        <div className="cdw-dock-body">
          {layoutMode === "dock" ? (
            <CodiumDockLayout
              project={project}
              openFile={openFile}
              setOpenFile={setOpenFile}
            />
          ) : (
            <CodiumFixedLayout
              project={project}
              openFile={openFile}
              setOpenFile={setOpenFile}
              showInfo={showInfo}
              chatInBottom={chatInBottom}
              chatNode={
                chatInBottom ? <AiAssistant projectId={project.id} /> : undefined
              }
              onToggleChatPos={() => {
                // Prelaz iz donjeg u desni režim odmah otvara pun desni panel.
                setChatPosSetting("right");
                setAiOpen("1");
              }}
            />
          )}
        </div>

        {/* Desni režim: pun panel (kad je otvoren) ili tab uz desnu ivicu. */}
        {!chatInBottom && aiOpen && (
          <WorkspaceAiColumn
            projectId={project.id}
            width={aiWidthPx}
            onWidth={(px) => setAiWidth(String(px))}
            onClose={() => setAiOpen("")}
            onDock={() => {
              setChatPosSetting("bottom");
              setAiOpen("");
            }}
            onDetach={() => {
              void openAiChatWindow(project.id).then((opened) => {
                // U desktop-u prozor je otvoren → sakrij ugrađeni panel.
                if (opened) {
                  setAiOpen("");
                }
              });
            }}
          />
        )}
      </div>

      {/* Minimizovan desni asistent: ikona-tab uz desnu ivicu (klik otvara). */}
      {!chatInBottom && !aiOpen && (
        <button
          type="button"
          className="chub-tab"
          onClick={() => setAiOpen("1")}
          aria-label="Otvori AI asistenta"
          title="AI asistent"
        >
          <Bot size={17} />
          <span className="chub-tab-label">Asistent</span>
        </button>
      )}

      {/* ==========          „USKORO" DIJALOG          ========== */}
      {soon && (
        <div
          className="cd-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label={soon.label}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              showSoon(null);
            }
          }}
        >
          <div className="cd-modal cdw-soon">
            <h2>{soon.label}</h2>
            <p>Ova alatka stiže u fazi {soon.phase}.</p>
            <button
              type="button"
              className="cd-btn-primary"
              onClick={() => showSoon(null)}
            >
              U redu
            </button>
          </div>
        </div>
      )}

      {/* ==========          AKTIVNI PANELI (iz sidebara)          ========== */}
      {(panel === "tasks" || panel === "notes") && (
        <ProjectWorkModal
          projectId={project.id}
          projectName={project.name}
          onClose={() => openPanel(null)}
        />
      )}
      {panel === "brain" && (
        <BrainModal
          projectId={project.id}
          projectName={project.name}
          onClose={() => openPanel(null)}
        />
      )}
    </div>
  );
}

export default CodiumWorkspace;
