import { useState } from "react";

import type { DeployKind, DeployTargetCreateRequest } from "../../../types/codium";

type Props = {
  onCreate: (zahtev: DeployTargetCreateRequest) => Promise<void>;
};

// Samo tipovi za koje u ovoj verziji postoji provajder. `ssh_host` stoji u
// backend-u bez provajdera, pa se ne nudi — ponuditi ga značilo bi obrazac
// koji uvek završi greškom.
const TIPOVI: { kind: DeployKind; label: string }[] = [
  { kind: "local_folder", label: "Lokalni folder" },
  { kind: "local_docker", label: "Lokalni Docker" },
];

/**
 * Upis novog cilja isporuke.
 *
 * Polja se menjaju sa tipom cilja jer ih provajder proverava na serveru;
 * jedan obrazac za sve tipove tražio bi da čovek pogađa koje polje važi.
 */
export default function NewTarget({ onCreate }: Props) {
  const [ime, setIme] = useState("");
  const [tip, setTip] = useState<DeployKind>("local_folder");
  const [putanja, setPutanja] = useState("");
  const [nacin, setNacin] = useState("compose");
  const [slika, setSlika] = useState("");
  const [kontejner, setKontejner] = useState("");
  const [port, setPort] = useState("");
  const [greska, setGreska] = useState("");

  function konfiguracija(): Record<string, string> {
    if (tip === "local_folder") {
      return { path: putanja.trim() };
    }
    if (nacin === "compose") {
      return { mode: "compose", compose_dir: putanja.trim() };
    }
    return {
      mode: "image",
      image: slika.trim(),
      container: kontejner.trim(),
      ...(port.trim() ? { port: port.trim() } : {}),
    };
  }

  async function upisi() {
    try {
      await onCreate({ name: ime.trim(), kind: tip, config: konfiguracija() });
      setIme("");
      setPutanja("");
      setSlika("");
      setKontejner("");
      setPort("");
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    }
  }

  const dockerSlika = tip === "local_docker" && nacin === "image";

  return (
    <form
      className="cdep-obrazac"
      onSubmit={(dogadjaj) => {
        dogadjaj.preventDefault();
        void upisi();
      }}
    >
      <label htmlFor="cdep-ime">Naziv</label>
      <input
        id="cdep-ime"
        value={ime}
        placeholder="produkcija"
        onChange={(dogadjaj) => setIme(dogadjaj.target.value)}
      />

      <label htmlFor="cdep-tip">Tip cilja</label>
      <select
        id="cdep-tip"
        value={tip}
        onChange={(dogadjaj) => setTip(dogadjaj.target.value as DeployKind)}
      >
        {TIPOVI.map((stavka) => (
          <option key={stavka.kind} value={stavka.kind}>
            {stavka.label}
          </option>
        ))}
      </select>

      {tip === "local_docker" && (
        <>
          <label htmlFor="cdep-nacin">Način</label>
          <select
            id="cdep-nacin"
            value={nacin}
            onChange={(dogadjaj) => setNacin(dogadjaj.target.value)}
          >
            <option value="compose">compose — docker compose up</option>
            <option value="image">image — build pa docker run</option>
          </select>
        </>
      )}

      {!dockerSlika && (
        <>
          <label htmlFor="cdep-putanja">
            {tip === "local_folder" ? "Folder isporuke" : "Folder sa compose fajlom"}
          </label>
          <input
            id="cdep-putanja"
            value={putanja}
            placeholder="C:\www\moj-sajt"
            onChange={(dogadjaj) => setPutanja(dogadjaj.target.value)}
          />
        </>
      )}

      {dockerSlika && (
        <>
          <label htmlFor="cdep-slika">Slika</label>
          <input
            id="cdep-slika"
            value={slika}
            placeholder="moja-app"
            onChange={(dogadjaj) => setSlika(dogadjaj.target.value)}
          />
          <label htmlFor="cdep-kontejner">Kontejner</label>
          <input
            id="cdep-kontejner"
            value={kontejner}
            placeholder="moja-app"
            onChange={(dogadjaj) => setKontejner(dogadjaj.target.value)}
          />
          <label htmlFor="cdep-port">Port (opciono)</label>
          <input
            id="cdep-port"
            value={port}
            placeholder="8080:80"
            onChange={(dogadjaj) => setPort(dogadjaj.target.value)}
          />
        </>
      )}

      {greska && <p className="cdep-greska">{greska}</p>}

      <button type="submit" disabled={!ime.trim()}>
        Dodaj cilj
      </button>
    </form>
  );
}
