import { useState } from "react";
import { Pencil, Plus, Save, Trash2, X } from "lucide-react";

import type { EnvPair, ShellInfo } from "./terminalApi";
import {
  removeProfile,
  upsertProfile,
  type TermProfile,
} from "./terminalProfiles";


// ==========          EDITOR PROFILA TERMINALA (T6)          ==========

type Draft = {
  id?: string;
  name: string;
  shellId: string;
  cwd: string;
  env: EnvPair[];
};

type EditorProps = {
  shells: ShellInfo[];
  profiles: TermProfile[];
  onChange: (profiles: TermProfile[]) => void;
  onClose: () => void;
};

function emptyDraft(shells: ShellInfo[]): Draft {
  return {
    name: "",
    shellId: shells[0]?.id ?? "",
    cwd: "",
    env: [],
  };
}

/**
 * Modal za upravljanje profilima terminala: lista postojećih (izmeni/obriši) +
 * forma (ime, shell, cwd, env parovi). Čuva kroz `upsertProfile/removeProfile`.
 */
function TerminalProfilesEditor({
  shells,
  profiles,
  onChange,
  onClose,
}: EditorProps) {
  const [draft, setDraft] = useState<Draft>(() => emptyDraft(shells));

  function edit(profile: TermProfile): void {
    setDraft({
      id: profile.id,
      name: profile.name,
      shellId: profile.shellId,
      cwd: profile.cwd ?? "",
      env: profile.env ? profile.env.map(([k, v]) => [k, v] as EnvPair) : [],
    });
  }

  function save(): void {
    const next = upsertProfile(profiles, {
      id: draft.id,
      name: draft.name,
      shellId: draft.shellId,
      cwd: draft.cwd,
      env: draft.env,
    });
    onChange(next);
    setDraft(emptyDraft(shells));
  }

  function del(id: string): void {
    onChange(removeProfile(profiles, id));
    if (draft.id === id) {
      setDraft(emptyDraft(shells));
    }
  }

  function setEnv(index: number, which: 0 | 1, value: string): void {
    setDraft((d) => {
      const env = d.env.map((pair) => [...pair] as EnvPair);
      env[index][which] = value;
      return { ...d, env };
    });
  }

  return (
    <div
      className="cterm-prof-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Profili terminala"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="cterm-prof">
        <div className="cterm-prof-head">
          <h3>Profili terminala</h3>
          <button
            type="button"
            className="cterm-prof-x"
            onClick={onClose}
            aria-label="Zatvori"
          >
            <X size={16} />
          </button>
        </div>

        <div className="cterm-prof-body">
          {/* Lista postojećih */}
          <div className="cterm-prof-list">
            {profiles.length === 0 ? (
              <p className="cterm-hint">Nema profila. Napravi prvi desno.</p>
            ) : (
              profiles.map((p) => (
                <div key={p.id} className="cterm-prof-row">
                  <span className="cterm-prof-name">{p.name}</span>
                  <span className="cterm-prof-meta">{p.shellId}</span>
                  <button
                    type="button"
                    className="cterm-prof-icon"
                    onClick={() => edit(p)}
                    aria-label={`Izmeni ${p.name}`}
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    type="button"
                    className="cterm-prof-icon"
                    onClick={() => del(p.id)}
                    aria-label={`Obriši ${p.name}`}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Forma */}
          <div className="cterm-prof-form">
            <label className="cterm-prof-field">
              <span>Ime</span>
              <input
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                placeholder="npr. Backend (venv)"
              />
            </label>

            <label className="cterm-prof-field">
              <span>Shell</span>
              <select
                value={draft.shellId}
                onChange={(e) => setDraft({ ...draft, shellId: e.target.value })}
              >
                {shells.length === 0 && <option value="">(nema shell-ova)</option>}
                {shells.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="cterm-prof-field">
              <span>Radni folder (cwd)</span>
              <input
                value={draft.cwd}
                onChange={(e) => setDraft({ ...draft, cwd: e.target.value })}
                placeholder="(prazno = folder projekta)"
              />
            </label>

            <div className="cterm-prof-field">
              <span>Env promenljive</span>
              {draft.env.map((pair, index) => (
                <div key={index} className="cterm-prof-env">
                  <input
                    value={pair[0]}
                    onChange={(e) => setEnv(index, 0, e.target.value)}
                    placeholder="KLJUČ"
                  />
                  <input
                    value={pair[1]}
                    onChange={(e) => setEnv(index, 1, e.target.value)}
                    placeholder="vrednost"
                  />
                  <button
                    type="button"
                    className="cterm-prof-icon"
                    onClick={() =>
                      setDraft((d) => ({
                        ...d,
                        env: d.env.filter((_, i) => i !== index),
                      }))
                    }
                    aria-label="Ukloni env"
                  >
                    <X size={13} />
                  </button>
                </div>
              ))}
              <button
                type="button"
                className="cterm-prof-add-env"
                onClick={() =>
                  setDraft((d) => ({ ...d, env: [...d.env, ["", ""]] }))
                }
              >
                <Plus size={12} /> Dodaj env
              </button>
            </div>

            <button
              type="button"
              className="cterm-prof-save"
              onClick={save}
              disabled={draft.name.trim() === "" || draft.shellId === ""}
            >
              <Save size={14} /> {draft.id ? "Sačuvaj izmene" : "Dodaj profil"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TerminalProfilesEditor;
