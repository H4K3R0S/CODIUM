// ==========          SASTAVLJANJE USLOVA          ==========
// Čist modul: uređivač bira polje, operator i vrednost, a ovde se od toga
// pravi izraz koji server parsira. Stoji odvojeno od komponente jer fajl koji
// uz komponentu izvozi i nešto drugo gubi hot reload.

/**
 * Sastavlja izraz koji server parsira.
 *
 * Brojevi i logičke vrednosti idu goli, sve ostalo pod navodnicima — inače bi
 * `status == failed` bilo poređenje sa poljem, a ne sa tekstom.
 */
export function sastaviUslov(polje: string, operator: string,
                             vrednost: string): string {
  if (polje === "") {
    return "";
  }
  const golo = vrednost.trim();
  const jeBroj = golo !== "" && !Number.isNaN(Number(golo));
  const jeLogicka = golo === "true" || golo === "false" || golo === "null";
  const desno = jeBroj || jeLogicka ? golo : `"${golo}"`;
  return `${polje} ${operator} ${desno}`;
}
