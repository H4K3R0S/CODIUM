import { useRef, useState } from "react";
import type { ReactElement } from "react";
import { DockviewReact, themeDark } from "dockview-react";
import type {
  DockviewApi,
  DockviewReadyEvent,
  IDockviewPanelProps,
} from "dockview-react";
import {
  Download,
  PictureInPicture2,
  RotateCcw,
  Save,
  Trash2,
  Upload,
} from "lucide-react";
import "dockview-react/dist/styles/dockview.css";

import {
  DEFAULT_PRESETS_KEY,
  exportDockPresets,
  mergeDockPresets,
  parseDockPresetsImport,
  readDockPresets,
  removeDockPreset,
  upsertDockPreset,
  writeDockPresets,
  type DockPreset,
} from "./dockPresets";
import "../../styles/core-dock.css";


// ==========          GENERIČKI CORE DOCKING LAYOUT (D4)          ==========
/*
 * CORE-nivo docking okvir: mehanika (toolbar za dodavanje panela, Float, Reset,
 * preseti rasporeda + import/export, serijalizacija u localStorage) izdvojena iz
 * CODIUM-a da je koristi bilo koji domen. Domen prosleđuje SVOJE panel-komponente
 * (`components`), meta (naslov+ikonica), podrazumevani raspored i ključeve za
 * čuvanje. Deljeno stanje domena (npr. aktivni fajl) ide kroz React kontekst koji
 * domen postavlja IZNAD ovog layout-a (isti React root — paneli ga vide).
 */

export type DockPanelMeta = { title: string; icon: ReactElement };

export type CoreDockLayoutProps = {
  /** Prostor imena rasporeda po instanci (npr. `codium.dock.<id>`). */
  storageKey: string;
  /** Prostor imena presetā (deljeno po domenu; default CORE). */
  presetsKey?: string;
  /** Panel-komponente po ključu (renderuju domenski sadržaj). */
  components: Record<string, React.FunctionComponent<IDockviewPanelProps>>;
  /** Naslov + ikonica po ključu (za dugmad dodavanja). */
  panelMeta: Record<string, DockPanelMeta>;
  /** Gradi podrazumevani raspored (koristi se i za Reset). */
  buildDefaultLayout: (api: DockviewApi) => void;
};

