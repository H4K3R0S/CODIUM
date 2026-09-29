import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";
import {
  Award,
  Bot,
  Boxes,
  GitBranch,
  LayoutGrid,
  ListTodo,
  Rocket,
  ShieldBan,
  TriangleAlert,
  Workflow,
  X,
} from "lucide-react";

import {
  fetchAlertRules,
  fetchAlerts,
  fetchDeployTargets,
  fetchDeployments,
  fetchMonitoringOverview,
  fetchPipelines,
  fetchRepositories,
  fetchRuns,
  getActivity,
  getAgentRuns,
  getProjects,
  getTasks,
} from "../services/codiumApi";
import { activityTone, relativeTime } from "../features/codium/activity";
import { isRunLive, runLabel } from "../features/codium/agentRun";
import { useCoreStringSetting } from "../lib/useCoreSetting";
import AlertStrip from "../features/codium/monitoring/AlertStrip";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type {
  ActivityItem,
  AgentRunSummary,
  AlertRow,
  Project,
  ServiceOverviewRow,
  Task,
} from "../types/codium";
import "../styles/codium-dashboard.css";


// ==========          POMOĆNE          ==========

/** Napredak projekta = završeni / ukupno taskova (0 ako nema taskova). */
function projectProgress(tasks: Task[]): number {
  if (tasks.length === 0) {
    return 0;
  }
  const done = tasks.filter((task) => task.status === "done").length;
  return Math.round((done / tasks.length) * 100);
}


// ==========          OPIS OKVIRA          ==========

/** Stat kartica: puna u rasporedu, gola ikona u skupljenoj traci. */
type StatItem = {
  id: string;
  icon: ReactNode;
  label: string;
  value: string;
  hint: string;
  /** Faza koja donosi prave podatke; dok stoji, broj je izmišljen. */
  soon?: string;
};

/** Panel (Active Projects, Live Activity, AI Agents). */
type PanelItem = {
  id: string;
  title: string;
  /** Faza koja donosi prave podatke; dok stoji, sadržaj je izmišljen. */
  soon?: string;
  wide?: boolean;
  /** Dugme uz naslov (npr. „Vidi sve"). */
  action?: ReactNode;
  body: ReactNode;
};


// ==========          CODIUM OVERVIEW (dashboard)          ==========

/**
 * Overview ekran CODIUM domena (/codium). Stat kartice i kolone — realni podaci
 * gde postoje (projekti, taskovi), ostalo je označeno kao „mock" dok API ne
 * stigne. Projekti se otvaraju u workspace-u; mreža projekata je na /codium/projects.
 */
