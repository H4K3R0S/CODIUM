import type { RepositoryWithStatus } from "../../../types/codium";
import { repoBadges } from "./repoBadges";

type Props = {
  repositories: RepositoryWithStatus[];
  selectedId: number | null;
  onSelect: (repoId: number) => void;
  onSync: (repoId: number) => void;
  onRemove: (repoId: number) => void;
};

export default function RepoList({
  repositories,
  selectedId,
  onSelect,
  onSync,
  onRemove,
}: Props) {
  if (repositories.length === 0) {
    return (
      <p className="crepo-prazno">
        Nijedan repozitorijum nije registrovan. Dodaj putanju iznad.
      </p>
    );
  }

  return (
    <ul className="crepo-lista">
      {repositories.map((repo) => (
        <li
          key={repo.id}
          className={`crepo-stavka ${repo.id === selectedId ? "izabrana" : ""}`}
        >
          <button type="button" className="crepo-ime" onClick={() => onSelect(repo.id)}>
            {repo.name}
          </button>
          <div className="crepo-znacke">
            {repoBadges(repo.status).map((znacka) => (
              <span key={znacka} className="crepo-znacka">
                {znacka}
              </span>
            ))}
          </div>
          <div className="crepo-akcije">
            <button type="button" onClick={() => onSync(repo.id)}>
              Sinhronizuj
            </button>
            <button type="button" onClick={() => onRemove(repo.id)}>
              Ukloni
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
