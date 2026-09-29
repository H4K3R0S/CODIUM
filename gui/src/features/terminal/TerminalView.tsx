import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { SearchAddon } from "@xterm/addon-search";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import type { UnlistenFn } from "@tauri-apps/api/event";
import "@xterm/xterm/css/xterm.css";

import {
  killTerminal,
  onTermData,
  onTermExit,
  resizeTerminal,
  spawnTerminal,
  writeTerminal,
  type EnvPair,
} from "./terminalApi";


// ==========          TERMINAL VIEW (xterm + PTY)          ==========

type TerminalViewProps = {
  /** Jedinstven ID sesije (uuid); veza sa PTY-om u Rust-u. */
  id: string;
  shell: string;
  args: string[];
  cwd?: string;
  env?: EnvPair[];
  /** Da li je tab trenutno vidljiv (za refit pri prebacivanju). */
  active: boolean;
  /** Poziva se kad shell izađe (proces završen). */
  onExit?: (id: string) => void;
};

// CORE tamna tema terminala (usaglašeno sa providnim panelima).
const THEME = {
  background: "#0b0e13",
  foreground: "#e9edf2",
  cursor: "#e9edf2",
  selectionBackground: "rgba(120,150,200,0.35)",
};

async function copySelection(term: Terminal): Promise<void> {
  const sel = term.getSelection();
  if (sel && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(sel);
    } catch {
      /* clipboard nedostupan */
    }
  }
}

async function pasteClipboard(id: string): Promise<void> {
  if (!navigator.clipboard) {
    return;
  }
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      await writeTerminal(id, text);
    }
  } catch {
    /* clipboard nedostupan */
  }
}

/**
 * Jedan xterm terminal vezan za PTY sesiju. Sam upravlja životnim ciklusom:
 * mount → fit → spawn shell; kucanje → PTY; izlaz PTY-a → ekran; resize → PTY;
 * unmount → kill + dispose. Prečice: Ctrl+F pretraga, Ctrl+Shift+C/V kopiraj/
 * nalepi, desni klik nalepi, Ctrl+Shift+L očisti. Emit stream je globalan (svi
 * tabovi), pa filtriramo po `id`.
 */
function TerminalView({ id, shell, args, cwd, env, active, onExit }: TerminalViewProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const searchAddonRef = useRef<SearchAddon | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const [searchOpen, setSearchOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const host = hostRef.current;
    if (!host) {
      return;
    }

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: '"Cascadia Mono", "Consolas", ui-monospace, monospace',
      theme: THEME,
      allowProposedApi: true,
    });
    const fit = new FitAddon();
    const search = new SearchAddon();
    term.loadAddon(fit);
    term.loadAddon(search);
    term.open(host);
    termRef.current = term;
    fitRef.current = fit;
    searchAddonRef.current = search;

    // Sigurno fitovanje: element ume da nema meru u prvom frame-u.
    const safeFit = (): { cols: number; rows: number } => {
      try {
        fit.fit();
      } catch {
        /* element bez mere */
      }
      const cols = term.cols > 0 ? term.cols : 80;
      const rows = term.rows > 0 ? term.rows : 24;
      return { cols, rows };
    };

    // Prečice koje presrećemo (ostalo ide u shell).
    term.attachCustomKeyEventHandler((event) => {
      if (event.type !== "keydown") {
        return true;
      }
      if (event.ctrlKey && event.shiftKey && event.code === "KeyC") {
        void copySelection(term);
        return false;
      }
      if (event.ctrlKey && event.shiftKey && event.code === "KeyV") {
        void pasteClipboard(id);
        return false;
      }
      if (event.ctrlKey && event.shiftKey && event.code === "KeyL") {
        term.clear();
        return false;
      }
      if (
        (event.ctrlKey && event.code === "KeyF") ||
        (event.ctrlKey && event.shiftKey && event.code === "KeyF")
      ) {
        setSearchOpen(true);
        requestAnimationFrame(() => searchInputRef.current?.focus());
        return false;
      }
      if (event.code === "Escape" && searchInputRef.current) {
        setSearchOpen(false);
        return false;
      }
      return true;
    });

    let unlistenData: UnlistenFn | null = null;
    let unlistenExit: UnlistenFn | null = null;
    let disposed = false;

    void (async () => {
      unlistenData = await onTermData((eventId, bytes) => {
        if (eventId === id && !disposed) {
          term.write(bytes);
        }
      });
      unlistenExit = await onTermExit((eventId) => {
        if (eventId === id && !disposed) {
          term.write("\r\n\x1b[90m[proces završen]\x1b[0m\r\n");
          onExit?.(id);
        }
      });

      const { cols, rows } = safeFit();
      try {
        await spawnTerminal({ id, shell, args, cwd, env, cols, rows });
      } catch (err) {
        term.write(
          `\r\n\x1b[31mNe mogu da pokrenem shell: ${
            err instanceof Error ? err.message : String(err)
          }\x1b[0m\r\n`,
        );
      }
      term.focus();
    })();

    // Kucanje → PTY.
    const dataSub = term.onData((data) => void writeTerminal(id, data));

    // Praćenje veličine kontejnera → fit + resize PTY-a.
    const observer = new ResizeObserver(() => {
      const { cols, rows } = safeFit();
      void resizeTerminal(id, cols, rows);
    });
    observer.observe(host);

    return () => {
      disposed = true;
      observer.disconnect();
      dataSub.dispose();
      unlistenData?.();
      unlistenExit?.();
      void killTerminal(id);
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
      searchAddonRef.current = null;
    };
    // Sesija se veže za `id`; ostali propovi su fiksni za dati tab.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Prebacivanje na ovaj tab → refit (element je dobio meru).
  useEffect(() => {
    if (!active) {
      return;
    }
    const term = termRef.current;
    const fit = fitRef.current;
    if (!term || !fit) {
      return;
    }
    requestAnimationFrame(() => {
      try {
        fit.fit();
      } catch {
        /* bez mere */
      }
      void resizeTerminal(id, term.cols || 80, term.rows || 24);
      term.focus();
    });
  }, [active, id]);

  function runSearch(direction: "next" | "prev"): void {
    const addon = searchAddonRef.current;
    if (!addon || searchTerm === "") {
      return;
    }
    if (direction === "next") {
      addon.findNext(searchTerm);
    } else {
      addon.findPrevious(searchTerm);
    }
  }

  return (
    <div className="cterm-view-inner">
      {searchOpen && (
        <div className="cterm-search">
          <input
            ref={searchInputRef}
            className="cterm-search-input"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                runSearch(event.shiftKey ? "prev" : "next");
              } else if (event.key === "Escape") {
                setSearchOpen(false);
                termRef.current?.focus();
              }
            }}
            placeholder="Pretraga…"
            aria-label="Pretraga u terminalu"
          />
          <button
            type="button"
            className="cterm-search-btn"
            onClick={() => runSearch("prev")}
            aria-label="Prethodno"
          >
            <ArrowUp size={13} />
          </button>
          <button
            type="button"
            className="cterm-search-btn"
            onClick={() => runSearch("next")}
            aria-label="Sledeće"
          >
            <ArrowDown size={13} />
          </button>
          <button
            type="button"
            className="cterm-search-btn"
            onClick={() => {
              setSearchOpen(false);
              termRef.current?.focus();
            }}
            aria-label="Zatvori pretragu"
          >
            <X size={13} />
          </button>
        </div>
      )}
      <div
        ref={hostRef}
        className="cterm-host"
        onContextMenu={(event) => {
          event.preventDefault();
          void pasteClipboard(id);
        }}
      />
    </div>
  );
}

export default TerminalView;
