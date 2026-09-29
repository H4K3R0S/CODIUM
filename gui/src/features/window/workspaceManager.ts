// ==========          WINDOW MANAGER (imperativni sloj)          ==========
/*
 * Primena profila i preview akcija preko Tauri window API-ja. Čita monitore
 * dinamički (`availableMonitors`) i mapira ih na uloge (central/left/right),
 * pa računa apsolutni fizički okvir (pozicija monitora + relativni offset).
 *
 * Niske operacije (resize/move trenutnog prozora, otvaranje bare prozora)
 * reuse-uje iz `windowManager` (applyPaneToCurrent, openPane). Van Tauri
 * okruženja sve je no-op.
 */

import { availableMonitors, getCurrentWindow } from "@tauri-apps/api/window";
import { getAllWebviewWindows } from "@tauri-apps/api/webviewWindow";

import { applyPaneToCurrent, isTauri, openPane } from "./windowManager";
import { labelsToClose, panicMainFrame } from "./panicReset";
import { behaviorForDomain } from "./domainBehavior";
import { openSnappedRight } from "./gridSnap";
import type { WindowPane } from "./windowProfiles";
import type { MonitorInfo } from "./windowPlacement";
import {
  absoluteFrame,
  mapMonitors,
  monitorAtPoint,
  monitorForTarget,
  type Frame,
  type MonitorMap,
  type MonitorTarget,
} from "./monitorLayout";
import {
  PREVIEW_SPECS,
  planEvacuation,
  profileById,
  resolveFrame,
  resolveMainFrame,
  type PreviewKind,
  type WorkspaceProfile,
  type WorkspaceWindow,
} from "./workspaceProfiles";
import {
  clearMainFrame,
  readMainFrame,
  saveMainFrame,
} from "./windowStateMemory";
import type { PreviewTabKind } from "./previewTabs";
import type { WebviewWindow } from "@tauri-apps/api/webviewWindow";
import type { WorkspaceAction } from "./workspaceShortcuts";


// ==========          MONITORI          ==========

/** Učita monitore i mapira ih na uloge (central/left-vertical/right-vertical). */
export async function loadMonitorMap(): Promise<MonitorMap> {
  const monitors = await availableMonitors();
  const infos: MonitorInfo[] = monitors.map((m) => ({
    position: { x: m.position.x, y: m.position.y },
    size: { width: m.size.width, height: m.size.height },
  }));
  return mapMonitors(infos);
}


// ==========          PRIMENA JEDNOG PROZORA          ==========

/** Gradi Tauri pane (apsolutni fizički okvir) iz specifikacije prozora. */
function paneFor(window: WorkspaceWindow, monitor: MonitorInfo): WindowPane {
  const abs = absoluteFrame(monitor, resolveFrame(window, monitor));
  return {
    x: abs.x,
    y: abs.y,
    width: abs.width,
    height: abs.height,
    view: window.view,
    title: window.title,
  };
}

/** Pane od eksplicitnog (relativnog) okvira na datom monitoru. */
function paneFromFrame(monitor: MonitorInfo, frame: Frame): WindowPane {
  const abs = absoluteFrame(monitor, frame);
  return { x: abs.x, y: abs.y, width: abs.width, height: abs.height };
}

/** Monitor na kom je trenutni prozor (po centru); fallback central. */
async function currentWindowMonitor(map: MonitorMap): Promise<MonitorInfo | null> {
  try {
    const win = getCurrentWindow();
    const pos = await win.outerPosition();
    const size = await win.outerSize();
    const all = [
      map.central,
      map["left-vertical"],
      map["right-vertical"],
      ...map.others,
    ].filter((m): m is MonitorInfo => m !== null);
    const found = monitorAtPoint(
      all,
      pos.x + size.width / 2,
      pos.y + size.height / 2,
    );
    return found ?? map.central;
  } catch {
    return map.central;
  }
}

/**
 * Realizuje jedan prozor: role "main" menja trenutni prozor, ostali se otvaraju
 * kao zasebni (bare) prozori na svom okviru.
 */
async function realizeWindow(
  window: WorkspaceWindow,
  map: MonitorMap,
): Promise<void> {
  const monitor = monitorForTarget(map, window.monitor);
  if (!monitor) {
    return;
  }
  const pane = paneFor(window, monitor);
  if (window.role === "main") {
    await applyPaneToCurrent(pane);
  } else {
    openPane(pane);
  }
}


// ==========          PROFILI          ==========

/**
 * Primeni profil. Podrazumevano menja SAMO trenutni prozor (na „main" okvir
 * profila) — prečice ne smeju da otvaraju nove prozore. Dodatni prozori
 * (Terminal/Chat i sl.) otvaraju se isključivo kad se eksplicitno zatraži
 * (`openOthers: true`).
 */
