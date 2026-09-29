import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  Boxes,
  Braces,
  CalendarClock,
  FolderOpen,
  Plus,
  Search,
  Star,
  X,
} from "lucide-react";

import {
  createProject,
  getClients,
  getProjects,
  updateProject,
} from "../services/codiumApi";
import { useCoreStringSetting } from "../lib/useCoreSetting";
import AgendaPanel from "../features/codium/AgendaPanel";
import BrainModal from "../features/codium/BrainModal";
import PreviewModal from "../features/codium/PreviewModal";
import ProjectWorkModal from "../features/codium/ProjectWorkModal";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type {
  Client,
  Project,
  ProjectCreateRequest,
  ProjectStatus,
  ProjectVisibility,
} from "../types/codium";
import "../styles/codium-hub.css";


// ==========          POMOĆNE          ==========

const STATUS_LABELS: Record<ProjectStatus, string> = {
  active: "Aktivan",
  paused: "Pauziran",
  done: "Završen",
  archived: "Arhiviran",
};

type FilterKey =
  | "all"
  | "client"
  | "private"
  | "active"
  | "paused"
  | "done";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "Sve" },
  { key: "client", label: "Klijentski" },
  { key: "private", label: "Privatni" },
  { key: "active", label: "Aktivni" },
  { key: "paused", label: "Pauzirani" },
  { key: "done", label: "Završeni" },
];

/** Deli stack string ("python, fastapi") na čipove. */
function stackChips(stack: string): string[] {
  return stack
    .split(/[,;]/)
    .map((part) => part.trim())
    .filter((part) => part !== "");
}

/** Rok je „uskoro" ako je u narednih 7 dana (ili prošao). */
function isDeadlineSoon(deadlineAt: string | null): boolean {
  if (!deadlineAt) {
    return false;
  }
  const deadline = new Date(deadlineAt).getTime();
  if (Number.isNaN(deadline)) {
    return false;
  }
  const week = 7 * 24 * 60 * 60 * 1000;
  return deadline - Date.now() <= week;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("sr-RS");
}


// ==========          FORMA ZA DODAVANJE PROJEKTA          ==========

const EMPTY_FORM: ProjectCreateRequest = {
  name: "",
  type: "",
  visibility: "private",
  client_id: null,
  local_path: "",
  stack: "",
  dev_command: "npm run dev",
  dev_port: 5173,
};

type AddProjectModalProps = {
  clients: Client[];
  onClose: () => void;
  onCreate: (project: ProjectCreateRequest) => Promise<void>;
};

