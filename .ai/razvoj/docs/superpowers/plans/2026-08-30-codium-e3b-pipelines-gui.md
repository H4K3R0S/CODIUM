---
id: codium-5dcdf756-2026-08-30-codium-e3b-pipelines-gui-md
type: plan
domain: codium
namespace: global
visibility: global
tier: domain
title: E3b Pipelines ekran — plan izvođenja
summary: '> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
  (recommended) or superpowers:executing-plans to implement this plan t'
keywords:
- e3b
- pipelines
- ekran
- izvođenja
- docs
- superpowers
- plans
tags:
- superpowers
- plans
source_path: docs/superpowers/plans/2026-08-30-codium-e3b-pipelines-gui.md
edges:
- type: references
  target: core-970a80a2-2026-08-30-codium-e3b-pipelines-gui-design-md
  weight: 0.3
---

# E3b Pipelines ekran — plan izvođenja

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strana `/codium/pipelines` na kojoj se pipeline definiše u Monaco uređivaču, pokreće, prati uživo sa obojenim logom i otkazuje.

**Architecture:** Backend se ne dira — sve rute postoje iz E3a. Tri čista modula (`ansi.ts`, `definitionSchema.ts`, `runBadges.ts`) nose većinu testova jer ne dodiruju ni React ni mrežu. Dva hook-a drže podatke: `usePipelines` listu, `useRunPolling` jedno pokretanje uživo preko `after_seq` prirasta. Komponente su tanke i sastavljaju se na jednoj strani.

**Tech Stack:** React 19 + TypeScript, `@monaco-editor/react`, `@tauri-apps/api/window`, vitest + Testing Library.

**Spec:** [docs/superpowers/specs/2026-08-30-codium-e3b-pipelines-gui-design.md](../specs/2026-08-30-codium-e3b-pipelines-gui-design.md)

## Global Constraints

- **Jezik.** Kod i identifikatori na engleskom; komentari, docstring-ovi, UI stringovi i dokumentacija na srpskom. Praksa ovog repozitorijuma je javna površina na engleskom, a lokalne promenljive na srpskom — prati susedne fajlove.
- **Backend se ne dira.** Nijedan fajl pod `core/` ili `apps/api/` se ne menja. Ako se pokaže da ekranu treba nešto što API ne daje, to je nalaz za zaseban posao — prijavi ga, ne dopisuj backend.
- **Nema nove GUI zavisnosti.** Monaco, dockview i `@tauri-apps/api` su već instalirani.
- **Bez WebSocket-a.** Log stiže polling-om na `logs?after_seq=`.
- **Veličina fajla.** 150–300 linija je cilj.
- **Testovi GUI-ja:** `npm run test -- <putanja>` iz `apps/gui`; provera tipova je `npm run build`.
- **Dve postojeće `tsc` greške** — `src/features/window/CoreDockLayout.tsx` (TS2503) i `src/pages/CodiumWorkspace.tsx` (TS6133) — prethode ovoj grani, poslednji put dirane u `74f6d1f`. Ne popravljaju se ovde. Merilo je da nema **novih**.
- **Van dometa:** panel u workspace-u, okidači osim ručnog, uređivanje definicije van ove strane.

---

### Task 1: Tipovi, API klijent i značke pokretanja

**Files:**
- Modify: `apps/gui/src/types/codium.ts`
- Modify: `apps/gui/src/services/codiumApi.ts`
- Create: `apps/gui/src/features/codium/pipelines/runBadges.ts`
- Test: `apps/gui/src/features/codium/pipelines/runBadges.test.ts`

**Interfaces:**
- Consumes: rute iz E3a pod `/api/v1/codium/pipelines`.
- Produces:
  - tipovi `Pipeline`, `PipelineRun`, `RunStep`, `RunLogLine`, `PipelinesResponse`, `RunsResponse`, `RunDetailResponse`, `RunLogsResponse`, `CancelResponse`, `PipelineCreateRequest`, `PipelineUpdateRequest`
  - funkcije `fetchPipelines`, `createPipeline`, `updatePipeline`, `deletePipeline`, `runPipeline`, `fetchRuns`, `fetchRunDetail`, `fetchRunLogs`, `cancelRun`
  - `runBadge(run: PipelineRun): { label: string; className: string }`
  - `runDuration(run: PipelineRun): string`

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/pipelines/runBadges.test.ts`:

```typescript
import { describe, expect, it } from "vitest";

import { runBadge, runDuration } from "./runBadges";
import type { PipelineRun } from "../../../types/codium";

function pokretanje(izmene: Partial<PipelineRun> = {}): PipelineRun {
  return {
    id: 1,
    pipeline_id: 1,
    status: "success",
    trigger: "manual",
    commit_sha: null,
    branch: null,
    exit_code: 0,
    detail: "",
    started_at: null,
    finished_at: null,
    created_at: "2026-08-30 10:00:00",
    ...izmene,
  };
}

describe("runBadge", () => {
  it("svaki status ima svoj tekst i svoju klasu", () => {
    const ocekivano: Record<string, string> = {
      queued: "u redu",
      running: "radi",
      success: "uspeh",
      failed: "pao",
      cancelled: "otkazano",
      timeout: "istekao",
    };
    for (const [status, tekst] of Object.entries(ocekivano)) {
      const znacka = runBadge(pokretanje({ status }));
      expect(znacka.label).toBe(tekst);
      expect(znacka.className).toBe(`cpipe-znacka ${status}`);
    }
  });

  it("nepoznat status ne ruši prikaz", () => {
    const znacka = runBadge(pokretanje({ status: "nesto-novo" }));
    expect(znacka.label).toBe("nesto-novo");
    expect(znacka.className).toBe("cpipe-znacka nepoznato");
  });
});