export async function applyProfile(
  profile: WorkspaceProfile,
  options?: { openOthers?: boolean },
): Promise<void> {
  if (!isTauri()) {
    return;
  }
  const map = await loadMonitorMap();

  const main = profile.windows.find((w) => w.role === "main");
  const others = profile.windows.filter((w) => w.role !== "main");

  // Uvek: pomeri/resize trenutni prozor na main okvir (ako profil ima main).
  if (main) {
    if (main.adaptive) {
      // Adaptira se monitoru NA KOM je trenutni prozor (pejzaž vs vertikala).
      const monitor = (await currentWindowMonitor(map)) ?? map.central;
      if (monitor) {
        const frame = resolveMainFrame(main.adaptive, monitor);
        await applyPaneToCurrent(paneFromFrame(monitor, frame));
      }
    } else {
      await realizeWindow(main, map);
    }
  }

  // Samo na eksplicitan zahtev: otvori ostale prozore kao nove.
  if (options?.openOthers) {
    for (const window of others) {
      await realizeWindow(window, map);
    }
  }
}

/** Ima li profil dodatne prozore pored glavnog (za „Otvori sve"). */
export function profileHasExtraWindows(profile: WorkspaceProfile): boolean {
  return profile.windows.some((w) => w.role !== "main");
}

/** Primeni profil po ID-u — samo trenutni prozor (bez otvaranja novih). */
export async function applyProfileId(id: string): Promise<void> {
  const profile = profileById(id);
  if (profile) {
    await applyProfile(profile);
  }
}


// ==========          FULLSCREEN          ==========

/** Uključi/isključi OS fullscreen na trenutnom prozoru. */
export async function toggleFullscreen(): Promise<void> {
  if (!isTauri()) {
    return;
  }
  const win = getCurrentWindow();
  const isFull = await win.isFullscreen();
  await win.setFullscreen(!isFull);
}


// ==========          PREVIEW NA MONITOR          ==========

/**
 * Otvara preview na ciljnom monitoru kao NOV(E) prozor(e) — trenutni (glavni)
 * prozor ostaje netaknut. Preview/mobile/pc su zaseban prozor koji se otvara
 * samo kad se zatraži (Alt+M/P ili dugme). Kod PC preview-a otvara i logs.
 */
export async function sendPreviewToMonitor(
  kind: PreviewKind,
  target: MonitorTarget = "left-vertical",
): Promise<void> {
  if (!isTauri()) {
    return;
  }
  const map = await loadMonitorMap();
  const monitor = monitorForTarget(map, target);
  if (!monitor) {
    return;
  }
  for (const spec of PREVIEW_SPECS[kind]) {
    openPane(paneFor({ ...spec, monitor: target }, monitor));
  }
}


// ==========          SNIMANJE TRENUTNOG PROZORA          ==========

/**
 * Pravi korisnički profil iz trenutnog prozora: hvata njegov okvir i monitor
 * na kom je (relativni offset), pa vraća profil sa jednim „main" prozorom.
 * Van Tauri-ja vraća razuman podrazumevani okvir.
 */
export async function captureCurrentAsProfile(
  name: string,
  description: string,
  scope: string,
): Promise<WorkspaceProfile> {
  const base = (target: MonitorTarget, frame: {
    x: number; y: number; width: number; height: number;
  }): WorkspaceProfile => ({
    id: `user-${Date.now()}`,
    name,
    description,
    scope,
    windows: [{ role: "main", monitor: target, frame }],
  });

  if (!isTauri()) {
    return base("central", { x: 0, y: 0, width: 1300, height: 850 });
  }

  const win = getCurrentWindow();
  const pos = await win.outerPosition();
  const size = await win.outerSize();
  const map = await loadMonitorMap();

  const cx = pos.x + size.width / 2;
  const cy = pos.y + size.height / 2;
  const candidates: [MonitorTarget, MonitorInfo | null][] = [
    ["central", map.central],
    ["left-vertical", map["left-vertical"]],
    ["right-vertical", map["right-vertical"]],
  ];

  let target: MonitorTarget = "central";
  let monitor: MonitorInfo | null = map.central;
  for (const [role, mon] of candidates) {
    if (
      mon &&
      cx >= mon.position.x &&
      cx < mon.position.x + mon.size.width &&
      cy >= mon.position.y &&
      cy < mon.position.y + mon.size.height
    ) {
      target = role;
      monitor = mon;
      break;
    }
  }

  const frame = monitor
    ? {
        x: pos.x - monitor.position.x,
        y: pos.y - monitor.position.y,
        width: size.width,
        height: size.height,
      }
    : { x: pos.x, y: pos.y, width: size.width, height: size.height };

  return base(target, frame);
}


