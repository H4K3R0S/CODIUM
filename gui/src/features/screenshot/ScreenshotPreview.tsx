import { useEffect } from "react";
import { useNavigate } from "react-router";
import { Check, Copy, FolderOpen, Pencil, X } from "lucide-react";

import { revealPath, type ShotResult } from "./screenshotApi";


// ==========          PREGLED SNIMKA + AKCIJE          ==========
/*
 * Snimak je u trenutku otvaranja već sačuvan na disk i (obično) u clipboard-u.
 * Panel prikazuje umanjeni pregled i nudi akcije nad sačuvanim fajlom.
 */

type ScreenshotPreviewProps = {
  result: ShotResult | null;
  error: string | null;
  onClose: () => void;
};

function ScreenshotPreview({ result, error, onClose }: ScreenshotPreviewProps) {
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="shot-preview-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Pregled snimka ekrana"
      onClick={onClose}
    >
      <div className="shot-preview" onClick={(event) => event.stopPropagation()}>
        <header className="shot-preview-head">
          <h2>{error ? "Snimak nije uspeo" : "Snimak sačuvan"}</h2>
          <button
            type="button"
            className="shot-preview-close"
            aria-label="Zatvori"
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </header>

        {error ? (
          <p className="shot-preview-error">{error}</p>
        ) : (
          result && (
            <>
              <div className="shot-preview-image">
                <img src={result.preview_base64} alt="Snimak ekrana" />
              </div>

              <p className="shot-preview-meta">
                {result.width}×{result.height} ·{" "}
                <span
                  className={
                    result.clipboard ? "shot-clip-ok" : "shot-clip-fail"
                  }
                >
                  {result.clipboard ? (
                    <>
                      <Check size={13} /> u clipboard-u
                    </>
                  ) : (
                    "clipboard nije uspeo"
                  )}
                </span>
              </p>

              <p className="shot-preview-path" title={result.path}>
                {result.path}
              </p>

              <div className="shot-preview-actions">
                <button
                  type="button"
                  onClick={() => revealPath(result.path, true)}
                >
                  <FolderOpen size={15} /> Otvori folder
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard?.writeText(result.path);
                  }}
                >
                  <Copy size={15} /> Kopiraj putanju
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    navigate("/photo-editor", { state: { sourcePath: result.path } });
                  }}
                >
                  <Pencil size={15} /> Editor
                </button>
              </div>
            </>
          )
        )}
      </div>
    </div>
  );
}

export default ScreenshotPreview;
