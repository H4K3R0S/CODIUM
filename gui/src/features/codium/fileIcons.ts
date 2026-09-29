// ==========          IKONICE I BOJE FAJLOVA          ==========
//
// Čista logika (bez React-a): iz imena fajla se izvodi kategorija, iz kategorije
// boja i (u komponenti) lucide ikonica. Boje foldera su determinističke —
// izvedene iz imena, pa isti folder uvek dobije istu boju.

export type FileCategory =
  | "js"
  | "ts"
  | "python"
  | "rust"
  | "html"
  | "css"
  | "json"
  | "markdown"
  | "image"
  | "video"
  | "audio"
  | "archive"
  | "pdf"
  | "config"
  | "shell"
  | "code"
  | "text"
  | "generic";

// Mapa ekstenzija na kategoriju. Sve malim slovima (poredi se lowercase).
const EXT_CATEGORY: Record<string, FileCategory> = {
  // JavaScript svet
  js: "js",
  jsx: "js",
  mjs: "js",
  cjs: "js",
  // TypeScript
  ts: "ts",
  tsx: "ts",
  // Python
  py: "python",
  pyw: "python",
  pyi: "python",
  // Rust
  rs: "rust",
  // Web markup
  html: "html",
  htm: "html",
  vue: "html",
  svelte: "html",
  // Stilovi
  css: "css",
  scss: "css",
  sass: "css",
  less: "css",
  // Podaci
  json: "json",
  jsonc: "json",
  // Markdown / dokumentacija
  md: "markdown",
  mdx: "markdown",
  markdown: "markdown",
  // Slike
  png: "image",
  jpg: "image",
  jpeg: "image",
  gif: "image",
  webp: "image",
  svg: "image",
  bmp: "image",
  ico: "image",
  avif: "image",
  // Video
  mp4: "video",
  mkv: "video",
  webm: "video",
  mov: "video",
  avi: "video",
  // Zvuk
  mp3: "audio",
  wav: "audio",
  flac: "audio",
  ogg: "audio",
  m4a: "audio",
  // Arhive
  zip: "archive",
  rar: "archive",
  "7z": "archive",
  tar: "archive",
  gz: "archive",
  bz2: "archive",
  xz: "archive",
  // PDF
  pdf: "pdf",
  // Konfiguracija
  toml: "config",
  yaml: "config",
  yml: "config",
  ini: "config",
  env: "config",
  conf: "config",
  cfg: "config",
  lock: "config",
  // Shell
  sh: "shell",
  bash: "shell",
  zsh: "shell",
  ps1: "shell",
  bat: "shell",
  cmd: "shell",
  // Ostali kod
  c: "code",
  h: "code",
  cpp: "code",
  hpp: "code",
  cc: "code",
  cs: "code",
  go: "code",
  java: "code",
  kt: "code",
  rb: "code",
  php: "code",
  swift: "code",
  sql: "code",
  // Tekst
  txt: "text",
  log: "text",
  csv: "text",
};

// Puna imena fajlova (bez ekstenzije) sa posebnom kategorijom.
const NAME_CATEGORY: Record<string, FileCategory> = {
  dockerfile: "config",
  makefile: "config",
  ".gitignore": "config",
  ".env": "config",
  "package.json": "json",
  "tsconfig.json": "json",
  "cargo.toml": "config",
};

/** Ekstenzija imena fajla (mala slova, bez tačke); prazno ako je nema. */
export function fileExt(name: string): string {
  const dot = name.lastIndexOf(".");
  if (dot <= 0) {
    // Nema tačke ili počinje tačkom (npr. „.gitignore") → nema prave ekstenzije.
    return "";
  }
  return name.slice(dot + 1).toLowerCase();
}

/** Kategorija fajla po imenu (prvo puna imena, pa ekstenzija). */
export function fileCategory(name: string): FileCategory {
  const lower = name.toLowerCase();
  if (NAME_CATEGORY[lower]) {
    return NAME_CATEGORY[lower];
  }
  const ext = fileExt(name);
  return EXT_CATEGORY[ext] ?? "generic";
}

// Boja po kategoriji (hex). Neutralne kad je „generic".
const CATEGORY_COLOR: Record<FileCategory, string> = {
  js: "#e8c33c",
  ts: "#4a9ce6",
  python: "#4b8bbe",
  rust: "#e06a3b",
  html: "#e6693b",
  css: "#5c6ffb",
  json: "#c9a34a",
  markdown: "#8aa0b8",
  image: "#3fb58b",
  video: "#c05bd6",
  audio: "#d64b8a",
  archive: "#c99a3c",
  pdf: "#e0503b",
  config: "#8a9aab",
  shell: "#5fae63",
  code: "#7aa0c4",
  text: "#9aa4b2",
  generic: "#9aa4b2",
};

/** Boja ikonice za kategoriju fajla. */
export function categoryColor(category: FileCategory): string {
  return CATEGORY_COLOR[category];
}

/** Skraćenica: boja direktno iz imena fajla. */
export function fileColor(name: string): string {
  return categoryColor(fileCategory(name));
}

// Paleta boja foldera — deterministički se bira po imenu (hash).
const FOLDER_PALETTE = [
  "#d9a441",
  "#4a9ce6",
  "#3fb58b",
  "#c05bd6",
  "#e0693b",
  "#5c6ffb",
  "#d64b8a",
  "#5fae63",
];

/** Stabilan indeks palete iz stringa (mali FNV-ish hash). */
function hashIndex(text: string, modulo: number): number {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return hash % modulo;
}

/**
 * Boja foldera — deterministička iz imena (poslednji segment putanje). Isti
 * folder uvek dobije istu boju, pa se stablo lakše skenira očima.
 */
export function folderColor(name: string): string {
  const leaf = name.split("/").pop() ?? name;
  return FOLDER_PALETTE[hashIndex(leaf.toLowerCase(), FOLDER_PALETTE.length)];
}
