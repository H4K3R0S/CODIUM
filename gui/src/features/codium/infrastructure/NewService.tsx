import { useState } from "react";

import type {
  InfraServiceCreateRequest,
  InfraServiceKind,
} from "../../../types/codium";

type Props = {
  nodeId: number;
  onCreate: (zahtev: InfraServiceCreateRequest) => Promise<void>;
};

const TIPOVI: { kind: InfraServiceKind; label: string }[] = [
  { kind: "local_process", label: "Lokalni proces" },
  { kind: "local_docker", label: "Docker kontejner" },
  { kind: "port_probe", label: "Samo prati port" },
];

/**
 * Ručan upis servisa.
 *
 * Polja se menjaju sa tipom jer ih provajder proverava na serveru; jedan
 * obrazac za sve tipove tražio bi da čovek pogađa koje polje važi.
 */
export default function NewService({ nodeId, onCreate }: Props) {
  const [ime, setIme] = useState("");
  const [tip, setTip] = useState<InfraServiceKind>("local_process");
  const [komanda, setKomanda] = useState("");
  const [folder, setFolder] = useState("");
  const [port, setPort] = useState("");
  const [kontejner, setKontejner] = useState("");
  const [greska, setGreska] = useState("");

  function konfiguracija(): Record<string, string> {
    if (tip === "local_docker") {
      return { container: kontejner.trim() };
    }
    if (tip === "port_probe") {
      return { port: port.trim() };
    }
    return {
      command: komanda.trim(),
      cwd: folder.trim(),
      ...(port.trim() ? { port: port.trim() } : {}),
    };
  }

  async function upisi() {
    try {
      await onCreate({
        node_id: nodeId,
        name: ime.trim(),
        kind: tip,
        config: konfiguracija(),
      });
      setIme("");
      setKomanda("");
      setFolder("");
      setPort("");
      setKontejner("");
      setGreska("");
    } catch (problem) {
      setGreska(problem instanceof Error ? problem.message : String(problem));
    }
  }

  return (
    <form
      className="cinf-obrazac"
      onSubmit={(dogadjaj) => {
        dogadjaj.preventDefault();
        void upisi();
      }}
    >
      <label htmlFor="cinf-ime">Naziv</label>
      <input
        id="cinf-ime"
        value={ime}
        placeholder="dev server"
        onChange={(dogadjaj) => setIme(dogadjaj.target.value)}
      />

      <label htmlFor="cinf-tip">Tip</label>
      <select
        id="cinf-tip"
        value={tip}
        onChange={(dogadjaj) =>
          setTip(dogadjaj.target.value as InfraServiceKind)
        }
      >
        {TIPOVI.map((stavka) => (
          <option key={stavka.kind} value={stavka.kind}>
            {stavka.label}
          </option>
        ))}
      </select>

      {tip === "local_process" && (
        <>
          <label htmlFor="cinf-komanda">Komanda</label>
          <input
            id="cinf-komanda"
            value={komanda}
            placeholder="npm run dev"
            onChange={(dogadjaj) => setKomanda(dogadjaj.target.value)}
          />
          <label htmlFor="cinf-folder">Radni folder</label>
          <input
            id="cinf-folder"
            value={folder}
            placeholder="C:\kod\projekat"
            onChange={(dogadjaj) => setFolder(dogadjaj.target.value)}
          />
        </>
      )}

      {tip === "local_docker" && (
        <>
          <label htmlFor="cinf-kontejner">Kontejner</label>
          <input
            id="cinf-kontejner"
            value={kontejner}
            placeholder="moja-app"
            onChange={(dogadjaj) => setKontejner(dogadjaj.target.value)}
          />
        </>
      )}

      {tip !== "local_docker" && (
        <>
          <label htmlFor="cinf-port">
            {tip === "port_probe" ? "Port" : "Port (opciono)"}
          </label>
          <input
            id="cinf-port"
            value={port}
            placeholder="5173"
            onChange={(dogadjaj) => setPort(dogadjaj.target.value)}
          />
        </>
      )}

      {greska && <p className="cinf-greska">{greska}</p>}

      <button type="submit" disabled={!ime.trim()}>
        Dodaj servis
      </button>
    </form>
  );
}
