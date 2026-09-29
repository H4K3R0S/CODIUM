import { useState } from "react";
import { Camera } from "lucide-react";

import { useScreenshot } from "./ScreenshotProvider";
import ScreenshotMenu from "./ScreenshotMenu";
import type { Mode } from "./captureController";


// ==========          TOOLBAR DUGME SNIMANJA          ==========
/*
 * Ista funkcija kao rail dugme, ali stil i položaj menija za workspace toolbar
 * (meni pada ispod dugmeta).
 */

function ScreenshotToolbarButton() {
  const { startCapture } = useScreenshot();
  const [open, setOpen] = useState(false);

  const pick = (mode: Mode, monitorId?: number) => {
    setOpen(false);
    startCapture(mode, monitorId);
  };

  return (
    <div className="shot-rail">
      <button
        type="button"
        className={`cdw-layout-toggle ${open ? "active" : ""}`}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        title="Snimak ekrana"
      >
        <Camera size={14} />
        Snimak
      </button>

      {open && (
        <ScreenshotMenu
          className="shot-menu--below"
          onPick={pick}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
}

export default ScreenshotToolbarButton;
