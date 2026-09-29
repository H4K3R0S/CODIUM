import { useState } from "react";

import type { RepoSuggestion } from "../../../types/codium";

type Props = {
  suggestions: RepoSuggestion[];
  onRegister: (localPath: string, projectId?: number | null) => Promise<void>;
};

/**
 * Ručan upis putanje, uz ponudu projekata čiji je `local_path` git repo.
 *
 * Registar ostaje čovekova odluka — ponuda samo skraćuje kucanje putanje
 * koju sistem ionako zna.
 */
export default function RegisterRepo({ suggestions, onRegister }: Props) {
  const [putanja, setPutanja] = useState("");
  const [greska, setGreska] = useState("");

  async function upisi(localPath: string, projectId?: number | null) {
    try {
      await onRegister(localPath, projectId);
      setPutanja("");
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <div className="crepo-upis">
      <form
        onSubmit={(dogadjaj) => {
          dogadjaj.preventDefault();
          void upisi(putanja.trim());
        }}
      >
        <input
          type="text"
          value={putanja}
          placeholder="Putanja do repozitorijuma"
          aria-label="Putanja do repozitorijuma"
          onChange={(dogadjaj) => setPutanja(dogadjaj.target.value)}
        />
        <button type="submit" disabled={!putanja.trim()}>
          Registruj
        </button>
      </form>

      {greska && <p className="crepo-greska">{greska}</p>}

      {suggestions.length > 0 && (
        <div className="crepo-ponuda">
          <p className="crepo-hint">Projekti čija je putanja git repozitorijum:</p>
          <ul>
            {suggestions.map((ponuda) => (
              <li key={ponuda.project_id}>
                <button
                  type="button"
                  onClick={() => void upisi(ponuda.local_path, ponuda.project_id)}
                >
                  {ponuda.project_name} — {ponuda.local_path}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