// ==========          KONTEKST MAIN PROZORA (za pametno pozicioniranje)          ==========

/** Trenutni okvir Main-a + monitor na kom je + svi monitori. */
export async function getMainContext(): Promise<{
  frame: Frame;
  monitor: MonitorInfo;
  monitors: MonitorInfo[];
} | null> {
  if (!isTauri()) {
    return null;
  }
  const win = getCurrentWindow();
  const pos = await win.outerPosition();
  const size = await win.outerSize();
  const map = await loadMonitorMap();
  const monitors = [
    map.central,
    map["left-vertical"],
    map["right-vertical"],
    ...map.others,
  ].filter((m): m is MonitorInfo => m !== null);
  const frame = { x: pos.x, y: pos.y, width: size.width, height: size.height };
  const monitor =
    monitorAtPoint(monitors, pos.x + size.width / 2, pos.y + size.height / 2) ??
    map.central;
  if (!monitor) {
    return null;
  }
  return { frame, monitor, monitors };
}

/** Pomeri/resize Main na dati apsolutni okvir. */
export async function moveMainTo(frame: Frame): Promise<void> {
  if (!isTauri()) {
    return;
  }
  await applyPaneToCurrent({
    x: frame.x,
    y: frame.y,
    width: frame.width,
    height: frame.height,
  });
}


// ==========          PREVIEW HOST (tabovi WEB|PC|MOBI)          ==========

/**
 * Otvara preview host prozor sa tabovima na ciljnom monitoru. `url` je dev
 * server / staging / live; `kinds` su tabovi (default svi). Bez `frame` puni
 * ceo ciljni monitor.
 */
export function openPreviewHost(opts: {
  url: string;
  kinds?: PreviewTabKind[];
  monitor: MonitorInfo;
  frame?: Frame;
}): WebviewWindow | null {
  if (!isTauri()) {
    return null;
  }
  const frame =
    opts.frame ?? {
      x: 0,
      y: 0,
      width: opts.monitor.size.width,
      height: opts.monitor.size.height,
    };
  const pane = paneFromFrame(opts.monitor, frame);
  pane.view = "preview-host";
  pane.title = "Preview";
  pane.query = {
    url: opts.url,
    tabs: (opts.kinds ?? ["web", "pc", "mobi"]).join(","),
  };
  return openPane(pane);
}


/** Otvara preview host na ciljnom monitoru (podrazumevano centralni). */
export async function openPreviewHostOn(opts: {
  url: string;
  kinds?: PreviewTabKind[];
  target?: MonitorTarget;
  frame?: Frame;
}): Promise<void> {
  if (!isTauri()) {
    return;
  }
  const map = await loadMonitorMap();
  const monitor = monitorForTarget(map, opts.target ?? "central");
  if (!monitor) {
    return;
  }
  openPreviewHost({
    url: opts.url,
    kinds: opts.kinds,
    monitor,
    frame: opts.frame,
  });
}

/** Otvara preview host na EKSPLICITNOM apsolutnom okviru (pametno pozicioniranje). */
export function openPreviewHostAt(opts: {
  url: string;
  kinds?: PreviewTabKind[];
  frame: Frame;
}): WebviewWindow | null {
  if (!isTauri()) {
    return null;
  }
  return openPane({
    x: opts.frame.x,
    y: opts.frame.y,
    width: opts.frame.width,
    height: opts.frame.height,
    view: "preview-host",
    title: "Preview",
    query: {
      url: opts.url,
      tabs: (opts.kinds ?? ["web", "pc", "mobi"]).join(","),
    },
  });
}


// ==========          EVACUATION (PC/WEB preview) + STATE MEMORY          ==========

/**
 * Evakuacija za veliki preview: zapamti okvir Main-a, pomeri Main na vrh
 * vertikalnog monitora i otvori preview preko celog glavnog monitora (0,0).
 * Kad se preview prozor zatvori, Main se automatski vraća na zapamćeno mesto.
 */
