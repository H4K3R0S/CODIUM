import { useCallback, useEffect, useState } from "react";

import {
  askCore,
  listCoreModels,
  listCorePersonas,
  type CoreChatTurn,
  type CorePersona,
} from "../../services/coreApi";
import { type CatalogModel } from "../settings/modelPicker";


// ==========          MOZAK CORE CHATA          ==========
// Jedno mesto za persone, izbor modela, istoriju i trošak CORE asistenta.
// (Ranije je živeo u CODIUM domenu; CODIUM je odcepljen u sopstvenu ćeliju, pa
// je ovaj hook prešao na CORE asistent API. CORE nema projekte, pa nema ni
// per-projekat pamćenja modela — izbor važi za tekuću sesiju.)

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

export function useAssistantChat() {
  const [personas, setPersonas] = useState<CorePersona[]>([]);
  // Podrazumevano opšti pomoćnik (globalna persona opsega).
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
        const { personas: list } = await listCorePersonas();
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
      const { models: list } = await listCoreModels("core", true);
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

  function chooseModel(next: string): void {
    if (next === API_KEY_OPTION) {
      // Izbor se ne pamti i ne menja aktivan model — red je dugme, ne model.
      setKljucDijalog(true);
      return;
    }
    // CORE nema per-projekat postavke modela — izbor važi samo za sesiju.
    setModel(next);
  }

  /**
   * Šalje pitanje i vraća odgovor. Istorija ide iz istog niza poruka, pa svaki
   * ekran pamti kontekst na isti način.
   */
  const ask = useCallback(
    async (text: string): Promise<string> => {
      const history: CoreChatTurn[] = messages.map((m) => ({
        author: m.author,
        text: m.text,
      }));
      const mine: ChatMsg = { id: msgId(), author: "me", text };
      setMessages((current) => [...current, mine]);
      setSending(true);

      try {
        const answer = await askCore({
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
    [messages, model, models, persona],
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
