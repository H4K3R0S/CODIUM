import { useEffect } from "react";

/**
 * Traži potvrdu pri zatvaranju prozora dok pokretanje traje.
 *
 * Runner živi u procesu backend-a, pa gašenje CORE-a prekida pokretanje —
 * ovo je jedino mesto koje čoveka na to upozori pre nego što se desi.
 * Van Tauri-ja je no-op, kao `openAiChatWindow`.
 */
export function useCloseGuard(activeRuns: number): void {
  useEffect(() => {
    if (activeRuns <= 0) {
      return;
    }

    let odjava: (() => void) | null = null;
    let odustao = false;

    async function zakaci(): Promise<void> {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        const prozor = getCurrentWindow();
        const skini = await prozor.onCloseRequested((dogadjaj) => {
          const nastavi = window.confirm(
            `Pokretanja u toku: ${activeRuns}. Zatvaranje CORE-a ih prekida. ` +
              "Zaista zatvoriti?",
          );
          if (!nastavi) {
            dogadjaj.preventDefault();
          }
        });
        if (odustao) {
          skini();
          return;
        }
        odjava = skini;
      } catch {
        // Van Tauri-ja (pregledač) nema prozora — nema ni šta da se čuva.
      }
    }

    void zakaci();

    return () => {
      odustao = true;
      if (odjava !== null) {
        odjava();
      }
    };
  }, [activeRuns]);
}
