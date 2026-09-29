import { useEffect, type RefObject } from "react";


// ==========          VISINA DOCK-A → CSS VAR NA :root          ==========
/**
 * Meri realnu visinu fiksiranog dock-a i upisuje je u CSS varijablu na
 * `document.documentElement` (:root), da bi radni prostor dobio donji razmak
 * (`.workspace-content { padding-bottom: var(<ime>) }`) i sadržaj ne stajao
 * iza chata. Var mora na zajednički predak (root), ne na sam dock — dock je
 * `position: fixed`, van toka, pa njegova varijabla ne bi stigla do sadržaja.
 *
 * `containerRef` pokazuje na omotač; meri se prvi `.cdock`/`.agent-dock` unutar
 * njega (fiksiran element ima svoju visinu), a promene hvata `ResizeObserver`
 * (npr. skupljanje). Čisti varijablu na unmount.
 */
export function useDockHeightVar(
  containerRef: RefObject<HTMLElement | null>,
  varName: string,
): void {
  useEffect(() => {
    const root = document.documentElement;
    const container = containerRef.current;
    if (container === null) {
      return;
    }
    // Meri sam fiksirani dock (omotač je često van toka, visina ~0).
    const target =
      container.matches(".cdock, .agent-dock")
        ? container
        : container.querySelector<HTMLElement>(".cdock, .agent-dock") ?? container;

    const postavi = () => root.style.setProperty(varName, `${target.offsetHeight}px`);
    postavi();

    const ro = new ResizeObserver(postavi);
    ro.observe(target);
    return () => {
      ro.disconnect();
      root.style.removeProperty(varName);
    };
  }, [containerRef, varName]);
}
