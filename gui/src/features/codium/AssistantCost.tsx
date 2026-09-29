import type { Merenje } from "./useAssistantChat";


// ==========          OZNAKA TROŠKA (deljena)          ==========

// Nije izvezena: koristi je samo ova komponenta, a izvoz uz komponentu gasi
// hot reload za ceo modul.
/** Trošak poziva; lokalni model se ne prikazuje kao „$0". */
function formatTrosak(cost: number): string {
  return cost > 0 ? `$${cost.toFixed(4)}` : "besplatno";
}

function AssistantCost({ merenje }: { merenje: Merenje | null }) {
  if (merenje === null) {
    return null;
  }

  return (
    <div className="cai-cost" data-testid="cai-cost">
      {merenje.model} · {formatTrosak(merenje.cost)} ·{" "}
      {(merenje.durationMs / 1000).toFixed(1)} s
    </div>
  );
}

export default AssistantCost;
