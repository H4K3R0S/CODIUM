// ==========          CODIUM WORKSPACE UI KONTEKST          ==========
// Deljeno stanje između CORE Sidebar-a (koji nosi CODIUM navigaciju) i
// CodiumWorkspace stranice (koja renderuje panele). Bez ovoga rail dugmad u
// sidebaru ne bi mogla da otvore panele u workspace-u (različita podstabla).
//
// Kontekst i tipovi stoje odvojeno od provajdera: modul koji uz komponentu
// izvozi i nešto drugo gubi hot reload.
import { createContext } from "react";

export type CodiumPanel = "tasks" | "notes" | "brain" | null;

export type CodiumSoonTool = { label: string; phase: string } | null;

export type CodiumUiValue = {
  /** Trenutno otvoren radni panel (modal) u workspace-u. */
  panel: CodiumPanel;
  openPanel: (panel: CodiumPanel) => void;
  /** „Uskoro" dijalog za nezavršene alatke. */
  soon: CodiumSoonTool;
  showSoon: (tool: CodiumSoonTool) => void;
  /** Da li je desni INFO panel vidljiv (podrazumevano sakriven). */
  showInfo: boolean;
  toggleInfo: () => void;
};

export const CodiumUiContext = createContext<CodiumUiValue | null>(null);
