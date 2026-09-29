import type { ReactNode } from "react";
import { X } from "lucide-react";

import type { SmartLayout } from "../../features/layout/useSmartLayout";
import "../../styles/smart-layout.css";


// ==========          OKVIR U PAMETNOM RASPOREDU          ==========

type SmartFrameProps = {
  /** Jedinstven id okvira na ekranu (preview se pamti po njemu). */
  id: string;
  /** Naslov — jedino što se vidi kada je okvir skupljen. */
  title: string;
  icon: ReactNode;
  layout: SmartLayout;
  children: ReactNode;
};

/**
 * Ljuska oko widgeta na ekranu sa chatom.
 *
 * U punom rasporedu se ne vidi — widget izgleda isto kao pre. Kada razgovor
 * krene, okvir se sklapa u karticu sa samim naslovom i odlazi uz levu ivicu;
 * klik ga otvara kao preview uz chat, gde se prikazuje isti, jedini primerak
 * widgeta (ne kopija — inače bi widget dva puta učitavao svoje podatke).
 */
function SmartFrame({ id, title, icon, layout, children }: SmartFrameProps) {
  const isPreview = layout.preview === id;
  const isTucked = layout.tucked && !isPreview;

  return (
    <section
      className={`sframe ${isTucked ? "is-tucked" : ""} ${
        isPreview ? "is-preview" : ""
      }`}
      title={isTucked ? title : undefined}
      onClick={isTucked ? () => layout.togglePreview(id) : undefined}
      aria-label={title}
    >
      <div className="sframe-head">
        <span className="sframe-icon">{icon}</span>
        <h2>{title}</h2>
        {isPreview && (
          <button
            type="button"
            className="sframe-close"
            onClick={() => layout.togglePreview(id)}
            aria-label="Zatvori preview"
            title="Zatvori"
          >
            <X size={15} />
          </button>
        )}
      </div>
      <div className="sframe-body">{children}</div>
    </section>
  );
}

export default SmartFrame;
