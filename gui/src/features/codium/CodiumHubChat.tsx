import { Bug, FolderPlus, Rocket, ScanSearch } from "lucide-react";

import type { ChatSuggestion } from "../../components/chat/CoreChat";
import CoreAssistantChat from "../chat/CoreAssistantChat";
import type { ChatPos } from "../chat/chatPrefs";
import { useAssistantChat } from "./useAssistantChat";
import "../../styles/codium-hub-chat.css";


// ==========          CHAT DOMENA CODIUM          ==========
/*
 * Jedan fajl po domenu: ovde stoji sve što je kod CODIUM chata drugačije —
 * asistent (CODIUM API sa kontekstom projekta), brze akcije i klasa izgleda.
 * Sam okvir, podešavanja, položaji i prelazi dolaze iz CORE chata; izgled je u
 * `styles/codium-hub-chat.css`.
 *
 * Ranije je ovaj fajl imao svoju kopiju okvira (izbornike, alatke, trošak,
 * dijalog za ključ). Dva okvira su se razilazila u ponašanju — sada ih je opet
 * jedan.
 */

/** Brze akcije (predlog-kartice) u praznom stanju CODIUM chata. */
const CHAT_SUGGESTIONS: ChatSuggestion[] = [
  {
    id: "new-project",
    label: "Napravi projekat",
    icon: <FolderPlus size={16} />,
    prompt: "Pomozi mi da napravim nov projekat — predloži strukturu i stack.",
  },
  {
    id: "analyze-project",
    label: "Analiziraj projekat",
    icon: <ScanSearch size={16} />,
    prompt: "Analiziraj aktivan projekat i predloži šta da poboljšam.",
  },
  {
    id: "debug-problem",
    label: "Debaguj problem",
    icon: <Bug size={16} />,
    prompt: "Pomozi mi da debagujem problem u kodu.",
  },
  {
    id: "deploy-project",
    label: "Deploy projekat",
    icon: <Rocket size={16} />,
    prompt: "Vodi me kroz deploy aktivnog projekta.",
  },
];


type CodiumHubChatProps = {
  /** Aktivan projekat (kontekst za asistenta); null = opšte. */
  projectId: number | null;
  /** Javlja dashboard-u da je razgovor počeo (unos teksta ili poslata poruka). */
  onEngaged?: (engaged: boolean) => void;
  /** Javlja dashboard-u gde okvir stoji, da raspored ne ostane iza chata. */
  onPosChange?: (pos: ChatPos) => void;
};

/**
 * Chat okvir na CODIUM dashboard-u: CORE chat sa CODIUM asistentom u njemu.
 */
function CodiumHubChat({
  projectId,
  onEngaged,
  onPosChange,
}: CodiumHubChatProps) {
  // Isti hook koji vozi AI Workspace: persone, izbor modela, istorija i trošak.
  const asistent = useAssistantChat(projectId);

  return (
    <CoreAssistantChat
      scope="codium"
      title="CODIUM asistent"
      variant="is-codium"
      suggestions={CHAT_SUGGESTIONS}
      assistant={asistent}
      onEngaged={onEngaged}
      onPosChange={onPosChange}
    />
  );
}

export default CodiumHubChat;