/** Okvir za unos novog projekta (naziv, tip, vidljivost, klijent, stack). */
function AddProjectModal({ clients, onClose, onCreate }: AddProjectModalProps) {
  const [form, setForm] = useState<ProjectCreateRequest>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  function update<K extends keyof ProjectCreateRequest>(
    key: K,
    value: ProjectCreateRequest[K],
  ): void {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(): Promise<void> {
    if (form.name.trim() === "" || saving) {
      return;
    }
    setSaving(true);
    try {
      await onCreate({
        ...form,
        name: form.name.trim(),
        // Privatan projekat nema klijenta.
        client_id: form.visibility === "client" ? form.client_id : null,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="cd-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Dodaj projekat"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="cd-modal">
        <div className="cd-modal-head">
          <h2 className="cd-modal-title">
            <Plus size={18} /> Nov projekat
          </h2>
          <button
            type="button"
            className="cd-modal-close"
            onClick={onClose}
            aria-label="Zatvori"
          >
            <X size={18} />
          </button>
        </div>

        <label className="cd-field">
          <span>Naziv projekta</span>
          <input
            autoFocus
            value={form.name}
            onChange={(event) => update("name", event.target.value)}
            placeholder="npr. CORE Nadogradnja"
          />
        </label>

        <div className="cd-field-row">
          <label className="cd-field">
            <span>Vidljivost</span>
            <select
              value={form.visibility}
              onChange={(event) =>
                update("visibility", event.target.value as ProjectVisibility)
              }
            >
              <option value="private">Privatan</option>
              <option value="client">Klijentski</option>
            </select>
          </label>

          <label className="cd-field">
            <span>Tip</span>
            <input
              value={form.type ?? ""}
              onChange={(event) => update("type", event.target.value)}
              placeholder="web · app · cli · library"
            />
          </label>
        </div>

        {form.visibility === "client" && (
          <label className="cd-field">
            <span>Klijent</span>
            <select
              value={form.client_id ?? ""}
              onChange={(event) =>
                update(
                  "client_id",
                  event.target.value === ""
                    ? null
                    : Number(event.target.value),
                )
              }
            >
              <option value="">— bez klijenta —</option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="cd-field">
          <span>Lokalna putanja</span>
          <input
            value={form.local_path ?? ""}
            onChange={(event) => update("local_path", event.target.value)}
            placeholder="C:\\...\\projekat"
          />
        </label>

        <label className="cd-field">
          <span>Stack (zarezom razdvojeno)</span>
          <input
            value={form.stack ?? ""}
            onChange={(event) => update("stack", event.target.value)}
            placeholder="python, fastapi, react"
          />
        </label>

        {/* Lokalni host: komanda + port; preview URL se izvodi automatski. */}
        <div className="cd-field-row">
          <label className="cd-field">
            <span>Dev komanda (lokalni host)</span>
            <input
              value={form.dev_command ?? ""}
              onChange={(event) => update("dev_command", event.target.value)}
              placeholder="npm run dev"
            />
          </label>
          <label className="cd-field">
            <span>Port</span>
            <input
              type="number"
              value={form.dev_port ?? ""}
              onChange={(event) =>
                update(
                  "dev_port",
                  event.target.value === ""
                    ? null
                    : Number(event.target.value),
                )
              }
              placeholder="5173"
            />
          </label>
        </div>

        {form.dev_port != null && String(form.dev_port) !== "" && (
          <p className="cd-form-hint">
            Preview URL: http://localhost:{form.dev_port}
          </p>
        )}

        <div className="cd-modal-actions">
          <button type="button" className="cd-btn-ghost" onClick={onClose}>
            Otkaži
          </button>
          <button
            type="button"
            className="cd-btn-primary"
            onClick={() => void submit()}
            disabled={form.name.trim() === "" || saving}
          >
            {saving ? "Čuvam…" : "Napravi projekat"}
          </button>
        </div>
      </div>
    </div>
  );
}


// ==========          KARTICA PROJEKTA          ==========

type ProjectCardProps = {
  project: Project;
  clientName: string | null;
  isActive: boolean;
  onOpen: (project: Project) => void;
  onBrain: (project: Project) => void;
  onWork: (project: Project) => void;
  onPreview: (project: Project) => void;
};

function ProjectCard({
  project,
  clientName,
  isActive,
  onOpen,
  onBrain,
  onWork,
  onPreview,
}: ProjectCardProps) {
  const chips = stackChips(project.stack);
  return (
    <article className={`cd-card ${isActive ? "is-active" : ""}`}>
      <div className="cd-card-head">
        <span className={`cd-badge ${project.visibility}`}>
          {project.visibility === "client" ? "Klijent" : "Privatno"}
        </span>
        <span className={`cd-status-dot cd-status-${project.status}`}>
          {STATUS_LABELS[project.status]}
        </span>
      </div>

      <h3 className="cd-card-title">
        {isActive && <Star size={14} style={{ marginRight: 4 }} />}
        {project.name}
      </h3>

      <div className="cd-card-meta">
        {clientName && <span>Klijent: {clientName}</span>}
        <span
          className={`cd-deadline ${
            isDeadlineSoon(project.deadline_at) ? "soon" : ""
          }`}
        >
          Rok: {formatDate(project.deadline_at)}
        </span>
        <span>Poslednji rad: {formatDate(project.last_opened_at)}</span>
      </div>

      {chips.length > 0 && (
        <div className="cd-stack">
          {chips.map((chip) => (
            <span key={chip} className="cd-chip">
              {chip}
            </span>
          ))}
        </div>
      )}

      <div className="cd-card-actions">
        <button
          type="button"
          className="cd-action primary"
          onClick={() => onOpen(project)}
        >
          {isActive ? "Aktivan" : "Otvori"}
        </button>
        <button
          type="button"
          className="cd-action"
          onClick={() => onPreview(project)}
          title="Otvori preview prozor (dev server / staging / live)"
        >
          Preview
        </button>
        <button
          type="button"
          className="cd-action"
          onClick={() => onBrain(project)}
          title="Project brain (.codium/)"
        >
          Brain
        </button>
        <button
          type="button"
          className="cd-action"
          onClick={() => onWork(project)}
          title="Taskovi i beleške"
        >
          Tasks
        </button>
      </div>
    </article>
  );
}


// ==========          CODIUM PROJECT HUB          ==========

/**
 * Prvi ekran CODIUM domena: pregled projekata (kartice iz baze), pretraga,
 * filteri, sekcije (Aktivni / Klijentski / Privatni / Nedavno), dodavanje i
 * otvaranje projekta. Otvaranje pamti aktivan projekat (kontekst za beleške).
 */
function CodiumPage() {
  const navigate = useNavigate();
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const [projects, setProjects] = useState<Project[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
  const [showAdd, setShowAdd] = useState(false);
  const [brainProject, setBrainProject] = useState<Project | null>(null);
  const [workProject, setWorkProject] = useState<Project | null>(null);
  const [previewProject, setPreviewProject] = useState<Project | null>(null);

  // Aktivan projekat se pamti (localStorage) — kontekst za auto-vezivanje beleški.
  const [activeProjectId, setActiveProjectId] = useCoreStringSetting(
    "codium.activeProjectId",
    "",
  );

  async function refresh(josTraje: () => boolean = () => true): Promise<void> {
    try {
      const [projectsResponse, clientsResponse] = await Promise.all([
        getProjects(),
        getClients(),
      ]);
      if (!josTraje()) {
        return;
      }
      setProjects(projectsResponse.projects);
      setClients(clientsResponse.clients);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Učitavanje nije uspelo.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await refresh(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, []);

  const clientNameById = useMemo(() => {
    const map = new Map<number, string>();
    for (const client of clients) {
      map.set(client.id, client.name);
    }
    return map;
  }, [clients]);

  // Pretraga + filter po vidljivosti/statusu.
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return projects.filter((project) => {
      if (needle !== "") {
        const haystack = [project.name, project.stack, project.type]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(needle)) {
          return false;
        }
      }
      switch (filter) {
        case "client":
          return project.visibility === "client";
        case "private":
          return project.visibility === "private";
        case "active":
          return project.status === "active";
        case "paused":
          return project.status === "paused";
        case "done":
          return project.status === "done";
        default:
          return true;
      }
    });
  }, [projects, query, filter]);

  const activeIdNum = activeProjectId === "" ? null : Number(activeProjectId);
  const activeProject = projects.find((project) => project.id === activeIdNum);

  // Sekcije (prikazuju se samo ako imaju stavke).
  const sections = useMemo(() => {
    const active = filtered.filter((project) => project.status === "active");
    const clientProjects = filtered.filter(
      (project) => project.visibility === "client",
    );
    const privateProjects = filtered.filter(
      (project) => project.visibility === "private",
    );
    const recent = [...filtered]
      .filter((project) => project.last_opened_at)
      .sort(
        (a, b) =>
          new Date(b.last_opened_at ?? 0).getTime() -
          new Date(a.last_opened_at ?? 0).getTime(),
      )
      .slice(0, 6);

    return [
      { key: "recent", title: "Nedavno otvarano", items: recent },
      { key: "active", title: "Aktivni projekti", items: active },
      { key: "client", title: "Klijentski projekti", items: clientProjects },
      { key: "private", title: "Privatni projekti", items: privateProjects },
    ].filter((section) => section.items.length > 0);
  }, [filtered]);

  async function handleOpen(project: Project): Promise<void> {
    setActiveProjectId(String(project.id));
    // Otvaranje projekta vodi u workspace ljusku (F4).
    navigate(`/codium/workspace/${project.id}`);
    try {
      await updateProject(project.id, {
        last_opened_at: new Date().toISOString(),
      });
    } catch {
      /* nebitno za UI tok */
    }
  }

  async function handleCreate(project: ProjectCreateRequest): Promise<void> {
    await createProject(project);
    await refresh();
  }

  return (
    <div
      className={`cd-page smart-page ${className}`}
      ref={rootRef}
    >
      {/* ==========          ZAGLAVLJE          ========== */}
      <header className="cd-header">
        <div>
          <p className="cd-eyebrow">CODIUM</p>
          <h1 className="cd-title">
            <Braces size={26} /> CODIUM
          </h1>
          <p className="cd-subtitle">
            Projekti, klijenti i razvoj — sve na jednom mestu.
          </p>
        </div>

        {activeProject && (
          <div className="cd-active">
            <FolderOpen size={16} />
            <span className="cd-active-label">Aktivan projekat:</span>
            <span className="cd-active-name">{activeProject.name}</span>
            <button
              type="button"
              className="cd-active-clear"
              onClick={() => setActiveProjectId("")}
              aria-label="Poništi aktivan projekat"
            >
              <X size={14} />
            </button>
          </div>
        )}
      </header>

      {/* ==========          ALATNA TRAKA          ========== */}
      <div className="cd-toolbar">
        <div className="cd-search">
          <Search size={16} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Pretraga po nazivu, stacku, tipu…"
            aria-label="Pretraga projekata"
          />
          {query && (
            <button
              type="button"
              className="cd-search-clear"
              onClick={() => setQuery("")}
              aria-label="Obriši pretragu"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className="cd-filters">
          {FILTERS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`cd-filter ${filter === item.key ? "active" : ""}`}
              onClick={() => setFilter(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          className="cd-btn-primary"
          onClick={() => setShowAdd(true)}
        >
          <Plus size={16} /> Dodaj projekat
        </button>
      </div>

      {/* ==========          AGENDA I SADRŽAJ (skupljivi okviri)          ========== */}
      <div className="smart-stack">
        <SmartFrame
          icon={<CalendarClock size={15} strokeWidth={1.8} />}
          id="agenda"
          layout={layout}
          title="Agenda i rokovi"
        >
          <AgendaPanel />
        </SmartFrame>

        {isLoading ? (
          <p className="cd-message">Učitavam projekte…</p>
        ) : errorMessage ? (
          <p className="cd-message error">{errorMessage}</p>
        ) : projects.length === 0 ? (
          <div className="cd-empty">
            Još nema projekata. Klikni „Dodaj projekat" da napraviš prvi.
          </div>
        ) : sections.length === 0 ? (
          <p className="cd-message">Nema projekata za dati filter/pretragu.</p>
        ) : (
          sections.map((section) => (
            <SmartFrame
              icon={<Boxes size={15} strokeWidth={1.8} />}
              id={`sekcija-${section.key}`}
              key={section.key}
              layout={layout}
              title={section.title}
            >
              <section className="cd-section" aria-label={section.title}>
                <div className="cd-section-head">
                  <h2 className="cd-section-title">{section.title}</h2>
                  <span className="cd-section-count">{section.items.length}</span>
                </div>
                <div className="cd-cards">
                  {section.items.map((project) => (
                    <ProjectCard
                      key={`${section.key}-${project.id}`}
                      project={project}
                      clientName={
                        project.client_id != null
                          ? clientNameById.get(project.client_id) ?? null
                          : null
                      }
                      isActive={project.id === activeIdNum}
                      onOpen={handleOpen}
                      onBrain={setBrainProject}
                      onWork={setWorkProject}
                      onPreview={setPreviewProject}
                    />
                  ))}
                </div>
              </section>
            </SmartFrame>
          ))
        )}
      </div>

      {showAdd && (
        <AddProjectModal
          clients={clients}
          onClose={() => setShowAdd(false)}
          onCreate={handleCreate}
        />
      )}

      {brainProject && (
        <BrainModal
          projectId={brainProject.id}
          projectName={brainProject.name}
          onClose={() => setBrainProject(null)}
        />
      )}

      {workProject && (
        <ProjectWorkModal
          projectId={workProject.id}
          projectName={workProject.name}
          onClose={() => setWorkProject(null)}
        />
      )}

      {previewProject && (
        <PreviewModal
          projectId={previewProject.id}
          projectName={previewProject.name}
          initialUrl={
            previewProject.preview_url ??
            previewProject.staging_url ??
            previewProject.live_url ??
            ""
          }
          onClose={() => setPreviewProject(null)}
        />
      )}

      {/* Chatbot okvir (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}

export default CodiumPage;
