// ==========          IZBORNIK MODELA (čist modul)          ==========
// Grupisanje i sortiranje kataloga za dropdown. Bez React-a i bez fetch-a, da
// se logika testira bez renderovanja.

export type CatalogModel = {
  id: string;
  label: string;
  provider: string;
  is_local: boolean;
  context_window: number;
  price_in_per_mtok: number;
  price_out_per_mtok: number;
  size_gb: number | null;
  oversized: boolean;
  available: boolean;
  unavailable_reason: string;
  // Da li korisnik želi model u chat izborniku (CODIUM podešavanja).
  // Katalog ga i dalje vraća, samo označenog.
  enabled: boolean;
  // Red koji stoji umesto modela kad provajder ne odgovara — nije model.
  is_placeholder: boolean;
  // Model koji je CORE isključio za sve domene. Domen ga ne može vratiti.
  disabled_globally: boolean;
  // Provajder čija se lista vodi allow listom (OpenRouter). Podešavanja ga
  // izdvajaju u zasebnu sekciju sa pretragom.
  needs_allowlist: boolean;
};

export type ModelGroup = {
  title: string;
  models: CatalogModel[];
};

/** Dostupni prvi, pa po nazivu. Nedostupni ostaju u listi — vide se sivi. */
function sortModels(models: CatalogModel[]): CatalogModel[] {
  return [...models].sort((a, b) => {
    if (a.available !== b.available) {
      return a.available ? -1 : 1;
    }
    return a.label.localeCompare(b.label);
  });
}

/** Deli katalog na „Lokalno" i „Online". Prazna grupa se ne prikazuje. */
export function groupModels(models: CatalogModel[]): ModelGroup[] {
  const local = models.filter((m) => m.is_local);
  const online = models.filter((m) => !m.is_local);

  const groups: ModelGroup[] = [];
  if (local.length > 0) {
    groups.push({ title: "Lokalno", models: sortModels(local) });
  }
  if (online.length > 0) {
    groups.push({ title: "Online", models: sortModels(online) });
  }
  return groups;
}

/**
 * Da li model zaista ne košta ništa.
 *
 * Nula u ceni ima dva različita značenja, a razlika je čitav račun:
 *
 *   lokalni model              — nula jer se vrti na tvom računaru
 *   provajder sa allow listom  — nula jer je katalog tako rekao (OpenRouter
 *                                cene donosi u samom katalogu)
 *   ostali online modeli       — nula jer cena NIJE poznata; ručna tabela
 *                                cena nema unos za taj model
 *
 * `needs_allowlist` je ovde znak da cene stižu iz izvora, pa je nula stvarna
 * nula. Kad cena jednom dobije svoje polje na serveru, ova zamena više neće
 * biti potrebna.
 */
export function isFreeModel(model: CatalogModel): boolean {
  if (model.is_placeholder) {
    return false;
  }
  if (model.is_local) {
    return true;
  }
  return (
    model.needs_allowlist &&
    model.price_in_per_mtok === 0 &&
    model.price_out_per_mtok === 0
  );
}

/** Natpis u dropdown-u: naziv plus veličina ili cena, plus razlog ako ne radi. */
export function formatModelLabel(model: CatalogModel): string {
  const parts: string[] = [];

  if (model.size_gb !== null) {
    parts.push(`${model.size_gb} GB`);
  }
  // Besplatan model se izricito oznacava. Bez toga se „nema cene" i „ne znam
  // cenu" citaju isto, a razlika je citav racun.
  if (isFreeModel(model)) {
    parts.push("besplatno");
  }
  if (model.oversized) {
    parts.push("veći od VRAM-a");
  }
  // Obe cene, ne samo ulazna: izlaz je po pravilu petostruko skuplji, a
  // odgovor asistenta je uglavnom izlaz — sama ulazna cena vara.
  if (!model.is_local && model.price_in_per_mtok > 0) {
    parts.push(`$${model.price_in_per_mtok}/$${model.price_out_per_mtok} po M`);
  } else if (!model.is_local && !isFreeModel(model)) {
    // Online model bez cene u tabeli. Prazno mesto bi se čitalo kao
    // „besplatno" — a nijedan online poziv to nije.
    parts.push("cena nepoznata");
  }
  if (!model.available && model.unavailable_reason !== "") {
    parts.push(model.unavailable_reason);
  }

  return parts.length === 0 ? model.label : `${model.label} (${parts.join(", ")})`;
}

/**
 * Da li izbornik treba da ponudi unos API ključa.
 *
 * Tačno samo kad online modeli postoje a nijedan ne radi. Ako online reda
 * uopšte nema, provajder nije ni registrovan, pa ključ ništa ne rešava;
 * lokalni model koji ne radi (npr. embedding) takođe nije razlog za ključ.
 */
export function needsApiKey(models: CatalogModel[]): boolean {
  const online = models.filter((m) => !m.is_local);
  return online.length > 0 && online.every((m) => !m.available);
}

/**
 * Modeli koje chat izbornik sme da ponudi.
 *
 * Isključeni ostaju u katalogu (podešavanja moraju da ih vide da bi se mogli
 * vratiti), ali se u chat okvir ne prosleđuju.
 */
export function chatModels(models: CatalogModel[]): CatalogModel[] {
  return models.filter((m) => m.enabled);
}


// ==========          KRATKO IME MODELA (uz polje za unos)          ==========
/*
 * Izbornik uz unos je uzak i stoji u redu sa personom, pa tu ide samo ime
 * modela — bez cene, velicine i razloga nedostupnosti. Pun natpis
 * (`formatModelLabel`) ostaje u podesavanjima, gde ima mesta i gde se izbor i
 * donosi.
 */

// Datum na kraju imena („-20251101") je snapshot, ne verzija modela.
const SNAPSHOT = /-\d{8}$/;

/** „claude-opus-4-5-20251101" → „opus 4.5"; „llama3.2:latest" → „llama3.2". */
export function shortModelLabel(model: CatalogModel): string {
  const id = model.id.replace(SNAPSHOT, "");

  if (model.is_local) {
    // Ollama: „ime:tag"; „latest" ne govori nista, ostale tagove zadrzavamo.
    const [ime, tag] = id.split(":");
    return tag === undefined || tag === "latest" ? ime : `${ime} ${tag}`;
  }

  if (id.startsWith("claude-")) {
    // „opus-4-5" → „opus 4.5": crtice izmedju brojeva su tacke u verziji.
    return id
      .slice("claude-".length)
      .replace(/(\d)-(\d)/g, "$1.$2")
      .replace(/-/g, " ");
  }

  if (id.startsWith("gpt-") || id.startsWith("o1") || id.startsWith("o3")) {
    return id.replace(/^gpt-/, "GPT ").replace(/-/g, " ");
  }

  return id;
}
