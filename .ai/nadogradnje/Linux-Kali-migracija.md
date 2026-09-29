# NADOGRADNJA (sledeća po rasporedu) — Linux/Kali migracija + native zavisnosti

> Mesto u planu razvoja: **sledeća stavka po rasporedu.** Cilj: CODIUM ćelija
> radi na Kali/Debian Linux-u. CODIUM nema svojih binarnih u CORE `bin/` —
> zavisnosti su alati razvojnog okruženja (git/docker/node) i npm/py paketi.

## 1. Native binarne iz CORE `bin/`
- **Nijedna ne pripada CODIUM-u.** `bin/` (mpv, whisper, piper) je za FILMIUM/IMPERIUM.
  CODIUM se oslanja na sistemske dev-alate na PATH-u.

## 2. Zavisnosti — Windows vs Linux/Kali

| Alat | Uloga u CODIUM-u | Windows sada | Linux/Kali |
|------|------------------|--------------|------------|
| **git** | Repositories (istorija/diff) | `winget install Git.Git` | `sudo apt install git` (često već tu na Kali) |
| **docker** | Deployments/Infrastructure/Monitoring | `winget install Docker.DockerDesktop` | `sudo apt install docker.io` + `systemctl enable --now docker`; korisnik u `docker` grupi |
| **Node.js** | build GUI + neki pipeline koraci | nodejs.org | `sudo apt install nodejs npm` (ili nvm) |
| **monaco/xterm/dockview** | editor/terminal/paneli (npm) | `npm install` | isto — **ne menja se** (web) |
| **keyring** | čuvanje API ključeva | Windows Credential Manager | Linux Secret Service (`libsecret` + `gnome-keyring`) ili KWallet |
| **anthropic/openai** | AI provajderi (Python) | pip | isto — **ne menja se** |

## 3. Kod koji treba dirati (Windows-specifično)
- **keyring backend:** na Windows-u je Credential Manager; na Linux-u treba
  `gnome-keyring`/`libsecret` (`sudo apt install gnome-keyring libsecret-1-0`) — u
  headless/Kali okruženju keyring može biti nedostupan → predvideti fallback
  (enkriptovan fajl store) kad Secret Service ne radi.
- **docker socket/putanje:** Windows named pipe vs Linux `/var/run/docker.sock`;
  proveri da Deployments/Infrastructure/Monitoring koriste docker SDK/`docker` CLI, ne
  Windows-specifičnu stazu.
- **PTY/terminal:** integrisani terminal — na Windows-u ConPTY, na Linux-u pseudo-tty
  (`pty`); proveri da backend terminala bira ljusku po platformi (`cmd`/`powershell` →
  `bash`/`sh`).
- `core/foundation/dependencies.py` / `installer.py` — `winget` hint → `apt`; probe
  ostaju `shutil.which` (isti mehanizam, radi na oba).
- Tauri build: `libwebkit2gtk-4.1-dev`, `libgtk-3-dev`, `build-essential`.

## 4. Šta NE treba dirati
- FastAPI/uvicorn, SQLite, RAG, GUI (React/Vite/Monaco/xterm — sve web).
- git/docker probe preko `shutil.which` (PATH radi isto).
- AI klijenti (`anthropic`, `openai`), OpenRouter — čist Python/HTTP.

## 5. Redosled primene
1. `apt install git docker.io nodejs npm gnome-keyring libsecret-1-0`.
2. Docker: `systemctl enable --now docker`, dodaj korisnika u `docker` grupu.
3. keyring fallback (fajl store) za headless.
4. Terminal: izbor ljuske po platformi (`bash`).
5. `winget`→`apt` u dependency hint-ovima; test Repositories/Deployments/Terminal.