export async function evacuateForPreview(
  kind: "pc" | "web",
  url?: string,
): Promise<void> {
  if (!isTauri()) {
    return;
  }
  const map = await loadMonitorMap();
  const plan = planEvacuation(map);
  if (!plan) {
    return;
  }

  // 1) Zapamti trenutni okvir Main prozora.
  try {
    const win = getCurrentWindow();
    const pos = await win.outerPosition();
    const size = await win.outerSize();
    saveMainFrame({
      x: pos.x,
      y: pos.y,
      width: size.width,
      height: size.height,
    });
  } catch {
    /* bez zapamćenog stanja nema ni vraćanja — nastavi */
  }

  // 2) Pomeri Main na vrh vertikalnog monitora (ako postoji).
  if (plan.vertical && plan.mainFrame) {
    await applyPaneToCurrent(paneFromFrame(plan.vertical, plan.mainFrame));
  }

  // 3) Preview preko celog glavnog monitora: sa URL-om → tab host (WEB|PC|MOBI,
  //    aktivan zadati kind), bez URL-a → generički bare prozor.
  const preview = url
    ? openPreviewHost({
        url,
        kinds: kind === "pc" ? ["pc", "web", "mobi"] : ["web", "pc", "mobi"],
        monitor: plan.central,
        frame: plan.previewFrame,
      })
    : (() => {
        const pane = paneFromFrame(plan.central, plan.previewFrame);
        pane.title = kind === "pc" ? "PC Preview" : "WEB Preview";
        pane.view = "preview";
        return openPane(pane);
      })();

  // 4) Vrati Main kad se preview zatvori.
  if (preview) {
    void preview.once("tauri://destroyed", () => {
      void restoreMainWindow();
    });
  }
}

/** Vrati Main prozor na okvir zapamćen pre evakuacije (ako postoji). */
export async function restoreMainWindow(): Promise<void> {
  if (!isTauri()) {
    return;
  }
  const saved = readMainFrame();
  if (!saved) {
    return;
  }
  await applyPaneToCurrent({
    x: saved.x,
    y: saved.y,
    width: saved.width,
    height: saved.height,
  });
  clearMainFrame();
}


// ==========          DOMEN-SVESNO PONAŠANJE (W2)          ==========

/**
 * Primeni podrazumevani profil aktivnog domena na Main (npr. ulazak u Filmium →
 * „filmium-work", Codium → „codium-work"). Samo Main; sateliti idu zasebno.
 */
export async function applyDomainDefaultProfile(domain: string): Promise<void> {
  if (!isTauri()) {
    return;
  }
  await applyProfileId(behaviorForDomain(domain).defaultProfileId);
}

/**
 * Otvara glavni pomoćni prozor domena po njegovoj strategiji:
 *  - Filmium (snap-right): Proširena biblioteka se magnetno lepi desno od Main-a
 *    i puni prostor do kraja ekrana (prati Main pri pomeranju/resize-u).
 *  - ostali: nema generičkog satelita (Codium preview je projektni tok kroz
 *    `launchPreview`; Kalima dolazi u W6). Vraća funkciju za isključivanje.
 */
export async function openDomainSatellite(domain: string): Promise<() => void> {
  if (!isTauri()) {
    return () => {};
  }
  const behavior = behaviorForDomain(domain);
  if (behavior.previewStrategy === "snap-right" && behavior.librarySnapsRight) {
    return openSnappedRight({ view: "library", title: "Biblioteka" });
  }
  return () => {};
}


// ==========          PANIC LAYOUT RESET (W7)          ==========

/**
 * „Panika" (Alt+R): zatvori sve satelitske prozore (preview/terminal/chat…),
 * poništi zapamćenu evakuaciju (da se Main ne vrati preko destroyed-hook-a) i
 * vrati Main na centralni monitor (0,0, default veličina, bez fullscreen-a).
 */
export async function panicReset(): Promise<void> {
  if (!isTauri()) {
    return;
  }

  // 1) Zatvori sve prozore osim trenutnog (Main).
  const keep = getCurrentWindow().label;
  try {
    const all = await getAllWebviewWindows();
    const doomed = new Set(labelsToClose(all.map((w) => w.label), keep));
    for (const w of all) {
      if (doomed.has(w.label)) {
        await w.close().catch(() => {
          /* već zatvoren */
        });
      }
    }
  } catch {
    /* nema pristupa listi prozora — nastavi sa Main resetom */
  }

  // 2) Poništi eventualnu zapamćenu evakuaciju (nema auto-vraćanja).
  clearMainFrame();

  // 3) Main → central (0,0), default veličina, van fullscreen-a.
  const map = await loadMonitorMap();
  const central = map.central;
  if (!central) {
    return;
  }
  await applyPaneToCurrent(paneFromFrame(central, panicMainFrame(central)));
}


// ==========          DISPEČER AKCIJA (prečice)          ==========

/** Izvrši akciju iz prečice (Alt+…). */
export async function dispatchWorkspaceAction(
  action: WorkspaceAction,
): Promise<void> {
  switch (action.type) {
    case "profile":
      await applyProfileId(action.id);
      return;
    case "fullscreen":
      await toggleFullscreen();
      return;
    case "preview":
      await sendPreviewToMonitor(action.kind, action.target);
      return;
    case "evacuate":
      await evacuateForPreview(action.kind);
      return;
    case "panic":
      await panicReset();
      return;
  }
}
