import { useCallback, useEffect, useRef, useState } from "react";

import { fetchRunDetail, fetchRunLogs } from "../../../services/codiumApi";
import type { PipelineRun, RunLogLine, RunStep } from "../../../types/codium";

// Koliko redova prikaz drži pre nego što najstariji počnu da ispadaju.
// Redovi ostaju u bazi — seče se samo prikaz.
export const MAX_PRIKAZANIH = 2000;

// Na koliko se pita dok pokretanje radi.
const RAZMAK_MS = 500;

const U_TOKU = new Set(["queued", "running"]);

/**
 * Jedno pokretanje uživo: zaglavlje, koraci i log koji stiže u prirastima.
 *
 * `setTimeout`, ne `setInterval`: spor odgovor ne sme da naslaže zahteve jedan
 * preko drugog. Petlja se gasi tek posle JOŠ JEDNOG kruga pošto status pređe u
 * završni — poslednja serija loga stiže iz sink-a tek na `flush()` pri kraju
 * pokretanja, pa bi bez toga poslednji redovi nedostajali.
 *
 * Zastavica za odbacivanje starog odgovora je LOKALNA promenljiva efekta, ne
 * ref: da je ref deljen između pokretanja efekta, novo pokretanje bi je
 * resetovalo na `false` pre nego što stari `await` stigne da se vrati, pa bi
 * zakasneli odgovor starog pokretanja upisao svoje podatke preko novog.
 */
export function useRunPolling(runId: number | null) {
  // Sve prikupljeno nosi oznaku pokretanja kome pripada. Kad se `runId`
  // promeni, prikaz je prazan zato što se to IZVODI pri crtanju — ranije je
  // zaseban efekat sinhrono brisao pet stanja, pa se između dva crteža video
  // log prethodnog pokretanja pod novim brojem.
  const [pripada, setPripada] = useState<number | null>(null);
  const vazi = pripada === runId;

  const [ucitanRun, setRun] = useState<PipelineRun | null>(null);
  const [ucitaniSteps, setSteps] = useState<RunStep[]>([]);
  const [ucitaneLines, setLines] = useState<RunLogLine[]>([]);
  const [ucitanoSkriveno, setHiddenCount] = useState(0);
  // Pokretanje je „u toku" dok se za njega ne javi da je stalo.
  const [stalo, setStalo] = useState<number | null>(null);
  const [ucitanaGreska, setError] = useState("");

  const run = vazi ? ucitanRun : null;
  const steps = vazi ? ucitaniSteps : [];
  const lines = vazi ? ucitaneLines : [];
  const hiddenCount = vazi ? ucitanoSkriveno : 0;
  const error = vazi ? ucitanaGreska : "";
  const isPolling = runId !== null && stalo !== runId;
  // Broj kruga koji `showAll` podiže da bi prisilio ponovno učitavanje bez
  // toga da se glavni efekat ponovo pokrene po `runId`-ju (koji bi ponovo
  // resetovao `bezGranice`).
  const [krugBroj, setKrugBroj] = useState(0);

  const poslednjiSeq = useRef(0);
  const tajmer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Ogledala trenutnog prikaza: efekat ih čita sinhrono da izračuna koliko je
  // redova višak PRE poziva `setLines`, pa `setHiddenCount` ne zavisi od
  // updater funkcije drugog stanja (React updater mora biti čist).
  const linijeRef = useRef<RunLogLine[]>([]);
  const skrivenoRef = useRef(0);
  // Granica prikaza je REF, ne stanje: da je u zavisnostima efekta, `showAll`
  // bi ga podigao, efekat bi se ponovo pokrenuo i spustio ga — i tako u krug.
  const bezGranice = useRef(false);
  // Da li je za OVO pokretanje već odrađen dvokružni završni tok (dole).
  // `showAll` posle prirodnog kraja ne treba da ponavlja "još jedan krug" —
  // log je već ispražnjen iz sink-a, pa bi drugi krug bio prazan zahtev koji
  // samo produžava `isPolling`. Reset na `runId` promenu, ne na `krugBroj`.
  const zavrsnoOdradjeno = useRef(false);

  const showAll = useCallback(() => {
    bezGranice.current = true;
    poslednjiSeq.current = 0;
    linijeRef.current = [];
    skrivenoRef.current = 0;
    setLines([]);
    setHiddenCount(0);
    setKrugBroj((n) => n + 1);
  }, []);

  // Koje pokretanje je poslednje viđeno — po tome se zna kada ref-ove treba
  // očistiti.
  const prethodniRun = useRef<number | null>(null);

  useEffect(() => {
    // Čišćenje ide po promeni `runId`, ne po svakom pokretanju efekta:
    // `showAll` podiže `krugBroj`, a on ne sme da vrati `bezGranice` na
    // `false` odmah pošto ga je sam postavio na `true`.
    if (prethodniRun.current !== runId) {
      prethodniRun.current = runId;
      poslednjiSeq.current = 0;
      linijeRef.current = [];
      skrivenoRef.current = 0;
      bezGranice.current = false;
      zavrsnoOdradjeno.current = false;
    }

    if (runId === null) {
      return;
    }

    let otkazano = false;

    async function krug(zavrsni: boolean): Promise<void> {
      try {
        const [detalj, log] = await Promise.all([
          fetchRunDetail(runId as number),
          fetchRunLogs(runId as number, poslednjiSeq.current),
        ]);
        if (otkazano) {
          return;
        }

        setPripada(runId);
        setRun(detalj.run);
        setSteps(detalj.steps);

        if (log.lines.length > 0) {
          poslednjiSeq.current = log.lines[log.lines.length - 1].seq;
          const spojeni = [...linijeRef.current, ...log.lines];
          let noveLinije = spojeni;
          let novoSkriveno = skrivenoRef.current;
          if (!bezGranice.current && spojeni.length > MAX_PRIKAZANIH) {
            const visak = spojeni.length - MAX_PRIKAZANIH;
            noveLinije = spojeni.slice(visak);
            novoSkriveno = skrivenoRef.current + visak;
          }
          linijeRef.current = noveLinije;
          skrivenoRef.current = novoSkriveno;
          setLines(noveLinije);
          setHiddenCount(novoSkriveno);
        }

        const jos = U_TOKU.has(detalj.run.status);
        if (jos) {
          tajmer.current = setTimeout(() => void krug(false), RAZMAK_MS);
          return;
        }
        if (!zavrsni) {
          // Status je završni, ali repu loga treba još jedan krug.
          tajmer.current = setTimeout(() => void krug(true), RAZMAK_MS);
          return;
        }
        zavrsnoOdradjeno.current = true;
        setStalo(runId);
      } catch (problem) {
        if (otkazano) {
          return;
        }
        setPripada(runId);
        setError(problem instanceof Error ? problem.message : String(problem));
        setStalo(runId);
      }
    }

    // Kad efekat pokrene `showAll` (krugBroj se menja, ne runId) posle
    // prirodnog kraja pokretanja, kreni pravo na "zadnji krug": nema smisla
    // ponovo raditi dvokružni završni tok kad je već jednom odrađen.
    void krug(zavrsnoOdradjeno.current);

    return () => {
      otkazano = true;
      if (tajmer.current !== null) {
        clearTimeout(tajmer.current);
        tajmer.current = null;
      }
    };
  }, [runId, krugBroj]);

  return { run, steps, lines, hiddenCount, isPolling, error, showAll };
}