function CoreDockLayout({
  storageKey,
  presetsKey = DEFAULT_PRESETS_KEY,
  components,
  panelMeta,
  buildDefaultLayout,
}: CoreDockLayoutProps) {
  const apiRef = useRef<DockviewApi | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [presets, setPresets] = useState<DockPreset[]>(() =>
    readDockPresets(presetsKey),
  );
  const [presetName, setPresetName] = useState("");

  function persist(): void {
    const api = apiRef.current;
    if (!api) {
      return;
    }
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(api.toJSON()));
    } catch {
      /* storage nedostupan */
    }
  }

  function onReady(event: DockviewReadyEvent): void {
    const api = event.api;
    apiRef.current = api;

    const saved = window.localStorage.getItem(storageKey);
    let restored = false;
    if (saved) {
      try {
        api.fromJSON(JSON.parse(saved));
        restored = true;
      } catch {
        restored = false;
      }
    }
    if (!restored) {
      buildDefaultLayout(api);
    }

    api.onDidLayoutChange(() => persist());
    persist();
  }

  function resetLayout(): void {
    const api = apiRef.current;
    if (!api) {
      return;
    }
    buildDefaultLayout(api);
    persist();
  }

  function ensurePanel(key: string): void {
    const api = apiRef.current;
    if (!api || api.getPanel(key)) {
      return;
    }
    api.addPanel({
      id: key,
      component: key,
      title: panelMeta[key]?.title ?? key,
    });
    persist();
  }

  // D2: izdvoji aktivni panel u plutajuću grupu (nazad se dokuje prevlačenjem).
  function floatActive(): void {
    const api = apiRef.current;
    const panel = api?.activePanel;
    if (!api || !panel) {
      return;
    }
    api.addFloatingGroup(panel, { width: 520, height: 420, x: 80, y: 80 });
    persist();
  }

  // --- D3: imenovani preseti rasporeda + import/export ---

  function savePreset(): void {
    const api = apiRef.current;
    if (!api || presetName.trim() === "") {
      return;
    }
    const next = upsertDockPreset(presets, presetName, api.toJSON());
    writeDockPresets(next, presetsKey);
    setPresets(next);
    setPresetName("");
  }

  function applyPreset(preset: DockPreset): void {
    const api = apiRef.current;
    if (!api) {
      return;
    }
    try {
      api.fromJSON(preset.layout as Parameters<DockviewApi["fromJSON"]>[0]);
      persist();
    } catch {
      /* neispravan preset — ignoriši */
    }
  }

  function deletePreset(id: string): void {
    const next = removeDockPreset(presets, id);
    writeDockPresets(next, presetsKey);
    setPresets(next);
  }

  function exportPresets(): void {
    const blob = new Blob([exportDockPresets(presets)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "core-dock-presets.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function importPresets(
    event: React.ChangeEvent<HTMLInputElement>,
  ): Promise<void> {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    const text = await file.text();
    const incoming = parseDockPresetsImport(text);
    if (incoming.length === 0) {
      return;
    }
    const next = mergeDockPresets(presets, incoming);
    writeDockPresets(next, presetsKey);
    setPresets(next);
  }

  return (
    <div className="cdk-shell">
      <div className="cdk-toolbar">
        <span className="cdk-toolbar-label">Paneli:</span>
        {Object.keys(panelMeta).map((key) => (
          <button
            key={key}
            type="button"
            className="cdk-add-btn"
            onClick={() => ensurePanel(key)}
            title={`Dodaj ${panelMeta[key].title}`}
          >
            {panelMeta[key].icon} {panelMeta[key].title}
          </button>
        ))}
        <button
          type="button"
          className="cdk-add-btn"
          onClick={floatActive}
          title="Izdvoj aktivni panel u plutajući prozor (float)"
        >
          <PictureInPicture2 size={13} /> Float
        </button>
        <button
          type="button"
          className="cdk-reset-btn"
          onClick={resetLayout}
          title="Vrati podrazumevani raspored"
        >
          <RotateCcw size={13} /> Reset
        </button>
      </div>

      {/* ==========          PRESETI RASPOREDA (D3)          ========== */}
      <div className="cdk-presets">
        <span className="cdk-toolbar-label">Preseti:</span>
        <input
          className="cdk-preset-input"
          value={presetName}
          onChange={(event) => setPresetName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              savePreset();
            }
          }}
          placeholder="Ime preseta…"
          aria-label="Ime preseta"
        />
        <button
          type="button"
          className="cdk-add-btn"
          onClick={savePreset}
          disabled={presetName.trim() === ""}
          title="Sačuvaj trenutni raspored kao preset"
        >
          <Save size={13} /> Sačuvaj
        </button>

        {presets.map((preset) => (
          <span key={preset.id} className="cdk-preset-chip">
            <button
              type="button"
              className="cdk-preset-apply"
              onClick={() => applyPreset(preset)}
              title={`Primeni „${preset.name}"`}
            >
              {preset.name}
            </button>
            <button
              type="button"
              className="cdk-preset-del"
              onClick={() => deletePreset(preset.id)}
              aria-label={`Obriši „${preset.name}"`}
            >
              <Trash2 size={12} />
            </button>
          </span>
        ))}

        <button
          type="button"
          className="cdk-add-btn cdk-presets-io"
          onClick={exportPresets}
          disabled={presets.length === 0}
          title="Izvezi presete u JSON fajl"
        >
          <Download size={13} /> Export
        </button>
        <button
          type="button"
          className="cdk-add-btn"
          onClick={() => fileInputRef.current?.click()}
          title="Uvezi presete iz JSON fajla"
        >
          <Upload size={13} /> Import
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/json,.json"
          onChange={(event) => void importPresets(event)}
          style={{ display: "none" }}
        />
      </div>

      <div className="cdk-dock">
        <DockviewReact
          components={components}
          onReady={onReady}
          theme={themeDark}
        />
      </div>
    </div>
  );
}

export default CoreDockLayout;
