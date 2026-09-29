import { useEffect, useState } from "react";

import type { Rect } from "./captureController";


// ==========          IZBOR ELEMENTA (pokazivač)          ==========
/*
 * Sloj bez hvatanja miša (`pointer-events: none`) da `elementFromPoint` vidi
 * pravi element ispod kursora. Kretanje ističe element pod pokazivačem; klik ga
 * bira (hvata se u capture fazi da underlying element ne reaguje). `Esc` otkazuje.
 */

type ElementPickOverlayProps = {
  onPick: (rect: Rect) => void;
  onCancel: () => void;
};

/** Pravougaonik elementa u CSS pikselima (viewport). */
export function rectOfElement(element: Element): Rect {
  const r = element.getBoundingClientRect();
  return { x: r.left, y: r.top, width: r.width, height: r.height };
}

function ElementPickOverlay({ onPick, onCancel }: ElementPickOverlayProps) {
  const [hover, setHover] = useState<Rect | null>(null);

  useEffect(() => {
    const elementAt = (x: number, y: number): Element | null => {
      // Preskoči sopstveni highlight (pointer-events:none ga ionako preskače).
      const found = document.elementFromPoint(x, y);
      if (found && found.getAttribute("data-shot-ignore") === "true") {
        return null;
      }
      return found;
    };

    const onMove = (event: MouseEvent) => {
      const element = elementAt(event.clientX, event.clientY);
      setHover(element ? rectOfElement(element) : null);
    };

    const onClick = (event: MouseEvent) => {
      const element = elementAt(event.clientX, event.clientY);
      if (!element) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      onPick(rectOfElement(element));
    };

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCancel();
      }
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("click", onClick, true);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("click", onClick, true);
      window.removeEventListener("keydown", onKey);
    };
  }, [onPick, onCancel]);

  return (
    <div className="shot-element-layer" data-shot-ignore="true">
      <p className="shot-element-hint" data-shot-ignore="true">
        Klikni element za snimak · <kbd>Esc</kbd> otkazuje
      </p>

      {hover && (
        <div
          className="shot-element-box"
          data-shot-ignore="true"
          data-testid="shot-element-box"
          style={{
            left: hover.x,
            top: hover.y,
            width: hover.width,
            height: hover.height,
          }}
        />
      )}
    </div>
  );
}

export default ElementPickOverlay;
