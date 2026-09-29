import { useEffect, useState } from "react";

import { fetchRepoCommits } from "../../../services/codiumApi";
import type { CommitInfo } from "../../../types/codium";

type Props = {
  repoId: number | null;
  branch?: string;
  onSelect: (commit: CommitInfo) => void;
  selectedSha: string | null;
};

export default function CommitHistory({
  repoId,
  branch = "",
  onSelect,
  selectedSha,
}: Props) {
  const [ucitani, setUcitani] = useState<CommitInfo[]>([]);
  const [greska, setGreska] = useState("");

  // Bez izabranog repozitorijuma spisak je prazan — to se IZVODI pri crtanju, a
  // ne upisuje u stanje iz efekta (upis bi značio još jedan crtež za isti
  // podatak, i kratak tren u kojem se vidi tuđ spisak).
  const commits = repoId === null ? [] : ucitani;

  useEffect(() => {
    if (repoId === null) {
      return;
    }
    let otkazano = false;
    fetchRepoCommits(repoId, branch, 50, 0)
      .then((odgovor) => {
        if (!otkazano) {
          setUcitani(odgovor.commits);
          setGreska("");
        }
      })
      .catch((problem: unknown) => {
        if (!otkazano) {
          setGreska(problem instanceof Error ? problem.message : String(problem));
        }
      });
    return () => {
      otkazano = true;
    };
  }, [repoId, branch]);

  if (repoId === null) {
    return <p className="crepo-hint">Izaberi repozitorijum.</p>;
  }
  if (greska) {
    return <p className="crepo-greska">{greska}</p>;
  }

  return (
    <ul className="crepo-istorija">
      {commits.map((commit) => (
        <li key={commit.sha}>
          <button
            type="button"
            className={commit.sha === selectedSha ? "izabran" : ""}
            onClick={() => onSelect(commit)}
          >
            <span className="crepo-sha">{commit.short_sha}</span>
            <span className="crepo-naslov">{commit.subject}</span>
            <span className="crepo-autor">{commit.author}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
