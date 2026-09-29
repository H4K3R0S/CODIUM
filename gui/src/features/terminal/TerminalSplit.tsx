import { Fragment, useRef, useState } from "react";
import { GripVertical, X } from "lucide-react";

import type { EnvPair, ShellInfo } from "./terminalApi";
import { groupColor, segmentByGroup } from "./terminalGroups";
import TerminalView from "./TerminalView";


// ==========          TERMINAL SPLIT (segmenti = split; grupa = tab-stack)          ==========

export type TermPane = {
  id: string;
  shell: ShellInfo;
  cwd?: string;
  env?: EnvPair[];
  /** Id grupe: panovi iste grupe dele jedan tab-stack (obojena ivica). */
  groupId?: string;
};

export type SplitDirection = "row" | "column";

type TerminalSplitProps = {
  panes: TermPane[];
  direction: SplitDirection;
  /** Da li je ceo tab vidljiv (za refit terminala). */
  visible: boolean;
  activePaneId: string | null;
  panelCwd?: string;
  onFocusPane: (paneId: string) => void;
  onClosePane: (paneId: string) => void;
  onExitPane: (paneId: string) => void;
  /** Prevlačenje jednog pana na drugi segment → spajanje u grupu (tab-stack). */
  onMergePane: (srcId: string, targetId: string) => void;
  /** Klik na tab u stacku → taj pan postaje vidljiv (premešten na kraj run-a). */
  onBringToFront: (paneId: string) => void;
};

/** Ravnomerne težine (suma = 1) za dati broj segmenata. */
function equalSizes(count: number): number[] {
  return count > 0 ? Array.from({ length: count }, () => 1 / count) : [];
}

/**
 * Raspoređuje panove jednog taba. Uzastopni panovi iste grupe čine STACK (tabovi,
 * vidljiv je poslednji u grupi); segmenti (grupe i pojedinačni panovi) ređaju se u
 * red/kolonu sa prevlačivim razdelnicima. Prevlačenje pana (glava/tab) na drugi
 * segment ga ubacuje u tu grupu — tako više terminala deli isti set tabova.
 */
