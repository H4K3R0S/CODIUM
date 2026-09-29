import { useEffect, useMemo, useState } from "react";
import { Monitor, Play, RefreshCw, Square, X } from "lucide-react";

import {
  getDevServerStatus,
  startDevServer,
  stopDevServer,
} from "../../services/codiumApi";
import { isTauri } from "../window/windowManager";
import {
  PREVIEW_DEVICES,
  normalizePreviewUrl,
  resolvePreviewSize,
  type PreviewDevice,
} from "./previewProfiles";
import {
  closePreview,
  listPreviewMonitors,
  openPreview,
  type PreviewMonitor,
} from "./previewOrchestrator";


// ==========          TRAJNE POSTAVKE (localStorage)          ==========

type PreviewPrefs = {
  url: string;
  device: PreviewDevice;
  customWidth: number;
  customHeight: number;
  monitorName: string;
};

function prefsKey(projectId: number): string {
  return `codium.preview.${projectId}`;
}

function loadPrefs(projectId: number, fallbackUrl: string): PreviewPrefs {
  const base: PreviewPrefs = {
    url: fallbackUrl,
    device: "desktop",
    customWidth: 1280,
    customHeight: 800,
    monitorName: "",
  };
  try {
    const raw = window.localStorage.getItem(prefsKey(projectId));
    if (!raw) {
      return base;
    }
    return { ...base, ...(JSON.parse(raw) as Partial<PreviewPrefs>) };
  } catch {
    return base;
  }
}

function savePrefs(projectId: number, prefs: PreviewPrefs): void {
  try {
    window.localStorage.setItem(prefsKey(projectId), JSON.stringify(prefs));
  } catch {
    // localStorage nedostupan — postavke se prosto ne pamte.
  }
}


// ==========          PREVIEW MODAL (F7)          ==========

type PreviewModalProps = {
  projectId: number;
  projectName: string;
  /** Predlog URL-a iz projekta (preview/staging/live). */
  initialUrl: string;
  onClose: () => void;
};

/**
 * Orkestrira preview prozor projekta: unos URL-a (dev server / staging / live),
 * izbor uređaja (Desktop/Tablet/Mobilni/Prilagođeno) i monitora, pa otvara
 * zaseban Tauri prozor. Radi samo u desktop aplikaciji; u browseru je pregled
 * postavki (dugmad onemogućena uz napomenu).
 */
