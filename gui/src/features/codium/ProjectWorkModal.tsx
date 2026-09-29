import { useCallback, useEffect, useState } from "react";
import {
  CheckSquare,
  ListTodo,
  Plus,
  Square,
  StickyNote,
  X,
} from "lucide-react";

import {
  createNote,
  createTask,
  getNotes,
  getTasks,
  updateTask,
} from "../../services/codiumApi";
import type { Note, Task, TaskStatus } from "../../types/codium";


// ==========          TASKS + BELEŠKE PANEL          ==========

type ProjectWorkModalProps = {
  projectId: number;
  projectName: string;
  onClose: () => void;
};

type Tab = "tasks" | "notes";

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "Za rad",
  in_progress: "U toku",
  done: "Gotovo",
  blocked: "Blokirano",
};

/**
 * Sadržaj (tabovi Taskovi/Beleške + telo) bez modal-okvira. Koristi ga i modal
 * (iz sidebara) i dockable panel „Tasks" u Codium docking rasporedu.
 */
export function ProjectWorkContent({ projectId }: { projectId: number }) {
  const [tab, setTab] = useState<Tab>("tasks");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [taskDraft, setTaskDraft] = useState("");
  const [noteTitle, setNoteTitle] = useState("");
  const [noteBody, setNoteBody] = useState("");

  // `josTraje` kaze da li ekran jos stoji: odgovor koji kasni ne sme da
  // upise nista u komponentu koje vise nema.
  const refresh = useCallback(async (josTraje: () => boolean = () => true) => {
    setLoading(true);
    try {
      const [tasksResponse, notesResponse] = await Promise.all([
        getTasks(projectId),
        getNotes(projectId),
      ]);
      if (!josTraje()) {
        return;
      }
      setTasks(tasksResponse.tasks);
      setNotes(notesResponse.notes);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await refresh(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [refresh]);

  async function addTask(): Promise<void> {
    const title = taskDraft.trim();
    if (title === "") {
      return;
    }
    setTaskDraft("");
    await createTask({ title, project_id: projectId });
    await refresh();
  }

  async function toggleTask(task: Task): Promise<void> {
    const next: TaskStatus = task.status === "done" ? "todo" : "done";
    await updateTask(task.id, { status: next });
    await refresh();
  }

  async function addNote(): Promise<void> {
    const title = noteTitle.trim();
    if (title === "") {
      return;
    }
    setNoteTitle("");
    setNoteBody("");
    await createNote({
      title,
      body: noteBody.trim(),
      project_id: projectId,
    });
    await refresh();
  }

  return (
    <>
      <div className="cd-work-tabs">
          <button
            type="button"
            className={`cd-work-tab ${tab === "tasks" ? "active" : ""}`}
            onClick={() => setTab("tasks")}
          >
            <ListTodo size={14} /> Taskovi ({tasks.length})
          </button>
          <button
            type="button"
            className={`cd-work-tab ${tab === "notes" ? "active" : ""}`}
            onClick={() => setTab("notes")}
          >
            <StickyNote size={14} /> Beleške ({notes.length})
          </button>
        </div>

        {loading ? (
          <p className="cd-message">Učitavam…</p>
        ) : tab === "tasks" ? (
          <div className="cd-work-body">
            <div className="cd-work-add">
              <input
                value={taskDraft}
                onChange={(event) => setTaskDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    void addTask();
                  }
                }}
                placeholder="Nov task…"
                aria-label="Nov task"
              />
              <button
                type="button"
                className="cd-btn-primary"
                onClick={() => void addTask()}
                disabled={taskDraft.trim() === ""}
              >
                <Plus size={15} /> Dodaj
              </button>
            </div>

            {tasks.length === 0 ? (
              <p className="cd-message">Nema taskova.</p>
            ) : (
              <ul className="cd-task-list">
                {tasks.map((task) => (
                  <li
                    key={task.id}
                    className={`cd-task ${task.status === "done" ? "done" : ""}`}
                  >
                    <button
                      type="button"
                      className="cd-task-check"
                      onClick={() => void toggleTask(task)}
                      aria-label={
                        task.status === "done"
                          ? "Označi kao nezavršen"
                          : "Označi kao gotov"
                      }
                    >
                      {task.status === "done" ? (
                        <CheckSquare size={16} />
                      ) : (
                        <Square size={16} />
                      )}
                    </button>
                    <span className="cd-task-title">{task.title}</span>
                    <span className={`cd-task-status status-${task.status}`}>
                      {TASK_STATUS_LABELS[task.status]}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div className="cd-work-body">
            <div className="cd-work-add cd-work-add-note">
              <input
                value={noteTitle}
                onChange={(event) => setNoteTitle(event.target.value)}
                placeholder="Naslov beleške…"
                aria-label="Naslov beleške"
              />
              <textarea
                value={noteBody}
                onChange={(event) => setNoteBody(event.target.value)}
                placeholder="Sadržaj (opciono)…"
                rows={2}
                aria-label="Sadržaj beleške"
              />
              <button
                type="button"
                className="cd-btn-primary"
                onClick={() => void addNote()}
                disabled={noteTitle.trim() === ""}
              >
                <Plus size={15} /> Dodaj belešku
              </button>
            </div>

            {notes.length === 0 ? (
              <p className="cd-message">Nema beleški.</p>
            ) : (
              <ul className="cd-note-list">
                {notes.map((note) => (
                  <li key={note.id} className="cd-note">
                    <h4 className="cd-note-title">{note.title}</h4>
                    {note.body && <p className="cd-note-body">{note.body}</p>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
    </>
  );
}


// ==========          MODAL OMOTAČ (iz sidebara)          ==========

/**
 * Panel projekta sa dva taba: Taskovi i Beleške. Modal-okvir oko
 * `ProjectWorkContent` (isti sadržaj koristi i dockable „Tasks" panel).
 */
function ProjectWorkModal({
  projectId,
  projectName,
  onClose,
}: ProjectWorkModalProps) {
  return (
    <div
      className="cd-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={`Taskovi i beleške — ${projectName}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="cd-modal cd-work">
        <div className="cd-modal-head">
          <h2 className="cd-modal-title">
            <ListTodo size={18} /> {projectName}
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
        <ProjectWorkContent projectId={projectId} />
      </div>
    </div>
  );
}

export default ProjectWorkModal;
