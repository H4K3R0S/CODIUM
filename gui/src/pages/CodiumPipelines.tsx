// ==========          PIPELINES          ==========
// Isti okvir kao ostale CODIUM strane (Access, Audit, AI Agents): zaglavlje sa
// eyebrow-om, okviri u `smart-stack` i CODIUM chat u dnu. Okvir strane je
// zajednicki da bi se domen citao kao jedna celina, a ne kao skup zasebnih
// alata.
import { useEffect, useState } from "react";
import { FileCode2, History, ListChecks, Workflow } from "lucide-react";

import DefinitionEditor from "../features/codium/pipelines/DefinitionEditor";
import PipelineList from "../features/codium/pipelines/PipelineList";
import RunDetail from "../features/codium/pipelines/RunDetail";
import RunHistory from "../features/codium/pipelines/RunHistory";
import { useCloseGuard } from "../features/codium/pipelines/useCloseGuard";
import { usePipelines } from "../features/codium/pipelines/usePipelines";
import { fetchRepositories, fetchRuns } from "../services/codiumApi";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type { RepositoryWithStatus } from "../types/codium";
import "../styles/codium-pipelines.css";

const NOVA_DEFINICIJA = JSON.stringify(
  {
    name: "nov-pipeline",
    timeout_minutes: 20,
    steps: [{ name: "korak", run: "echo zdravo" }],
  },
  null,
  2,
);

