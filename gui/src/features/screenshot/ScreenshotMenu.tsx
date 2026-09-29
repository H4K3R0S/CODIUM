import { useEffect, useRef, useState } from "react";
import {
  Monitor,
  MousePointerSquareDashed,
  SquareDashed,
  AppWindow,
} from "lucide-react";

import { listMonitors, type MonitorInfo } from "./screenshotApi";
import type { Mode } from "./captureController";


// ==========          MENI SNIMANJA          ==========
/*
 * Padajući izbor načina: Ceo ekran / Aktivan prozor / Region / Element. Pri više
 * monitora „Ceo ekran" se širi u izbor monitora. Sam meni ne snima — poziva
 * `onPick`, a orkestraciju radi provider.
 */

type ScreenshotMenuProps = {
  onPick: (mode: Mode, monitorId?: number) => void;
  onClose: () => void;
  /** Dodatna klasa za poziciju menija (npr. ispod dugmeta u toolbaru). */
  className?: string;
};

function ScreenshotMenu({ onPick, onClose, className }: ScreenshotMenuProps) {
  const [monitors, setMonitors] = useState<MonitorInfo[]>([]);
  const [showMonitors, setShowMonitors] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let alive = true;
    void listMonitors().then((list) => {
      if (alive) {
        setMonitors(list);
      }
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const onDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const pickFull = () => {
    if (monitors.length > 1) {
      setShowMonitors(true);
    } else {
      onPick("full");
    }
  };

  return (
    <div className={`shot-menu ${className ?? ""}`} ref={rootRef} role="menu">
      {showMonitors ? (
        <>
          <p className="shot-menu-label">Koji monitor</p>
          {monitors.map((m) => (
            <button
              key={m.id}
              type="button"
              className="shot-menu-item"
              role="menuitem"
              onClick={() => onPick("full", m.id)}
            >
              <Monitor size={16} />
              <span>
                {m.name || `Monitor ${m.id}`} ({m.width}×{m.height})
                {m.is_primary ? " · glavni" : ""}
              </span>
            </button>
          ))}
        </>
      ) : (
        <>
          <button
            type="button"
            className="shot-menu-item"
            role="menuitem"
            onClick={pickFull}
          >
            <Monitor size={16} />
            <span>Ceo ekran</span>
          </button>
          <button
            type="button"
            className="shot-menu-item"
            role="menuitem"
            onClick={() => onPick("window")}
          >
            <AppWindow size={16} />
            <span>Aktivan prozor</span>
          </button>
          <button
            type="button"
            className="shot-menu-item"
            role="menuitem"
            onClick={() => onPick("region")}
          >
            <SquareDashed size={16} />
            <span>Region</span>
          </button>
          <button
            type="button"
            className="shot-menu-item"
            role="menuitem"
            onClick={() => onPick("element")}
          >
            <MousePointerSquareDashed size={16} />
            <span>Element</span>
          </button>
        </>
      )}
    </div>
  );
}

export default ScreenshotMenu;
