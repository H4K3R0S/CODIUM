import { useEffect, useRef, useState } from "react";

import {
  clampRectToBounds,
  normalizeDragRect,
  type Point,
  type Rect,
} from "./captureController";


// ==========          IZBOR REGIONA (prevlačenje)          ==========
/*
 * Providan sloj preko celog prozora: prevlačenje crta pravougaonik, otpuštanje
 * ga vraća (isečen na granice prozora). `Esc` otkazuje. Rezultat je u CSS
 * pikselima; `screenshotApi` ga prevodi u ekranske pre snimanja.
 */

type RegionSelectOverlayProps = {
  onComplete: (rect: Rect) => void;
  onCancel: () => void;
};

function RegionSelectOverlay({ onComplete, onCancel }: RegionSelectOverlayProps) {
  const [start, setStart] = useState<Point | null>(null);
  const [current, setCurrent] = useState<Point | null>(null);
  const draggingRef = useRef(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCancel();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  const selection =
    start && current ? normalizeDragRect(start, current) : null;

  const finish = () => {
    if (!draggingRef.current || !start || !current) {
      return;
    }
    draggingRef.current = false;

    const rect = clampRectToBounds(normalizeDragRect(start, current), {
      width: window.innerWidth,
      height: window.innerHeight,
    });

    if (rect.width > 2 && rect.height > 2) {
      onComplete(rect);
    } else {
      onCancel();
    }
  };

  return (
    <div
      className="shot-region-overlay"
      role="presentation"
      onMouseDown={(event) => {
        draggingRef.current = true;
        const point = { x: event.clientX, y: event.clientY };
        setStart(point);
        setCurrent(point);
      }}
      onMouseMove={(event) => {
        if (draggingRef.current) {
          setCurrent({ x: event.clientX, y: event.clientY });
        }
      }}
      onMouseUp={finish}
    >
      <p className="shot-region-hint">
        Prevuci da izabereš oblast · <kbd>Esc</kbd> otkazuje
      </p>

      {selection && (
        <div
          className="shot-region-box"
          data-testid="shot-region-box"
          style={{
            left: selection.x,
            top: selection.y,
            width: selection.width,
            height: selection.height,
          }}
        />
      )}
    </div>
  );
}

export default RegionSelectOverlay;
