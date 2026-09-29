// ==========          OPENROUTER KATALOG (čist modul)          ==========
// Pretraga i odsecanje kataloga od 300+ modela. Bez React-a i bez fetch-a, da
// se logika testira bez renderovanja — isti obrazac kao `modelPicker.ts`.

import type { CatalogModel } from "./modelPicker";

export type CatalogSearch = {
  /** Redovi koji se prikazuju. */
  shown: CatalogModel[];
  /** Koliko pogodaka je odsečeno granicom. */
  hidden: number;
};

/** Koliko redova ide u DOM. 300 redova nije spisak nego kazna. */
export const DEFAULT_LIMIT = 50;

/**
 * Pretraga po id-u i nazivu, sa uključenima na vrhu.
 *
 * Uključeni idu prvi jer su ono što korisnik zapravo koristi — ostatak
 * kataloga je tu da bi se nešto novo našlo, ne da bi se svaki put prelistalo.
 */
export function searchCatalog(models: CatalogModel[], query: string,
                              limit: number = DEFAULT_LIMIT): CatalogSearch {
  const igla = query.trim().toLowerCase();
  const pogodjeni = igla === ""
    ? [...models]
    : models.filter(
        (m) =>
          m.id.toLowerCase().includes(igla) ||
          m.label.toLowerCase().includes(igla),
      );

  pogodjeni.sort((a, b) => {
    if (a.enabled !== b.enabled) {
      return a.enabled ? -1 : 1;
    }
    return a.id.localeCompare(b.id);
  });

  return {
    shown: pogodjeni.slice(0, limit),
    hidden: Math.max(0, pogodjeni.length - limit),
  };
}

/** Cena po milionu tokena, ulaz pa izlaz. */
export function formatPrice(model: CatalogModel): string {
  if (model.price_in_per_mtok === 0 && model.price_out_per_mtok === 0) {
    return "besplatno";
  }
  const ulaz = model.price_in_per_mtok.toFixed(2);
  const izlaz = model.price_out_per_mtok.toFixed(2);
  return `$${ulaz} / $${izlaz} po Mtok`;
}
