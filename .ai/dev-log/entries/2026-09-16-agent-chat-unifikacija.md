---
id: codium-2026-09-16-agent-chat-unifikacija
type: log
domain: codium
title: 2026-09-16-agent-chat-unifikacija
tags:
- dev-log
- entries
edges:
- type: preceded_by
  target: codium-2026-09-04-zavrsna-provera
  weight: 0.8
- type: followed_by
  target: codium-2026-09-16-agent-persona-retrieval-popravke
  weight: 0.8
---

# 2026-09-16 — Agent Chat Unifikacija: jedan dole-centar dock svuda + dosledno ime

Cilj: jedan Agent chat okvir, fiksiran dole-centar prozora, dostupan na SVIM
stranicama svakog domena i u samom CORE-u, sa smart reflow-om (sadržaj se
pomera da ne stoji iza chata). Uz to: reč „Kurator" ostaje SAMO u FILMIUM-u
(to mu je ime agenta); u drugim domenima agent je „<DOMAIN> Agent". Radjeno
preko 4 repoa (CORE + FILMIUM/CODIUM/KALIMA ćelije).

## Urađeno

**CORE — generički slot + globalni dock.** `CellNav` dobio opcioni
`AgentDock?: ComponentType`; `CellShell` i `CellApp` `ChromelessContent`
renderuju taj dock jednom (unutar workspace-a, posle `<main>`) — tako se
domenski dock vidi i standalone (Tauri ćelija) i u CORE embed-u. CORE sopstveni
chat (`CoreAssistantChat`, `scope=core`, `forcePos=bottom`) montiran globalno u
`App` shell-u kroz `CoreGlobalDock`, ali **skriven na odcepljenim rutama**
(`isDetachedCellRoute`: `/codium`,`/kalima`,`/filmium`) — tamo se vidi domenski
dock iz iframe-a, pa nikad nema dva dock-a. Uklonjena po-stranici montaža iz
`DashboardPage`. Nov `agent-dock.css` (fixed, `left:50%`+`translateX(-50%)`,
`max-height: min(58vh,460px)`, `chat-scroll` cap).

**Reflow (smart razmak).** Dock je `position: fixed` (van toka), pa CSS var ne
može da stigne do sadržaja ako stoji na samom dock-u. Nov hook
`useDockHeightVar(ref, varName)` meri realnu visinu fiksiranog dock-a i upisuje
je na `document.documentElement` (:root); `.core-layout .workspace-content
{ padding-bottom: var(--core-dock-h | --agent-dock-h) }` daje donji razmak.
Specifičnost `.core-layout .workspace-content` je nužna — osnovni
`.workspace-content { padding: … }` je isti selektor, učitan kasnije, pa bi inače
pobedio (bug uhvaćen u živoj verifikaciji: razmak je bio 30px umesto visine
dock-a, sadržaj iza chata).

**Ćelije.** KALIMA: `KalimaHubChat` → `KalimaAgentDock` (globalni dole-centar,
persona picker 5, „KALIMA Agent"; uklonjen dashboard mount). CODIUM:
`CodiumKuratorChat` (zasebna `/codium/kurator` stranica) → `CodiumAgentDock`
(globalni, 12 persona, „CODIUM Agent"); uklonjeni ruta+nav+stranica; dodat
`forwardRef`/`appendReply` u CODIUM `CoreChat` + `reply` u `apply` izvršioce
(confirm feedback, paritet sa KALIMA). FILMIUM: `FilmiumKuratorChat` (lebdeća
ikonica) → `FilmiumKuratorDock` (dole-centar, izvučen sadržaj bez
frame-in-frame); **ime „Kurator" zadržano**; mount premešten iz
`FilmiumWorkspace` u shell slot. Svaka ćelija nosi kopiju `agent-dock.css` +
`useDockHeightVar.ts`.

## Provereno

Per-task review sve zeleno (5 taskova, SDD). CORE: `tsc` čist, `npm run build`
čist, vitest 490 (uklj. `isDetachedCellRoute` + slot testove). Ćelije: `tsc` +
`npm run build` čisti; CODIUM py 16, KALIMA py 21 (nepromenjeni). Živa
verifikacija (KALIMA ćelija 8782): dock **dole-centar** (centar 640/640, dno
720), **na više stranica** (Dashboard i Threats), reflow radi
(`--agent-dock-h`=366px, `.workspace-content` padding-bottom=366px, sadržaj se
čisti). CORE/CODIUM/FILMIUM ćelije nisu pokrenute za živu proveru — kod
simetričan KALIMA.

## Napomene

- Za živ chat u ćelijama treba restart ćelije (nov backend); GUI je u dist-u
  (KALIMA/CODIUM ne prate dist, FILMIUM prati — rebuildovan i committovan).
- Mrtav kod ostavljen van obima: `CellAssistantChat` (stari inline asistent),
  `useSmartLayout` gde je bio samo za chat.
- Sledeće: D (vektorski RAG ingest atoma+loga) — pauziran zbog ove unifikacije,
  sada se nastavlja. Spec/plan: `docs/superpowers/specs|plans/2026-09-16-agent-chat-unifikacija*`.
