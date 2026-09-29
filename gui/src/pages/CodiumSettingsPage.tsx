import { Bot, Cpu, FileCode, KeyRound, Palette, UserRound } from "lucide-react";

import ApiKeysPanel from "../features/settings/ApiKeysPanel";
import ChatPanel from "../features/settings/ChatPanel";
import ModelsPanel from "../features/settings/ModelsPanel";
import PersonaPanel from "../features/settings/PersonaPanel";
import SettingsShell, {
  type SettingsCategory,
} from "../features/settings/SettingsShell";
import ThemePanel from "../features/settings/ThemePanel";
import { AtomiPanel, ModelPanel } from "../cell/AssistantSettingsPanels";

// Ponuđene pozadine za CODIUM (jedna; drugi domeni imaju svoje).
const CODIUM_BACKGROUNDS = [
  { id: "codium", label: "CODIUM (podrazumevana)", url: "/codium-bg.png" },
];


// ==========          CODIUM PODEŠAVANJA          ==========

// CODIUM ima svoja podešavanja, ali ključevi i globalni izbor modela pripadaju
// CORE-u: unose se jednom i nasleđuje ih svaki domen. Ovde se taj izbor može
// samo suziti — model koji je CORE isključio ovde stoji zaključan.
const KATEGORIJE: SettingsCategory[] = [
  {
    id: "tema",
    label: "Tema",
    icon: Palette,
    render: () => (
      <ThemePanel
        backgrounds={CODIUM_BACKGROUNDS}
        subtitle="Pozadina i ambijentalni efekat „Povezane tačke“ za CODIUM. Menja se odmah i pamti na ovom uređaju."
      />
    ),
  },
  {
    id: "chat",
    label: "Chat okvir",
    icon: Bot,
    render: () => (
      <ChatPanel
        scope="codium"
        subtitle="Chat okvir CODIUM-a. Dok stavku ne promeniš, prati CORE — i menja se sa njim. Promenjena stavka ostaje domenska dok je ne vratiš na CORE."
      />
    ),
  },
  {
    id: "models",
    label: "Modeli",
    icon: Cpu,
    render: () => (
      <ModelsPanel subtitle="Izbor važi samo za CODIUM. Isključeni modeli se ne nude u chat okviru, ali ostaju ovde da bi mogli da se vrate. Model koji je CORE isključio ne može se vratiti odavde." />
    ),
  },
  {
    id: "persone",
    label: "Persone",
    icon: UserRound,
    render: () => (
      <PersonaPanel
        scope="codium"
        subtitle="Persone CODIUM chata. Opšti pomoćnik je podrazumevani režim — širok razvojni sagovornik; ostale persone su uže uloge. Sve važe samo u CODIUM-u."
      />
    ),
  },
  {
    id: "api-keys",
    label: "API ključevi",
    icon: KeyRound,
    render: () => <ApiKeysPanel />,
  },
  {
    id: "agent",
    label: "Agent",
    icon: FileCode,
    render: () => (
      <>
        <ModelPanel brand="Codium" />
        <AtomiPanel brand="Codium" />
      </>
    ),
  },
];

function CodiumSettingsPage() {
  return (
    <SettingsShell
      eyebrow="CODIUM"
      title="CODIUM — Podešavanja"
      note="Ključevi su CORE postavka i vide ih svi domeni. Izbor modela ovde važi samo za CODIUM."
      categories={KATEGORIJE}
    />
  );
}

export default CodiumSettingsPage;
