// ==========          BRZO POKRETANJE PREVIEW-A          ==========
/*
 * Deljeni tok: pokreni lokalni host projekta (ako ima dev komandu) pa otvori
 * preview prozor na njegovom URL-u u zadatoj veličini. Koriste ga brza dugmad
 * WEB/MOBI/PC u workspace toolbaru i PreviewModal.
 */
import { startDevServer } from "../../services/codiumApi";
import type { Project } from "../../types/codium";
import {
  getMainContext,
  moveMainTo,
  openPreviewHostAt,
  openPreviewHostOn,
  restoreMainWindow,
} from "../window/workspaceManager";
import { planPreviewPlacement } from "../window/previewPlacement";
import { saveMainFrame } from "../window/windowStateMemory";
import { openPreview } from "./previewOrchestrator";
import {
  normalizePreviewUrl,
  resolvePreviewSize,
  type PreviewDevice,
  type PreviewSize,
} from "./previewProfiles";


export type LaunchResult = {
  ok: boolean;
  url: string | null;
  message: string;
};

/** Efektivni preview URL projekta: preview_url, pa izveden iz dev_port. */
export function projectPreviewUrl(project: Project): string | null {
  if (project.preview_url) {
    return normalizePreviewUrl(project.preview_url);
  }
  if (project.dev_port != null) {
    return normalizePreviewUrl(`http://localhost:${project.dev_port}`);
  }
  return null;
}

/**
 * Pokreće host (best-effort) i otvara preview za dati uređaj. Ako projekat nema
 * dev komandu, preskače pokretanje i samo otvara URL (staging/live/već pokrenut).
 */
export async function launchPreview(
  project: Project,
  device: PreviewDevice,
  customSize?: Partial<PreviewSize>,
): Promise<LaunchResult> {
  const url = projectPreviewUrl(project);
  if (!url) {
    return {
      ok: false,
      url: null,
      message: "Projekat nema preview URL (dodaj port ili URL).",
    };
  }

  let started = false;
  if (project.dev_command.trim() !== "") {
    try {
      await startDevServer(project.id);
      started = true;
    } catch {
      // Host možda već radi ili komanda ne uspeva — svejedno probaj da otvoriš.
    }
  }

  if (started) {
    // Dev server-u treba trenutak da počne da sluša.
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }

  const size = resolvePreviewSize(device, customSize);
  const title = `Preview — ${project.name}`;

  // Pametno pozicioniranje: dokuj desno od Main-a ako ima mesta, inače Main
  // migrira na drugi monitor a preview zauzme (0,0) trenutnog.
  const ctx = await getMainContext();
  if (ctx) {
    const plan = planPreviewPlacement(ctx.frame, ctx.monitor, ctx.monitors, size);
    if (plan.mode === "evacuate" && plan.mainTargetFrame) {
      saveMainFrame(ctx.frame);
      await moveMainTo(plan.mainTargetFrame);
    }
    const win = await openPreview({
      projectId: project.id,
      url,
      size,
      title,
      frame: plan.previewFrame,
    });
    if (plan.mode === "evacuate" && win) {
      void win.once("tauri://destroyed", () => void restoreMainWindow());
    }
    return {
      ok: true,
      url,
      message:
        plan.mode === "dock-right"
          ? `Preview dokovan desno od CORE: ${url}.`
          : `Nema mesta desno — Main prebačen, preview na 0,0: ${url}.`,
    };
  }

  // Van Tauri-ja (browser): prosto otvori (no-op prozor).
  await openPreview({ projectId: project.id, url, size, title });
  return { ok: true, url, message: `Preview otvoren: ${url}.` };
}

/**
 * Otvara preview TAB host (WEB|PC|MOBI, isti URL) na centralnom monitoru —
 * pokreće lokalni host ako projekat ima dev komandu.
 */
export async function launchPreviewTabs(project: Project): Promise<LaunchResult> {
  const url = projectPreviewUrl(project);
  if (!url) {
    return { ok: false, url: null, message: "Projekat nema preview URL." };
  }

  let started = false;
  if (project.dev_command.trim() !== "") {
    try {
      await startDevServer(project.id);
      started = true;
    } catch {
      /* host možda već radi */
    }
  }
  if (started) {
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }

  // Tab host je širok (PC tab 1280); pametno pozicioniranje kao i single preview.
  const required = { width: 1300, height: 1000 };
  const ctx = await getMainContext();
  if (ctx) {
    const plan = planPreviewPlacement(ctx.frame, ctx.monitor, ctx.monitors, required);
    if (plan.mode === "evacuate" && plan.mainTargetFrame) {
      saveMainFrame(ctx.frame);
      await moveMainTo(plan.mainTargetFrame);
    }
    const win = openPreviewHostAt({
      url,
      kinds: ["web", "pc", "mobi"],
      frame: plan.previewFrame,
    });
    if (plan.mode === "evacuate" && win) {
      void win.once("tauri://destroyed", () => void restoreMainWindow());
    }
    return {
      ok: true,
      url,
      message:
        plan.mode === "dock-right"
          ? `Tab preview dokovan desno od CORE: ${url}.`
          : `Nema mesta desno — Main prebačen, tab preview na 0,0: ${url}.`,
    };
  }

  // Van Tauri-ja: centralni monitor.
  await openPreviewHostOn({ url, kinds: ["web", "pc", "mobi"], target: "central" });
  return { ok: true, url, message: `Tab preview otvoren: ${url}.` };
}
