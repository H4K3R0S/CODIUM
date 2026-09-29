import Editor from "@monaco-editor/react";
import { useCallback, useMemo, useState } from "react";

import {
  PIPELINE_MODEL_PATH,
  PIPELINE_SCHEMA_URI,
  pipelineDefinitionSchema,
  validateDefinition,
} from "./definitionSchema";

/** Deo Monaco API-ja koji nam treba; postoji samo kad je JSON servis uvucen. */
type JsonJezik = {
  jsonDefaults: {
    setDiagnosticsOptions: (opcije: {
      validate: boolean;
      schemas: { uri: string; fileMatch: string[]; schema: unknown }[];
    }) => void;
  };
};

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
  // Izmene se pamte UZ definiciju od koje su krenule. Kada sa servera stigne
  // druga definicija (drugi pipeline ili snimljena verzija), ključ se razlikuje
  // i uređivač pokazuje nju — bez upisa iz efekta, koji je značio jedan kadar
  // sa tuđim tekstom.
  const [izmena, setIzmena] = useState<{ osnova: string; tekst: string } | null>(
    null,
  );
  const tekst = izmena?.osnova === value ? izmena.tekst : value;

  const setTekst = useCallback(
    (sledeci: string) => {
      setIzmena({ osnova: value, tekst: sledeci });
    },
    [value],
  );

  // Greške su računica nad tekstom, ne zasebno stanje: isti ulaz uvek daje isti
  // spisak, pa se računa pri crtanju umesto da ga efekat upisuje.
  const greske = useMemo(() => validateDefinition(tekst), [tekst]);

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
        theme="codium-json"
        language="json"
        path={PIPELINE_MODEL_PATH}
        value={tekst}
        onChange={(novo) => setTekst(novo ?? "")}
        beforeMount={(monaco) => {
          // Monaco podrazumevano ide u svetloj temi („vs“), pa je uređivač bio
          // bela mrlja na tamnom ekranu. Tema se definiše ovde, a ne globalno,
          // jer `defineTheme` vezuje ime — F6 editor ima svoju („core-editor“)
          // sa providnom podlogom, dok ova stoji u panelu koji nosi svoju.
          monaco.editor.defineTheme("codium-json", {
            base: "vs-dark",
            inherit: true,
            rules: [],
            colors: {
              "editor.background": "#0f1522",
              "editorGutter.background": "#0f1522",
            },
          });

          // `monaco-editor` 0.56 je JSON servis izmestio u zaseban unos
          // (`esm/vs/language/json/monaco.contribution`), a glavni ESM ulaz
          // koji Vite razrešava ga ne uvlači — pa `languages.json` ume da
          // bude `undefined`. Bez ove provere poziv obara ceo ekran.
          // Podvlačenje greške je zato dodatak, a ne uslov: `validateDefinition`
          // ionako ispisuje greške iznad uređivača i gasi „Snimi".
          const json = (monaco.languages as { json?: JsonJezik }).json;
          if (json === undefined) {
            return;
          }
          json.jsonDefaults.setDiagnosticsOptions({
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
