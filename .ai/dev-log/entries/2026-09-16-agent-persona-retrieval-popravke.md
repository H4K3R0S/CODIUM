---
id: codium-2026-09-16-agent-persona-retrieval-popravke
type: log
domain: codium
title: 2026-09-16-agent-persona-retrieval-popravke
tags:
- dev-log
- entries
edges:
- type: preceded_by
  target: codium-2026-09-16-agent-chat-unifikacija
  weight: 0.8
---

# 2026-09-16 — Agent popravke posle živog CODIUM testa (persona u prompt, retrieval, model)

Posle živog testa CODIUM agenta (Postgres+Ollama gore) izašla su četiri
nalaza; sva popravljena i verifikovana uživo.

## Urađeno

**A — Persona ulazi u system prompt.** Kanon `core/cell/curator/agent.py`:
`_ask_model` sada prefiksuje sistemski prompt telom aktivne persone
(`_sa_personom`). Ranije se persona učitavala (`AtomLoader.persona()`) ali NIJE
ulazila u prompt — prompt je bio samo bazna instrukcija + katalog komandi, pa
izbor persone NIJE menjao ponašanje (multi-persona bila čista kozmetika).
Kopirano byte-identično u KALIMA/CODIUM; FILMIUM (bespoke `intent_router`)
dobio ekvivalentni `_sa_personom`. Nedostatak persona.md je bezopasan.

**Rec2 — Retrieval samo agent namespace.** `/api/v1/rag/retrieve` sada traži
ISKLJUČIVO `cell:<domain>` (ne više i `global`). U `global` je ranije seedovana
cela repo baza (E-planovi, docs) koja je ranking-om gušila agentove atome/logove;
agent je dobijao repo dokumentaciju umesto svog znanja. Sad vraća persona/komande/
tools atome + (kasnije) prošle tačne interakcije.

**D — Podrazumevani model.** Runtime fallback `_MANIFEST.ai_curator_model or
"qwen2.5"` → `"qwen2.5:7b"` u sve tri ćelije. „qwen2.5" (bez taga) nije povučen
u Ollami (samo `:7b`/`:14b`), pa bi agent pao na prvu komandu ako model nije
podešen. (Korisnik i dalje bira model u Settings; ovo je samo zdrav fallback.)

## Provereno (uživo, CODIUM, qwen2.5:7b + pgvector)

- **Intent prepoznavanje:** „izlistaj repozitorijume"→list_repos,
  „sinhronizuj repo X"→sync_repo, „pokreni pipeline Y"→run_pipeline, itd.
- **Persona u promptu:** presretnut system prompt — bezbednjak („stručnjak za
  sajber bezbednost") vs graditelj („glavni programer") sada dobijaju RAZLIČIT
  prompt (ranije identičan).
- **Retrieval:** za „sinhronizuj repozitorijum" vraća `agent-codium-tool-repo`,
  `agent-codium-command-katalog`, `agent-codium-debager` (agent znanje), ne više
  repo E-plan docs.
- **Write-confirm (Rec4 demo, stub izvršilac, bez diranja realne DB):**
  proposal → confirm_token izdat (ništa upisano) → confirm → apply (tek tada
  upis) → ponovni token odbijen (single-use). Write-safety airtight.
- Testovi: CORE curator+rag 13, KALIMA 15, CODIUM 2, FILMIUM 59 (`-k curator`).

## Napomene

- CODIUM ćelija DB je prazan (0 repo/pipeline) — pun write-confirm nad realnim
  podacima čeka seed; mehanizam dokazan stub-om.
- Za živ end-to-end u ćelijama: CORE API na `core_url` mora da radi (ćelijski
  `HttpRetriever` gađa CORE); test je koristio mini RAG server (samo rag router)
  da izbegne CORE auto-launch svih ćelija.
- Commits: CORE 69bcd09, KALIMA 6ed385d, CODIUM a1fb824, FILMIUM 613bb3c.
