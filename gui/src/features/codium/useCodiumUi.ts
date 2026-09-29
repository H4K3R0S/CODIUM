// ==========          CODIUM UI HOOK          ==========
import { useContext } from "react";

import { CodiumUiContext, type CodiumUiValue } from "./codiumUiContext";

/** Pristup CODIUM UI stanju (mora biti unutar CodiumUiProvider). */
export function useCodiumUi(): CodiumUiValue {
  const context = useContext(CodiumUiContext);
  if (context === null) {
    throw new Error("useCodiumUi mora biti unutar CodiumUiProvider.");
  }
  return context;
}