function PreviewModal({
  projectId,
  projectName,
  initialUrl,
  onClose,
}: PreviewModalProps) {
  const tauri = isTauri();
  const [prefs, setPrefs] = useState<PreviewPrefs>(() =>
    loadPrefs(projectId, initialUrl),
  );
  const [monitors, setMonitors] = useState<PreviewMonitor[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [hostRunning, setHostRunning] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void listPreviewMonitors().then((list) => {
      if (active) {
        setMonitors(list);
      }
    });
    // Stanje lokalnog hosta (da li dev server već radi).
    void getDevServerStatus(projectId)
      .then((status) => {
        if (active) {
          setHostRunning(status.running);
        }
      })
      .catch(() => {
        /* status nije kritičan za UI */
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const size = useMemo(
    () =>
      resolvePreviewSize(prefs.device, {
        width: prefs.customWidth,
        height: prefs.customHeight,
      }),
    [prefs.device, prefs.customWidth, prefs.customHeight],
  );

  function patch(change: Partial<PreviewPrefs>): void {
    setPrefs((current) => ({ ...current, ...change }));
  }

  async function handleOpen(): Promise<void> {
    const url = normalizePreviewUrl(prefs.url);
    if (!url) {
      setMessage("Unesi ispravan URL (npr. http://localhost:5173).");
      return;
    }
    savePrefs(projectId, prefs);

    if (!tauri) {
      setMessage("Preview prozor radi samo u desktop aplikaciji (Tauri).");
      return;
    }

    await openPreview({
      projectId,
      url,
      size,
      title: `Preview — ${projectName}`,
      monitorName: prefs.monitorName || undefined,
    });
    setIsOpen(true);
    setMessage(`Otvoren preview: ${url} (${size.width}×${size.height}).`);
  }

  async function handleClose(): Promise<void> {
    await closePreview(projectId);
    setIsOpen(false);
    setMessage("Preview prozor zatvoren.");
  }

  /** Pokreće lokalni host projekta pa otvara preview na njegovom URL-u. */
  async function handleStartHostAndOpen(): Promise<void> {
    setBusy(true);
    try {
      const status = await startDevServer(projectId);
      setHostRunning(status.running);
      savePrefs(projectId, prefs);
      if (!tauri) {
        setMessage(
          "Host pokrenut. Preview prozor se otvara samo u desktop aplikaciji.",
        );
        return;
      }
      const url = normalizePreviewUrl(prefs.url) ?? status.preview_url;
      if (!url) {
        setMessage("Host pokrenut, ali nema preview URL-a.");
        return;
      }
      // Dev server-u treba trenutak da počne da sluša na portu.
      await new Promise((resolve) => setTimeout(resolve, 1200));
      await openPreview({
        projectId,
        url,
        size,
        title: `Preview — ${projectName}`,
        monitorName: prefs.monitorName || undefined,
      });
      setIsOpen(true);
      setMessage(`Host radi, preview otvoren: ${url}.`);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? `Host nije pokrenut: ${error.message}`
          : "Host nije pokrenut.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleStopHost(): Promise<void> {
    setBusy(true);
    try {
      await stopDevServer(projectId);
      setHostRunning(false);
      setMessage("Lokalni host zaustavljen.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Gašenje nije uspelo.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="cd-modal-overlay" onClick={onClose}>
      <div className="cd-modal" onClick={(event) => event.stopPropagation()}>
        <div className="cd-modal-head">
          <h2 className="cd-modal-title">
            <Monitor size={18} /> Preview — {projectName}
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

        <div className="cd-modal-body">
          {/* URL */}
          <label className="cd-field">
            <span className="cd-field-label">URL (dev server / staging / live)</span>
            <input
              type="text"
              value={prefs.url}
              onChange={(event) => patch({ url: event.target.value })}
              placeholder="http://localhost:5173"
              aria-label="Preview URL"
            />
          </label>

          {/* Uređaj */}
          <div className="cd-field">
            <span className="cd-field-label">Uređaj</span>
            <div className="cd-preview-devices">
              {PREVIEW_DEVICES.map((device) => (
                <button
                  key={device.id}
                  type="button"
                  className={`cd-preview-device ${
                    prefs.device === device.id ? "active" : ""
                  }`}
                  onClick={() => patch({ device: device.id })}
                >
                  {device.label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom dimenzije */}
          {prefs.device === "custom" && (
            <div className="cd-field-row">
              <label className="cd-field">
                <span className="cd-field-label">Širina</span>
                <input
                  type="number"
                  value={prefs.customWidth}
                  onChange={(event) =>
                    patch({ customWidth: Number(event.target.value) })
                  }
                  aria-label="Širina"
                />
              </label>
              <label className="cd-field">
                <span className="cd-field-label">Visina</span>
                <input
                  type="number"
                  value={prefs.customHeight}
                  onChange={(event) =>
                    patch({ customHeight: Number(event.target.value) })
                  }
                  aria-label="Visina"
                />
              </label>
            </div>
          )}

          {/* Monitor */}
          {monitors.length > 1 && (
            <label className="cd-field">
              <span className="cd-field-label">Monitor</span>
              <select
                value={prefs.monitorName}
                onChange={(event) => patch({ monitorName: event.target.value })}
                aria-label="Monitor"
              >
                <option value="">Primarni</option>
                {monitors.map((monitor) => (
                  <option key={monitor.name} value={monitor.name}>
                    {monitor.name} ({monitor.width}×{monitor.height})
                  </option>
                ))}
              </select>
            </label>
          )}

          <div className="cd-preview-statusrow">
            <span className="cd-preview-size">
              Veličina prozora: <strong>{size.width}×{size.height}</strong>
            </span>
            <span
              className={`cd-host-badge ${hostRunning ? "on" : "off"}`}
              aria-label="Stanje lokalnog hosta"
            >
              {hostRunning ? "Host radi" : "Host ne radi"}
            </span>
          </div>

          {!tauri && (
            <p className="cd-preview-note">
              Napomena: preview prozor se otvara samo u desktop aplikaciji.
            </p>
          )}

          {message && <p className="cd-preview-message">{message}</p>}
        </div>

        <div className="cd-modal-actions">
          <button
            type="button"
            className="cd-btn-primary"
            onClick={() => void handleStartHostAndOpen()}
            disabled={busy}
          >
            <Play size={16} /> {busy ? "Pokrećem…" : "Pokreni host + otvori"}
          </button>
          <button
            type="button"
            className="cd-action"
            onClick={() => void handleOpen()}
            title="Otvori bez pokretanja hosta (staging/live ili već pokrenut host)"
          >
            <Monitor size={16} /> {isOpen ? "Ponovo otvori" : "Samo otvori"}
          </button>
          <button
            type="button"
            className="cd-action"
            onClick={() => void handleClose()}
            disabled={!isOpen}
            title="Zatvori preview prozor"
          >
            <RefreshCw size={16} /> Zatvori prozor
          </button>
          <button
            type="button"
            className="cd-action"
            onClick={() => void handleStopHost()}
            disabled={busy || !hostRunning}
            title="Zaustavi lokalni host"
          >
            <Square size={16} /> Zaustavi host
          </button>
        </div>
      </div>
    </div>
  );
}

export default PreviewModal;
