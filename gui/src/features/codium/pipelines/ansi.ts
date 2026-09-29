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
// Kontrolni znak u izrazu je poenta, ne previd: ANSI niz pocinje ESC-om.
// eslint-disable-next-line no-control-regex
const NIZ = /\[([0-9;]*)([A-Za-z])/g;

// Nezavršen niz na kraju ulaza: ESC pa `[` pa cifre/tačka-zarezi, bez slova
// koje bi ga zatvorilo. Regex iznad ga ne pogađa, pa ostaje u repu — a rep se
// dodaje kao tekst. Njega treba odseći, ne prikazati.
// eslint-disable-next-line no-control-regex
const NEZAVRSEN_NIZ_NA_KRAJU = /\[[0-9;]*$/;

export function parseAnsi(text: string): AnsiChunk[] {
  const komadi: AnsiChunk[] = [];
  let boja: string | undefined;
  let podebljano = false;
  let od = 0;

  function dodaj(deo: string): void {
    if (!deo) {
      return;
    }
    // Spoji sa prethodnim komadom ako je isti stil — niz koji samo pomera
    // kursor (npr. brisanje reda pa povratak na početak) ne sme da preseče
    // jedan red teksta na dva komada.
    const prethodni = komadi[komadi.length - 1];
    if (prethodni !== undefined && prethodni.color === boja && !!prethodni.bold === podebljano) {
      prethodni.text += deo;
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

  const rep = text.slice(od).replace(NEZAVRSEN_NIZ_NA_KRAJU, "");
  dodaj(rep);
  return komadi;
}