describe("runDuration", () => {
  it("pokretanje koje nije počelo nema trajanje", () => {
    expect(runDuration(pokretanje({ started_at: null }))).toBe("");
  });

  it("završeno pokretanje daje razliku u sekundama", () => {
    expect(
      runDuration(
        pokretanje({
          started_at: "2026-08-30 10:00:00",
          finished_at: "2026-08-30 10:00:07",
        }),
      ),
    ).toBe("7 s");
  });

  it("preko minuta ide u minute i sekunde", () => {
    expect(
      runDuration(
        pokretanje({
          started_at: "2026-08-30 10:00:00",
          finished_at: "2026-08-30 10:02:05",
        }),
      ),
    ).toBe("2 min 5 s");
  });

  it("pokretanje koje još radi kaže da traje", () => {
    expect(
      runDuration(pokretanje({ started_at: "2026-08-30 10:00:00", finished_at: null })),
    ).toBe("u toku");
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/pipelines/runBadges.test.ts
```

(iz `apps/gui`.) Očekivano: FAIL — modul `./runBadges` ne postoji.

- [ ] **Step 3: Dodaj tipove**

U `apps/gui/src/types/codium.ts` dodaj:

```typescript
// ==========          PIPELINE-I (E3)          ==========

export interface Pipeline {
  id: number;
  repository_id: number;
  name: string;
  definition: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PipelineRun {
  id: number;
  pipeline_id: number;
  status: string;
  trigger: string;
  commit_sha: string | null;
  branch: string | null;
  exit_code: number | null;
  detail: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface RunStep {
  idx: number;
  name: string;
  status: string;
  exit_code: number | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface RunLogLine {
  seq: number;
  step_idx: number;
  stream: string;
  line: string;
  at: string;
}

export interface PipelinesResponse {
  pipelines: Pipeline[];
}

export interface RunsResponse {
  runs: PipelineRun[];
}

export interface RunDetailResponse {
  run: PipelineRun;
  steps: RunStep[];
}

export interface RunLogsResponse {
  lines: RunLogLine[];
}

export interface CancelResponse {
  cancelled: boolean;
}

export interface PipelineCreateRequest {
  repository_id: number;
  definition: string;
}

export interface PipelineUpdateRequest {
  definition: string;
}
```

- [ ] **Step 4: Dopuni API klijent**

U `apps/gui/src/services/codiumApi.ts` dodaj nove tipove u postojeći `import type { ... }` blok (`CancelResponse`, `Pipeline`, `PipelineCreateRequest`, `PipelinesResponse`, `PipelineRun`, `PipelineUpdateRequest`, `RunDetailResponse`, `RunLogsResponse`, `RunsResponse`) i na dno fajla:

```typescript
// ==========          PIPELINE-I (E3)          ==========

export function fetchPipelines(repositoryId?: number): Promise<PipelinesResponse> {
  const upit = repositoryId === undefined ? "" : `?repository_id=${repositoryId}`;
  return getJson(`/api/v1/codium/pipelines/${upit}`);
}

export function createPipeline(zahtev: PipelineCreateRequest): Promise<Pipeline> {
  return postJson("/api/v1/codium/pipelines/", zahtev);
}

export function updatePipeline(
  pipelineId: number,
  zahtev: PipelineUpdateRequest,
): Promise<Pipeline> {
  return putJson(`/api/v1/codium/pipelines/${pipelineId}`, zahtev);
}

export function deletePipeline(pipelineId: number): Promise<{ deleted: number }> {
  return deleteRequest(`/api/v1/codium/pipelines/${pipelineId}`);
}

export function runPipeline(pipelineId: number): Promise<PipelineRun> {
  return postJson(`/api/v1/codium/pipelines/${pipelineId}/run`, {});
}

export function fetchRuns(
  pipelineId?: number,
  limit = 50,
): Promise<RunsResponse> {
  const filter = pipelineId === undefined ? "" : `&pipeline_id=${pipelineId}`;
  return getJson(`/api/v1/codium/pipelines/runs?limit=${limit}${filter}`);
}

export function fetchRunDetail(runId: number): Promise<RunDetailResponse> {
  return getJson(`/api/v1/codium/pipelines/runs/${runId}`);
}

export function fetchRunLogs(
  runId: number,
  afterSeq = 0,
): Promise<RunLogsResponse> {
  return getJson(
    `/api/v1/codium/pipelines/runs/${runId}/logs?after_seq=${afterSeq}`,
  );
}

export function cancelRun(runId: number): Promise<CancelResponse> {
  return postJson(`/api/v1/codium/pipelines/runs/${runId}/cancel`, {});
}
```

- [ ] **Step 5: Napiši značke**

`apps/gui/src/features/codium/pipelines/runBadges.ts`:

```typescript
import type { PipelineRun } from "../../../types/codium";

// Status sa servera u srpski tekst. Nepoznat status se prikazuje kakav jeste —
// bolje sirov naziv nego prazna značka koja krije da je backend napredovao.
const TEKST: Record<string, string> = {
  queued: "u redu",
  running: "radi",
  success: "uspeh",
  failed: "pao",
  cancelled: "otkazano",
  timeout: "istekao",
};

/** Tekst i CSS klasa značke za jedno pokretanje. */
export function runBadge(run: PipelineRun): { label: string; className: string } {
  const tekst = TEKST[run.status];
  return {
    label: tekst ?? run.status,
    className: `cpipe-znacka ${tekst === undefined ? "nepoznato" : run.status}`,
  };
}

/**
 * Trajanje pokretanja u čitljivom obliku.
 *
 * Vremena sa servera su SQLite `CURRENT_TIMESTAMP` u UTC-u, bez oznake zone,
 * pa se razlika računa tako što se obema stranama doda `Z`. Bez toga bi ih
 * pregledač čitao kao lokalna vremena i razlika bi i dalje bila tačna, ali
 * samo slučajno — dok jedno od njih ne dođe iz drugog izvora.
 */
export function runDuration(run: PipelineRun): string {
  if (!run.started_at) {
    return "";
  }
  if (!run.finished_at) {
    return "u toku";
  }

  const pocetak = Date.parse(`${run.started_at.replace(" ", "T")}Z`);
  const kraj = Date.parse(`${run.finished_at.replace(" ", "T")}Z`);
  if (Number.isNaN(pocetak) || Number.isNaN(kraj)) {
    return "";
  }

  const sekundi = Math.max(0, Math.round((kraj - pocetak) / 1000));
  if (sekundi < 60) {
    return `${sekundi} s`;
  }
  return `${Math.floor(sekundi / 60)} min ${sekundi % 60} s`;
}
```

- [ ] **Step 6: Pokreni test da prođe**

```bash
npm run test -- src/features/codium/pipelines/runBadges.test.ts
```

Očekivano: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/gui/src/types/codium.ts apps/gui/src/services/codiumApi.ts apps/gui/src/features/codium/pipelines
git commit -m "feat(gui): tipovi, API klijent i znacke pokretanja za pipeline-e"
```

---

### Task 2: ANSI parser

**Files:**
- Create: `apps/gui/src/features/codium/pipelines/ansi.ts`
- Test: `apps/gui/src/features/codium/pipelines/ansi.test.ts`

**Interfaces:**
- Consumes: ništa.
- Produces: `AnsiChunk = { text: string; color?: string; bold?: boolean }` i `parseAnsi(text: string): AnsiChunk[]`.

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/pipelines/ansi.test.ts`:

```typescript
import { describe, expect, it } from "vitest";

import { parseAnsi } from "./ansi";

describe("parseAnsi", () => {
  it("običan tekst je jedan komad bez boje", () => {
    expect(parseAnsi("zdravo svete")).toEqual([{ text: "zdravo svete" }]);
  });

  it("prazan ulaz daje praznu listu", () => {
    expect(parseAnsi("")).toEqual([]);
  });

  it("boja pa reset deli tekst na tri komada", () => {
    expect(parseAnsi("pre\u001b[31mcrveno\u001b[0mposle")).toEqual([
      { text: "pre" },
      { text: "crveno", color: "red" },
      { text: "posle" },
    ]);
  });

  it("podebljano se pamti odvojeno od boje", () => {
    expect(parseAnsi("\u001b[1mjako\u001b[0m")).toEqual([
      { text: "jako", bold: true },
    ]);
  });

  it("boja i podebljano u istom nizu važe zajedno", () => {
    expect(parseAnsi("\u001b[1;32mzeleno jako\u001b[0m")).toEqual([
      { text: "zeleno jako", color: "green", bold: true },
    ]);
  });

  it("svetle varijante imaju svoja imena", () => {
    expect(parseAnsi("\u001b[91msvetlo crveno")).toEqual([
      { text: "svetlo crveno", color: "bright-red" },
    ]);
  });

  it("nepoznat niz nestaje umesto da se ispiše", () => {
    // `2K` briše red, `1A` pomera kursor — prikaz koji se samo čita ih ignoriše.
    expect(parseAnsi("a\u001b[2K\u001b[1Ab")).toEqual([{ text: "ab" }]);
  });

  it("nezavršen niz na kraju ne obara parser", () => {
    expect(parseAnsi("kraj\u001b[")).toEqual([{ text: "kraj" }]);
  });

  it("uzastopni nizovi bez teksta ne prave prazne komade", () => {
    expect(parseAnsi("\u001b[31m\u001b[0mtekst")).toEqual([{ text: "tekst" }]);
  });

  it("boja bez reseta važi do kraja reda", () => {
    expect(parseAnsi("\u001b[33mžuto do kraja")).toEqual([
      { text: "žuto do kraja", color: "yellow" },
    ]);
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/pipelines/ansi.test.ts
```

Očekivano: FAIL — modul `./ansi` ne postoji.

- [ ] **Step 3: Napiši parser**

`apps/gui/src/features/codium/pipelines/ansi.ts`:

```typescript
/**
 * ANSI tekst u komade sa bojom.
 *
 * Pokriva ono što `npm`, `pytest` i `vite` stvarno šalju: reset, osam osnovnih
 * boja, svetle varijante i podebljano. Sve ostalo — pozicioniranje kursora,
 * brisanje reda, nepoznati kodovi — se tiho guta. Prikaz koji se samo čita
 * nema šta da radi sa kursorom, a ispisati sirov niz kao tekst je gore nego
 * ne prikazati ga.
 */
export type AnsiChunk = {
  text: string;
  color?: string;
  bold?: boolean;
};

const BOJE: Record<number, string> = {
  30: "black",
  31: "red",
  32: "green",
  33: "yellow",
  34: "blue",
  35: "magenta",
  36: "cyan",
  37: "white",
  90: "bright-black",
  91: "bright-red",
  92: "bright-green",
  93: "bright-yellow",
  94: "bright-blue",
  95: "bright-magenta",
  96: "bright-cyan",
  97: "bright-white",
};

// `\x1b[` pa cifre i tačka-zarezi, pa jedno slovo koje kaže šta je niz.
// Hvata se svaki niz, ali samo `m` (SGR) menja izgled — ostali se gutaju.
const NIZ = /\u001b\[([0-9;]*)([A-Za-z])/g;

export function parseAnsi(text: string): AnsiChunk[] {
  const komadi: AnsiChunk[] = [];
  let boja: string | undefined;
  let podebljano = false;
  let od = 0;

  function dodaj(deo: string): void {
    if (!deo) {
      return;
    }
    const komad: AnsiChunk = { text: deo };
    if (boja !== undefined) {
      komad.color = boja;
    }
    if (podebljano) {
      komad.bold = true;
    }
    komadi.push(komad);
  }

  NIZ.lastIndex = 0;
  let pogodak = NIZ.exec(text);
  while (pogodak !== null) {
    dodaj(text.slice(od, pogodak.index));
    od = pogodak.index + pogodak[0].length;

    if (pogodak[2] === "m") {
      // Prazni parametri (`\x1b[m`) znače reset, isto kao `0`.
      const kodovi = (pogodak[1] || "0").split(";");
      for (const sirov of kodovi) {
        const kod = Number(sirov);
        if (kod === 0) {
          boja = undefined;
          podebljano = false;
        } else if (kod === 1) {
          podebljano = true;
        } else if (kod === 22) {
          podebljano = false;
        } else if (kod === 39) {
          boja = undefined;
        } else if (BOJE[kod] !== undefined) {
          boja = BOJE[kod];
        }
        // Sve ostalo (pozadina, podvučeno, 256 boja) se ignoriše.
      }
    }

    pogodak = NIZ.exec(text);
  }

  dodaj(text.slice(od));
  return komadi;
}
```

- [ ] **Step 4: Pokreni test da prođe**

```bash
npm run test -- src/features/codium/pipelines/ansi.test.ts
```

Očekivano: PASS. Napomena: test „nezavršen niz na kraju" prolazi zato što
`\u001b[` bez završnog slova ne pogađa regularni izraz, pa ostaje u repu — a rep
se dodaje kao tekst. Ako implementacija odseca rep drugačije, uskladi je sa
testom, ne obrnuto.

- [ ] **Step 5: Commit**

```bash
git add apps/gui/src/features/codium/pipelines/ansi.ts apps/gui/src/features/codium/pipelines/ansi.test.ts
git commit -m "feat(gui): ANSI parser za log pipeline-a"
```

---

### Task 3: JSON šema definicije

**Files:**
- Create: `apps/gui/src/features/codium/pipelines/definitionSchema.ts`
- Test: `apps/gui/src/features/codium/pipelines/definitionSchema.test.ts`

**Interfaces:**
- Consumes: ništa.
- Produces: `PIPELINE_SCHEMA_URI` (string), `PIPELINE_MODEL_PATH` (string), `pipelineDefinitionSchema` (objekat JSON šeme), i `validateDefinition(text: string): string[]` — spisak grešaka, prazan kad je definicija ispravna.

`validateDefinition` je namerno mali sopstveni validator, ne biblioteka: uvesti
validator JSON šeme značilo bi novu zavisnost, a šemu ionako treba proveriti da
se slaže sa `definition.py`.

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/pipelines/definitionSchema.test.ts`:

```typescript
import { describe, expect, it } from "vitest";

import {
  PIPELINE_MODEL_PATH,
  pipelineDefinitionSchema,
  validateDefinition,
} from "./definitionSchema";

// Ista tabela slucajeva koju `tests/test_pipeline_definition.py` vec proverava.
// Sema koja dozvoljava ono sto server odbija je gora od nikakve, jer laze pre
// snimanja.
const ISPRAVNA = JSON.stringify({
  name: "test-i-build",
  timeout_minutes: 20,
  env: { CI: "1" },
  steps: [
    { name: "instalacija", run: "npm ci" },
    { name: "lint", run: "npm run lint", continue_on_error: true },
    { name: "build", run: "npm run build", working_dir: "apps/gui" },
  ],
});

describe("validateDefinition", () => {
  it("ispravna definicija nema grešaka", () => {
    expect(validateDefinition(ISPRAVNA)).toEqual([]);
  });

  it("minimalna definicija prolazi", () => {
    expect(
      validateDefinition(
        JSON.stringify({ name: "min", steps: [{ name: "a", run: "b" }] }),
      ),
    ).toEqual([]);
  });

  it("neispravan JSON prijavljuje JSON", () => {
    expect(validateDefinition("{ nije json").join(" ")).toContain("JSON");
  });

  it("prazno ime pada", () => {
    expect(
      validateDefinition(
        JSON.stringify({ name: "  ", steps: [{ name: "a", run: "b" }] }),
      ).join(" "),
    ).toContain("name");
  });

  it("prazna lista koraka pada", () => {
    expect(
      validateDefinition(JSON.stringify({ name: "x", steps: [] })).join(" "),
    ).toContain("steps");
  });

  it("korak bez run polja pada", () => {
    expect(
      validateDefinition(
        JSON.stringify({ name: "x", steps: [{ name: "bez komande" }] }),
      ).join(" "),
    ).toContain("run");
  });

  it("nepozitivan timeout pada", () => {
    expect(
      validateDefinition(
        JSON.stringify({
          name: "x",
          timeout_minutes: 0,
          steps: [{ name: "a", run: "b" }],
        }),
      ).join(" "),
    ).toContain("timeout_minutes");
  });

  it("env vrednost koja nije tekst pada", () => {
    expect(
      validateDefinition(
        JSON.stringify({
          name: "x",
          env: { CI: 1 },
          steps: [{ name: "a", run: "b" }],
        }),
      ).join(" "),
    ).toContain("env");
  });

  it("logička vrednost za timeout ne prolazi kao broj", () => {
    // U Python-u je `bool` podtip `int`; server to izričito odbija, pa i ovde
    // `true` ne sme da prođe kao 1.
    expect(
      validateDefinition(
        JSON.stringify({
          name: "x",
          timeout_minutes: true,
          steps: [{ name: "a", run: "b" }],
        }),
      ).join(" "),
    ).toContain("timeout_minutes");
  });

  it("niz na vrhu nije objekat definicije", () => {
    expect(validateDefinition("[]").join(" ")).toContain("objekat");
  });
});

describe("šema za Monaco", () => {
  it("model ima svoj URI da šema ne curi u druge JSON fajlove", () => {
    expect(PIPELINE_MODEL_PATH).toContain("pipeline-definition.json");
  });

  it("šema traži name i steps", () => {
    expect(pipelineDefinitionSchema.required).toEqual(["name", "steps"]);
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/pipelines/definitionSchema.test.ts
```

Očekivano: FAIL — modul `./definitionSchema` ne postoji.

- [ ] **Step 3: Napiši šemu i validator**

`apps/gui/src/features/codium/pipelines/definitionSchema.ts`:

```typescript
/**
 * JSON šema definicije pipeline-a i mali validator uz nju.
 *
 * Šema se registruje u Monaco sa `fileMatch` na namenski URI: metoda
 * `setDiagnosticsOptions` je GLOBALNA za celu aplikaciju, a F6 editor otvara
 * `.json` fajlove kroz isti Monaco. Bez ograničenja bi šema pipeline-a
 * podvlačila greške u `package.json`-u koji čovek otvori u Explorer-u.
 */

export const PIPELINE_SCHEMA_URI = "https://core.local/schemas/codium-pipeline.json";
export const PIPELINE_MODEL_PATH = "inmemory://codium/pipeline-definition.json";

export const pipelineDefinitionSchema = {
  $id: PIPELINE_SCHEMA_URI,
  type: "object",
  required: ["name", "steps"],
  additionalProperties: false,
  properties: {
    name: { type: "string", minLength: 1, description: "Ime pipeline-a." },
    timeout_minutes: {
      type: "integer",
      minimum: 1,
      description: "Rok za celo pokretanje, u minutima.",
    },
    env: {
      type: "object",
      additionalProperties: { type: "string" },
      description: "Promenljive okruženja; samo tekst kao vrednost.",
    },
    steps: {
      type: "array",
      minItems: 1,
      items: {
        type: "object",
        required: ["name", "run"],
        additionalProperties: false,
        properties: {
          name: { type: "string", minLength: 1 },
          run: { type: "string", minLength: 1, description: "Komanda kroz shell." },
          working_dir: {
            type: "string",
            description: "Relativno na koren repozitorijuma; ne sme da izađe iz njega.",
          },
          continue_on_error: { type: "boolean" },
        },
      },
    },
  },
} as const;

function tekstNijePrazan(vrednost: unknown): boolean {
  return typeof vrednost === "string" && vrednost.trim().length > 0;
}

/**
 * Proverava definiciju istim pravilima koja `definition.py` primenjuje.
 *
 * Sopstveni validator, a ne biblioteka: uvesti validator JSON šeme značilo bi
 * novu zavisnost zbog desetak provera. Server ostaje autoritet — ovo samo
 * skraćuje petlju pre snimanja.
 */
export function validateDefinition(text: string): string[] {
  let sirovo: unknown;
  try {
    sirovo = JSON.parse(text);
  } catch (greska) {
    return [`Definicija nije ispravan JSON: ${(greska as Error).message}`];
  }

  if (typeof sirovo !== "object" || sirovo === null || Array.isArray(sirovo)) {
    return ["Definicija mora biti JSON objekat."];
  }
  const definicija = sirovo as Record<string, unknown>;
  const greske: string[] = [];

  if (!tekstNijePrazan(definicija.name)) {
    greske.push("Polje `name` mora biti neprazan tekst.");
  }

  const timeout = definicija.timeout_minutes;
  if (timeout !== undefined) {
    // `typeof true === "boolean"`, pa logička vrednost ovde i ne stiže do
    // provere broja — ali server izričito odbija `true`, pa je poruka ista.
    if (typeof timeout !== "number" || !Number.isInteger(timeout) || timeout <= 0) {
      greske.push("Polje `timeout_minutes` mora biti pozitivan ceo broj.");
    }
  }

  const env = definicija.env;
  if (env !== undefined) {
    if (typeof env !== "object" || env === null || Array.isArray(env)) {
      greske.push("Polje `env` mora biti objekat.");
    } else {
      for (const vrednost of Object.values(env as Record<string, unknown>)) {
        if (typeof vrednost !== "string") {
          greske.push("Polje `env` sme da drži samo tekst kao vrednost.");
          break;
        }
      }
    }
  }

  const koraci = definicija.steps;
  if (!Array.isArray(koraci) || koraci.length === 0) {
    greske.push("Polje `steps` mora biti neprazna lista.");
    return greske;
  }

  koraci.forEach((sirovKorak, redni) => {
    if (typeof sirovKorak !== "object" || sirovKorak === null || Array.isArray(sirovKorak)) {
      greske.push(`Korak ${redni} nije objekat.`);
      return;
    }
    const korak = sirovKorak as Record<string, unknown>;
    if (!tekstNijePrazan(korak.name)) {
      greske.push(`Polje \`steps[${redni}].name\` mora biti neprazan tekst.`);
    }
    if (!tekstNijePrazan(korak.run)) {
      greske.push(`Polje \`steps[${redni}].run\` mora biti neprazan tekst.`);
    }
    if (korak.working_dir !== undefined && typeof korak.working_dir !== "string") {
      greske.push(`Polje \`steps[${redni}].working_dir\` mora biti tekst.`);
    }
    if (
      korak.continue_on_error !== undefined &&
      typeof korak.continue_on_error !== "boolean"
    ) {
      greske.push(
        `Polje \`steps[${redni}].continue_on_error\` mora biti tačno ili netačno.`,
      );
    }
  });

  return greske;
}
```

- [ ] **Step 4: Pokreni test da prođe**

```bash
npm run test -- src/features/codium/pipelines/definitionSchema.test.ts
```

Očekivano: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gui/src/features/codium/pipelines/definitionSchema.ts apps/gui/src/features/codium/pipelines/definitionSchema.test.ts
git commit -m "feat(gui): JSON sema definicije pipeline-a i validator uz nju"
```

---

### Task 4: Hook-ovi za listu i za pokretanje uživo

**Files:**
- Create: `apps/gui/src/features/codium/pipelines/usePipelines.ts`
- Create: `apps/gui/src/features/codium/pipelines/useRunPolling.ts`
- Test: `apps/gui/src/features/codium/pipelines/useRunPolling.test.ts`

**Interfaces:**
- Consumes: API funkcije iz Task-a 1.
- Produces:
  - `usePipelines(repositoryId?: number)` → `{ pipelines, isLoading, error, refresh, create, update, remove, start }`
  - `useRunPolling(runId: number | null)` → `{ run, steps, lines, hiddenCount, isPolling, error, showAll }`
  - `MAX_PRIKAZANIH = 2000`

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/pipelines/useRunPolling.test.ts`:

```typescript
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useRunPolling } from "./useRunPolling";
import * as api from "../../../services/codiumApi";

vi.mock("../../../services/codiumApi");

function detalj(status: string) {
  return {
    run: {
      id: 5,
      pipeline_id: 1,
      status,
      trigger: "manual",
      commit_sha: null,
      branch: null,
      exit_code: status === "success" ? 0 : null,
      detail: "",
      started_at: "2026-08-30 10:00:00",
      finished_at: status === "success" ? "2026-08-30 10:00:05" : null,
      created_at: "2026-08-30 10:00:00",
    },
    steps: [
      {
        idx: 0,
        name: "jedan",
        status,
        exit_code: null,
        started_at: null,
        finished_at: null,
      },
    ],
  };
}

function red(seq: number) {
  return {
    seq,
    step_idx: 0,
    stream: "stdout",
    line: `red ${seq}`,
    at: "2026-08-30 10:00:01",
  };
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
  vi.resetAllMocks();
});

describe("useRunPolling", () => {
  it("bez izabranog pokretanja ne zove API", () => {
    renderHook(() => useRunPolling(null));
    expect(api.fetchRunDetail).not.toHaveBeenCalled();
  });

  it("dohvata detalj i log, pa nastavlja dok radi", async () => {
    vi.mocked(api.fetchRunDetail).mockResolvedValue(detalj("running"));
    vi.mocked(api.fetchRunLogs).mockResolvedValue({ lines: [red(1)] });

    const { result } = renderHook(() => useRunPolling(5));

    await waitFor(() => expect(result.current.lines).toHaveLength(1));
    expect(result.current.isPolling).toBe(true);
    expect(api.fetchRunLogs).toHaveBeenCalledWith(5, 0);
  });

  it("sledeci krug trazi log od poslednjeg seq", async () => {
    vi.mocked(api.fetchRunDetail).mockResolvedValue(detalj("running"));
    vi.mocked(api.fetchRunLogs)
      .mockResolvedValueOnce({ lines: [red(1), red(2)] })
      .mockResolvedValue({ lines: [red(3)] });

    const { result } = renderHook(() => useRunPolling(5));
    await waitFor(() => expect(result.current.lines).toHaveLength(2));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(600);
    });

    await waitFor(() => expect(api.fetchRunLogs).toHaveBeenCalledWith(5, 2));
  });

  it("zavrsni status gasi petlju posle jos jednog poziva", async () => {
    vi.mocked(api.fetchRunDetail).mockResolvedValue(detalj("success"));
    vi.mocked(api.fetchRunLogs).mockResolvedValue({ lines: [red(1)] });

    const { result } = renderHook(() => useRunPolling(5));
    await waitFor(() => expect(result.current.isPolling).toBe(false));

    // Prvi krug plus zavrsni: poslednja serija loga stize iz sink-a tek na
    // `flush()` pri kraju pokretanja.
    expect(vi.mocked(api.fetchRunLogs).mock.calls.length).toBe(2);

    const pre = vi.mocked(api.fetchRunLogs).mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(vi.mocked(api.fetchRunLogs).mock.calls.length).toBe(pre);
  });

  it("promena izabranog pokretanja odbacuje stari odgovor", async () => {
    vi.mocked(api.fetchRunDetail).mockResolvedValue(detalj("success"));
    vi.mocked(api.fetchRunLogs).mockResolvedValue({ lines: [red(1)] });

    const { result, rerender } = renderHook(
      ({ id }: { id: number | null }) => useRunPolling(id),
      { initialProps: { id: 5 as number | null } },
    );
    await waitFor(() => expect(result.current.lines).toHaveLength(1));

    vi.mocked(api.fetchRunLogs).mockResolvedValue({ lines: [] });
    rerender({ id: 9 });

    await waitFor(() => expect(result.current.lines).toHaveLength(0));
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/pipelines/useRunPolling.test.ts
```

Očekivano: FAIL — modul `./useRunPolling` ne postoji.

- [ ] **Step 3: Napiši `useRunPolling`**

`apps/gui/src/features/codium/pipelines/useRunPolling.ts`:

```typescript
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
 */
export function useRunPolling(runId: number | null) {
  const [run, setRun] = useState<PipelineRun | null>(null);
  const [steps, setSteps] = useState<RunStep[]>([]);
  const [lines, setLines] = useState<RunLogLine[]>([]);
  const [hiddenCount, setHiddenCount] = useState(0);
  const [isPolling, setPolling] = useState(false);
  const [error, setError] = useState("");

  const poslednjiSeq = useRef(0);
  const otkazano = useRef(false);
  const tajmer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Granica prikaza je REF, ne stanje: da je u zavisnostima efekta, `showAll`
  // bi ga podigao, efekat bi se ponovo pokrenuo i spustio ga — i tako u krug.
  const bezGranice = useRef(false);

  const showAll = useCallback(() => {
    bezGranice.current = true;
    poslednjiSeq.current = 0;
    setLines([]);
    setHiddenCount(0);
  }, []);

  useEffect(() => {
    otkazano.current = false;
    poslednjiSeq.current = 0;
    setRun(null);
    setSteps([]);
    setLines([]);
    setHiddenCount(0);
    setError("");
    bezGranice.current = false;

    if (runId === null) {
      setPolling(false);
      return;
    }

    setPolling(true);

    async function krug(zavrsni: boolean): Promise<void> {
      try {
        const [detalj, log] = await Promise.all([
          fetchRunDetail(runId as number),
          fetchRunLogs(runId as number, poslednjiSeq.current),
        ]);
        if (otkazano.current) {
          return;
        }

        setRun(detalj.run);
        setSteps(detalj.steps);

        if (log.lines.length > 0) {
          poslednjiSeq.current = log.lines[log.lines.length - 1].seq;
          setLines((stari) => {
            const spojeni = [...stari, ...log.lines];
            if (bezGranice.current || spojeni.length <= MAX_PRIKAZANIH) {
              return spojeni;
            }
            const visak = spojeni.length - MAX_PRIKAZANIH;
            setHiddenCount((prethodno) => prethodno + visak);
            return spojeni.slice(visak);
          });
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
        setPolling(false);
      } catch (problem) {
        if (otkazano.current) {
          return;
        }
        setError(problem instanceof Error ? problem.message : String(problem));
        setPolling(false);
      }
    }

    void krug(false);

    return () => {
      otkazano.current = true;
      if (tajmer.current !== null) {
        clearTimeout(tajmer.current);
        tajmer.current = null;
      }
    };
  }, [runId]);

  return { run, steps, lines, hiddenCount, isPolling, error, showAll };
}
```

- [ ] **Step 4: Napiši `usePipelines`**

`apps/gui/src/features/codium/pipelines/usePipelines.ts`:

```typescript
import { useCallback, useEffect, useState } from "react";

import {
  createPipeline,
  deletePipeline,
  fetchPipelines,
  runPipeline,
  updatePipeline,
} from "../../../services/codiumApi";
import type { Pipeline, PipelineRun } from "../../../types/codium";

/**
 * Lista pipeline-a jednog repozitorijuma, sa akcijama nad njom.
 *
 * Bez tajmera: lista se menja samo kad čovek nešto uradi. Pokretanja koja
 * traju prati `useRunPolling`, svako svoje.
 */
export function usePipelines(repositoryId?: number) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const odgovor = await fetchPipelines(repositoryId);
      setPipelines(odgovor.pipelines);
      setError("");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : String(problem));
    } finally {
      setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = useCallback(
    async (forRepository: number, definition: string) => {
      await createPipeline({ repository_id: forRepository, definition });
      await refresh();
    },
    [refresh],
  );

  const update = useCallback(
    async (pipelineId: number, definition: string) => {
      await updatePipeline(pipelineId, { definition });
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (pipelineId: number) => {
      await deletePipeline(pipelineId);
      await refresh();
    },
    [refresh],
  );

  const start = useCallback(
    async (pipelineId: number): Promise<PipelineRun> => runPipeline(pipelineId),
    [],
  );

  return { pipelines, isLoading, error, refresh, create, update, remove, start };
}
```

- [ ] **Step 5: Pokreni test da prođe**

```bash
npm run test -- src/features/codium/pipelines/useRunPolling.test.ts
```

Očekivano: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/gui/src/features/codium/pipelines
git commit -m "feat(gui): hook-ovi za listu pipeline-a i pracenje pokretanja uzivo"
```

---

### Task 5: Prikaz loga i detalja pokretanja

**Files:**
- Create: `apps/gui/src/features/codium/pipelines/RunLog.tsx`
- Create: `apps/gui/src/features/codium/pipelines/RunDetail.tsx`
- Test: `apps/gui/src/features/codium/pipelines/RunLog.test.tsx`

**Interfaces:**
- Consumes: `parseAnsi` (Task 2), `useRunPolling`, `MAX_PRIKAZANIH` (Task 4), `runBadge`, `runDuration` (Task 1), `cancelRun` (Task 1).
- Produces:
  - `RunLog({ lines, hiddenCount, onShowAll })`
  - `RunDetail({ runId, onCancelled })`

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/pipelines/RunLog.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import RunLog from "./RunLog";
import type { RunLogLine } from "../../../types/codium";

function red(seq: number, line: string, stream = "stdout"): RunLogLine {
  return { seq, step_idx: 0, stream, line, at: "2026-08-30 10:00:00" };
}

describe("RunLog", () => {
  it("prazan log kaže da još nema ničega", () => {
    render(<RunLog lines={[]} hiddenCount={0} onShowAll={() => {}} />);
    expect(screen.getByText(/nema ispisa/i)).toBeInTheDocument();
  });

  it("crta redove redom", () => {
    render(
      <RunLog
        lines={[red(1, "prvi"), red(2, "drugi")]}
        hiddenCount={0}
        onShowAll={() => {}}
      />,
    );
    expect(screen.getByText("prvi")).toBeInTheDocument();
    expect(screen.getByText("drugi")).toBeInTheDocument();
  });

  it("boja iz ANSI niza postaje klasa, a niz se ne ispisuje", () => {
    render(
      <RunLog
        lines={[red(1, "\u001b[31mgreška\u001b[0m")]}
        hiddenCount={0}
        onShowAll={() => {}}
      />,
    );
    const komad = screen.getByText("greška");
    expect(komad).toHaveClass("ansi-red");
    expect(screen.queryByText(/\u001b/)).toBeNull();
  });

  it("stderr red nosi svoju klasu", () => {
    const { container } = render(
      <RunLog
        lines={[red(1, "lose", "stderr")]}
        hiddenCount={0}
        onShowAll={() => {}}
      />,
    );
    expect(container.querySelector(".cpipe-log-red.stderr")).not.toBeNull();
  });

  it("traka sa sakrivenim redovima nudi učitavanje svega", async () => {
    const naSve = vi.fn();
    render(<RunLog lines={[red(1, "a")]} hiddenCount={42} onShowAll={naSve} />);

    expect(screen.getByText(/42/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /učitaj sve/i }));
    expect(naSve).toHaveBeenCalledOnce();
  });

  it("bez sakrivenih redova nema trake", () => {
    render(<RunLog lines={[red(1, "a")]} hiddenCount={0} onShowAll={() => {}} />);
    expect(screen.queryByRole("button", { name: /učitaj sve/i })).toBeNull();
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/pipelines/RunLog.test.tsx
```

Očekivano: FAIL — modul `./RunLog` ne postoji.

- [ ] **Step 3: Napiši `RunLog`**

`apps/gui/src/features/codium/pipelines/RunLog.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";

import type { RunLogLine } from "../../../types/codium";
import { parseAnsi } from "./ansi";

type Props = {
  lines: RunLogLine[];
  hiddenCount: number;
  onShowAll: () => void;
};

// Koliko piksela od dna se i dalje računa kao „na dnu".
const PRAG_DNA = 40;

/**
 * Log jednog pokretanja, sa bojama i granicom prikaza.
 *
 * Automatski skrol radi SAMO dok je čovek na dnu. Čim odskroluje gore, skrol
 * se ne pomera pod njim — prikaz koji otima skrol dok čitaš grešku je gori od
 * prikaza bez skrola.
 */
export default function RunLog({ lines, hiddenCount, onShowAll }: Props) {
  const okvir = useRef<HTMLDivElement | null>(null);
  const [prati, setPrati] = useState(true);

  useEffect(() => {
    const element = okvir.current;
    if (element === null || !prati) {
      return;
    }
    element.scrollTop = element.scrollHeight;
  }, [lines, prati]);

  function naSkrol(): void {
    const element = okvir.current;
    if (element === null) {
      return;
    }
    const odDna = element.scrollHeight - element.scrollTop - element.clientHeight;
    setPrati(odDna <= PRAG_DNA);
  }

  return (
    <div className="cpipe-log-okvir">
      {hiddenCount > 0 && (
        <div className="cpipe-log-traka">
          <span>Starijih redova sakriveno: {hiddenCount}</span>
          <button type="button" onClick={onShowAll}>
            Učitaj sve
          </button>
        </div>
      )}

      <div className="cpipe-log" ref={okvir} onScroll={naSkrol}>
        {lines.length === 0 ? (
          <p className="cpipe-hint">Još nema ispisa.</p>
        ) : (
          lines.map((red) => (
            <div key={red.seq} className={`cpipe-log-red ${red.stream}`}>
              {parseAnsi(red.line).map((komad, redni) => (
                <span
                  key={redni}
                  className={[
                    komad.color ? `ansi-${komad.color}` : "",
                    komad.bold ? "ansi-bold" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  {komad.text}
                </span>
              ))}
            </div>
          ))
        )}
      </div>

      {!prati && (
        <button
          type="button"
          className="cpipe-na-dno"
          onClick={() => setPrati(true)}
        >
          Na dno
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Napiši `RunDetail`**

`apps/gui/src/features/codium/pipelines/RunDetail.tsx`:

```tsx
import { useState } from "react";

import { cancelRun } from "../../../services/codiumApi";
import RunLog from "./RunLog";
import { runBadge, runDuration } from "./runBadges";
import { useRunPolling } from "./useRunPolling";

type Props = {
  runId: number | null;
  onCancelled: () => void;
};

/** Zaglavlje pokretanja, koraci i log. */
export default function RunDetail({ runId, onCancelled }: Props) {
  const { run, steps, lines, hiddenCount, isPolling, error, showAll } =
    useRunPolling(runId);
  const [greskaAkcije, setGreskaAkcije] = useState("");

  if (runId === null) {
    return <p className="cpipe-hint">Izaberi pokretanje.</p>;
  }
  if (error) {
    return <p className="cpipe-greska">{error}</p>;
  }
  if (run === null) {
    return <p className="cpipe-hint">Učitavanje…</p>;
  }

  const znacka = runBadge(run);

  async function otkazi(): Promise<void> {
    try {
      await cancelRun(runId as number);
      setGreskaAkcije("");
      onCancelled();
    } catch (problem) {
      setGreskaAkcije(
        problem instanceof Error ? problem.message : String(problem),
      );
    }
  }

  return (
    <div className="cpipe-detalj">
      <header className="cpipe-detalj-glava">
        <span className={znacka.className}>{znacka.label}</span>
        <span className="cpipe-trajanje">{runDuration(run)}</span>
        {run.detail && <span className="cpipe-razlog">{run.detail}</span>}
        {isPolling && (
          <button type="button" onClick={() => void otkazi()}>
            Otkaži
          </button>
        )}
      </header>

      {greskaAkcije && <p className="cpipe-greska">{greskaAkcije}</p>}

      <ol className="cpipe-koraci">
        {steps.map((korak) => (
          <li key={korak.idx} className={`cpipe-korak ${korak.status}`}>
            <span className="cpipe-korak-ime">{korak.name}</span>
            <span className="cpipe-korak-status">{korak.status}</span>
            {korak.exit_code !== null && (
              <span className="cpipe-korak-kod">kod {korak.exit_code}</span>
            )}
          </li>
        ))}
      </ol>

      <RunLog lines={lines} hiddenCount={hiddenCount} onShowAll={showAll} />
    </div>
  );
}
```

- [ ] **Step 5: Pokreni test da prođe**

```bash
npm run test -- src/features/codium/pipelines/RunLog.test.tsx
```

Očekivano: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/gui/src/features/codium/pipelines
git commit -m "feat(gui): prikaz loga sa bojama i detalj pokretanja"
```

---

### Task 6: Lista pipeline-a, uređivač i istorija

**Files:**
- Create: `apps/gui/src/features/codium/pipelines/PipelineList.tsx`
- Create: `apps/gui/src/features/codium/pipelines/DefinitionEditor.tsx`
- Create: `apps/gui/src/features/codium/pipelines/RunHistory.tsx`
- Test: `apps/gui/src/features/codium/pipelines/DefinitionEditor.test.tsx`

**Interfaces:**
- Consumes: `validateDefinition`, `pipelineDefinitionSchema`, `PIPELINE_SCHEMA_URI`, `PIPELINE_MODEL_PATH` (Task 3); `runBadge`, `runDuration` (Task 1); `fetchRuns` (Task 1).
- Produces:
  - `PipelineList({ pipelines, selectedId, onSelect, onRemove })`
  - `DefinitionEditor({ value, onSave, onRun, saveError })`
  - `RunHistory({ pipelineId, selectedRunId, onSelect, refreshKey })`

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/pipelines/DefinitionEditor.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import DefinitionEditor from "./DefinitionEditor";

// Monaco ne radi u jsdom-u; zamenjuje ga obicno polje koje zove istu povratnu
// funkciju. Test proverava ponasanje uredjivaca, ne sam Monaco.
vi.mock("@monaco-editor/react", () => ({
  default: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (v: string | undefined) => void;
  }) => (
    <textarea
      aria-label="definicija"
      value={value}
      onChange={(dogadjaj) => onChange(dogadjaj.target.value)}
    />
  ),
}));

const ISPRAVNA = JSON.stringify({ name: "x", steps: [{ name: "a", run: "b" }] });

describe("DefinitionEditor", () => {
  it("ispravna definicija dozvoljava snimanje", async () => {
    const naSnimi = vi.fn();
    render(
      <DefinitionEditor value={ISPRAVNA} onSave={naSnimi} onRun={() => {}} />,
    );

    await userEvent.click(screen.getByRole("button", { name: /snimi/i }));
    expect(naSnimi).toHaveBeenCalledWith(ISPRAVNA);
  });

  it("neispravna definicija prikazuje gresku i ne snima", async () => {
    const naSnimi = vi.fn();
    render(
      <DefinitionEditor value="{ nije json" onSave={naSnimi} onRun={() => {}} />,
    );

    expect(screen.getByText(/JSON/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /snimi/i }));
    expect(naSnimi).not.toHaveBeenCalled();
  });

  it("greska sa servera se prikazuje iznad uredjivaca", () => {
    render(
      <DefinitionEditor
        value={ISPRAVNA}
        onSave={() => {}}
        onRun={() => {}}
        saveError="Polje `steps` mora biti neprazna lista."
      />,
    );
    expect(screen.getByText(/neprazna lista/)).toBeInTheDocument();
  });

  it("dugme Pokreni zove svoju povratnu funkciju", async () => {
    const naPokreni = vi.fn();
    render(
      <DefinitionEditor value={ISPRAVNA} onSave={() => {}} onRun={naPokreni} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /pokreni/i }));
    expect(naPokreni).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/pipelines/DefinitionEditor.test.tsx
```

Očekivano: FAIL — modul `./DefinitionEditor` ne postoji.

- [ ] **Step 3: Napiši `DefinitionEditor`**

`apps/gui/src/features/codium/pipelines/DefinitionEditor.tsx`:

```tsx
import Editor from "@monaco-editor/react";
import { useEffect, useState } from "react";

import {
  PIPELINE_MODEL_PATH,
  PIPELINE_SCHEMA_URI,
  pipelineDefinitionSchema,
  validateDefinition,
} from "./definitionSchema";

type Props = {
  value: string;
  onSave: (definition: string) => void;
  onRun: () => void;
  saveError?: string;
};

/**
 * Uređivač definicije u Monaco `json` režimu.
 *
 * Šema se registruje sa `fileMatch` na namenski URI modela: metoda
 * `setDiagnosticsOptions` je globalna za celu aplikaciju, a F6 editor otvara
 * `.json` fajlove kroz isti Monaco. Bez ograničenja bi šema pipeline-a
 * podvlačila greške u tuđim JSON fajlovima.
 */
export default function DefinitionEditor({
  value,
  onSave,
  onRun,
  saveError,
}: Props) {
  const [tekst, setTekst] = useState(value);
  const [greske, setGreske] = useState<string[]>([]);

  useEffect(() => {
    setTekst(value);
  }, [value]);

  useEffect(() => {
    setGreske(validateDefinition(tekst));
  }, [tekst]);

  const ispravna = greske.length === 0;

  return (
    <div className="cpipe-uredjivac">
      <div className="cpipe-uredjivac-akcije">
        <button
          type="button"
          disabled={!ispravna}
          onClick={() => onSave(tekst)}
        >
          Snimi
        </button>
        <button type="button" onClick={onRun}>
          Pokreni
        </button>
      </div>

      {saveError && <p className="cpipe-greska">{saveError}</p>}
      {greske.map((poruka) => (
        <p key={poruka} className="cpipe-greska">
          {poruka}
        </p>
      ))}

      <Editor
        height="320px"
        language="json"
        path={PIPELINE_MODEL_PATH}
        value={tekst}
        onChange={(novo) => setTekst(novo ?? "")}
        beforeMount={(monaco) => {
          monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
            validate: true,
            // `fileMatch` drži šemu na ovom modelu; bez toga bi važila za
            // svaki JSON koji aplikacija otvori.
            schemas: [
              {
                uri: PIPELINE_SCHEMA_URI,
                fileMatch: [PIPELINE_MODEL_PATH],
                schema: pipelineDefinitionSchema,
              },
            ],
          });
        }}
        options={{ minimap: { enabled: false }, tabSize: 2 }}
      />
    </div>
  );
}
```

- [ ] **Step 4: Napiši `PipelineList` i `RunHistory`**

`apps/gui/src/features/codium/pipelines/PipelineList.tsx`:

```tsx
import type { Pipeline } from "../../../types/codium";

type Props = {
  pipelines: Pipeline[];
  selectedId: number | null;
  onSelect: (pipelineId: number) => void;
  onRemove: (pipelineId: number) => void;
};

export default function PipelineList({
  pipelines,
  selectedId,
  onSelect,
  onRemove,
}: Props) {
  if (pipelines.length === 0) {
    return (
      <p className="cpipe-prazno">
        Nijedan pipeline nije definisan. Napravi ga u uređivaču desno.
      </p>
    );
  }

  return (
    <ul className="cpipe-lista">
      {pipelines.map((pipeline) => (
        <li
          key={pipeline.id}
          className={`cpipe-stavka ${pipeline.id === selectedId ? "izabrana" : ""}`}
        >
          <button type="button" onClick={() => onSelect(pipeline.id)}>
            {pipeline.name}
          </button>
          <button type="button" onClick={() => onRemove(pipeline.id)}>
            Obriši
          </button>
        </li>
      ))}
    </ul>
  );
}
```

`apps/gui/src/features/codium/pipelines/RunHistory.tsx`:

```tsx
import { useEffect, useState } from "react";

import { fetchRuns } from "../../../services/codiumApi";
import type { PipelineRun } from "../../../types/codium";
import { runBadge, runDuration } from "./runBadges";

type Props = {
  pipelineId: number | null;
  selectedRunId: number | null;
  onSelect: (runId: number) => void;
  // Menja se kad se pokrene novo pokretanje, da se istorija osveži.
  refreshKey: number;
};

export default function RunHistory({
  pipelineId,
  selectedRunId,
  onSelect,
  refreshKey,
}: Props) {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [greska, setGreska] = useState("");

  useEffect(() => {
    if (pipelineId === null) {
      setRuns([]);
      return;
    }
    let otkazano = false;
    fetchRuns(pipelineId, 30)
      .then((odgovor) => {
        if (!otkazano) {
          setRuns(odgovor.runs);
          setGreska("");
        }
      })
      .catch((problem: unknown) => {
        if (!otkazano) {
          setGreska(problem instanceof Error ? problem.message : String(problem));
        }
      });
    return () => {
      otkazano = true;
    };
  }, [pipelineId, refreshKey]);

  if (pipelineId === null) {
    return <p className="cpipe-hint">Izaberi pipeline.</p>;
  }
  if (greska) {
    return <p className="cpipe-greska">{greska}</p>;
  }
  if (runs.length === 0) {
    return <p className="cpipe-hint">Ovaj pipeline još nije pokretan.</p>;
  }

  return (
    <ul className="cpipe-istorija">
      {runs.map((run) => {
        const znacka = runBadge(run);
        return (
          <li key={run.id}>
            <button
              type="button"
              className={run.id === selectedRunId ? "izabran" : ""}
              onClick={() => onSelect(run.id)}
            >
              <span className={znacka.className}>{znacka.label}</span>
              <span className="cpipe-trajanje">{runDuration(run)}</span>
              <span className="cpipe-vreme">{run.created_at}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
```

- [ ] **Step 5: Pokreni test da prođe**

```bash
npm run test -- src/features/codium/pipelines/DefinitionEditor.test.tsx
```

Očekivano: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/gui/src/features/codium/pipelines
git commit -m "feat(gui): lista pipeline-a, Monaco uredjivac sa semom i istorija"
```

---

### Task 7: Strana, ruta i sidebar

**Files:**
- Create: `apps/gui/src/pages/CodiumPipelines.tsx`
- Create: `apps/gui/src/styles/codium-pipelines.css`
- Modify: `apps/gui/src/App.tsx`
- Modify: `apps/gui/src/components/layout/Sidebar.tsx`
- Test: `apps/gui/src/pages/CodiumPipelines.test.tsx`

**Interfaces:**
- Consumes: sve iz Task-ova 1–6, plus `fetchRepositories` (iz E2).
- Produces: strana montirana na `/codium/pipelines`.

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/pages/CodiumPipelines.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CodiumPipelines from "./CodiumPipelines";
import * as api from "../services/codiumApi";

vi.mock("../services/codiumApi");

vi.mock("@monaco-editor/react", () => ({
  default: ({ value }: { value: string }) => (
    <textarea aria-label="definicija" value={value} readOnly />
  ),
}));

const REPO = {
  id: 1,
  project_id: null,
  name: "core",
  local_path: "C:/kod/core",
  remote_url: null,
  default_branch: "main",
  provider: "local_git",
  last_synced_at: null,
  status: {
    branch: "main",
    dirty: false,
    changed_files: 0,
    ahead: 0,
    behind: 0,
    missing: false,
  },
};

const PIPELINE = {
  id: 3,
  repository_id: 1,
  name: "test-i-build",
  definition: '{"name": "test-i-build", "steps": [{"name": "a", "run": "b"}]}',
  enabled: true,
  created_at: "2026-08-30 10:00:00",
  updated_at: "2026-08-30 10:00:00",
};

const RUN = {
  id: 9,
  pipeline_id: 3,
  status: "success",
  trigger: "manual",
  commit_sha: null,
  branch: null,
  exit_code: 0,
  detail: "",
  started_at: "2026-08-30 10:00:00",
  finished_at: "2026-08-30 10:00:04",
  created_at: "2026-08-30 10:00:00",
};

beforeEach(() => {
  vi.mocked(api.fetchRepositories).mockResolvedValue({ repositories: [REPO] });
  vi.mocked(api.fetchPipelines).mockResolvedValue({ pipelines: [PIPELINE] });
  vi.mocked(api.fetchRuns).mockResolvedValue({ runs: [RUN] });
  vi.mocked(api.fetchRunDetail).mockResolvedValue({ run: RUN, steps: [] });
  vi.mocked(api.fetchRunLogs).mockResolvedValue({ lines: [] });
});

function nacrtaj() {
  return render(
    <MemoryRouter>
      <CodiumPipelines />
    </MemoryRouter>,
  );
}

describe("CodiumPipelines", () => {
  it("crta pipeline-e izabranog repozitorijuma", async () => {
    nacrtaj();
    expect(await screen.findByText("test-i-build")).toBeInTheDocument();
  });

  it("prazan registar nudi da se napravi prvi", async () => {
    vi.mocked(api.fetchPipelines).mockResolvedValue({ pipelines: [] });
    nacrtaj();
    expect(
      await screen.findByText(/nijedan pipeline nije definisan/i),
    ).toBeInTheDocument();
  });

  it("izbor pipeline-a dohvata istoriju", async () => {
    nacrtaj();
    await userEvent.click(await screen.findByText("test-i-build"));
    await waitFor(() => expect(api.fetchRuns).toHaveBeenCalledWith(3, 30));
  });

  it("Pokreni zove API za izabran pipeline", async () => {
    vi.mocked(api.runPipeline).mockResolvedValue({ ...RUN, status: "queued" });
    nacrtaj();
    await userEvent.click(await screen.findByText("test-i-build"));
    await userEvent.click(screen.getByRole("button", { name: /pokreni/i }));
    await waitFor(() => expect(api.runPipeline).toHaveBeenCalledWith(3));
  });

  it("bez registrovanog repozitorijuma vodi na Repositories", async () => {
    vi.mocked(api.fetchRepositories).mockResolvedValue({ repositories: [] });
    nacrtaj();
    expect(
      await screen.findByText(/nijedan repozitorijum nije registrovan/i),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/pages/CodiumPipelines.test.tsx
```

Očekivano: FAIL — modul `./CodiumPipelines` ne postoji.

- [ ] **Step 3: Napiši stranu**

`apps/gui/src/pages/CodiumPipelines.tsx`:

```tsx
import { useEffect, useState } from "react";

import DefinitionEditor from "../features/codium/pipelines/DefinitionEditor";
import PipelineList from "../features/codium/pipelines/PipelineList";
import RunDetail from "../features/codium/pipelines/RunDetail";
import RunHistory from "../features/codium/pipelines/RunHistory";
import { usePipelines } from "../features/codium/pipelines/usePipelines";
import { fetchRepositories } from "../services/codiumApi";
import type { RepositoryWithStatus } from "../types/codium";
import "../styles/codium-pipelines.css";

const NOVA_DEFINICIJA = JSON.stringify(
  {
    name: "nov-pipeline",
    timeout_minutes: 20,
    steps: [{ name: "korak", run: "echo zdravo" }],
  },
  null,
  2,
);

export default function CodiumPipelines() {
  const [repositories, setRepositories] = useState<RepositoryWithStatus[]>([]);
  const [repoId, setRepoId] = useState<number | null>(null);
  const [izabran, setIzabran] = useState<number | null>(null);
  const [izabranoPokretanje, setIzabranoPokretanje] = useState<number | null>(null);
  const [osvezi, setOsvezi] = useState(0);
  const [greskaSnimanja, setGreskaSnimanja] = useState("");

  const { pipelines, isLoading, error, create, update, remove, start } =
    usePipelines(repoId ?? undefined);

  useEffect(() => {
    fetchRepositories()
      .then((odgovor) => {
        setRepositories(odgovor.repositories);
        if (odgovor.repositories.length > 0) {
          setRepoId(odgovor.repositories[0].id);
        }
      })
      // Strana ne sme da padne zbog liste repozitorijuma; prazna lista je
      // sama po sebi poruka.
      .catch(() => setRepositories([]));
  }, []);

  const izabranPipeline = pipelines.find((p) => p.id === izabran) ?? null;
  const definicija = izabranPipeline?.definition ?? NOVA_DEFINICIJA;

  async function snimi(tekst: string): Promise<void> {
    try {
      if (izabranPipeline === null) {
        if (repoId === null) {
          return;
        }
        await create(repoId, tekst);
      } else {
        await update(izabranPipeline.id, tekst);
      }
      setGreskaSnimanja("");
    } catch (problem) {
      setGreskaSnimanja(
        problem instanceof Error ? problem.message : String(problem),
      );
    }
  }

  async function pokreni(): Promise<void> {
    if (izabranPipeline === null) {
      setGreskaSnimanja("Izaberi pipeline pre pokretanja.");
      return;
    }
    try {
      const pokretanje = await start(izabranPipeline.id);
      setIzabranoPokretanje(pokretanje.id);
      setOsvezi((prethodno) => prethodno + 1);
      setGreskaSnimanja("");
    } catch (problem) {
      setGreskaSnimanja(
        problem instanceof Error ? problem.message : String(problem),
      );
    }
  }

  if (repositories.length === 0) {
    return (
      <div className="cpipe-strana">
        <p className="cpipe-prazno">
          Nijedan repozitorijum nije registrovan. Dodaj ga na strani Repositories —
          pipeline se uvek pokreće nad repozitorijumom.
        </p>
      </div>
    );
  }

  return (
    <div className="cpipe-strana">
      <header className="cpipe-zaglavlje">
        <h1>Pipelines</h1>
        <select
          aria-label="Repozitorijum"
          value={repoId ?? ""}
          onChange={(dogadjaj) => {
            setRepoId(Number(dogadjaj.target.value));
            setIzabran(null);
            setIzabranoPokretanje(null);
          }}
        >
          {repositories.map((repo) => (
            <option key={repo.id} value={repo.id}>
              {repo.name}
            </option>
          ))}
        </select>
        {isLoading && <span className="cpipe-hint">Učitavanje…</span>}
        {error && <span className="cpipe-greska">{error}</span>}
      </header>

      <section className="cpipe-levo">
        <PipelineList
          pipelines={pipelines}
          selectedId={izabran}
          onSelect={(id) => {
            setIzabran(id);
            setIzabranoPokretanje(null);
          }}
          onRemove={(id) => void remove(id)}
        />
        <RunHistory
          pipelineId={izabran}
          selectedRunId={izabranoPokretanje}
          onSelect={setIzabranoPokretanje}
          refreshKey={osvezi}
        />
      </section>

      <section className="cpipe-sredina">
        <DefinitionEditor
          value={definicija}
          onSave={(tekst) => void snimi(tekst)}
          onRun={() => void pokreni()}
          saveError={greskaSnimanja}
        />
      </section>

      <section className="cpipe-desno">
        <RunDetail
          runId={izabranoPokretanje}
          onCancelled={() => setOsvezi((prethodno) => prethodno + 1)}
        />
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Napiši stil**

`apps/gui/src/styles/codium-pipelines.css` (uskladi promenljive sa postojećim `codium-repositories.css`):

```css
/* ==========          CODIUM PIPELINES          ========== */

.cpipe-strana {
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(320px, 1fr) minmax(320px, 1.2fr);
  grid-template-rows: auto 1fr;
  gap: 12px;
  height: 100%;
  padding: 16px;
}

.cpipe-zaglavlje {
  grid-column: 1 / -1;
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.cpipe-levo,
.cpipe-sredina,
.cpipe-desno {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow: auto;
}

.cpipe-lista,
.cpipe-istorija,
.cpipe-koraci {
  list-style: none;
  margin: 0;
  padding: 0;
}

.cpipe-stavka {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
}

.cpipe-stavka.izabrana {
  outline: 1px solid currentColor;
}

.cpipe-znacka {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 999px;
  border: 1px solid currentColor;
}

.cpipe-znacka.success { color: #4c9; }
.cpipe-znacka.failed,
.cpipe-znacka.timeout { color: #d66; }
.cpipe-znacka.running { color: #6af; }
.cpipe-znacka.cancelled,
.cpipe-znacka.queued,
.cpipe-znacka.nepoznato { color: #999; }

.cpipe-log-okvir {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 220px;
}

.cpipe-log {
  flex: 1;
  overflow: auto;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.45;
  padding: 8px;
  border-radius: 6px;
  background: #0b0b0b;
  color: #ddd;
}

.cpipe-log-red { white-space: pre-wrap; word-break: break-word; }
.cpipe-log-red.stderr { color: #f3b0b0; }

.cpipe-log-traka {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 4px 0;
}

.cpipe-na-dno {
  position: absolute;
  right: 12px;
  bottom: 12px;
}

.cpipe-greska { color: #d66; }

/* Boje iz ANSI parsera. */
.ansi-bold { font-weight: 700; }
.ansi-black { color: #666; }
.ansi-red { color: #e06c75; }
.ansi-green { color: #98c379; }
.ansi-yellow { color: #e5c07b; }
.ansi-blue { color: #61afef; }
.ansi-magenta { color: #c678dd; }
.ansi-cyan { color: #56b6c2; }
.ansi-white { color: #eee; }
.ansi-bright-black { color: #888; }
.ansi-bright-red { color: #ff7b86; }
.ansi-bright-green { color: #b5e890; }
.ansi-bright-yellow { color: #ffd68a; }
.ansi-bright-blue { color: #82c7ff; }
.ansi-bright-magenta { color: #e29bf5; }
.ansi-bright-cyan { color: #6fd5e0; }
.ansi-bright-white { color: #fff; }
```

- [ ] **Step 5: Uveži rutu i sidebar**

U `apps/gui/src/App.tsx`, uz ostale CODIUM rute (import napiši istim stilom kao susedne CODIUM strane u tom fajlu):

```tsx
        <Route path="/codium/pipelines" element={<CodiumPipelines />} />
```

U `apps/gui/src/components/layout/Sidebar.tsx` zameni red:

```tsx
        { id: "pipelines", label: "Pipelines", icon: Workflow, kind: "soon", phase: "F14" },
```

sa:

```tsx
        { id: "pipelines", label: "Pipelines", icon: Workflow, kind: "route", path: "/codium/pipelines" },
```

- [ ] **Step 6: Pokreni testove da prođu**

```bash
npm run test -- src/pages/CodiumPipelines.test.tsx
```

Očekivano: PASS.

- [ ] **Step 7: Ceo GUI skup i tipovi**

```bash
npm run test
```

```bash
npm run build
```

Očekivano: testovi prolaze; `npm run build` prijavljuje samo dve postojeće greške (`CoreDockLayout.tsx` TS2503, `CodiumWorkspace.tsx` TS6133), nijednu novu.

- [ ] **Step 8: Commit**

```bash
git add apps/gui/src
git commit -m "feat(gui): strana Pipelines, ruta i sidebar stavka"
```

---

### Task 8: Overview pločica i upozorenje pri zatvaranju

**Files:**
- Modify: `apps/gui/src/pages/CodiumOverview.tsx`
- Create: `apps/gui/src/features/codium/pipelines/useCloseGuard.ts`
- Modify: `apps/gui/src/pages/CodiumPipelines.tsx`
- Test: `apps/gui/src/features/codium/pipelines/useCloseGuard.test.ts`

**Interfaces:**
- Consumes: `fetchPipelines`, `fetchRuns` (Task 1).
- Produces: `useCloseGuard(activeRuns: number)` — bez povratne vrednosti; dok je `activeRuns > 0`, zatvaranje Tauri prozora traži potvrdu.

- [ ] **Step 1: Napiši test koji pada**

`apps/gui/src/features/codium/pipelines/useCloseGuard.test.ts`:

```typescript
import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCloseGuard } from "./useCloseGuard";

const onCloseRequested = vi.fn();

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ onCloseRequested }),
}));

afterEach(() => {
  vi.resetAllMocks();
});

describe("useCloseGuard", () => {
  it("bez pokretanja u toku ne kači ništa", () => {
    renderHook(() => useCloseGuard(0));
    expect(onCloseRequested).not.toHaveBeenCalled();
  });

  it("sa pokretanjem u toku kači slušaoca", () => {
    onCloseRequested.mockResolvedValue(() => {});
    renderHook(() => useCloseGuard(2));
    expect(onCloseRequested).toHaveBeenCalledOnce();
  });

  it("potvrda koju čovek odbije sprečava zatvaranje", async () => {
    let uhvacen: ((dogadjaj: { preventDefault: () => void }) => void) | null = null;
    onCloseRequested.mockImplementation((slusalac: typeof uhvacen) => {
      uhvacen = slusalac;
      return Promise.resolve(() => {});
    });
    const sprecen = vi.fn();
    vi.stubGlobal("confirm", () => false);

    renderHook(() => useCloseGuard(1));
    uhvacen?.({ preventDefault: sprecen });

    expect(sprecen).toHaveBeenCalledOnce();
    vi.unstubAllGlobals();
  });
});
```

- [ ] **Step 2: Pokreni test da vidiš da pada**

```bash
npm run test -- src/features/codium/pipelines/useCloseGuard.test.ts
```

Očekivano: FAIL — modul `./useCloseGuard` ne postoji.

- [ ] **Step 3: Napiši `useCloseGuard`**

`apps/gui/src/features/codium/pipelines/useCloseGuard.ts`:

```typescript
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
```

- [ ] **Step 4: Uveži stražara u stranu**

U `apps/gui/src/pages/CodiumPipelines.tsx` strana sama broji pokretanja u toku,
sopstvenim pozivom — `RunHistory` se ne dira, jer on prikazuje jedan pipeline, a
upozorenje mora da zna za sva pokretanja. Dodaj:

```tsx
  const [aktivnih, setAktivnih] = useState(0);

  useEffect(() => {
    let otkazano = false;
    fetchRuns(undefined, 50)
      .then((odgovor) => {
        if (!otkazano) {
          setAktivnih(
            odgovor.runs.filter(
              (run) => run.status === "running" || run.status === "queued",
            ).length,
          );
        }
      })
      .catch(() => setAktivnih(0));
    return () => {
      otkazano = true;
    };
  }, [osvezi, izabranoPokretanje]);

  useCloseGuard(aktivnih);
```

uz `import { useCloseGuard } from "../features/codium/pipelines/useCloseGuard";`
i dopunu `fetchRuns` u postojećem import-u iz `../services/codiumApi`.

- [ ] **Step 5: Oživi Overview pločicu**

U `apps/gui/src/pages/CodiumOverview.tsx` zameni pločicu `stat-pipelines`, koja
danas piše tvrdo ukucano `3 / 4` sa oznakom „uskoro":

```tsx
  const [pipelineStats, setPipelineStats] = useState({ ukupno: 0, aktivnih: 0 });

  useEffect(() => {
    Promise.all([fetchPipelines(), fetchRuns(undefined, 50)])
      .then(([lista, pokretanja]) => {
        setPipelineStats({
          ukupno: lista.pipelines.length,
          aktivnih: pokretanja.runs.filter(
            (run) => run.status === "running" || run.status === "queued",
          ).length,
        });
      })
      // Overview ne sme da padne zbog jedne pločice.
      .catch(() => setPipelineStats({ ukupno: 0, aktivnih: 0 }));
  }, []);
```

i u `stats` listi:

```tsx
    {
      id: "stat-pipelines",
      icon: <Workflow size={20} />,
      label: "Pipelines",
      value: String(pipelineStats.ukupno),
      hint: `${pipelineStats.aktivnih} u toku`,
    },
```

Dodaj `fetchPipelines` i `fetchRuns` u postojeći import iz `../services/codiumApi`.

Ako `CodiumOverview.test.tsx` posle ovoga padne zato što automatski mock vraća
`undefined` za nove pozive, dopuni njegov `beforeEach` sa
`vi.mocked(api.fetchPipelines).mockResolvedValue({ pipelines: [] })` i
`vi.mocked(api.fetchRuns).mockResolvedValue({ runs: [] })` — isto je urađeno u
E2 kad je pločica repozitorijuma prešla na stvarne podatke.

- [ ] **Step 6: Pokreni testove**

```bash
npm run test
```

```bash
npm run build
```

Očekivano: sve prolazi; `npm run build` samo dve postojeće greške, nijedna nova.

- [ ] **Step 7: Commit**

```bash
git add apps/gui/src
git commit -m "feat(gui): ozivljena Pipelines plocica i upozorenje pri zatvaranju"
```

---

### Task 9: Dokumentacija i zatvaranje faze

**Files:**
- Modify ili Create: `.ai/dev-log/entries/<današnji-datum>.md`
- Modify: `.ai/dev-log/INDEX.md`
- Modify: `.ai/izgradnja/codium/00-INDEX.md`
- Modify: `.ai/izgradnja/codium/13-E3-pipelines.md`

**Interfaces:**
- Consumes: sve prethodne task-ove.
- Produces: ništa u kodu; zatvara E3.

- [ ] **Step 1: Pokreni oba skupa**

```bash
npm run test
```

```bash
./.venv/Scripts/python.exe -m pytest tests -q
```

Zabeleži tačne brojeve. Backend se u ovoj fazi ne dira, pa je očekivano da bude
isti broj kao pre E3b — ako nije, to je nalaz, ne šum.

- [ ] **Step 2: Proveri tipove**

```bash
npm run build
```

Očekivano: samo dve postojeće greške. Ne piši „tsc čist" — nije, i razlog nije E3b.

- [ ] **Step 3: Napiši dev-log**

Unos u `.ai/dev-log/entries/` po konvenciji `GGGG-MM-DD.md`. Ako fajl za današnji
datum već postoji, **dopuni ga** i osveži postojeći red u `.ai/dev-log/INDEX.md`
umesto da dodaješ drugi. Pročitaj poslednja dva unosa pre pisanja i uskladi oblik.

Sadržaj: šta je napravljeno; da E3b zatvara E3; odluke iz razgovora (samo strana
bez panela u workspace-u, sopstveni ANSI parser umesto ugrađenog xterm-a, Monaco
šema ograničena preko `fileMatch`, prikaz loga staje na 2000 redova); i šta još
treba proveriti uživo, jer ništa nije provereno kroz pokrenut CORE — definisati
pipeline, snimiti ga, pokrenuti, gledati kako log stiže i boji se, otkazati
pokretanje u toku, i zatvoriti prozor dok pokretanje traje da se vidi potvrda.

- [ ] **Step 4: Upiši status u indekse**

U `.ai/izgradnja/codium/00-INDEX.md`: red `E3` dobija status `**zavrseno**`
(E3a plus E3b) i današnji datum. Pasus koji imenuje sledeći posao zameni novim
koji kaže da je sledeći `E4 Deployments`.

U `.ai/izgradnja/codium/13-E3-pipelines.md` dopuni odeljak „Podela na E3a i E3b"
napomenom da je i E3b završen, sa datumom.

- [ ] **Step 5: Commit**

```bash
git add .ai
git commit -m "docs(codium): E3b Pipelines ekran zavrsen, indeks i dev-log"
```
