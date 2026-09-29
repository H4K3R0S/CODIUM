import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactElement,
} from "react";
import {
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  File as FileIcon,
  FileArchive,
  FileCode2,
  FileJson2,
  FilePlus,
  FileText,
  FileType,
  FileVideo,
  Folder,
  FolderPlus,
  Image as ImageIcon,
  Music,
  Pencil,
  RefreshCw,
  Scissors,
  Search,
  Settings2,
  TerminalSquare,
  Trash2,
  type LucideIcon,
} from "lucide-react";

import {
  copyFileNode,
  createFileNode,
  deleteFileNode,
  listFiles,
  moveFileNode,
  renameFileNode,
  revealFileNode,
} from "../../services/codiumApi";
import { requestTerminalHere } from "../terminal/terminalBus";
import {
  categoryColor,
  fileCategory,
  folderColor,
  type FileCategory,
} from "./fileIcons";
import { canDropInto } from "./fileDnd";
import type { FileNode } from "../../types/codium";


// ==========          POMOĆNE          ==========

function parentOf(path: string): string {
  const parts = path.split("/");
  parts.pop();
  return parts.join("/");
}

function joinPath(parent: string, name: string): string {
  return parent ? `${parent}/${name}` : name;
}

/** Apsolutna putanja: koren projekta + relativna, u OS separatoru. */
function absolutePath(localPath: string | null, rel: string): string {
  if (!localPath) {
    return rel;
  }
  const sep = localPath.includes("\\") ? "\\" : "/";
  const relOs = rel.split("/").join(sep);
  const base = localPath.replace(/[\\/]+$/, "");
  return `${base}${sep}${relOs}`;
}

async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // Bez dozvole za clipboard — tiho preskoči.
  }
}

// Tipovi fajlova ponuđeni u „Novi fajl" podmeniju.
const NEW_FILE_TYPES: { label: string; ext: string }[] = [
  { label: "Tekst", ext: "txt" },
  { label: "Python", ext: "py" },
  { label: "HTML", ext: "html" },
  { label: "JavaScript", ext: "js" },
  { label: "Markdown", ext: "md" },
];


// Kategorija fajla → lucide ikonica. Boja se dodaje inline (categoryColor).
const CATEGORY_ICON: Record<FileCategory, LucideIcon> = {
  js: FileCode2,
  ts: FileCode2,
  python: FileCode2,
  rust: FileCode2,
  html: FileCode2,
  css: FileCode2,
  code: FileCode2,
  json: FileJson2,
  config: Settings2,
  shell: TerminalSquare,
  markdown: FileText,
  text: FileText,
  image: ImageIcon,
  video: FileVideo,
  audio: Music,
  archive: FileArchive,
  pdf: FileType,
  generic: FileIcon,
};

/** Ikonica fajla obojena po tipu (JS žuto, TS plavo, slika zeleno…). */
function FileGlyph({ name }: { name: string }): ReactElement {
  const category = fileCategory(name);
  const Icon = CATEGORY_ICON[category];
  return <Icon size={14} color={categoryColor(category)} />;
}


// ==========          KONTEKST MENI          ==========

type MenuState = { x: number; y: number; node: FileNode | null };

type ClipboardState = { path: string; mode: "cut" | "copy" } | null;


// ==========          FILE EXPLORER (F5)          ==========

type FileExplorerProps = {
  projectId: number;
  onOpenFile: (path: string) => void;
  activePath: string | null;
  /** Apsolutni koren projekta (za „Copy path"). */
  localPath?: string | null;
};

/**
 * Lazy fajl-stablo projekta. Desni klik otvara kontekst meni: na praznini/folderu
 * „Novi fajl" (po tipu) / „Novi folder" / „Nalepi"; na stavci Open in explorer,
 * Cut, Copy, Copy path, Copy relative path, Rename, Delete.
 */
