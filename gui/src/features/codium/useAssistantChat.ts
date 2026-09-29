import { useCallback, useEffect, useState } from "react";

import {
  askAssistant,
  clearModelPref,
  getModelPref,
  listAssistantModels,
  listAssistantPersonas,
  setModelPref,
  type AssistantChatTurn,
  type AssistantPersona,
  type CatalogModel,
} from "../../services/codiumApi";


// ==========          MOZAK CODIUM CHATA          ==========
// Jedno mesto za persone, izbor modela, istoriju i trošak. Dashboard i AI
// Workspace koriste isti hook, pa se dva chata ne mogu raziću u ponašanju —
// ranije jesu: Workspace je imao izbornik modela i pamtio razgovor, a
// dashboard je slao `history: []`, dakle svaka poruka je kretala od nule.

/** Vrednost reda koji otvara dijalog za ključ — namerno nije id modela. */
export const API_KEY_OPTION = "__api_key__";

export type ChatMsg = {
  id: string;
  author: "me" | "assistant";
  text: string;
  fallback?: boolean;
};

/** Merenja poslednjeg odgovora, za oznaku ispod chata. */
export type Merenje = { model: string; cost: number; durationMs: number };

function msgId(): string {
  return `m-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useAssistantChat(projectId: number | null) {
  const [personas, setPersonas] = useState<AssistantPersona[]>([]);
  // Podrazumevano opšti razvojni pomoćnik (globalna persona domena).
  const [persona, setPersona] = useState("global");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [models, setModels] = useState<CatalogModel[]>([]);
  const [model, setModel] = useState("");
  const [sending, setSending] = useState(false);
  const [kljucDijalog, setKljucDijalog] = useState(false);
  const [merenje, setMerenje] = useState<Merenje | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { personas: list } = await listAssistantPersonas();
        if (!cancelled && list.length > 0) {
          setPersonas(list);
          setPersona((current) =>
            list.some((p) => p.id === current) ? current : list[0].id,
          );
        }
      } catch {
        // Backend nedostupan — persone ostaju prazne, chat i dalje radi.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // `josTraje` kaze da li ekran jos stoji: odgovor koji kasni ne sme da
  // upise nista u komponentu koje vise nema.
  const osveziKatalog = useCallback(async (josTraje: () => boolean = () => true) => {
    try {
      const { models: list } = await listAssistantModels(true);
      if (!josTraje()) {
        return;
      }
      setModels(list);
    } catch {
      // Katalog nedostupan — bez dropdown-a, chat neometan.
    }
  }, []);

  useEffect(() => {
    let ziv = true;
    async function pokreni() {
      await osveziKatalog(() => ziv);
    }
    void pokreni();
    return () => {
      ziv = false;
    };
  }, [osveziKatalog]);

  // Zapamćen izbor za par (projekat, persona).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { pref } = await getModelPref(projectId, persona);
        if (!cancelled) {
          setModel(pref?.model ?? "");
        }
      } catch {
        if (!cancelled) {
          setModel("");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, persona]);

  function chooseModel(next: string): void {
    if (next === API_KEY_OPTION) {
      // Izbor se ne pamti i ne menja aktivan model — red je dugme, ne model.
      setKljucDijalog(true);
      return;
    }

    setModel(next);

    // Prazan izbor znači „vrati me na podrazumevani". Postavka se mora obrisati,
    // ne samo prestati da se šalje: dok red stoji u bazi, ruter ga bira ispred
    // registra, pa bi izbornik pokazivao „Podrazumevani model" a odgovarao bi
    // zapamćeni.
    if (next === "") {
      void clearModelPref(projectId, persona).catch(() => {
        // Pamćenje je pogodnost, ne uslov.
      });
      return;
    }

    const chosen = models.find((m) => m.id === next);
    if (chosen === undefined) {
      return;
    }
    void setModelPref({
      project_id: projectId,
      persona,
      model: chosen.id,
      provider: chosen.provider,
    }).catch(() => {
      // Pamćenje je pogodnost, ne uslov — neuspeh ne obara izbor u sesiji.
    });
  }

  /**
   * Šalje pitanje i vraća odgovor.
   *
   * Istorija ide iz istog niza poruka bez obzira ko crta razgovor, pa oba
   * ekrana pamte kontekst na isti način.
   */
  const ask = useCallback(
    async (text: string): Promise<string> => {
      const history: AssistantChatTurn[] = messages.map((m) => ({
        author: m.author,
        text: m.text,
      }));
      const mine: ChatMsg = { id: msgId(), author: "me", text };
      setMessages((current) => [...current, mine]);
      setSending(true);

      try {
        const answer = await askAssistant({
          project_id: projectId,
          persona,
          message: text,
          history,
          ...(model === ""
            ? {}
            : { model, provider: models.find((m) => m.id === model)?.provider }),
        });
        setMessages((current) => [
          ...current,
          {
            id: msgId(),
            author: "assistant",
            text: answer.reply,
            fallback: answer.is_fallback,
          },
        ]);
        setMerenje({
          model: answer.model,
          cost: answer.cost_usd,
          durationMs: answer.duration_ms,
        });
        return answer.reply;
      } catch (err) {
        const poruka =
          err instanceof Error ? `Greška: ${err.message}` : "Backend nije dostupan.";
        setMessages((current) => [
          ...current,
          { id: msgId(), author: "assistant", text: poruka, fallback: true },
        ]);
        return poruka;
      } finally {
        setSending(false);
      }
    },
    [messages, model, models, persona, projectId],
  );

  return {
    personas,
    persona,
    setPersona,
    messages,
    models,
    model,
    chooseModel,
    sending,
    merenje,
    ask,
    kljucDijalog,
    setKljucDijalog,
    osveziKatalog,
  };
}
