import { useEffect, useState, type ReactNode } from "react";
import {
  ChevronDown,
  ChevronUp,
  FolderTree,
  Info,
  PanelRight,
  SquareTerminal,
} from "lucide-react";

import type { Project } from "../../types/codium";
import FileExplorer from "./FileExplorer";
import CodeEditorPanel from "./CodeEditorPanel";
import TerminalPanel from "../terminal/TerminalPanel";

const STATUS_LABELS: Record<string, string> = {
  active: "Aktivan",
  paused: "Pauziran",
  done: "Završen",
  archived: "Arhiviran",
};


/** Pročita zapamćenu visinu terminala (clamp 90–720; default 150). */
function readHeight(key: string): number {
  try {
    const raw = window.localStorage.getItem(key);
    const value = raw ? Number(raw) : NaN;
    if (Number.isFinite(value)) {
      return Math.min(Math.max(value, 90), 720);
    }
  } catch {
    /* storage nedostupan */
  }
  return 150;
}


// ==========          FIKSNI RASPORED (default)          ==========

type CodiumFixedLayoutProps = {
  project: Project;
  openFile: string | null;
  setOpenFile: (path: string) => void;
  showInfo: boolean;
  /** Kad je dat i chatInBottom=true, chat deli donji okvir sa terminalom (desno). */
  chatNode?: ReactNode;
  chatInBottom?: boolean;
  /** Prebacuje chat iz donjeg u desni režim (kontrola u deljenom zaglavlju). */
  onToggleChatPos?: () => void;
};

/**
 * Podrazumevani raspored CODIUM workspace-a: svi okviri na svojim mestima —
 * Explorer (levo), Editor (centar), opcioni Info (desno), Terminal (dole).
 * Docking (prevlačenje/tabovi) je zasebna opcija (CodiumDockLayout).
 */
