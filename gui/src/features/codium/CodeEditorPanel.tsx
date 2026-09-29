import { useCallback, useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { FileCode2, Save, X } from "lucide-react";

import { readFileContent, writeFileContent } from "../../services/codiumApi";


// ==========          POMOĆNE          ==========

// Monaco jezik po ekstenziji fajla (podskup; ostalo → plaintext).
const LANGUAGE_BY_EXT: Record<string, string> = {
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  jsx: "javascript",
  py: "python",
  json: "json",
  css: "css",
  scss: "scss",
  html: "html",
  md: "markdown",
  yml: "yaml",
  yaml: "yaml",
  toml: "ini",
  sh: "shell",
  rs: "rust",
  go: "go",
  sql: "sql",
};

function languageFor(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  return LANGUAGE_BY_EXT[ext] ?? "plaintext";
}

function baseName(path: string): string {
  return path.split("/").pop() ?? path;
}


// ==========          CODE EDITOR PANEL (F6)          ==========

type CodeEditorPanelProps = {
  projectId: number;
  /** Putanja fajla koji Explorer traži da otvori (nova vrednost = nov tab). */
  fileToOpen: string | null;
};

/**
 * Monaco editor sa više tabova. Otvoreni fajlovi postaju tabovi; prati se dirty
 * stanje; Save (Ctrl+S) i Save all pišu kroz API. Jezik se bira po ekstenziji.
 */
function CodeEditorPanel({ projectId, fileToOpen }: CodeEditorPanelProps) {
  const [tabs, setTabs] = useState<string[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [content, setContent] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, string>>({});
  const [readOnlyNote, setReadOnlyNote] = useState<Record<string, string>>({});

  // `josTraje` kaže da li je panel još otvoren: fajl koji se dugo čita ne sme
  // da otvori karticu u komponenti koje više nema.
  const openFile = useCallback(
    async (path: string, josTraje: () => boolean = () => true) => {
      if (tabs.includes(path)) {
        setActive(path);
        return;
      }
      try {
        const file = await readFileContent(projectId, path);
        if (!josTraje()) {
          return;
        }
        const value = file.binary
          ? ""
          : file.truncated
            ? ""
            : file.content;
        setContent((current) => ({ ...current, [path]: value }));
        setSaved((current) => ({ ...current, [path]: value }));
        setReadOnlyNote((current) => ({
          ...current,
          [path]: file.binary
            ? "Binarni fajl — nije za uređivanje."
            : file.truncated
              ? "Fajl je prevelik za uređivanje."
              : "",
        }));
        // Dedup u funkcionalnom update-u: dva brza poziva (stari closure `tabs`)
        // ne smeju da dodaju isti tab dvaput (React „duplicate key").
        setTabs((current) =>
          current.includes(path) ? current : [...current, path],
        );
        setActive(path);
      } catch {
        /* fajl nedostupan — ignoriši */
      }
    },
    [projectId, tabs],
  );

  useEffect(() => {
    if (!fileToOpen) {
      return;
    }
    let ziv = true;
    async function pokreni() {
      await openFile(fileToOpen as string, () => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
    // openFile menja identitet sa tabs; namerno pratimo samo fileToOpen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileToOpen]);

  const isDirty = useCallback(
    (path: string) => content[path] !== saved[path],
    [content, saved],
  );

  async function save(path: string | null): Promise<void> {
    if (!path || readOnlyNote[path] || !isDirty(path)) {
      return;
    }
    try {
      await writeFileContent(projectId, path, content[path] ?? "");
      setSaved((current) => ({ ...current, [path]: content[path] ?? "" }));
    } catch {
      /* zadrži dirty stanje */
    }
  }

  // Uvek svež „save active" za Monaco Ctrl+S komandu (izbegava stari closure).
  // Upis ide u efekat: telo crtanja sme samo da čita.
  const saveActiveRef = useRef<() => void>(() => {});
  useEffect(() => {
    saveActiveRef.current = () => {
      void save(active);
    };
  });

  async function saveAll(): Promise<void> {
    for (const path of tabs) {
      if (isDirty(path) && !readOnlyNote[path]) {
        await save(path);
      }
    }
  }

  function closeTab(path: string): void {
    if (isDirty(path) && !window.confirm(`Zatvoriti „${baseName(path)}" bez čuvanja?`)) {
      return;
    }
    setTabs((current) => {
      const next = current.filter((tab) => tab !== path);
      setActive((currentActive) =>
        currentActive === path ? (next[next.length - 1] ?? null) : currentActive,
      );
      return next;
    });
  }

  const dirtyCount = tabs.filter((path) => isDirty(path) && !readOnlyNote[path]).length;

  if (tabs.length === 0 || active === null) {
    return (
      <div className="cdw-editor-body cdw-placeholder">
        <FileCode2 size={30} />
        <p>Izaberi fajl iz Explorer-a.</p>
      </div>
    );
  }

  const activeNote = readOnlyNote[active];

  return (
    <>
      <div className="cde-tabbar">
        <div className="cde-tabs">
          {tabs.map((path) => (
            <div
              key={path}
              className={`cde-tab ${active === path ? "active" : ""}`}
            >
              <button
                type="button"
                className="cde-tab-name"
                onClick={() => setActive(path)}
              >
                {isDirty(path) && !readOnlyNote[path] && (
                  <span className="cde-dot" aria-label="Nesačuvano" />
                )}
                {baseName(path)}
              </button>
              <button
                type="button"
                className="cde-tab-close"
                onClick={() => closeTab(path)}
                aria-label={`Zatvori ${baseName(path)}`}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
        <div className="cde-actions">
          <button
            type="button"
            className="cde-save"
            onClick={() => void save(active)}
            disabled={!isDirty(active) || !!activeNote}
            title="Sačuvaj (Ctrl+S)"
          >
            <Save size={13} /> Sačuvaj
          </button>
          <button
            type="button"
            className="cde-save"
            onClick={() => void saveAll()}
            disabled={dirtyCount === 0}
            title="Sačuvaj sve"
          >
            Sve ({dirtyCount})
          </button>
        </div>
      </div>

      {activeNote ? (
        <div className="cdw-editor-body cdw-placeholder">
          <FileCode2 size={30} />
          <p>{activeNote}</p>
        </div>
      ) : (
        <div className="cde-editor-wrap">
          <Editor
            height="100%"
            theme="core-editor"
            path={active}
            language={languageFor(active)}
            value={content[active] ?? ""}
            onChange={(value) =>
              setContent((current) => ({ ...current, [active]: value ?? "" }))
            }
            beforeMount={(monaco) => {
              // Providna Monaco tema — 50% tint dolazi iza (.cde-editor-wrap),
              // pa se editor slaže sa ostalim (providnim) panelima.
              monaco.editor.defineTheme("core-editor", {
                base: "vs-dark",
                inherit: true,
                rules: [],
                colors: {
                  "editor.background": "#00000000",
                  "minimap.background": "#00000000",
                  "editorGutter.background": "#00000000",
                  "editorStickyScroll.background": "#00000000",
                  "editorOverviewRuler.background": "#00000000",
                },
              });
            }}
            onMount={(editor, monaco) => {
              editor.addCommand(
                monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
                () => saveActiveRef.current(),
              );
              // U flex/grid kontejneru automaticLayout ume da promaši prvu
              // meru — ručno relayout posle mount-a.
              requestAnimationFrame(() => editor.layout());
              setTimeout(() => editor.layout(), 60);
            }}
            options={{
              fontSize: 13,
              minimap: { enabled: true },
              automaticLayout: true,
              scrollBeyondLastLine: false,
              tabSize: 2,
            }}
          />
        </div>
      )}
    </>
  );
}

export default CodeEditorPanel;
