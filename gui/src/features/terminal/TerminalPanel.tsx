import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  Copy,
  Pencil,
  Plus,
  SlidersHorizontal,
  SplitSquareHorizontal,
  SplitSquareVertical,
  TerminalSquare,
  X,
} from "lucide-react";

import { listShells, type EnvPair, type ShellInfo } from "./terminalApi";
import {
  pickDefaultShell,
  shellInstanceIndex,
  shellTabTitle,
} from "./shellCatalog";
import {
  readSession,
  restoreLayout,
  writeSession,
  type RestoredTab,
} from "./terminalSession";
import { subscribeTerminalHere } from "./terminalBus";
import { readProfiles, writeProfiles, type TermProfile } from "./terminalProfiles";
import {
  bringPaneToGroupEnd,
  mergePanes,
  pruneSingletonGroups,
} from "./terminalGroups";
import TerminalProfilesEditor from "./TerminalProfilesEditor";
import TerminalSplit, {
  type SplitDirection,
  type TermPane,
} from "./TerminalSplit";
import "../../styles/terminal.css";


// ==========          TERMINAL PANEL (tabovi + split + shell meni)          ==========

type TermTab = {
  id: string;
  title: string;
  direction: SplitDirection;
  panes: TermPane[];
  activePaneId: string | null;
  /** Korisnička boja taba (opciono). */
  color?: string;
};

// Paleta boja taba (drop meni). „bez boje" uklanja tint.
const TAB_COLORS = [
  "#4a9ce6",
  "#3fb58b",
  "#d9a441",
  "#e0693b",
  "#c05bd6",
  "#d64b8a",
];