function CodiumFixedLayout({
  project,
  openFile,
  setOpenFile,
  showInfo,
  chatNode,
  chatInBottom = false,
  onToggleChatPos,
}: CodiumFixedLayoutProps) {
  // Visina donjeg (terminal) reda — korisnik je menja prevlačenjem gornje ivice.
  // Pamti se po projektu (preživljava ponovno otvaranje workspace-a).
  const heightKey = `core.term.height.codium.${project.id}`;
  const [termHeight, setTermHeight] = useState<number>(() => readHeight(heightKey));

  // Sklopljen terminal: ostaje samo tanka traka (klik na nju vraća). Pamti se.
  const collapsedKey = `core.term.collapsed.codium.${project.id}`;
  const [termCollapsed, setTermCollapsed] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem(collapsedKey) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(heightKey, String(termHeight));
    } catch {
      /* storage nedostupan */
    }
  }, [heightKey, termHeight]);

  useEffect(() => {
    try {
      window.localStorage.setItem(collapsedKey, termCollapsed ? "1" : "0");
    } catch {
      /* storage nedostupan */
    }
  }, [collapsedKey, termCollapsed]);

  // Visina sklopljenog donjeg reda: tanka traka za vraćanje kad chat deli okvir,
  // inače zaglavlje terminala (34).
  const collapsedRow = chatInBottom ? 22 : 34;

  // Dvoklik po „naslovnim" zonama sklapa donji okvir: prazna tab-traka
  // terminala ili zaglavlje asistenta — ne na sam sadržaj/dugmad.
  function collapseFromHeader(event: React.MouseEvent): void {
    const target = event.target as HTMLElement;
    const onTermTabbar =
      target.closest(".cterm-tabbar") &&
      !target.closest(".cterm-tab") &&
      !target.closest(".cterm-actions") &&
      !target.closest(".cterm-new");
    const onChatHead =
      target.closest(".cai-head") &&
      !target.closest("select") &&
      !target.closest(".cdw-bottom-chat-pos");
    if (onTermTabbar || onChatHead) {
      setTermCollapsed(true);
    }
  }

  function startTermResize(event: React.MouseEvent): void {
    event.preventDefault();
    const startY = event.clientY;
    const base = termHeight;
    function onMove(moveEvent: MouseEvent): void {
      // Prevlačenje na gore = veći terminal.
      const next = Math.min(Math.max(base + (startY - moveEvent.clientY), 90), 720);
      setTermHeight(next);
    }
    function onUp(): void {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  return (
    <div
      className={`cdf-grid ${showInfo ? "with-info" : "no-info"}`}
      style={{
        gridTemplateRows: `1fr ${termCollapsed ? collapsedRow : termHeight}px`,
      }}
    >
      {/* Explorer */}
      <aside className="cdw-explorer" aria-label="Explorer">
        <div className="cdw-panel-head">
          <FolderTree size={14} /> Explorer
        </div>
        {project.local_path ? (
          <FileExplorer
            projectId={project.id}
            onOpenFile={setOpenFile}
            activePath={openFile}
            localPath={project.local_path}
          />
        ) : (
          <div className="cdw-placeholder">
            <p>Projekat nema lokalnu putanju.</p>
            <p className="cdw-hint">Dodaj `local_path` da se prikaže stablo.</p>
          </div>
        )}
      </aside>

      {/* Editor */}
      <main className="cdw-editor" aria-label="Editor">
        <CodeEditorPanel projectId={project.id} fileToOpen={openFile} />
      </main>

      {/* Info (opcioni) */}
      {showInfo && (
        <aside className="cdw-right" aria-label="Info panel">
          <div className="cdw-panel-head">
            <Info size={14} /> Info
          </div>
          <div className="cdw-info">
            <dl>
              <dt>Slug</dt>
              <dd>{project.slug}</dd>
              <dt>Status</dt>
              <dd>{STATUS_LABELS[project.status] ?? project.status}</dd>
              <dt>Prioritet</dt>
              <dd>{project.priority}</dd>
              {project.repository_url && (
                <>
                  <dt>Repo</dt>
                  <dd className="cdw-truncate">{project.repository_url}</dd>
                </>
              )}
            </dl>
            <p className="cdw-hint">AI asistent: uključi Docking → panel „AI".</p>
          </div>
        </aside>
      )}

      {/* Donji okvir (PTY terminal + opcioni asistent desno). */}
      <footer
        className={`cdw-bottom ${termCollapsed ? "collapsed" : ""} ${
          chatInBottom ? "shared" : ""
        }`}
        aria-label="Terminal"
      >
        {chatInBottom ? (
          termCollapsed ? (
            // Sklopljeno: samo tanka traka za vraćanje (bez debelog zaglavlja).
            <button
              type="button"
              className="cdw-bottom-restore"
              onClick={() => setTermCollapsed(false)}
              title="Prikaži terminal i asistenta"
              aria-label="Prikaži terminal i asistenta"
            >
              <ChevronUp size={15} />
            </button>
          ) : (
            <>
              {/* Ivica: prevlačenje = visina, dvoklik = sakrij ceo donji okvir. */}
              <div
                className="cdw-term-resizer"
                role="separator"
                aria-orientation="horizontal"
                title="Prevuci za visinu · dvoklik skriva"
                onMouseDown={startTermResize}
                onDoubleClick={() => setTermCollapsed(true)}
              />
              <div className="cdw-bottom-split">
                <div className="cdw-term-fill" onDoubleClick={collapseFromHeader}>
                  <TerminalPanel
                    cwd={project.local_path ?? undefined}
                    persistKey={`codium.${project.id}`}
                  />
                </div>
                <div
                  className="cdw-bottom-chat"
                  onDoubleClick={collapseFromHeader}
                >
                  {onToggleChatPos && (
                    <button
                      type="button"
                      className="cdw-bottom-chat-pos"
                      onClick={onToggleChatPos}
                      aria-label="Prebaci asistenta u desni panel"
                      title="Asistent → desni panel"
                    >
                      <PanelRight size={14} />
                    </button>
                  )}
                  {chatNode}
                </div>
              </div>
            </>
          )
        ) : (
          <>
            {!termCollapsed && (
              <div
                className="cdw-term-resizer"
                role="separator"
                aria-orientation="horizontal"
                title="Prevuci za visinu terminala"
                onMouseDown={startTermResize}
              />
            )}

            <div
              className="cdw-term-header"
              role="button"
              tabIndex={0}
              title={termCollapsed ? "Prikaži terminal" : "Sakrij terminal"}
              onClick={() => setTermCollapsed((value) => !value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setTermCollapsed((value) => !value);
                }
              }}
            >
              <span className="cdw-term-title">
                <SquareTerminal size={14} /> Terminal
              </span>
              <div className="cdw-term-head-actions">
                <ChevronDown
                  size={16}
                  className={`cdw-term-caret ${termCollapsed ? "" : "up"}`}
                />
              </div>
            </div>

            {!termCollapsed && (
              <div className="cdw-term-fill">
                <TerminalPanel
                  cwd={project.local_path ?? undefined}
                  persistKey={`codium.${project.id}`}
                />
              </div>
            )}
          </>
        )}
      </footer>
    </div>
  );
}

export default CodiumFixedLayout;
