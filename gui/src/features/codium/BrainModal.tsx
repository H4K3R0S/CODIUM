import { useCallback, useEffect, useState } from "react";
import { BrainCircuit, FileText, RefreshCw, X } from "lucide-react";

import {
  generateBrain,
  getBrain,
  getBrainDevlog,
  getBrainFile,
} from "../../services/codiumApi";
import type { BrainInfo } from "../../types/codium";


// ==========          PROJECT BRAIN PANEL (read-only)          ==========

type BrainModalProps = {
  projectId: number;
  projectName: string;
  onClose: () => void;
};

// Poseban „virtuelni" izbor za dev-log INDEX.
const DEVLOG_KEY = "__devlog__";

/**
 * Read-only sadržaj `.codium/` foldera (lista fajlova + dev-log INDEX) bez
 * modal-okvira. Koristi ga modal (iz sidebara) i dockable „Brain" panel.
 */
export function BrainContent({ projectId }: { projectId: number }) {
  const [info, setInfo] = useState<BrainInfo | null>(null);
  const [selected, setSelected] = useState<string>("project.md");
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // `josTraje` kaze da li ekran jos stoji: odgovor koji kasni ne sme da
  // upise nista u komponentu koje vise nema.
  const loadInfo = useCallback(async (josTraje: () => boolean = () => true) => {
    setLoading(true);
    try {
      const data = await getBrain(projectId);
      if (!josTraje()) {
        return;
      }
      setInfo(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Učitavanje nije uspelo.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await loadInfo(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [loadInfo]);

  // Učitaj sadržaj izabranog fajla / dev-log-a kad se izbor ili stanje promeni.
  useEffect(() => {
    if (!info?.exists) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const result =
          selected === DEVLOG_KEY
            ? (await getBrainDevlog(projectId)).content
            : (await getBrainFile(projectId, selected)).content;
        if (!cancelled) {
          setContent(result);
        }
      } catch {
        if (!cancelled) {
          setContent("(fajl još nije dostupan)");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, selected, info]);

  async function handleGenerate(): Promise<void> {
    setBusy(true);
    try {
      await generateBrain(projectId);
      await loadInfo();
      setSelected("project.md");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {loading ? (
          <p className="cd-message">Učitavam…</p>
        ) : error ? (
          <p className="cd-message error">{error}</p>
        ) : !info?.exists ? (
          <div className="cd-empty">
            <p>Brain folder još nije napravljen za ovaj projekat.</p>
            <button
              type="button"
              className="cd-btn-primary"
              onClick={() => void handleGenerate()}
              disabled={busy}
              style={{ marginTop: 12 }}
            >
              <RefreshCw size={15} /> {busy ? "Generišem…" : "Generiši .codium"}
            </button>
          </div>
        ) : (
          <div className="cd-brain-body">
            <aside className="cd-brain-files">
              {info.files.map((file) => (
                <button
                  key={file.name}
                  type="button"
                  className={`cd-brain-file ${
                    selected === file.name ? "active" : ""
                  }`}
                  onClick={() => setSelected(file.name)}
                >
                  <FileText size={13} /> {file.name}
                </button>
              ))}
              <button
                type="button"
                className={`cd-brain-file ${
                  selected === DEVLOG_KEY ? "active" : ""
                }`}
                onClick={() => setSelected(DEVLOG_KEY)}
              >
                <FileText size={13} /> dev-log
              </button>
            </aside>

            <pre className="cd-brain-content">{content}</pre>
          </div>
        )}

      {info?.exists && (
        <p className="cd-brain-path" title={info.path}>
          {info.path}
        </p>
      )}
    </>
  );
}


// ==========          MODAL OMOTAČ (iz sidebara)          ==========

/** Modal-okvir oko `BrainContent` (isti sadržaj koristi i dockable panel). */
function BrainModal({ projectId, projectName, onClose }: BrainModalProps) {
  return (
    <div
      className="cd-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={`Project brain — ${projectName}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="cd-modal cd-brain">
        <div className="cd-modal-head">
          <h2 className="cd-modal-title">
            <BrainCircuit size={18} /> Brain · {projectName}
          </h2>
          <button
            type="button"
            className="cd-modal-close"
            onClick={onClose}
            aria-label="Zatvori"
          >
            <X size={18} />
          </button>
        </div>
        <BrainContent projectId={projectId} />
      </div>
    </div>
  );
}

export default BrainModal;
