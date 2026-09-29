import { useMemo, useState, type ReactNode } from "react";

import {
  CodiumUiContext,
  type CodiumPanel,
  type CodiumSoonTool,
  type CodiumUiValue,
} from "./codiumUiContext";


// ==========          CODIUM WORKSPACE UI PROVIDER          ==========

/**
 * Provider za CODIUM UI stanje. Obavija ceo AppShell (Sidebar + rute) da bi
 * sidebar navigacija i workspace paneli delili isto stanje.
 */
export function CodiumUiProvider({ children }: { children: ReactNode }) {
  const [panel, setPanel] = useState<CodiumPanel>(null);
  const [soon, setSoon] = useState<CodiumSoonTool>(null);
  const [showInfo, setShowInfo] = useState(false);

  const value = useMemo<CodiumUiValue>(
    () => ({
      panel,
      openPanel: setPanel,
      soon,
      showSoon: setSoon,
      showInfo,
      toggleInfo: () => setShowInfo((current) => !current),
    }),
    [panel, soon, showInfo],
  );

  return (
    <CodiumUiContext.Provider value={value}>
      {children}
    </CodiumUiContext.Provider>
  );
}