export default function CodiumPipelines() {
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const [repositories, setRepositories] = useState<RepositoryWithStatus[]>([]);
  const [repoId, setRepoId] = useState<number | null>(null);
  const [izabran, setIzabran] = useState<number | null>(null);
  const [izabranoPokretanje, setIzabranoPokretanje] = useState<number | null>(null);
  const [osvezi, setOsvezi] = useState(0);
  const [greskaSnimanja, setGreskaSnimanja] = useState("");

  const { pipelines, isLoading, error, create, update, remove, start } =
    usePipelines(repoId ?? undefined);

  useEffect(() => {
    fetchRepositories()
      .then((odgovor) => {
        setRepositories(odgovor.repositories);
        if (odgovor.repositories.length > 0) {
          setRepoId(odgovor.repositories[0].id);
        }
      })
      // Strana ne sme da padne zbog liste repozitorijuma; prazna lista je
      // sama po sebi poruka.
      .catch(() => setRepositories([]));
  }, []);

  const [aktivnih, setAktivnih] = useState(0);

  useEffect(() => {
    let otkazano = false;
    fetchRuns(undefined, 50)
      .then((odgovor) => {
        if (!otkazano) {
          setAktivnih(
            odgovor.runs.filter(
              (run) => run.status === "running" || run.status === "queued",
            ).length,
          );
        }
      })
      .catch(() => setAktivnih(0));
    return () => {
      otkazano = true;
    };
  }, [osvezi, izabranoPokretanje]);

  useCloseGuard(aktivnih);

  const izabranPipeline = pipelines.find((p) => p.id === izabran) ?? null;
  const definicija = izabranPipeline?.definition ?? NOVA_DEFINICIJA;

  async function snimi(tekst: string): Promise<void> {
    try {
      if (izabranPipeline === null) {
        if (repoId === null) {
          return;
        }
        await create(repoId, tekst);
      } else {
        await update(izabranPipeline.id, tekst);
      }
      setGreskaSnimanja("");
    } catch (problem) {
      setGreskaSnimanja(
        problem instanceof Error ? problem.message : String(problem),
      );
    }
  }

  async function pokreni(): Promise<void> {
    if (izabranPipeline === null) {
      setGreskaSnimanja("Izaberi pipeline pre pokretanja.");
      return;
    }
    try {
      const pokretanje = await start(izabranPipeline.id);
      setIzabranoPokretanje(pokretanje.id);
      setOsvezi((prethodno) => prethodno + 1);
      setGreskaSnimanja("");
    } catch (problem) {
      setGreskaSnimanja(
        problem instanceof Error ? problem.message : String(problem),
      );
    }
  }

  async function obrisi(pipelineId: number): Promise<void> {
    const pipeline = pipelines.find((p) => p.id === pipelineId);
    if (!pipeline) {
      return;
    }
    if (
      !window.confirm(
        `Obrisati pipeline „${pipeline.name}"? Ovo briše i svu istoriju pokretanja.`,
      )
    ) {
      return;
    }
    try {
      await remove(pipeline.id);
      if (izabran === pipeline.id) {
        setIzabran(null);
        setIzabranoPokretanje(null);
      }
      setGreskaSnimanja("");
    } catch (problem) {
      setGreskaSnimanja(
        problem instanceof Error ? problem.message : String(problem),
      );
    }
  }

  if (repositories.length === 0) {
    return (
      <div className="cpipe-page">
        <header className="cpipe-head">
          <p className="cpipe-eyebrow">CODIUM · Kod</p>
          <h1>Pipelines</h1>
        </header>
        <p className="cpipe-prazno">
          Nijedan repozitorijum nije registrovan. Dodaj ga na strani Repositories —
          pipeline se uvek pokreće nad repozitorijumom.
        </p>
      </div>
    );
  }

  return (
    <div
      className={`cpipe-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cpipe-head">
        <p className="cpipe-eyebrow">CODIUM · Kod</p>
        <h1>Pipelines</h1>
        <p className="cpipe-sub">
          Definicija koraka, pokretanje nad repozitorijumom i ispis svakog posla.
        </p>
        <div className="cpipe-alat">
          <label htmlFor="cpipe-repo">Repozitorijum</label>
          <select
            id="cpipe-repo"
            aria-label="Repozitorijum"
            value={repoId ?? ""}
            onChange={(dogadjaj) => {
              setRepoId(Number(dogadjaj.target.value));
              setIzabran(null);
              setIzabranoPokretanje(null);
            }}
          >
            {repositories.map((repo) => (
              <option key={repo.id} value={repo.id}>
                {repo.name}
              </option>
            ))}
          </select>
          {isLoading && <span className="cpipe-hint">Učitavanje…</span>}
        </div>
      </header>

      {error && <p className="cpipe-error">{error}</p>}

      <div className="cpipe-grid smart-stack">
        <SmartFrame
          icon={<Workflow size={15} strokeWidth={1.8} />}
          id="pipelines"
          layout={layout}
          title="Pipelines"
        >
          <section className="cpipe-panel">
            <h2>Pipelines</h2>
            <PipelineList
              pipelines={pipelines}
              selectedId={izabran}
              onSelect={(id) => {
                setIzabran(id);
                setIzabranoPokretanje(null);
              }}
              onRemove={(id) => void obrisi(id)}
            />
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<History size={15} strokeWidth={1.8} />}
          id="istorija"
          layout={layout}
          title="Istorija pokretanja"
        >
          <section className="cpipe-panel">
            <h2>Istorija pokretanja</h2>
            <RunHistory
              pipelineId={izabran}
              selectedRunId={izabranoPokretanje}
              onSelect={setIzabranoPokretanje}
              refreshKey={osvezi}
            />
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<FileCode2 size={15} strokeWidth={1.8} />}
          id="definicija"
          layout={layout}
          title="Definicija"
        >
          <section className="cpipe-panel cpipe-panel-editor">
            <h2>Definicija</h2>
            <DefinitionEditor
              value={definicija}
              onSave={(tekst) => void snimi(tekst)}
              onRun={() => void pokreni()}
              saveError={greskaSnimanja}
            />
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<ListChecks size={15} strokeWidth={1.8} />}
          id="detalj"
          layout={layout}
          title="Detalj pokretanja"
        >
          <section className="cpipe-panel cpipe-panel-detalj">
            <h2>Detalj pokretanja</h2>
            <RunDetail
              runId={izabranoPokretanje}
              onCancelled={() => setOsvezi((prethodno) => prethodno + 1)}
              onRunEnded={() => setOsvezi((prethodno) => prethodno + 1)}
            />
          </section>
        </SmartFrame>
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
