import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useCoreStringSetting } from "../../lib/useCoreSetting";
import { isTauri } from "../window/windowManager";
import type { Mode, Rect } from "./captureController";
import {
  capture,
  registerCaptureShortcuts,
  unregisterCaptureShortcuts,
  type ShotResult,
} from "./screenshotApi";
import {
  DEFAULT_FORMAT,
  DEFAULT_QUALITY,
  DEFAULT_SHORTCUTS,
  FORMAT_KEY,
  QUALITY_KEY,
  SHORTCUT_KEYS,
  normalizeFormat,
} from "./screenshotSettings";
import ElementPickOverlay from "./ElementPickOverlay";
import RegionSelectOverlay from "./RegionSelectOverlay";
import ScreenshotPreview from "./ScreenshotPreview";

import "../../styles/screenshot.css";


// ==========          KONTEKST          ==========

type ScreenshotContextValue = {
  /** Pokreće snimanje datog načina (region/element otvaraju izbor prvo). */
  startCapture: (mode: Mode, monitorId?: number) => void;
};

const ScreenshotContext = createContext<ScreenshotContextValue | null>(null);

/** Pristup pokretanju snimanja iz bilo koje komponente (rail, toolbar). */
export function useScreenshot(): ScreenshotContextValue {
  const value = useContext(ScreenshotContext);
  if (!value) {
    return { startCapture: () => undefined };
  }
  return value;
}


// ==========          ORKESTRATOR          ==========

type Phase = "idle" | "region" | "element" | "busy" | "preview";

/**
 * Drži stanje snimanja i spaja meni/prečicu → overlay → snimak → pregled. Montira
 * se jednom, visoko u ljusci, da overlaye i pregled crta preko celog prozora.
 */
function ScreenshotProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<ShotResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [formatSetting] = useCoreStringSetting(FORMAT_KEY, DEFAULT_FORMAT);
  const [qualitySetting] = useCoreStringSetting(
    QUALITY_KEY,
    String(DEFAULT_QUALITY),
  );

  // Prečica po načinu — svaka svoje polje u Podešavanjima.
  const [fullKey] = useCoreStringSetting(
    SHORTCUT_KEYS.full,
    DEFAULT_SHORTCUTS.full,
  );
  const [windowKey] = useCoreStringSetting(
    SHORTCUT_KEYS.window,
    DEFAULT_SHORTCUTS.window,
  );
  const [regionKey] = useCoreStringSetting(
    SHORTCUT_KEYS.region,
    DEFAULT_SHORTCUTS.region,
  );
  const [elementKey] = useCoreStringSetting(
    SHORTCUT_KEYS.element,
    DEFAULT_SHORTCUTS.element,
  );

  // Snimanje čita sveže podešavanje bez ponovnog vezivanja callback-a.
  const settingsRef = useRef({ formatSetting, qualitySetting });
  settingsRef.current = { formatSetting, qualitySetting };

  const runCapture = useCallback((mode: Mode, monitorId?: number, rect?: Rect) => {
    const format = normalizeFormat(settingsRef.current.formatSetting);
    const parsed = Number.parseInt(settingsRef.current.qualitySetting, 10);
    const quality = Number.isNaN(parsed) ? DEFAULT_QUALITY : parsed;

    setPhase("busy");
    setResult(null);
    setError(null);

    capture({ mode, format, quality, monitorId, rect })
      .then((shot) => {
        setResult(shot);
        setError(null);
        setPhase("preview");
      })
      .catch((err: unknown) => {
        setResult(null);
        setError(err instanceof Error ? err.message : String(err));
        setPhase("preview");
      });
  }, []);

  const startCapture = useCallback(
    (mode: Mode, monitorId?: number) => {
      if (mode === "region") {
        setPhase("region");
      } else if (mode === "element") {
        setPhase("element");
      } else {
        runCapture(mode, monitorId);
      }
    },
    [runCapture],
  );

  // Globalne prečice po načinu. Ponovo se registruju kad se bilo koja promeni.
  useEffect(() => {
    if (!isTauri()) {
      return;
    }
    const bindings = [
      { mode: "full" as Mode, accelerator: fullKey },
      { mode: "window" as Mode, accelerator: windowKey },
      { mode: "region" as Mode, accelerator: regionKey },
      { mode: "element" as Mode, accelerator: elementKey },
    ];
    void registerCaptureShortcuts(bindings, startCapture);
    return () => {
      void unregisterCaptureShortcuts();
    };
  }, [fullKey, windowKey, regionKey, elementKey, startCapture]);

  return (
    <ScreenshotContext.Provider value={{ startCapture }}>
      {children}

      {phase === "region" && (
        <RegionSelectOverlay
          onComplete={(rect) => runCapture("region", undefined, rect)}
          onCancel={() => setPhase("idle")}
        />
      )}

      {phase === "element" && (
        <ElementPickOverlay
          onPick={(rect) => runCapture("element", undefined, rect)}
          onCancel={() => setPhase("idle")}
        />
      )}

      {phase === "preview" && (
        <ScreenshotPreview
          result={result}
          error={error}
          onClose={() => setPhase("idle")}
        />
      )}
    </ScreenshotContext.Provider>
  );
}

export default ScreenshotProvider;
