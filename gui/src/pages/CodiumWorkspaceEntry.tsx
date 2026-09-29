import { Navigate } from "react-router";

import { useCoreStringSetting } from "../lib/useCoreSetting";


// ==========          AI WORKSPACE — ULAZ (bez id-a u ruti)          ==========
//
// Sidebar stavka „AI Workspace" vodi na `/codium/workspace` (bez projekta).
// Ovaj ulaz razreši poslednji aktivan projekat (`codium.activeProjectId`, upisan
// pri ulasku u workspace) i preusmeri na njegov radni prostor. Ako aktivnog
// projekta nema, vodi na listu projekata da se prvo izabere. Čitanje je sinhrono
// (localStorage), pa nema treptaja pogrešne rute.

function CodiumWorkspaceEntry() {
  const [activeProjectId] = useCoreStringSetting("codium.activeProjectId", "");
  const id = Number(activeProjectId);
  const imaProjekat = activeProjectId !== "" && !Number.isNaN(id);

  return (
    <Navigate
      to={imaProjekat ? `/codium/workspace/${id}` : "/codium/projects"}
      replace
    />
  );
}

export default CodiumWorkspaceEntry;