function TerminalSplit({
  panes,
  direction,
  visible,
  activePaneId,
  panelCwd,
  onFocusPane,
  onClosePane,
  onExitPane,
  onMergePane,
  onBringToFront,
}: TerminalSplitProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const segments = segmentByGroup(panes);
  // Zapamćene težine važe samo dok broj segmenata ne mrdne; posle split-a,
  // zatvaranja ili spajanja ravnomerna podela se IZVODI pri crtanju. Upis iz
  // efekta bi značio jedan crtež sa starim težinama pa drugi sa novim.
  const [zapamceneTezine, setSizes] =
    useState<number[]>(() => equalSizes(segments.length));
  const sizes = zapamceneTezine.length === segments.length
    ? zapamceneTezine
    : equalSizes(segments.length);
  const [dragId, setDragId] = useState<string | null>(null);
  const [overKey, setOverKey] = useState<string | null>(null);

  function startDrag(index: number, event: React.MouseEvent): void {
    event.preventDefault();
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const rect = container.getBoundingClientRect();
    const length = direction === "row" ? rect.width : rect.height;
    const startPos = direction === "row" ? event.clientX : event.clientY;
    const base = [...sizes];
    const combined = base[index] + base[index + 1];

    function onMove(moveEvent: MouseEvent): void {
      const pos = direction === "row" ? moveEvent.clientX : moveEvent.clientY;
      const deltaFraction = (pos - startPos) / length;
      const first = Math.min(
        Math.max(base[index] + deltaFraction, 0.08),
        combined - 0.08,
      );
      setSizes((current) => {
        const next = [...current];
        next[index] = first;
        next[index + 1] = combined - first;
        return next;
      });
    }
    function onUp(): void {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  // Zajednički drag-props za izvor (glava pana ili tab u stacku).
  function dragSource(paneId: string) {
    return {
      draggable: true,
      onDragStart: (event: React.DragEvent) => {
        event.dataTransfer.setData("text/plain", paneId);
        event.dataTransfer.effectAllowed = "move";
        setDragId(paneId);
      },
      onDragEnd: () => {
        setDragId(null);
        setOverKey(null);
      },
    };
  }

  const multiSegment = segments.length > 1;

  return (
    <div ref={containerRef} className={`cterm-split ${direction}`}>
      {segments.map((segment, index) => {
        const stacked = segment.panes.length > 1;
        const visiblePane = segment.panes[segment.panes.length - 1];
        const border = segment.groupId ? groupColor(segment.groupId) : undefined;
        const key = segment.groupId ?? visiblePane.id;
        const isOver = overKey === key && dragId !== null;
        const showHead = stacked || multiSegment;
        return (
          <Fragment key={key}>
            <div
              className={`cterm-pane ${
                activePaneId === visiblePane.id ? "active" : ""
              } ${segment.groupId ? "grouped" : ""} ${isOver ? "drop-over" : ""}`}
              style={{
                flexGrow: sizes[index] ?? 1,
                flexShrink: 1,
                flexBasis: 0,
                ...(border ? { borderColor: border } : {}),
              }}
              onMouseDown={() => onFocusPane(visiblePane.id)}
              onDragOver={
                dragId !== null
                  ? (event) => {
                      event.preventDefault();
                      event.dataTransfer.dropEffect = "move";
                      setOverKey(key);
                    }
                  : undefined
              }
              onDragLeave={() => setOverKey((o) => (o === key ? null : o))}
              onDrop={
                dragId !== null
                  ? (event) => {
                      event.preventDefault();
                      if (dragId !== visiblePane.id) {
                        onMergePane(dragId, visiblePane.id);
                      }
                      setDragId(null);
                      setOverKey(null);
                    }
                  : undefined
              }
            >
              {stacked ? (
                // Grupa sa više panova → tab-stack (unutrašnji tabovi).
                <div className="cterm-stack-bar">
                  {segment.panes.map((pane) => (
                    <div
                      key={pane.id}
                      className={`cterm-stack-tab ${
                        pane.id === visiblePane.id ? "active" : ""
                      }`}
                      {...dragSource(pane.id)}
                      onClick={(event) => {
                        event.stopPropagation();
                        onBringToFront(pane.id);
                      }}
                      title="Prevuci na drugi segment; klik = prikaži"
                    >
                      <GripVertical size={10} className="cterm-pane-grip" />
                      <span className="cterm-stack-name">{pane.shell.name}</span>
                      <button
                        type="button"
                        className="cterm-pane-close"
                        onClick={(event) => {
                          event.stopPropagation();
                          onClosePane(pane.id);
                        }}
                        aria-label={`Zatvori ${pane.shell.name}`}
                      >
                        <X size={10} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                showHead && (
                  // Pojedinačan pan, ali ima drugih segmenata → glava = drag ručica.
                  <div
                    className="cterm-pane-head"
                    {...dragSource(visiblePane.id)}
                    title="Prevuci da spojiš u grupu (tab-stack)"
                  >
                    <span className="cterm-pane-name">
                      <GripVertical size={11} className="cterm-pane-grip" />
                      {visiblePane.shell.name}
                    </span>
                    <button
                      type="button"
                      className="cterm-pane-close"
                      onClick={(event) => {
                        event.stopPropagation();
                        onClosePane(visiblePane.id);
                      }}
                      aria-label={`Zatvori pan ${visiblePane.shell.name}`}
                    >
                      <X size={11} />
                    </button>
                  </div>
                )
              )}

              {/* Svi panovi segmenta ostaju montirani (PTY živi); vidljiv je poslednji. */}
              <div className="cterm-pane-body">
                {segment.panes.map((pane) => (
                  <div
                    key={pane.id}
                    className="cterm-pane-slot"
                    style={{
                      display: pane.id === visiblePane.id ? "block" : "none",
                    }}
                  >
                    <TerminalView
                      id={pane.id}
                      shell={pane.shell.path}
                      args={pane.shell.args}
                      cwd={pane.cwd ?? panelCwd}
                      env={pane.env}
                      active={visible && pane.id === visiblePane.id}
                      onExit={onExitPane}
                    />
                  </div>
                ))}
              </div>
            </div>

            {index < segments.length - 1 && (
              <div
                className={`cterm-divider ${direction}`}
                onMouseDown={(event) => startDrag(index, event)}
                role="separator"
                aria-orientation={direction === "row" ? "vertical" : "horizontal"}
              />
            )}
          </Fragment>
        );
      })}
    </div>
  );
}

export default TerminalSplit;