function FileExplorer({
  projectId,
  onOpenFile,
  activePath,
  localPath,
}: FileExplorerProps) {
  const [children, setChildren] = useState<Record<string, FileNode[]>>({});
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [activeDir, setActiveDir] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const [creating, setCreating] = useState<
    { parent: string; kind: "file" | "dir" } | null
  >(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const [menu, setMenu] = useState<MenuState | null>(null);
  const [submenu, setSubmenu] = useState(false);
  const [clipboard, setClipboard] = useState<ClipboardState>(null);
  const createSelectRef = useRef<number | null>(null);

  // Drag-drop premeštanje: putanja koja se prevlači + trenutni cilj (za highlight).
  const [dragPath, setDragPath] = useState<string | null>(null);
  const [dropDir, setDropDir] = useState<string | null>(null);

  // `josTraje` kaže da li je panel još otvoren: odgovor koji kasni ne sme da
  // upiše spisak fajlova u komponentu koje više nema.
  const loadDir = useCallback(
    async (path: string, josTraje: () => boolean = () => true) => {
      try {
        const response = await listFiles(projectId, path);
        if (!josTraje()) {
          return;
        }
        setChildren((current) => ({ ...current, [path]: response.nodes }));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Listanje nije uspelo.");
      }
    },
    [projectId],
  );

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await loadDir("", () => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [loadDir]);

  // Zatvori meni na klik bilo gde ili Escape.
  useEffect(() => {
    if (!menu) {
      return;
    }
    const close = () => {
      setMenu(null);
      setSubmenu(false);
    };
    const onKey = (event: KeyboardEvent) => {
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
  }, [menu]);

  function toggle(path: string): void {
    setActiveDir(path);
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
        if (!children[path]) {
          void loadDir(path);
        }
      }
      return next;
    });
  }

  async function refresh(): Promise<void> {
    await loadDir("");
    for (const path of expanded) {
      await loadDir(path);
    }
  }

  function collapseAll(): void {
    setExpanded(new Set());
    setActiveDir("");
  }

  // ---------- kreiranje ----------

  function startCreate(kind: "file" | "dir", parent = activeDir): void {
    if (parent && !expanded.has(parent)) {
      toggle(parent);
    }
    setCreating({ parent, kind });
    setDraft("");
    createSelectRef.current = null;
    setRenaming(null);
  }

  /** „Novi fajl" po tipu: inline unos sa prefiliranom ekstenzijom, ime selektovano. */
  function startCreateTyped(ext: string, parent: string): void {
    if (parent && !expanded.has(parent)) {
      toggle(parent);
    }
    setCreating({ parent, kind: "file" });
    setDraft(`novo.${ext}`);
    // Selektuj bazni deo imena (pre tačke) da korisnik samo otkuca naziv.
    createSelectRef.current = "novo".length;
    setRenaming(null);
  }

  async function commitCreate(): Promise<void> {
    if (!creating) {
      return;
    }
    const name = draft.trim();
    const { parent, kind } = creating;
    setCreating(null);
    setDraft("");
    if (name === "") {
      return;
    }
    try {
      await createFileNode(projectId, joinPath(parent, name), kind);
      await loadDir(parent);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kreiranje nije uspelo.");
    }
  }

  // ---------- rename ----------

  function startRename(path: string): void {
    setRenaming(path);
    setDraft(path.split("/").pop() ?? "");
    setCreating(null);
  }

  async function commitRename(path: string): Promise<void> {
    const name = draft.trim();
    setRenaming(null);
    setDraft("");
    if (name === "" || name === path.split("/").pop()) {
      return;
    }
    try {
      await renameFileNode(projectId, path, name);
      await loadDir(parentOf(path));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preimenovanje nije uspelo.");
    }
  }

  async function remove(node: FileNode): Promise<void> {
    const label = node.is_dir ? "folder (i sav sadržaj)" : "fajl";
    if (!window.confirm(`Obrisati ${label} „${node.name}"?`)) {
      return;
    }
    try {
      await deleteFileNode(projectId, node.path);
      await loadDir(parentOf(node.path));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Brisanje nije uspelo.");
    }
  }

  // ---------- kontekst meni akcije ----------

  function openMenu(event: React.MouseEvent, node: FileNode | null): void {
    event.preventDefault();
    event.stopPropagation();
    setSubmenu(false);
    setMenu({ x: event.clientX, y: event.clientY, node });
  }

  /** Ciljni folder za „Novi …/Nalepi": folder-node ili koren. */
  function targetDir(node: FileNode | null): string {
    if (!node) {
      return "";
    }
    return node.is_dir ? node.path : parentOf(node.path);
  }

  async function paste(node: FileNode | null): Promise<void> {
    if (!clipboard) {
      return;
    }
    const dir = targetDir(node);
    try {
      if (clipboard.mode === "copy") {
        await copyFileNode(projectId, clipboard.path, dir);
      } else {
        await moveFileNode(projectId, clipboard.path, dir);
        await loadDir(parentOf(clipboard.path));
      }
      setClipboard(clipboard.mode === "cut" ? null : clipboard);
      await loadDir(dir);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nalepljivanje nije uspelo.");
    }
  }

  // ---------- drag-drop premeštanje ----------

  /** Premesti prevučenu stavku u folder `destDir` („" = koren) i osveži oba. */
  async function moveInto(destDir: string): Promise<void> {
    const src = dragPath;
    setDragPath(null);
    setDropDir(null);
    if (!src || !canDropInto(src, destDir)) {
      return;
    }
    try {
      await moveFileNode(projectId, src, destDir);
      await loadDir(parentOf(src));
      if (destDir !== "" && !expanded.has(destDir)) {
        setExpanded((current) => new Set(current).add(destDir));
      }
      await loadDir(destDir);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Premeštanje nije uspelo.");
    }
  }

  async function reveal(node: FileNode): Promise<void> {
    try {
      await revealFileNode(projectId, node.path);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Otvaranje nije uspelo.");
    }
  }

  // ---------- render ----------

  function renderCreateInput(parent: string, depth: number): ReactElement | null {
    if (!creating || creating.parent !== parent) {
      return null;
    }
    return (
      <div
        className="cdx-row cdx-input-row"
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        {creating.kind === "dir" ? <Folder size={14} /> : <FileIcon size={14} />}
        <input
          autoFocus
          value={draft}
          onFocus={(event) => {
            if (createSelectRef.current != null) {
              event.target.setSelectionRange(0, createSelectRef.current);
              createSelectRef.current = null;
            }
          }}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={() => void commitCreate()}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              void commitCreate();
            } else if (event.key === "Escape") {
              setCreating(null);
            }
          }}
          placeholder={creating.kind === "dir" ? "novi-folder" : "novi-fajl.txt"}
          aria-label="Ime nove stavke"
        />
      </div>
    );
  }

  function renderNodes(path: string, depth: number): ReactElement[] {
    const list = children[path] ?? [];
    const needle = query.trim().toLowerCase();
    const visible = needle
      ? list.filter((node) => node.name.toLowerCase().includes(needle))
      : list;

    return visible.map((node) => {
      const isOpen = expanded.has(node.path);
      const isRenaming = renaming === node.path;
      const isCut = clipboard?.mode === "cut" && clipboard.path === node.path;
      // Folder je meta drop-a (osim za samog sebe / sopstveno podstablo).
      const canDrop =
        node.is_dir && dragPath !== null && canDropInto(dragPath, node.path);
      const isDropDir = canDrop && dropDir === node.path;
      return (
        <div key={node.path}>
          <div
            className={`cdx-row ${activePath === node.path ? "active" : ""} ${
              isCut ? "cut" : ""
            } ${isDropDir ? "drop-target" : ""} ${
              dragPath === node.path ? "dragging" : ""
            }`}
            style={{ paddingLeft: 8 + depth * 14 }}
            draggable={!isRenaming}
            onDragStart={(event) => {
              event.dataTransfer.setData("text/plain", node.path);
              event.dataTransfer.effectAllowed = "move";
              setDragPath(node.path);
            }}
            onDragEnd={() => {
              setDragPath(null);
              setDropDir(null);
            }}
            onDragOver={
              canDrop
                ? (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    event.dataTransfer.dropEffect = "move";
                    setDropDir(node.path);
                  }
                : undefined
            }
            onDragLeave={
              canDrop
                ? () => setDropDir((d) => (d === node.path ? null : d))
                : undefined
            }
            onDrop={
              node.is_dir
                ? (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    void moveInto(node.path);
                  }
                : undefined
            }
            onContextMenu={(event) => openMenu(event, node)}
          >
            {node.is_dir ? (
              <button
                type="button"
                className="cdx-name"
                onClick={() => toggle(node.path)}
              >
                {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                <Folder size={14} color={folderColor(node.path)} />
                {isRenaming ? null : <span>{node.name}</span>}
              </button>
            ) : (
              <button
                type="button"
                className="cdx-name"
                onClick={() => onOpenFile(node.path)}
              >
                <span className="cdx-spacer" />
                <FileGlyph name={node.name} />
                {isRenaming ? null : <span>{node.name}</span>}
              </button>
            )}

            {isRenaming && (
              <input
                autoFocus
                className="cdx-rename"
                value={draft}
                onFocus={(event) => {
                  const dot = draft.lastIndexOf(".");
                  event.target.setSelectionRange(0, dot > 0 ? dot : draft.length);
                }}
                onChange={(event) => setDraft(event.target.value)}
                onBlur={() => void commitRename(node.path)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    void commitRename(node.path);
                  } else if (event.key === "Escape") {
                    setRenaming(null);
                  }
                }}
                aria-label="Novo ime"
              />
            )}

            <span className="cdx-actions">
              <button
                type="button"
                onClick={() => startRename(node.path)}
                title="Preimenuj"
                aria-label={`Preimenuj ${node.name}`}
              >
                <Pencil size={12} />
              </button>
              <button
                type="button"
                onClick={() => void remove(node)}
                title="Obriši"
                aria-label={`Obriši ${node.name}`}
              >
                <Trash2 size={12} />
              </button>
            </span>
          </div>

          {node.is_dir && isOpen && (
            <>
              {renderCreateInput(node.path, depth + 1)}
              {renderNodes(node.path, depth + 1)}
            </>
          )}
        </div>
      );
    });
  }

  // ---------- kontekst meni (render) ----------

  function renderMenu(): ReactElement | null {
    if (!menu) {
      return null;
    }
    const { node } = menu;
    const isFolderLike = node === null || node.is_dir;
    const style = { left: menu.x, top: menu.y } as const;

    return (
      <div
        className="cdx-menu"
        style={style}
        onClick={(event) => event.stopPropagation()}
        onContextMenu={(event) => event.preventDefault()}
      >
        {isFolderLike && (
          <>
            <div
              className="cdx-menu-item has-sub"
              onMouseEnter={() => setSubmenu(true)}
              onMouseLeave={() => setSubmenu(false)}
            >
              <span>
                <FilePlus size={13} /> Novi fajl
              </span>
              <ChevronRight size={13} />
              {submenu && (
                <div className="cdx-submenu">
                  {NEW_FILE_TYPES.map((type) => (
                    <button
                      key={type.ext}
                      type="button"
                      className="cdx-menu-item"
                      onClick={() => {
                        startCreateTyped(type.ext, targetDir(node));
                        setMenu(null);
                        setSubmenu(false);
                      }}
                    >
                      {type.label} <code>.{type.ext}</code>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              type="button"
              className="cdx-menu-item"
              onClick={() => {
                startCreate("dir", targetDir(node));
                setMenu(null);
              }}
            >
              <FolderPlus size={13} /> Novi folder
            </button>
            {clipboard && (
              <button
                type="button"
                className="cdx-menu-item"
                onClick={() => {
                  void paste(node);
                  setMenu(null);
                }}
              >
                <Copy size={13} /> Nalepi
              </button>
            )}
            {localPath && (
              <button
                type="button"
                className="cdx-menu-item"
                onClick={() => {
                  const rel = targetDir(node);
                  const dirAbs =
                    rel === "" ? localPath : absolutePath(localPath, rel);
                  requestTerminalHere(dirAbs);
                  setMenu(null);
                }}
              >
                <TerminalSquare size={13} /> Otvori terminal ovde
              </button>
            )}
          </>
        )}

        {node && (
          <>
            {isFolderLike && <div className="cdx-menu-sep" />}
            <button
              type="button"
              className="cdx-menu-item"
              onClick={() => {
                void reveal(node);
                setMenu(null);
              }}
            >
              <ExternalLink size={13} /> Open in explorer
            </button>
            <button
              type="button"
              className="cdx-menu-item"
              onClick={() => {
                setClipboard({ path: node.path, mode: "cut" });
                setMenu(null);
              }}
            >
              <Scissors size={13} /> Cut
            </button>
            <button
              type="button"
              className="cdx-menu-item"
              onClick={() => {
                setClipboard({ path: node.path, mode: "copy" });
                setMenu(null);
              }}
            >
              <Copy size={13} /> Copy
            </button>
            <button
              type="button"
              className="cdx-menu-item"
              onClick={() => {
                void copyToClipboard(absolutePath(localPath ?? null, node.path));
                setMenu(null);
              }}
            >
              Copy path
            </button>
            <button
              type="button"
              className="cdx-menu-item"
              onClick={() => {
                void copyToClipboard(node.path);
                setMenu(null);
              }}
            >
              Copy relative path
            </button>
            <div className="cdx-menu-sep" />
            <button
              type="button"
              className="cdx-menu-item"
              onClick={() => {
                startRename(node.path);
                setMenu(null);
              }}
            >
              <Pencil size={13} /> Rename
            </button>
            <button
              type="button"
              className="cdx-menu-item danger"
              onClick={() => {
                void remove(node);
                setMenu(null);
              }}
            >
              <Trash2 size={13} /> Delete
            </button>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="cdx-explorer">
      <div className="cdx-toolbar">
        <button
          type="button"
          onClick={() => startCreate("file")}
          title="Nov fajl"
          aria-label="Nov fajl"
        >
          <FilePlus size={14} />
        </button>
        <button
          type="button"
          onClick={() => startCreate("dir")}
          title="Nov folder"
          aria-label="Nov folder"
        >
          <FolderPlus size={14} />
        </button>
        <button
          type="button"
          onClick={() => void refresh()}
          title="Osveži"
          aria-label="Osveži"
        >
          <RefreshCw size={14} />
        </button>
        <button
          type="button"
          onClick={collapseAll}
          title="Skupi sve"
          aria-label="Skupi sve"
        >
          <ChevronRight size={14} />
        </button>
      </div>

      <div className="cdx-search">
        <Search size={13} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Pretraga fajlova…"
          aria-label="Pretraga fajlova"
        />
      </div>

      {error && <p className="cdx-error">{error}</p>}

      <div
        className={`cdx-tree ${dropDir === "" ? "drop-root" : ""}`}
        onDragOver={
          dragPath !== null && canDropInto(dragPath, "")
            ? (event) => {
                event.preventDefault();
                event.dataTransfer.dropEffect = "move";
                setDropDir("");
              }
            : undefined
        }
        onDragLeave={(event) => {
          // Napusti koren-highlight samo ako miš izađe iz stabla.
          if (event.target === event.currentTarget) {
            setDropDir((d) => (d === "" ? null : d));
          }
        }}
        onDrop={(event) => {
          event.preventDefault();
          void moveInto("");
        }}
        onContextMenu={(event) => {
          // Desni klik na praznину stabla → meni za koren.
          if (event.target === event.currentTarget) {
            openMenu(event, null);
          }
        }}
      >
        {renderCreateInput("", 0)}
        {renderNodes("", 0)}
        {(children[""] ?? []).length === 0 && !creating && (
          <p className="cdx-empty">Prazan folder. Desni klik → Novi fajl.</p>
        )}
      </div>

      {renderMenu()}
    </div>
  );
}

export default FileExplorer;
