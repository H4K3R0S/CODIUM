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
  // Namerno strože od servera, koji nepoznata polja tiho ignoriše kroz
  // `.get(...)`. Smer je bezbedan (odbija se pre snimanja, ne posle), pa
  // ostaje — ne ublažavati bez razloga: ublažavanje je i vratilo prazninu
  // oko `pattern` ispod (vidi FINDING 1 u pregledu ovog task-a).
  additionalProperties: false,
  properties: {
    name: {
      type: "string",
      minLength: 1,
      // `pattern` traži bar jedan ne-belinski znak bilo gde u tekstu — to je
      // JSON šema ekvivalent za `.strip()` neprazno, jer `minLength` sam po
      // sebi broji i razmake (definition.py._tekst trimuje pa proverava).
      pattern: "\\S",
      description: "Ime pipeline-a.",
    },
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
          name: { type: "string", minLength: 1, pattern: "\\S" },
          run: {
            type: "string",
            minLength: 1,
            pattern: "\\S",
            description: "Komanda kroz shell.",
          },
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
