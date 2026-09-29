import type { ConnectorKindDto } from "../../../services/coreApi";

// ==========          OPIS FORME KONEKTORA          ==========
// Čist modul: od opisa vrste pravi opis forme i proverava unos. Nema React-a,
// pa se testira bez renderovanja.
//
// Ekran NEMA poseban kod po vrsti. Nova vrsta u backend-u dobija svoju formu
// čim se pojavi u `GET /kinds` — inače bi svaki novi konektor tražio izmenu
// GUI-ja na mestu koje niko ne pamti.

export interface FormField {
  /** Ime polja kako ga backend očekuje (`config` ključ ili logička tajna). */
  name: string;
  label: string;
  /** Tajna se šalje jednom i nikad se ne prikazuje nazad. */
  secret: boolean;
  required: boolean;
  placeholder: string;
}

export interface FormDescription {
  kind: string;
  label: string;
  fields: FormField[];
}

// Nazivi polja koja se ponavljaju kroz vrste. Nepoznato ime ostaje kakvo jeste
// — bolje sirovo `webhook_url` nego pogrešan prevod.
const NAZIVI: Record<string, string> = {
  api_key: "[Here put api_key]",
  token: "Token",
  password: "[Here put password]",
  passphrase: "Lozinka ključa",
  username: "Korisničko ime",
  host: "Adresa servera",
  port: "Port",
  registry_url: "Adresa registry-ja",
  key_path: "Putanja do ključa",
  api_url: "Adresa API-ja",
  use_tls: "TLS",
};

const PRIMERI: Record<string, string> = {
  host: "smtp.firma.rs",
  registry_url: "https://registry.firma.rs",
  key_path: "C:\\Users\\ja\\.ssh\\id_ed25519",
  api_url: "https://api.github.com",
};

function polje(name: string, secret: boolean, required: boolean): FormField {
  return {
    name,
    label: NAZIVI[name] ?? name,
    secret,
    required,
    placeholder: PRIMERI[name] ?? "",
  };
}

/**
 * Opis forme za jednu vrstu konektora.
 *
 * Koja je tajna neobavezna kaže backend (`optional_secret_fields`), ne ovaj
 * modul: to je svojstvo konektora, a ne ekrana. Jedini takav slučaj danas je
 * SSH ključ bez lozinke.
 */
export function describeForm(kind: ConnectorKindDto): FormDescription {
  const neobavezne = new Set(kind.optional_secret_fields ?? []);
  return {
    kind: kind.id,
    label: kind.label,
    fields: [
      ...kind.required_fields.map((ime) => polje(ime, false, true)),
      ...kind.secret_fields.map((ime) => polje(ime, true, !neobavezne.has(ime))),
    ],
  };
}

export interface FormValues {
  name: string;
  values: Record<string, string>;
}

/**
 * Vraća imena polja koja fale. Prazan niz znači da se sme snimiti.
 *
 * Provera je ovde, a ne u komponenti, da bi ista pravila važila i kad forma
 * jednog dana dođe sa druge strane (uvoz, agent).
 */
export function missingFields(opis: FormDescription,
                              unos: FormValues): string[] {
  const fale: string[] = [];
  if (unos.name.trim() === "") {
    fale.push("name");
  }
  for (const polje of opis.fields) {
    if (polje.required && (unos.values[polje.name] ?? "").trim() === "") {
      fale.push(polje.name);
    }
  }
  return fale;
}

/**
 * Deli unos na ne-tajni `config` i vrednost tajne.
 *
 * Backend prima jednu tajnu po konektoru; vrsta sa više logičkih tajni ovde bi
 * tražila dogovor kojeg još nema, pa se uzima prva popunjena.
 */
export function splitPayload(opis: FormDescription, unos: FormValues): {
  config: Record<string, string>;
  secret: string;
} {
  const config: Record<string, string> = {};
  let secret = "";
  for (const polje of opis.fields) {
    const vrednost = (unos.values[polje.name] ?? "").trim();
    if (vrednost === "") {
      continue;
    }
    if (polje.secret) {
      if (secret === "") {
        secret = vrednost;
      }
    } else {
      config[polje.name] = vrednost;
    }
  }
  return { config, secret };
}
