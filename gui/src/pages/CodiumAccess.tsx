// ==========          ACCESS & USERS          ==========
// Dve stvari na jednoj strani: sta akteri smeju (pravila) i sta upravo ceka
// ljudsku odluku (red odobrenja). Red stoji gore jer je hitniji — pravilo se
// pise jednom, a molba blokira posao dok stoji.
import { Check, ShieldBan, ShieldCheck, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { describePayload } from "../features/codium/approvals";
import { relativeTime } from "../features/codium/activity";
import {
  addScopeRule,
  approveRequest,
  deleteScopeRule,
  getApprovals,
  getScopeRules,
  rejectRequest,
} from "../services/codiumApi";
import SmartFrame from "../components/layout/SmartFrame";
import { useSmartLayout } from "../features/layout/useSmartLayout";
import type { Approval, ScopeRule, ScopeVerdict } from "../types/codium";
import "../styles/codium-access.css";

const PRAZAN_OBRAZAC = {
  actor: "",
  action: "",
  target: "*",
  verdict: "deny" as ScopeVerdict,
  note: "",
};

export default function CodiumAccess() {
  // Isti pametan raspored kao na kontrolnoj tabli: cim razgovor krene okviri se
  // sklapaju u stubac uz levu ivicu, a klik ih otvara kao preview uz chat.
  const layout = useSmartLayout(".sframe");
  // Polja rasporeda se uzimaju jednom, razlaganjem: `react-hooks/refs`
  // prijavljuje svako čitanje polja objekta koji vraća hook, jer ne razlikuje
  // ref od obične vrednosti. Sam objekat ide dalje samo tamo gde ga traži
  // `SmartFrame`.
  const { changeTuck, className, handlePosChange, rootRef } = layout;
  const [rules, setRules] = useState<ScopeRule[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [error, setError] = useState("");
  const [obrazac, setObrazac] = useState(PRAZAN_OBRAZAC);
  const [razlozi, setRazlozi] = useState<Record<number, string>>({});

  // `josTraje` kaze da li ekran jos stoji: odgovor koji kasni ne sme da
  // upise nista u komponentu koje vise nema.
  const ucitaj = useCallback(async (josTraje: () => boolean = () => true) => {
    try {
      const [pravila, molbe] = await Promise.all([
        getScopeRules(),
        getApprovals(),
      ]);
      if (!josTraje()) {
        return;
      }
      setRules(pravila.rules);
      setApprovals(molbe.approvals);
      setError("");
    } catch {
      // Greska je traka iznad sadrzaja, ne prazna strana: vec ucitana
      // pravila ostaju vidljiva.
      setError("Učitavanje nije uspelo.");
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

  const odluci = async (id: number, odobri: boolean) => {
    // Napomena je zajednička za oba ishoda — backend je čuva i uz odobrenje,
    // ne samo uz odbijanje, pa se ovde ne baca ako je čovek stigne da upiše
    // pre klika na Odobri.
    const razlog = razlozi[id] ?? "";
    try {
      if (odobri) {
        await approveRequest(id, razlog);
      } else {
        await rejectRequest(id, razlog);
      }
      await ucitaj();
    } catch {
      setError("Odluka nije prošla — možda je molba već odlučena.");
      await ucitaj();
    }
  };

  const dodajPravilo = async () => {
    if (!obrazac.actor.trim() || !obrazac.action.trim()) {
      return;
    }
    try {
      await addScopeRule(obrazac);
      setObrazac(PRAZAN_OBRAZAC);
      await ucitaj();
    } catch {
      setError("Dodavanje pravila nije uspelo.");
    }
  };

  const obrisiPravilo = async (id: number) => {
    try {
      await deleteScopeRule(id);
      await ucitaj();
    } catch {
      setError("Brisanje pravila nije uspelo.");
    }
  };

  return (
    <div
      className={`cacc-page smart-page ${className}`}
      ref={rootRef}
    >
      <header className="cacc-head">
        <p className="cacc-eyebrow">CODIUM · Sistem</p>
        <h1>Access &amp; Users</h1>
        <p className="cacc-sub">
          Ko sme šta. „Korisnici" su agenti i automatizacije — čovek odobrava.
        </p>
      </header>

      {error && <p className="cacc-error">{error}</p>}

      <div className="smart-stack">
        <SmartFrame
          icon={<ShieldBan size={15} strokeWidth={1.8} />}
          id="odobrenja"
          layout={layout}
          title="Čeka odobrenje"
        >
          <section className="cacc-panel">
            <h2>Čeka odobrenje</h2>
            {approvals.length === 0 ? (
              <p className="cacc-empty">Nema molbi koje čekaju odluku.</p>
            ) : (
              <ul className="cacc-approvals">
                {approvals.map((molba) => (
                  <li className="cacc-approval" key={molba.id}>
                    <div className="cacc-approval-head">
                      <ShieldBan aria-hidden="true" size={15} />
                      <span className="cacc-actor">{molba.actor}</span>
                      <span className="cacc-action">{molba.action}</span>
                      <span className="cacc-target">{molba.target}</span>
                      <span className="cacc-when">
                        {relativeTime(molba.requested_at)}
                      </span>
                    </div>

                    <dl className="cacc-approval-payload">
                      {describePayload(molba.payload).map((linija) => (
                        <div key={linija.label}>
                          <dt>{linija.label}</dt>
                          <dd>{linija.value}</dd>
                        </div>
                      ))}
                    </dl>

                    <div className="cacc-actions">
                      <input
                        aria-label={`Razlog za molbu ${molba.id}`}
                        onChange={(e) =>
                          setRazlozi((prev) => ({
                            ...prev,
                            [molba.id]: e.target.value,
                          }))
                        }
                        placeholder="Napomena (uz odobrenje ili odbijanje)"
                        value={razlozi[molba.id] ?? ""}
                      />
                      <button
                        className="cacc-approve"
                        onClick={() => void odluci(molba.id, true)}
                        type="button"
                      >
                        <Check aria-hidden="true" size={14} /> Odobri
                      </button>
                      <button
                        className="cacc-reject"
                        onClick={() => void odluci(molba.id, false)}
                        type="button"
                      >
                        <X aria-hidden="true" size={14} /> Odbij
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </SmartFrame>

        <SmartFrame
          icon={<ShieldCheck size={15} strokeWidth={1.8} />}
          id="pravila"
          layout={layout}
          title="Pravila dozvola"
        >
          <section className="cacc-panel">
            <h2>Pravila dozvola</h2>
            {rules.length === 0 ? (
              <p className="cacc-empty">
                Nema pravila — važi podrazumevano ponašanje po glagolu akcije.
              </p>
            ) : (
              <table className="cacc-table">
                <thead>
                  <tr>
                    <th>Akter</th>
                    <th>Akcija</th>
                    <th>Cilj</th>
                    <th>Odgovor</th>
                    <th>Napomena</th>
                    <th aria-label="Brisanje" />
                  </tr>
                </thead>
                <tbody>
                  {rules.map((pravilo) => (
                    <tr key={pravilo.id}>
                      <td>{pravilo.actor}</td>
                      <td>{pravilo.action}</td>
                      <td>{pravilo.target}</td>
                      <td className={`cacc-verdict v-${pravilo.verdict}`}>
                        {pravilo.verdict}
                      </td>
                      <td>{pravilo.note}</td>
                      <td>
                        <button
                          aria-label={`Obriši pravilo ${pravilo.id}`}
                          onClick={() => {
                            void obrisiPravilo(pravilo.id as number);
                          }}
                          type="button"
                        >
                          <Trash2 aria-hidden="true" size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <div className="cacc-form">
              <input
                aria-label="Akter pravila"
                onChange={(e) => setObrazac({ ...obrazac, actor: e.target.value })}
                placeholder="agent:architect"
                value={obrazac.actor}
              />
              <input
                aria-label="Akcija pravila"
                onChange={(e) => setObrazac({ ...obrazac, action: e.target.value })}
                placeholder="file.write"
                value={obrazac.action}
              />
              <input
                aria-label="Cilj pravila"
                onChange={(e) => setObrazac({ ...obrazac, target: e.target.value })}
                value={obrazac.target}
              />
              <select
                aria-label="Odgovor pravila"
                onChange={(e) =>
                  setObrazac({ ...obrazac, verdict: e.target.value as ScopeVerdict })
                }
                value={obrazac.verdict}
              >
                <option value="allow">allow</option>
                <option value="needs_approval">needs_approval</option>
                <option value="deny">deny</option>
              </select>
              <input
                aria-label="Napomena pravila"
                onChange={(e) => setObrazac({ ...obrazac, note: e.target.value })}
                placeholder="zašto"
                value={obrazac.note}
              />
              <button onClick={() => void dodajPravilo()} type="button">
                Dodaj pravilo
              </button>
            </div>
          </section>
        </SmartFrame>
      </div>

      {/* Chatbot (donji-centar) — CODIUM asistent (F9). */}
    </div>
  );
}
