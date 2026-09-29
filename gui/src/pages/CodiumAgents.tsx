// ==========          AI AGENTS          ==========
// Agent radi u koracima i svaki mu potez prolazi kroz kapiju. Zato uz svaki
// alat u uredjivacu pise koju dozvolu trazi: covek koji cekira alat mora da
// vidi sta time otvara.
import { Bot, ListChecks, Play, ShieldAlert, Square, Wrench } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { isRunLive, runLabel, stepTone } from "../features/codium/agentRun";
import { relativeTime } from "../features/codium/activity";
import { useCoreStringSetting } from "../lib/useCoreSetting";
import {
  cancelAgentRun,
  getAgentRun,
  getAgentTools,
  getAgents,
  getProjects,
  startAgentRun,
  updateAgent,
} from "../services/codiumApi";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type {
  AgentRunSummary,
  AgentStep,
  AgentSummary,
  AgentTool,
  Project,
} from "../types/codium";
import "../styles/codium-agents.css";

// Razmak izmedju provera stanja posla. Kratko dovoljno da izgleda zivo,
// dugacko dovoljno da ne tuce server dok model razmislja.
const POLL_MS = 1500;

export default function CodiumAgents() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [tools, setTools] = useState<AgentTool[]>([]);
  const [izabran, setIzabran] = useState<AgentSummary | null>(null);
  const [zadatak, setZadatak] = useState("");
  const [run, setRun] = useState<AgentRunSummary | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [error, setError] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);

  // Isti kljuc kojim CODIUM projekat pamti koji je otvoren (CodiumPage,
  // CodiumOverview, CodiumWorkspace) — agent mora da radi nad istim
  // projektom koji covek gleda, ne nad drugim izvorom istine.
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const [activeProjectId] = useCoreStringSetting("codium.activeProjectId", "");
  const activeProjekat = projects.find(
    (p) => String(p.id) === activeProjectId,
  ) ?? null;

  // Posao koji je trenutno prikazan i poslednji vidjen korak za njega.
  // Cuvaju se zajedno — ne kao goli indeks — jer poll za stariji posao moze
  // da stigne posle sto je novi vec pokrenut; bez id-a uz indeks, njegov
  // odgovor bi se pripisao pogresnom poslu i pomesao dve istorije koraka.
  const aktivniPoll = useRef<{ runId: number; idx: number } | null>(null);

  // `josTraje` kaze da li ekran jos stoji: odgovor koji kasni ne sme da
  // upise nista u komponentu koje vise nema.
  const ucitaj = useCallback(async (josTraje: () => boolean = () => true) => {
    try {
      const [spisak, alati, projektiOdg] = await Promise.all([
        getAgents(), getAgentTools(), getProjects(),
      ]);
      if (!josTraje()) {
        return;
      }
      setAgents(spisak.agents);
      setTools(alati.tools);
      setProjects(projektiOdg.projects);
      setIzabran((prev) =>
        prev ? spisak.agents.find((a) => a.id === prev.id) ?? prev
             : spisak.agents[0] ?? null,
      );
      setError("");
    } catch {
      setError("Učitavanje agenata nije uspelo.");
    }
  }, []);

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await ucitaj(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [ucitaj]);

  // ----------          POLL          ----------

  useEffect(() => {
    if (run === null || !isRunLive(run.status)) {
      return;
    }
    const runId = run.id;
    const timer = window.setInterval(async () => {
      const posaljiOd = aktivniPoll.current?.runId === runId
        ? aktivniPoll.current.idx
        : -1;
      try {
        const sveze = await getAgentRun(runId, posaljiOd);
        // Dok je odgovor bio u letu, mogao je da se pokrene sledeci posao —
        // ovaj odgovor tada vise ne pripada onome sto je na ekranu i baca se.
        if (aktivniPoll.current?.runId !== runId) {
          return;
        }
        if (sveze.steps.length > 0) {
          aktivniPoll.current = {
            runId,
            idx: sveze.steps[sveze.steps.length - 1].idx,
          };
          setSteps((prev) => [...prev, ...sveze.steps]);
        }
        setRun(sveze.run);
      } catch {
        // Jedan promasen poll nije razlog da se prikaz obori; sledeci ce
        // doneti isto stanje.
      }
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [run]);

  // ----------          RADNJE          ----------

  const promeniAlat = async (ime: string, ukljucen: boolean) => {
    if (izabran === null) {
      return;
    }
    const novi = ukljucen
      ? [...izabran.tools, ime]
      : izabran.tools.filter((t) => t !== ime);
    try {
      const posle = await updateAgent(izabran.id, { tools: novi });
      setIzabran(posle);
      setAgents((prev) => prev.map((a) => (a.id === posle.id ? posle : a)));
    } catch {
      setError("Izmena alata nije uspela.");
    }
  };

  const sacuvajPrompt = async (prompt: string, maxSteps: number) => {
    if (izabran === null) {
      return;
    }
    try {
      const posle = await updateAgent(izabran.id, {
        system_prompt: prompt,
        max_steps: maxSteps,
      });
      setIzabran(posle);
      setAgents((prev) => prev.map((a) => (a.id === posle.id ? posle : a)));
    } catch {
      setError("Čuvanje agenta nije uspelo.");
    }
  };

  const pokreni = async () => {
    // Dugme je vec onemoguceno dok je posao ziv, ali provera ostaje i ovde —
    // dvostruki klik pre ponovnog crtanja ne sme da pokrene drugi posao.
    if (izabran === null || !zadatak.trim() || (run !== null && isRunLive(run.status))) {
      return;
    }
    try {
      // Bez id-a projekta agent radi nad korenom CORE repozitorijuma
      // (fallback na backendu) — treci argument se salje samo kad postoji
      // aktivan projekat, da se ne nametne id kad ga nema.
      const { run_id } = activeProjekat
        ? await startAgentRun(izabran.id, zadatak.trim(), activeProjekat.id)
        : await startAgentRun(izabran.id, zadatak.trim());
      aktivniPoll.current = { runId: run_id, idx: -1 };
      setSteps([]);
      const prvo = await getAgentRun(run_id);
      setSteps(prvo.steps);
      if (prvo.steps.length > 0) {
        aktivniPoll.current = {
          runId: run_id,
          idx: prvo.steps[prvo.steps.length - 1].idx,
        };
      }
      setRun(prvo.run);
      setError("");
    } catch {
      setError("Pokretanje posla nije uspelo.");
    }
  };

  const prekini = async () => {
    if (run === null) {
      return;
    }
    try {
      setRun(await cancelAgentRun(run.id));
    } catch {
      setError("Prekid nije prošao — možda je posao već završen.");
    }
  };

  // ----------          PRIKAZ          ----------

  return (
    <div
      className={`cag-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cag-head">
        <p className="cag-eyebrow">CODIUM · AI &amp; Automation</p>
        <h1>AI Agents</h1>
        <p className="cag-sub">
          Agent ima alate, radi u koracima, i svaki potez mu proverava kapija.
        </p>
      </header>

      {error && <p className="cag-error">{error}</p>}

      <div className="cag-grid smart-stack">
        <SmartFrame
          icon={<Bot size={15} strokeWidth={1.8} />}
          id="agenti"
          layout={layout}
          title="Agenti"
        >
          <section className="cag-panel cag-list">
            <h2>Agenti</h2>
            <ul>
              {agents.map((agent) => (
                <li key={agent.id}>
                  <button
                    className={agent.id === izabran?.id ? "is-active" : ""}
                    onClick={() => setIzabran(agent)}
                    type="button"
                  >
                    <Bot aria-hidden="true" size={15} />
                    <span className="cag-name">{agent.name}</span>
                    <span className="cag-meta">
                      {agent.model || "nasleđuje iz chata"} ·{" "}
                      {agent.tools.length} alata
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </SmartFrame>

        {izabran && (
          <SmartFrame
            icon={<Wrench size={15} strokeWidth={1.8} />}
            id="uredjivac"
            layout={layout}
            title={izabran.name}
          >
            <section className="cag-panel cag-editor">
              <h2>{izabran.name}</h2>

              <label htmlFor="cag-prompt">Sistemski prompt</label>
              <textarea
                id="cag-prompt"
                onChange={(e) =>
                  setIzabran({ ...izabran, system_prompt: e.target.value })
                }
                rows={6}
                value={izabran.system_prompt}
              />

              <label htmlFor="cag-steps">Najviše koraka</label>
              <input
                id="cag-steps"
                max={50}
                min={1}
                onChange={(e) =>
                  setIzabran({ ...izabran, max_steps: Number(e.target.value) })
                }
                type="number"
                value={izabran.max_steps}
              />

              <button
                onClick={() =>
                  void sacuvajPrompt(izabran.system_prompt, izabran.max_steps)
                }
                type="button"
              >
                Sačuvaj
              </button>

              <h3>Alati</h3>
              <ul className="cag-tools">
                {tools.map((alat) => (
                  <li key={alat.name}>
                    <label>
                      <input
                        checked={izabran.tools.includes(alat.name)}
                        onChange={(e) =>
                          void promeniAlat(alat.name, e.target.checked)
                        }
                        type="checkbox"
                      />
                      <span className="cag-tool-name">{alat.name}</span>
                    </label>
                    <span className="cag-tool-desc">{alat.description}</span>
                    <span className="cag-tool-action">
                      traži dozvolu <code>{alat.action}</code>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </SmartFrame>
        )}

        <SmartFrame
          icon={<ListChecks size={15} strokeWidth={1.8} />}
          id="zadatak"
          layout={layout}
          title="Zadatak"
        >
          <section className="cag-panel cag-run">
            <h2>Zadatak</h2>
            <p className="cag-project">
              {activeProjekat
                ? <>Radi nad projektom: <strong>{activeProjekat.name}</strong></>
                : "Nijedan projekat nije aktivan — agent radi nad korenom CORE repozitorijuma."}
            </p>
            <textarea
              aria-label="Zadatak za agenta"
              onChange={(e) => setZadatak(e.target.value)}
              placeholder="Analiziraj sloj API-ja i predloži izmenu."
              rows={3}
              value={zadatak}
            />
            <div className="cag-run-actions">
              <button
                disabled={run !== null && isRunLive(run.status)}
                onClick={() => void pokreni()}
                type="button"
              >
                <Play aria-hidden="true" size={14} /> Pokreni
              </button>
              {run !== null && isRunLive(run.status) && (
                <button onClick={() => void prekini()} type="button">
                  <Square aria-hidden="true" size={14} /> Prekini
                </button>
              )}
            </div>

            {run !== null && (
              <>
                <p className={`cag-status s-${run.status}`}>
                  {runLabel(run.status)}
                  {run.steps_used > 0 && ` · ${run.steps_used} koraka`}
                  {run.started_at && ` · ${relativeTime(run.started_at)}`}
                </p>

                {run.status === "waiting_approval" && (
                  <p className="cag-approval">
                    <ShieldAlert aria-hidden="true" size={15} />
                    Potez čeka tvoju odluku.{" "}
                    <a href="#/codium/access">Otvori red odobrenja</a>
                  </p>
                )}

                <ol className="cag-steps">
                  {steps.map((step) => (
                    <li className={`cag-step t-${stepTone(step)}`} key={step.idx}>
                      <span className="cag-step-kind">
                        {step.tool || step.kind}
                      </span>
                      <pre>{step.payload}</pre>
                    </li>
                  ))}
                </ol>

                {run.result && <p className="cag-result">{run.result}</p>}
              </>
            )}
          </section>
        </SmartFrame>
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
