import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarClock,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  FolderKanban,
  ListTodo,
  RefreshCw,
  StickyNote,
} from "lucide-react";

import { getAgenda } from "../../services/codiumApi";
import type { AgendaItem, AgendaKind } from "../../types/codium";


// ==========          POMOĆNE FUNKCIJE ZA DATUME          ==========

/** Ključ dana (GGGG-MM-DD) po lokalnom vremenu, za grupisanje i grid. */
function dayKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** Parsira ISO string agende u lokalni Date (tolerantno). */
function parseAt(value: string): Date | null {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** Čitljiv prikaz datuma i vremena; vreme se izostavlja ako je ponoć. */
function formatWhen(date: Date): string {
  const datePart = date.toLocaleDateString("sr-RS", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
  const hasTime = date.getHours() !== 0 || date.getMinutes() !== 0;
  if (!hasTime) {
    return datePart;
  }
  const timePart = date.toLocaleTimeString("sr-RS", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${datePart} · ${timePart}`;
}

const KIND_LABEL: Record<AgendaKind, string> = {
  task: "Task",
  note: "Podsetnik",
  project: "Rok projekta",
};

function KindIcon({ kind }: { kind: AgendaKind }) {
  if (kind === "task") {
    return <ListTodo size={15} />;
  }
  if (kind === "note") {
    return <StickyNote size={15} />;
  }
  return <FolderKanban size={15} />;
}

const MONTH_NAMES = [
  "Januar", "Februar", "Mart", "April", "Maj", "Jun",
  "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar",
];

const WEEKDAY_NAMES = ["Pon", "Uto", "Sre", "Čet", "Pet", "Sub", "Ned"];


// ==========          JEDNA STAVKA AGENDE          ==========

function AgendaRow({ item }: { item: AgendaItem }) {
  const when = parseAt(item.at);
  return (
    <div className={`cd-agenda-row ${item.overdue ? "overdue" : ""}`}>
      <span className={`cd-agenda-kind kind-${item.kind}`}>
        <KindIcon kind={item.kind} />
      </span>
      <div className="cd-agenda-main">
        <span className="cd-agenda-title">{item.title}</span>
        <span className="cd-agenda-sub">{KIND_LABEL[item.kind]}</span>
      </div>
      <span className="cd-agenda-when">
        {item.overdue && <AlertTriangle size={13} />}
        {when ? formatWhen(when) : item.at}
      </span>
    </div>
  );
}


// ==========          LISTA (grupisano po hitnosti)          ==========

type Bucket = { key: string; title: string; items: AgendaItem[] };

function buildBuckets(items: AgendaItem[]): Bucket[] {
  const now = new Date();
  const todayKey = dayKey(now);
  const weekEnd = new Date(now);
  weekEnd.setDate(weekEnd.getDate() + 7);

  const overdue: AgendaItem[] = [];
  const today: AgendaItem[] = [];
  const week: AgendaItem[] = [];
  const later: AgendaItem[] = [];

  for (const item of items) {
    if (item.overdue) {
      overdue.push(item);
      continue;
    }
    const when = parseAt(item.at);
    if (when && dayKey(when) === todayKey) {
      today.push(item);
    } else if (when && when <= weekEnd) {
      week.push(item);
    } else {
      later.push(item);
    }
  }

  return [
    { key: "overdue", title: "Probijen rok", items: overdue },
    { key: "today", title: "Danas", items: today },
    { key: "week", title: "Narednih 7 dana", items: week },
    { key: "later", title: "Kasnije", items: later },
  ].filter((bucket) => bucket.items.length > 0);
}


// ==========          MESEČNI GRID          ==========

function MonthView({ items }: { items: AgendaItem[] }) {
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  // Mapiranje dan → stavke tog dana.
  const byDay = useMemo(() => {
    const map = new Map<string, AgendaItem[]>();
    for (const item of items) {
      const when = parseAt(item.at);
      if (!when) {
        continue;
      }
      const key = dayKey(when);
      const list = map.get(key) ?? [];
      list.push(item);
      map.set(key, list);
    }
    return map;
  }, [items]);

  // Ćelije grida: vodeći praznici (pon-prvi) + svi dani meseca.
  const cells = useMemo(() => {
    const year = cursor.getFullYear();
    const month = cursor.getMonth();
    const first = new Date(year, month, 1);
    // JS: 0=nedelja; pomeramo tako da ponedeljak bude prvi (0).
    const lead = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const result: (Date | null)[] = [];
    for (let i = 0; i < lead; i += 1) {
      result.push(null);
    }
    for (let d = 1; d <= daysInMonth; d += 1) {
      result.push(new Date(year, month, d));
    }
    return result;
  }, [cursor]);

  const todayKey = dayKey(new Date());
  const selectedItems = selectedDay ? byDay.get(selectedDay) ?? [] : [];

  function shiftMonth(delta: number): void {
    setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + delta, 1));
    setSelectedDay(null);
  }

  return (
    <div className="cd-month">
      <div className="cd-month-head">
        <button
          type="button"
          className="cd-month-nav"
          onClick={() => shiftMonth(-1)}
          aria-label="Prethodni mesec"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="cd-month-label">
          {MONTH_NAMES[cursor.getMonth()]} {cursor.getFullYear()}
        </span>
        <button
          type="button"
          className="cd-month-nav"
          onClick={() => shiftMonth(1)}
          aria-label="Sledeći mesec"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      <div className="cd-month-grid">
        {WEEKDAY_NAMES.map((name) => (
          <div key={name} className="cd-month-weekday">
            {name}
          </div>
        ))}

        {cells.map((date, index) => {
          if (!date) {
            return <div key={`empty-${index}`} className="cd-month-cell empty" />;
          }
          const key = dayKey(date);
          const dayItems = byDay.get(key) ?? [];
          const hasOverdue = dayItems.some((item) => item.overdue);
          return (
            <button
              type="button"
              key={key}
              className={[
                "cd-month-cell",
                key === todayKey ? "today" : "",
                key === selectedDay ? "selected" : "",
                dayItems.length > 0 ? "has-items" : "",
              ].join(" ")}
              onClick={() => setSelectedDay(key)}
              disabled={dayItems.length === 0}
            >
              <span className="cd-month-daynum">{date.getDate()}</span>
              {dayItems.length > 0 && (
                <span
                  className={`cd-month-dot ${hasOverdue ? "overdue" : ""}`}
                  aria-hidden="true"
                >
                  {dayItems.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {selectedDay && (
        <div className="cd-month-day">
          <h4 className="cd-month-day-title">{selectedDay}</h4>
          {selectedItems.length === 0 ? (
            <p className="cd-agenda-empty">Nema stavki.</p>
          ) : (
            selectedItems.map((item) => (
              <AgendaRow key={`${item.kind}-${item.ref_id}`} item={item} />
            ))
          )}
        </div>
      )}
    </div>
  );
}


// ==========          GLAVNI PANEL          ==========

type AgendaPanelProps = {
  /** Ako je zadat, agenda se sužava na jedan projekat. */
  projectId?: number;
  /** Koliko dana unapred (default 60 — pokriva listu i par meseci grida). */
  daysAhead?: number;
};

/**
 * Agenda CODIUM domena: objedinjuje rokove taskova, podsetnike beleški i rokove
 * projekata. Dva prikaza — Lista (grupisano po hitnosti) i Mesec (kalendar).
 */
function AgendaPanel({ projectId, daysAhead = 60 }: AgendaPanelProps) {
  const [items, setItems] = useState<AgendaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"list" | "month">("list");

  async function refresh(josTraje: () => boolean = () => true): Promise<void> {
    setLoading(true);
    try {
      const response = await getAgenda({
        daysAhead,
        includeOverdue: true,
        projectId,
      });
      if (!josTraje()) {
        return;
      }
      setItems(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Učitavanje nije uspelo.");
    } finally {
      setLoading(false);
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
    // `refresh` je obična funkcija i pravi se iznova pri svakom crtanju; efekat
    // zato prati podatke od kojih zavisi, a ne nju.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, daysAhead]);

  const buckets = useMemo(() => buildBuckets(items), [items]);
  const overdueCount = items.filter((item) => item.overdue).length;

  return (
    <section className="cd-agenda" aria-label="Agenda i podsetnici">
      <div className="cd-agenda-head">
        <h2 className="cd-agenda-heading">
          <CalendarClock size={18} /> Agenda i rokovi
          {overdueCount > 0 && (
            <span className="cd-agenda-badge">{overdueCount} u kašnjenju</span>
          )}
        </h2>

        <div className="cd-agenda-controls">
          <div className="cd-agenda-tabs">
            <button
              type="button"
              className={`cd-agenda-tab ${view === "list" ? "active" : ""}`}
              onClick={() => setView("list")}
            >
              <ListTodo size={14} /> Lista
            </button>
            <button
              type="button"
              className={`cd-agenda-tab ${view === "month" ? "active" : ""}`}
              onClick={() => setView("month")}
            >
              <CalendarDays size={14} /> Mesec
            </button>
          </div>
          <button
            type="button"
            className="cd-agenda-refresh"
            onClick={() => void refresh()}
            aria-label="Osveži agendu"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {loading ? (
        <p className="cd-agenda-empty">Učitavam agendu…</p>
      ) : error ? (
        <p className="cd-agenda-empty error">{error}</p>
      ) : items.length === 0 ? (
        <p className="cd-agenda-empty">
          Nema rokova ni podsetnika u narednom periodu.
        </p>
      ) : view === "list" ? (
        <div className="cd-agenda-list">
          {buckets.map((bucket) => (
            <div key={bucket.key} className={`cd-agenda-bucket ${bucket.key}`}>
              <h3 className="cd-agenda-bucket-title">
                {bucket.title}
                <span className="cd-agenda-bucket-count">
                  {bucket.items.length}
                </span>
              </h3>
              {bucket.items.map((item) => (
                <AgendaRow key={`${item.kind}-${item.ref_id}`} item={item} />
              ))}
            </div>
          ))}
        </div>
      ) : (
        <MonthView items={items} />
      )}
    </section>
  );
}

export default AgendaPanel;