function CodiumOverview() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [repoStats, setRepoStats] = useState({ ukupno: 0, prljavih: 0 });
  const [pipelineStats, setPipelineStats] = useState({ ukupno: 0, aktivnih: 0 });
  // Traka aktivnih alarma (E6) — najkorisnija stvar koju zbirna tabla moze
  // da pokaze. Prazna traka znaci da je sve u redu, i to se izgovara.
  const [alarmi, setAlarmi] = useState<AlertRow[]>([]);
  const [pravilaPoServisu, setPravilaPoServisu] = useState<
    Record<number, number>
  >({});
  const [merenjeServisi, setMerenjeServisi] = useState<ServiceOverviewRow[]>([]);
  const [deployStats, setDeployStats] = useState({
    ciljeva: 0,
    poslednja: "",
    cekaOdobrenje: 0,
  });

  const [activeProjectId, setActiveProjectId] = useCoreStringSetting(
    "codium.activeProjectId",
    "",
  );
  const activeIdNum = activeProjectId === "" ? null : Number(activeProjectId);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [projectsResponse, tasksResponse, activityResponse, runsResponse] =
          await Promise.all([getProjects(), getTasks(), getActivity(8), getAgentRuns(5)]);
        if (!cancelled) {
          setProjects(projectsResponse.projects);
          setTasks(tasksResponse.tasks);
          setActivity(activityResponse.items);
          setRuns(runsResponse.runs);
        }
      } catch {
        // Backend nedostupan — ostaju prazne liste (dashboard i dalje radi).
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    fetchRepositories()
      .then((odgovor) => {
        setRepoStats({
          ukupno: odgovor.repositories.length,
          prljavih: odgovor.repositories.filter((r) => r.status.dirty).length,
        });
      })
      // Overview ne sme da padne zbog jedne pločice.
      .catch(() => setRepoStats({ ukupno: 0, prljavih: 0 }));
  }, []);

  useEffect(() => {
    Promise.all([fetchPipelines(), fetchRuns(undefined, 50)])
      .then(([lista, pokretanja]) => {
        setPipelineStats({
          ukupno: lista.pipelines.length,
          aktivnih: pokretanja.runs.filter(
            (run) => run.status === "running" || run.status === "queued",
          ).length,
        });
      })
      // Overview ne sme da padne zbog jedne pločice.
      .catch(() => setPipelineStats({ ukupno: 0, aktivnih: 0 }));
  }, []);

  useEffect(() => {
    Promise.all([fetchDeployTargets(), fetchDeployments(undefined, 20)])
      .then(([ciljevi, istorija]) => {
        const zavrsene = istorija.deployments.filter(
          (isporuka) => isporuka.status === "success" || isporuka.status === "failed",
        );
        setDeployStats({
          ciljeva: ciljevi.targets.length,
          // Istorija stiže najnovija prvo, pa je prva završena i poslednja.
          poslednja: zavrsene.length > 0 ? zavrsene[0].status : "",
          cekaOdobrenje: istorija.deployments.filter(
            (isporuka) => isporuka.status === "pending",
          ).length,
        });
      })
      // Overview ne sme da padne zbog jedne pločice.
      .catch(() => setDeployStats({ ciljeva: 0, poslednja: "", cekaOdobrenje: 0 }));
  }, []);

  useEffect(() => {
    Promise.all([fetchAlerts("firing", 10), fetchAlertRules()])
      .then(([upaljeni, pravila]) => {
        setAlarmi(upaljeni.alerts);
        const mapa: Record<number, number> = {};
        for (const pravilo of pravila.rules) {
          if (pravilo.service_id !== null) {
            mapa[pravilo.id] = pravilo.service_id;
          }
        }
        setPravilaPoServisu(mapa);
      })
      // Traka alarma je dodatak — bez nje tabla i dalje radi.
      .catch(() => setAlarmi([]));
  }, []);

  useEffect(() => {
    fetchMonitoringOverview()
      .then((odgovor) => setMerenjeServisi(odgovor.services))
      .catch(() => setMerenjeServisi([]));
  }, []);

  // Taskovi grupisani po projektu (za napredak i broj).
  const tasksByProject = useMemo(() => {
    const map = new Map<number, Task[]>();
    for (const task of tasks) {
      if (task.project_id == null) {
        continue;
      }
      const list = map.get(task.project_id) ?? [];
      list.push(task);
      map.set(task.project_id, list);
    }
    return map;
  }, [tasks]);

  const activeProjects = useMemo(
    () => projects.filter((project) => project.status === "active"),
    [projects],
  );

  const openTasks = useMemo(
    () => tasks.filter((task) => task.status !== "done").length,
    [tasks],
  );

  // ==========          PAMETAN RASPORED OKO CHATA          ==========
  /*
   * Skupljanje okvira dok razgovor traje, preview uz chat i mesto za chat kada
   * je panel desno — sve to vozi `useSmartLayout`, isti kao na CORE dashboard-u.
   * Ovde ostaje samo kako CODIUM okviri izgledaju u tim stanjima.
   */

  const layout = useSmartLayout(".cdash-stat, .cdash-panel, .cdash-preview");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef, togglePreview } = layout;
  const { tucked, preview } = layout;

  function openProject(project: Project): void {
    setActiveProjectId(String(project.id));
    navigate(`/codium/workspace/${project.id}`);
  }

  // ==========          SADRŽAJ OKVIRA          ==========

  const stats: StatItem[] = [
    {
      id: "stat-projects",
      icon: <Boxes size={20} />,
      label: "Active Projects",
      value: isLoading ? "—" : String(activeProjects.length),
      hint: `${projects.length} ukupno`,
    },
    {
      id: "stat-repos",
      icon: <GitBranch size={20} />,
      label: "Repositories",
      value: isLoading ? "—" : String(repoStats.ukupno),
      hint: `${repoStats.prljavih} sa neispraćenim izmenama`,
    },
    {
      id: "stat-tasks",
      icon: <ListTodo size={20} />,
      label: "Tasks",
      value: isLoading ? "—" : String(openTasks),
      hint: `${tasks.length} ukupno`,
    },
    {
      id: "stat-pipelines",
      icon: <Workflow size={20} />,
      label: "Pipelines",
      value: String(pipelineStats.ukupno),
      hint: `${pipelineStats.aktivnih} u toku`,
    },
    {
      id: "stat-deployments",
      icon: <Rocket size={20} />,
      label: "Deployments",
      value: String(deployStats.ciljeva),
      // Molba koja čeka čoveka je hitnija vest od ishoda poslednje isporuke,
      // pa ona ide u nagoveštaj kad postoji.
      hint:
        deployStats.cekaOdobrenje > 0
          ? `${deployStats.cekaOdobrenje} čeka odobrenje`
          : deployStats.poslednja === ""
            ? "još nema isporuka"
            : `poslednja: ${deployStats.poslednja === "success" ? "uspeh" : "pala"}`,
    },
    {
      id: "stat-quality",
      icon: <Award size={20} />,
      label: "Code Quality",
      value: "A",
      hint: "maintainability",
      soon: "E7 Analytics",
    },
  ];

  const projectsBody = isLoading ? (
    <p className="cdash-empty">Učitavam…</p>
  ) : activeProjects.length === 0 ? (
    <p className="cdash-empty">Nema aktivnih projekata.</p>
  ) : (
    <ul className="cdash-projects">
      {activeProjects.slice(0, 5).map((project) => {
        const progress = projectProgress(tasksByProject.get(project.id) ?? []);
        return (
          <li key={project.id}>
            <button
              type="button"
              className={`cdash-project ${
                project.id === activeIdNum ? "is-active" : ""
              }`}
              onClick={() => openProject(project)}
            >
              <div className="cdash-project-top">
                <span className="cdash-project-name">{project.name}</span>
                <span className="cdash-project-pct">{progress}%</span>
              </div>
              <div className="cdash-progress">
                <span
                  className="cdash-progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="cdash-project-meta">
                <span className="cdash-tag">{project.type || "—"}</span>
                <span className="cdash-tag">
                  {project.stack.split(/[,;]/)[0]?.trim() || "—"}
                </span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );

  const activityBody = isLoading ? (
    <p className="cdash-empty">Učitavam…</p>
  ) : activity.length === 0 ? (
    // Prazno stanje se kaže, ne popunjava izmišljenim redovima.
    <p className="cdash-empty">Još nema zabeleženih dešavanja.</p>
  ) : (
    <ul className="cdash-activity">
      {activity.map((item, index) => {
        const tone = activityTone(item);
        return (
          <li
            key={`${item.at}-${index}`}
            className={`cdash-activity-item tone-${tone}`}
          >
            <span className="cdash-activity-icon">
              {item.kind === "gate" ? (
                <ShieldBan size={15} />
              ) : tone === "error" ? (
                <TriangleAlert size={15} />
              ) : (
                <Bot size={15} />
              )}
            </span>
            <div>
              <p className="cdash-activity-title">{item.title}</p>
              <p className="cdash-activity-meta">
                {item.meta}
                {relativeTime(item.at) !== "" && ` · ${relativeTime(item.at)}`}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );

  const agentsBody = runs.length === 0 ? (
    <p className="cdash-empty">Nijedan agent još nije radio.</p>
  ) : (
    <ul className="cdash-agents">
      {runs.map((run) => (
        <li className="cdash-agent" key={run.id}>
          <span className="cdash-agent-avatar">
            <Bot size={14} />
          </span>
          <div className="cdash-agent-body">
            <p className="cdash-agent-name">{run.task}</p>
            <p className="cdash-agent-role">
              {run.agent_slug || "agent"} · {run.steps_used} koraka
            </p>
          </div>
          <span
            className={`cdash-agent-status ${
              isRunLive(run.status) ? "working" : "idle"
            } s-${run.status}`}
          >
            {runLabel(run.status)}
          </span>
        </li>
      ))}
    </ul>
  );

  const panels: PanelItem[] = [
    {
      id: "panel-projects",
      title: "Active Projects",
      wide: true,
      action: (
        <button
          type="button"
          className="cdash-link"
          onClick={() => navigate("/codium/projects")}
        >
          Vidi sve →
        </button>
      ),
      body: projectsBody,
    },
    { id: "panel-activity", title: "Live Activity", body: activityBody },
    { id: "panel-agents", title: "AI Agents", body: agentsBody },
    {
      id: "panel-podsetnik",
      title: "Podsetnik",
      body: (
        <div style={{ padding: "4px 2px" }}>
          <p style={{ margin: "0 0 6px", fontWeight: 600, color: "#e2e8f0" }}>
            IntelliSense — odloženo
          </p>
          <p className="cdash-empty" style={{ margin: 0 }}>
            Monaco „exports" mapa + Vite ne resolve-uju deep worker importe.
          </p>
        </div>
      ),
    },
  ];

  // Sadržaj preview-a: isti okvir koji je skupljen, samo otvoren uz chat.
  const previewStat = stats.find((item) => item.id === preview);
  const previewPanel = panels.find((item) => item.id === preview);
  const previewTitle = previewStat?.label ?? previewPanel?.title ?? "";

  return (
    <div
      className={`cdash ${className}`}
      ref={rootRef}
    >
      {/* ==========          ZAGLAVLJE          ========== */}
      <header className="cdash-header">
        <div>
          <p className="cdash-eyebrow">CODIUM</p>
          <h1 className="cdash-title">CODIUM — Development Platform</h1>
        </div>
        <div className="cdash-header-actions">
          {tucked && (
            <button
              type="button"
              className="cdash-header-action"
              onClick={() => changeTuck(false)}
            >
              <LayoutGrid size={16} /> Vrati raspored
            </button>
          )}
          <button
            type="button"
            className="cdash-header-action"
            onClick={() => navigate("/codium/projects")}
          >
            <Boxes size={16} /> Svi projekti
          </button>
        </div>
      </header>

      {/* ==========          AKTIVNI ALARMI (E6)          ========== */}
      {/* Stoji iznad svega: ako nesto gori, to je prvo sto treba da se vidi. */}
      <section className="cdash-alarmi" aria-label="Aktivni alarmi">
        <AlertStrip
          alerts={alarmi}
          services={merenjeServisi}
          ruleServiceIds={pravilaPoServisu}
        />
      </section>

      {/* ==========          STAT KARTICE          ========== */}
      <section className="cdash-stats" aria-label="Pregled">
        {stats.map((item) => (
          <article
            key={item.id}
            className={`cdash-stat ${preview === item.id ? "is-previewed" : ""}`}
            // `title` je jedini trag kartice kada je dashboard skupljen u ikone.
            title={`${item.label}: ${item.value}`}
            onClick={tucked ? () => togglePreview(item.id) : undefined}
          >
            <div className="cdash-stat-icon">{item.icon}</div>
            <div className="cdash-stat-body">
              <p className="cdash-stat-label">
                {item.label}
                {item.soon && (
                  <span className="cdash-mock" title={`Prave podatke donosi ${item.soon}`}>
                    {item.soon}
                  </span>
                )}
              </p>
              <p className="cdash-stat-value">{item.value}</p>
              <p className="cdash-stat-hint">{item.hint}</p>
            </div>
          </article>
        ))}
      </section>

      {/* ==========          KOLONE          ========== */}
      <div className="cdash-columns">
        {panels.map((panel) => (
          <section
            key={panel.id}
            className={`cdash-panel ${panel.wide ? "cdash-panel-wide" : ""} ${
              preview === panel.id ? "is-previewed" : ""
            }`}
            title={panel.title}
            onClick={tucked ? () => togglePreview(panel.id) : undefined}
          >
            <div className="cdash-panel-head">
              <h2>
                {panel.title}
                {panel.soon && (
                  <span className="cdash-mock" title={`Prave podatke donosi ${panel.soon}`}>
                    {panel.soon}
                  </span>
                )}
              </h2>
              {panel.action}
            </div>
            {panel.body}
          </section>
        ))}
      </div>

      {/* ==========          PREVIEW UZ CHAT          ========== */}
      {preview !== null && (
        <aside
          // Ključ po okviru: promena kartice ponovo odigra klizanje.
          key={preview}
          className="cdash-preview"
          aria-label={`Preview — ${previewTitle}`}
        >
          <div className="cdash-preview-head">
            <h2>{previewTitle}</h2>
            <button
              type="button"
              className="cdash-preview-close"
              onClick={() => togglePreview(preview)}
              aria-label="Zatvori preview"
              title="Zatvori"
            >
              <X size={15} />
            </button>
          </div>
          <div className="cdash-preview-body">
            {previewStat !== undefined && (
              <div className="cdash-preview-stat">
                <span className="cdash-stat-icon">{previewStat.icon}</span>
                <p className="cdash-stat-value">{previewStat.value}</p>
                <p className="cdash-stat-hint">{previewStat.hint}</p>
              </div>
            )}
            {previewPanel?.body}
          </div>
        </aside>
      )}

      {/* Chatbot (donji-centar) — CODIUM asistent sa brzim akcijama (F9). */}
    </div>
  );
}

export default CodiumOverview;
