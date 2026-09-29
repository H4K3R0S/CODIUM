import { DiffEditor } from "@monaco-editor/react";
import { useEffect, useState } from "react";

import { fetchRepoDiff } from "../../../services/codiumApi";
import type { CommitInfo } from "../../../types/codium";

type Props = {
  repoId: number | null;
  commit: CommitInfo | null;
};

// SHA praznog stabla — isti u svakom git repozitorijumu, jer ne zavisi od
// sadrzaja. Standardan nacin da se prikaze "razlika" prvog commit-a, koji
// nema roditelja pa `sha~1` ne postoji.
const PRAZNO_STABLO = "4b825dc642cb6eb9a060e54bf8d69288fbee4904";

/**
 * Razlika izabranog commit-a prema njegovom roditelju.
 *
 * Monaco `DiffEditor` traži dva teksta, a ne unified patch. Dok se ne
 * izabere pojedinačan fajl, prikazuje se sam patch kao tekst — to je i
 * dalje tačna slika izmene, bez lažne strukture.
 */
export default function CommitDiff({ repoId, commit }: Props) {
  const [ucitanPatch, setUcitanPatch] = useState("");
  const [greska, setGreska] = useState("");

  // Bez izabranog commita nema šta da se prikaže — izvedeno pri crtanju.
  const patch = repoId === null || commit === null ? "" : ucitanPatch;

  useEffect(() => {
    if (repoId === null || commit === null) {
      return;
    }
    let otkazano = false;
    const idRepo = repoId;
    const sha = commit.sha;

    async function ucitaj() {
      try {
        const odgovor = await fetchRepoDiff(idRepo, `${sha}~1`, sha);
        if (!otkazano) {
          setUcitanPatch(odgovor.diff);
          setGreska("");
        }
      } catch {
        // Prvi commit nema roditelja — `sha~1` ne postoji. Prazno stablo
        // kao leva strana daje istu razliku bez nove rute.
        try {
          const odgovor = await fetchRepoDiff(idRepo, PRAZNO_STABLO, sha);
          if (!otkazano) {
            setUcitanPatch(odgovor.diff);
            setGreska("");
          }
        } catch (problem: unknown) {
          if (!otkazano) {
            setGreska(problem instanceof Error ? problem.message : String(problem));
          }
        }
      }
    }

    void ucitaj();
    return () => {
      otkazano = true;
    };
  }, [repoId, commit]);

  if (commit === null) {
    return <p className="crepo-hint">Izaberi commit da vidiš razliku.</p>;
  }
  if (greska) {
    return <p className="crepo-greska">{greska}</p>;
  }

  return (
    <div className="crepo-razlika">
      <DiffEditor
        height="100%"
        language="diff"
        original=""
        modified={patch}
        options={{ readOnly: true, renderSideBySide: false }}
      />
    </div>
  );
}
