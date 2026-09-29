---
id: codium-2026-09-16-agent-dock-unifikacija
type: log
domain: codium
title: 2026-09-16-agent-dock-unifikacija
tags:
- dev-log
- entries
---

# 2026-09-16 — CODIUM Agent dock: dole-centar, uklonjen „Kurator"

Cilj: komandni Agent chat kao jedan dock, fiksiran dole-centar, na SVIM
stranicama (standalone + CORE embed), umesto zasebne „/codium/kurator" stranice.
Ime „CODIUM Agent" — reč „Kurator" uklonjena (to je samo FILMIUM ime agenta).

## Urađeno

`CodiumKuratorChat` (stranica) prebačen u `CodiumAgentDock` (12 persona,
predlog/potvrda, navigate, appendReply) u `.agent-dock` dole-centar kontejner sa
skupljanjem. Montiran jednom preko `cellAgentDock` slota (`CellNav.AgentDock` →
`CellShell` + `CellApp` `ChromelessContent`). Uklonjeni: ruta `/codium/kurator`,
nav stavka „Kurator", stranica `CodiumKuratorChat.tsx`. Naslovi settings panela
„Kurator" → „CODIUM Agent". Dodat `forwardRef`/`appendReply` u `CoreChat` +
`kind`+`reply` u `CodiumExecutors.apply` (confirm feedback, paritet sa KALIMA).
Reflow: `useDockHeightVar` (var na :root) + `agent-dock.css` cap.

## Provereno

`tsc` čist, `npm run build` čist, py 16 prošao. Nema vidljivog „Kurator"
(ostaju backend `/codium/curator/*`, identifikatori, css ime). Ćelija (8784)
nije živo proverena — kod simetričan KALIMA (verifikovana uživo).

## Napomene

Deo cross-repo „Agent Chat Unifikacija". Za živ chat restart ćelije.