type TerminalPanelProps = {
  /** Radni direktorijum novih terminala (npr. lokalna putanja projekta). */
  cwd?: string;
  /** Kontekst za pamćenje otvorenih tabova (npr. `codium.<projectId>`). */
  persistKey?: string;
};

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `term-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Prvi (glavni) shell taba — za naslov i persist. */
function tabShell(tab: TermTab): ShellInfo | null {
  return tab.panes[0]?.shell ?? null;
}

/**
 * Integrisani terminal: tabovi (svaki može imati više panova — split), „+“
 * otvara podrazumevani shell, strelica → drop meni za izbor shell-a, a dugmad
 * Split dele aktivni tab na panove (red/kolonu, prevlačivi razdelnici). Kao
 * Windows Terminal.
 */
function TerminalPanel({ cwd, persistKey }: TerminalPanelProps) {
  const [shells, setShells] = useState<ShellInfo[]>([]);
  const [tabs, setTabs] = useState<TermTab[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const [profiles, setProfiles] = useState<TermProfile[]>(() => readProfiles());
  const [editorOpen, setEditorOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Kontekst meni taba (preimenuj/dupliciraj/boja) + inline preimenovanje.
  const [tabMenu, setTabMenu] = useState<{ id: string; x: number; y: number } | null>(null);
  const [renamingTab, setRenamingTab] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");

  // Napravi tab sa jednim panom datog shell-a; naslov po broju instanci shell-a
  // (ili eksplicitan naslov iz profila). Opciono cwd/env.
  const makeTab = useCallback(
    (
      shell: ShellInfo,
      current: TermTab[],
      opts?: { cwd?: string; env?: EnvPair[]; title?: string },
    ): TermTab => {
      const index = shellInstanceIndex(
        current.map((t) => tabShell(t)?.id ?? ""),
        shell.id,
      );
      const paneId = newId();
      return {
        id: newId(),
        title: opts?.title ?? shellTabTitle(shell, index),
        direction: "row",
        panes: [{ id: paneId, shell, cwd: opts?.cwd, env: opts?.env }],
        activePaneId: paneId,
      };
    },
    [],
  );

  // Napravi tab iz zapamćenog rasporeda (panovi + grupe + smer + naslov).
  const tabFromRestored = useCallback(
    (restored: RestoredTab, existing: TermTab[]): TermTab => {
      const panes: TermPane[] = restored.panes.map((rp) => ({
        id: newId(),
        shell: rp.shell,
        groupId: rp.groupId,
      }));
      const first = restored.panes[0].shell;
      const index = shellInstanceIndex(
        existing.map((t) => tabShell(t)?.id ?? ""),
        first.id,
      );
      return {
        id: newId(),
        title: restored.title ?? shellTabTitle(first, index),
        direction: restored.direction,
        panes,
        activePaneId: panes[0].id,
        color: restored.color,
      };
    },
    [],
  );

  const addTab = useCallback(
    (shell: ShellInfo, opts?: { cwd?: string; env?: EnvPair[]; title?: string }): void => {
      setTabs((current) => {
        const tab = makeTab(shell, current, opts);
        setActive(tab.id);
        return [...current, tab];
      });
      setMenuOpen(false);
    },
    [makeTab],
  );

  // Otvori tab iz profila (shell po ID-u iz kataloga + cwd + env).
  const openProfileTab = useCallback(
    (profile: TermProfile): void => {
      const shell = shells.find((s) => s.id === profile.shellId);
      if (!shell) {
        return;
      }
      addTab(shell, { cwd: profile.cwd, env: profile.env, title: profile.name });
    },
    [shells, addTab],
  );

  function updateProfiles(next: TermProfile[]): void {
    setProfiles(next);
    writeProfiles(next);
  }

  // Učitaj shell-ove pa vrati zapamćene tabove (ili otvori podrazumevani).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const list = await listShells();
      if (cancelled) {
        return;
      }
      setShells(list);

      const restored = persistKey
        ? restoreLayout(readSession(persistKey), list)
        : [];

      setTabs((current) => {
        if (current.length > 0) {
          return current;
        }
        const built: TermTab[] = [];
        if (restored.length > 0) {
          for (const rt of restored) {
            built.push(tabFromRestored(rt, built));
          }
        } else {
          const def = pickDefaultShell(list);
          if (def) {
            built.push(makeTab(def, built));
          }
        }
        if (built.length > 0) {
          setActive(built[0].id);
        }
        return built;
      });
      setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [makeTab, tabFromRestored, persistKey]);

  // Zapamti otvorene tabove (po glavnom shell-u) kad se promene.
  useEffect(() => {
    if (!ready || !persistKey) {
      return;
    }
    writeSession(
      persistKey,
      tabs
        .filter((t) => tabShell(t) !== null)
        .map((t) => ({
          shellId: tabShell(t)!.id,
          title: t.title,
          direction: t.direction,
          color: t.color,
          panes: t.panes.map((p) => ({ shellId: p.shell.id, groupId: p.groupId })),
        })),
    );
  }, [tabs, ready, persistKey]);

  // Zatvaranje kontekst menija taba (klik bilo gde / Escape).
  useEffect(() => {
    if (!tabMenu) {
      return;
    }
    const close = (): void => setTabMenu(null);
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        close();
      }
    };
    window.addEventListener("click", close);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [tabMenu]);

  // „Otvori terminal ovde“ (npr. iz Explorer-a): nov tab u traženom folderu.
  useEffect(() => {
    return subscribeTerminalHere((hereCwd) => {
      const def = pickDefaultShell(shells);
      if (def) {
        addTab(def, { cwd: hereCwd });
      }
    });
  }, [shells, addTab]);

  // Zatvaranje drop menija klikom van njega.
  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    function onDown(event: MouseEvent): void {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [menuOpen]);

  function addDefaultTab(): void {
    const def = pickDefaultShell(shells);
    if (def) {
      addTab(def);
    }
  }

  // Podeli aktivni tab: nov pan (isti shell/cwd kao aktivni pan) u datom smeru.
  function splitActive(direction: SplitDirection): void {
    setTabs((current) =>
      current.map((tab) => {
        if (tab.id !== active) {
          return tab;
        }
        const src =
          tab.panes.find((p) => p.id === tab.activePaneId) ?? tab.panes[0];
        if (!src) {
          return tab;
        }
        const pane: TermPane = { id: newId(), shell: src.shell, cwd: src.cwd };
        return {
          ...tab,
          direction,
          panes: [...tab.panes, pane],
          activePaneId: pane.id,
        };
      }),
    );
  }

  // Spoji pan `srcId` u grupu pana `targetId` (drag-merge); ukloni singleton grupe.
  function mergePanesInTab(tabId: string, srcId: string, targetId: string): void {
    setTabs((current) =>
      current.map((tab) => {
        if (tab.id !== tabId) {
          return tab;
        }
        const merged = mergePanes(tab.panes, srcId, targetId, newId());
        return { ...tab, panes: pruneSingletonGroups(merged) };
      }),
    );
  }

  // Klik na tab u stacku → pan na kraj svog run-a (postaje vidljiv) + fokus.
  function bringToFront(tabId: string, paneId: string): void {
    setTabs((current) =>
      current.map((tab) =>
        tab.id === tabId
          ? { ...tab, panes: bringPaneToGroupEnd(tab.panes, paneId), activePaneId: paneId }
          : tab,
      ),
    );
  }

  function focusPane(tabId: string, paneId: string): void {
    setTabs((current) =>
      current.map((tab) =>
        tab.id === tabId ? { ...tab, activePaneId: paneId } : tab,
      ),
    );
  }

  function closePane(tabId: string, paneId: string): void {
    setTabs((current) => {
      const tab = current.find((t) => t.id === tabId);
      if (!tab) {
        return current;
      }
      const panes = tab.panes.filter((p) => p.id !== paneId);
      if (panes.length === 0) {
        // Poslednji pan → zatvori ceo tab.
        const next = current.filter((t) => t.id !== tabId);
        setActive((a) =>
          a === tabId ? (next[next.length - 1]?.id ?? null) : a,
        );
        return next;
      }
      return current.map((t) =>
        t.id === tabId
          ? {
              ...t,
              panes: pruneSingletonGroups(panes),
              activePaneId:
                t.activePaneId === paneId ? panes[panes.length - 1].id : t.activePaneId,
            }
          : t,
      );
    });
  }

  function closeTab(id: string): void {
    setTabs((current) => {
      const next = current.filter((t) => t.id !== id);
      setActive((a) => (a === id ? (next[next.length - 1]?.id ?? null) : a));
      return next;
    });
  }

  // ---------- kontekst meni taba ----------

  function openTabMenu(event: React.MouseEvent, id: string): void {
    event.preventDefault();
    setTabMenu({ id, x: event.clientX, y: event.clientY });
  }

  function startRenameTab(id: string): void {
    const tab = tabs.find((t) => t.id === id);
    setRenamingTab(id);
    setRenameDraft(tab?.title ?? "");
    setTabMenu(null);
  }

  function commitRenameTab(id: string): void {
    const name = renameDraft.trim();
    setRenamingTab(null);
    if (name === "") {
      return;
    }
    setTabs((current) =>
      current.map((t) => (t.id === id ? { ...t, title: name } : t)),
    );
  }

  // Dupliciraj tab: isti shell-ovi/grupe/boja, novi PTY id-jevi (nove sesije).
  function duplicateTab(id: string): void {
    setTabs((current) => {
      const src = current.find((t) => t.id === id);
      if (!src) {
        return current;
      }
      let newActive: string | null = null;
      const panes: TermPane[] = src.panes.map((p) => {
        const nid = newId();
        if (p.id === src.activePaneId) {
          newActive = nid;
        }
        return { ...p, id: nid };
      });
      const dup: TermTab = {
        id: newId(),
        title: `${src.title} (kopija)`,
        direction: src.direction,
        panes,
        activePaneId: newActive ?? panes[panes.length - 1]?.id ?? null,
        color: src.color,
      };
      setActive(dup.id);
      const at = current.findIndex((t) => t.id === id);
      const next = [...current];
      next.splice(at + 1, 0, dup);
      return next;
    });
    setTabMenu(null);
  }

  function setTabColor(id: string, color?: string): void {
    setTabs((current) =>
      current.map((t) => (t.id === id ? { ...t, color } : t)),
    );
    setTabMenu(null);
  }

  if (shells.length === 0 && tabs.length === 0) {
    return (
      <div className="cterm-empty">
        <TerminalSquare size={26} />
        <p>Terminal je dostupan u desktop aplikaciji.</p>
        <p className="cterm-hint">(U browser pregledu nema pristupa shell-u.)</p>
      </div>
    );
  }

  const activeTab = tabs.find((t) => t.id === active) ?? null;

  return (
    <div className="cterm">
      <div className="cterm-tabbar">
        <div className="cterm-tabs">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={`cterm-tab ${active === tab.id ? "active" : ""}`}
              style={
                tab.color
                  ? ({ "--tab-color": tab.color } as React.CSSProperties)
                  : undefined
              }
              onContextMenu={(event) => openTabMenu(event, tab.id)}
            >
              {tab.color && (
                <span
                  className="cterm-tab-dot"
                  style={{ background: tab.color }}
                  aria-hidden
                />
              )}
              {renamingTab === tab.id ? (
                <input
                  autoFocus
                  className="cterm-tab-rename"
                  value={renameDraft}
                  onChange={(event) => setRenameDraft(event.target.value)}
                  onBlur={() => commitRenameTab(tab.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      commitRenameTab(tab.id);
                    } else if (event.key === "Escape") {
                      setRenamingTab(null);
                    }
                  }}
                  aria-label="Novo ime terminala"
                />
              ) : (
                <button
                  type="button"
                  className="cterm-tab-name"
                  onClick={() => setActive(tab.id)}
                  onDoubleClick={() => startRenameTab(tab.id)}
                  title={tabShell(tab)?.name}
                >
                  <TerminalSquare size={12} /> {tab.title}
                  {tab.panes.length > 1 && (
                    <span className="cterm-tab-count">{tab.panes.length}</span>
                  )}
                </button>
              )}
              <button
                type="button"
                className="cterm-tab-close"
                onClick={() => closeTab(tab.id)}
                aria-label={`Zatvori ${tab.title}`}
              >
                <X size={11} />
              </button>
            </div>
          ))}
        </div>

        <div className="cterm-actions">
          {activeTab && (
            <>
              <button
                type="button"
                className="cterm-act-btn"
                onClick={() => splitActive("row")}
                title="Podeli levo/desno"
                aria-label="Podeli horizontalno"
              >
                <SplitSquareHorizontal size={14} />
              </button>
              <button
                type="button"
                className="cterm-act-btn"
                onClick={() => splitActive("column")}
                title="Podeli gore/dole"
                aria-label="Podeli vertikalno"
              >
                <SplitSquareVertical size={14} />
              </button>
            </>
          )}

          <div className="cterm-new" ref={menuRef}>
            <button
              type="button"
              className="cterm-new-btn"
              onClick={addDefaultTab}
              title="Nov terminal (podrazumevani shell)"
              aria-label="Nov terminal"
            >
              <Plus size={13} />
            </button>
            <button
              type="button"
              className="cterm-new-caret"
              onClick={() => setMenuOpen((open) => !open)}
              title="Izaberi shell"
              aria-label="Izaberi shell"
            >
              <ChevronDown size={12} />
            </button>

            {menuOpen && (
              <div className="cterm-menu" role="menu">
                {shells.map((shell) => (
                  <button
                    key={shell.id}
                    type="button"
                    className="cterm-menu-item"
                    onClick={() => addTab(shell)}
                    role="menuitem"
                  >
                    <TerminalSquare size={13} /> {shell.name}
                  </button>
                ))}

                {profiles.length > 0 && (
                  <>
                    <div className="cterm-menu-sep" />
                    <div className="cterm-menu-label">Profili</div>
                    {profiles.map((profile) => (
                      <button
                        key={profile.id}
                        type="button"
                        className="cterm-menu-item"
                        onClick={() => {
                          openProfileTab(profile);
                          setMenuOpen(false);
                        }}
                        role="menuitem"
                      >
                        <SlidersHorizontal size={13} /> {profile.name}
                      </button>
                    ))}
                  </>
                )}

                <div className="cterm-menu-sep" />
                <button
                  type="button"
                  className="cterm-menu-item"
                  onClick={() => {
                    setEditorOpen(true);
                    setMenuOpen(false);
                  }}
                  role="menuitem"
                >
                  <SlidersHorizontal size={13} /> Uredi profile…
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="cterm-body">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className="cterm-view"
            style={{ display: active === tab.id ? "block" : "none" }}
          >
            <TerminalSplit
              panes={tab.panes}
              direction={tab.direction}
              visible={active === tab.id}
              activePaneId={tab.activePaneId}
              panelCwd={cwd}
              onFocusPane={(paneId) => focusPane(tab.id, paneId)}
              onClosePane={(paneId) => closePane(tab.id, paneId)}
              onExitPane={(paneId) => closePane(tab.id, paneId)}
              onMergePane={(srcId, targetId) =>
                mergePanesInTab(tab.id, srcId, targetId)
              }
              onBringToFront={(paneId) => bringToFront(tab.id, paneId)}
            />
          </div>
        ))}
      </div>

      {editorOpen && (
        <TerminalProfilesEditor
          shells={shells}
          profiles={profiles}
          onChange={updateProfiles}
          onClose={() => setEditorOpen(false)}
        />
      )}

      {tabMenu && (
        <div
          className="cterm-tab-menu"
          style={{ left: tabMenu.x, top: tabMenu.y }}
          role="menu"
          onClick={(event) => event.stopPropagation()}
          onContextMenu={(event) => event.preventDefault()}
        >
          <button
            type="button"
            className="cterm-menu-item"
            onClick={() => startRenameTab(tabMenu.id)}
            role="menuitem"
          >
            <Pencil size={13} /> Preimenuj
          </button>
          <button
            type="button"
            className="cterm-menu-item"
            onClick={() => duplicateTab(tabMenu.id)}
            role="menuitem"
          >
            <Copy size={13} /> Dupliciraj
          </button>
          <div className="cterm-menu-sep" />
          <div className="cterm-menu-label">Boja taba</div>
          <div className="cterm-color-row">
            {TAB_COLORS.map((color) => (
              <button
                key={color}
                type="button"
                className="cterm-swatch"
                style={{ background: color }}
                onClick={() => setTabColor(tabMenu.id, color)}
                aria-label={`Boja ${color}`}
              />
            ))}
            <button
              type="button"
              className="cterm-swatch none"
              onClick={() => setTabColor(tabMenu.id, undefined)}
              aria-label="Bez boje"
              title="Bez boje"
            >
              <X size={11} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default TerminalPanel;
