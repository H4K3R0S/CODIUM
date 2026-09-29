import type { ReactNode } from "react";


// ==========          REGISTAR PRIKAZA ČISTOG PROZORA          ==========
/*
 * Čist (bare) prozor je prazan izuzev pozadine i titlebar kontrola. Šta se u
 * njemu prikazuje određuje `view` ključ iz pane-a. Domeni (npr. KALIMA)
 * registruju svoje prikaze ovde, pa profil samo otvara prozore, a domen u
 * njih renderuje odgovarajući prikaz — bez ručnog podešavanja veličine i
 * pozicije.
 */

export type BareView = () => ReactNode;

/** Ključ prikaza → render funkcija. Domeni ga popunjavaju svojim prikazima. */
export const bareViews: Record<string, BareView> = {};

/** Registruje prikaz za dati ključ (idempotentno). */
export function registerBareView(key: string, view: BareView): void {
  bareViews[key] = view;
}
