// ==========          PRIKAZ MOLBE ZA ODOBRENJE          ==========
// Čist modul bez ijednog uvoza — prevod payload-a u redove koje čovek čita
// pre nego što klikne Odobri.

export type PayloadLine = { label: string; value: string };

/**
 * Razlaže payload molbe u redove za prikaz.
 *
 * Payload dolazi iz baze i ne mora biti ispravan JSON. Neispravan se pokazuje
 * kao sirov tekst: strana koja bi pukla sakrila bi upravo ono što treba
 * videti pre odluke.
 */
export function describePayload(payload: string): PayloadLine[] {
  const tekst = payload.trim();
  if (!tekst) {
    return [];
  }

  let podaci: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(tekst);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return [{ label: "Sadržaj", value: tekst }];
    }
    podaci = parsed as Record<string, unknown>;
  } catch {
    return [{ label: "Sadržaj", value: tekst }];
  }

  // Molba za online model nema alat ni argumente — nosi samo čime bi se
  // odgovorilo. Bez ove grane bi se prikazala kao sirov JSON.
  if (podaci.kind === "model") {
    const tekst = (vrednost: unknown): string =>
      typeof vrednost === "string" && vrednost !== "" ? vrednost : "—";
    return [
      { label: "Provajder", value: tekst(podaci.provider) },
      { label: "Model", value: tekst(podaci.model) },
    ];
  }

  const linije: PayloadLine[] = [];
  if (typeof podaci.tool === "string") {
    linije.push({ label: "Alat", value: podaci.tool });
  }

  const args = podaci.args;
  if (typeof args === "object" && args !== null && !Array.isArray(args)) {
    for (const [ime, vrednost] of Object.entries(args)) {
      // Ugnježden objekat ili niz pretvoren sa `String(...)` daje
      // "[object Object]" ili niz zapetama slepljen — čovek tada ne vidi
      // šta zapravo odobrava. JSON.stringify ostaje čitljiv.
      const linijaVrednost =
        typeof vrednost === "object" && vrednost !== null
          ? JSON.stringify(vrednost)
          : String(vrednost);
      linije.push({ label: ime, value: linijaVrednost });
    }
  }

  if (typeof podaci.content_hash === "string") {
    linije.push({ label: "Otisak sadržaja", value: podaci.content_hash });
  }

  return linije.length > 0 ? linije : [{ label: "Sadržaj", value: tekst }];
}
