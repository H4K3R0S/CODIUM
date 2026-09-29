import { createElement, useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { ExternalLink, X } from "lucide-react";

import type { BrainFile, BrainNode } from "../../types/secondBrain";
import { getBrainFile } from "../../services/secondBrainApi";
import { groupColor, iconFor } from "./brainColors";
import { renderMarkdown } from "./markdown";

type BrainContentPanelProps = {
  node: BrainNode | null;
  onOpen: (node: BrainNode) => void;
  onClose: () => void;
};

// Monaco jezik po ekstenziji (podskup; ostalo → plaintext).
const LANGUAGE_BY_EXT: Record<string, string> = {
  ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript",
  py: "python", json: "json", css: "css", scss: "scss", html: "html",
  yml: "yaml", yaml: "yaml", toml: "ini", sh: "shell", rs: "rust", go: "go",
  sql: "sql", md: "markdown", markdown: "markdown",
};

function extOf(path: string): string {
  return path.split(".").pop()?.toLowerCase() ?? "";
}

function baseName(path: string): string {
  return path.split("/").pop() ?? path;
}

/**
 * Levi panel (uz sidebar) sa sadrzajem izabranog fajla. Markdown se renderuje
 * formatirano; kod se prikazuje u read-only Monaco editoru (syntax highlight).
 */
function BrainContentPanel({ node, onOpen, onClose }: BrainContentPanelProps) {
  const [file, setFile] = useState<BrainFile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const path = node?.path ?? null;

  useEffect(() => {
    if (!path) {
      return;
    }
    let alive = true;
    void (async () => {
      setIsLoading(true);
      setErrorMessage(null);
      setFile(null);
      try {
        const data = await getBrainFile(path);
        if (alive) {
          setFile(data);
        }
      } catch (error) {
        if (alive) {
          setErrorMessage(error instanceof Error ? error.message : "Citanje fajla nije uspelo.");
        }
      } finally {
        if (alive) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [path]);

  if (node === null || path === null) {
    return null;
  }

  const color = groupColor(node.group);
  const ext = extOf(path);
  const isMarkdown = ext === "md" || ext === "markdown";

  return (
    <aside className="brain-content-panel" data-testid="brain-content-panel" aria-label="Sadrzaj fajla">
      <header className="brain-content-head">
        <span className="brain-content-icon" style={{ color }}>
          {createElement(iconFor(node.icon), { size: 18 })}
        </span>
        <div className="brain-content-titles">
          <h2 className="brain-content-title">{baseName(path)}</h2>
          <p className="brain-content-path">{path}</p>
        </div>
        {node.route && (
          <button
            className="brain-content-open"
            type="button"
            onClick={() => onOpen(node)}
            title="Otvori u domenu"
          >
            <ExternalLink size={14} />
          </button>
        )}
        <button className="brain-content-close" type="button" aria-label="Zatvori" onClick={onClose}>
          <X size={16} />
        </button>
      </header>

      <div className="brain-content-body">
        {isLoading && <p className="brain-content-note">Ucitavam…</p>}
        {errorMessage && <p className="brain-content-note error">{errorMessage}</p>}
        {file && file.binary && <p className="brain-content-note">Binarni fajl — nema pregleda.</p>}
        {file && file.truncated && <p className="brain-content-note">Fajl je prevelik za pregled.</p>}
        {file && !file.binary && !file.truncated && isMarkdown && (
          <div className="bm" data-testid="brain-markdown">{renderMarkdown(file.content)}</div>
        )}
        {file && !file.binary && !file.truncated && !isMarkdown && (
          <div className="brain-content-code">
            <Editor
              height="100%"
              theme="core-editor"
              path={path}
              language={LANGUAGE_BY_EXT[ext] ?? "plaintext"}
              value={file.content}
              beforeMount={(monaco) => {
                monaco.editor.defineTheme("core-editor", {
                  base: "vs-dark",
                  inherit: true,
                  rules: [],
                  colors: {
                    "editor.background": "#00000000",
                    "minimap.background": "#00000000",
                    "editorGutter.background": "#00000000",
                  },
                });
              }}
              options={{
                readOnly: true,
                domReadOnly: true,
                fontSize: 12,
                minimap: { enabled: false },
                automaticLayout: true,
                scrollBeyondLastLine: false,
                lineNumbers: "on",
                folding: true,
              }}
            />
          </div>
        )}
      </div>
    </aside>
  );
}

export default BrainContentPanel;
