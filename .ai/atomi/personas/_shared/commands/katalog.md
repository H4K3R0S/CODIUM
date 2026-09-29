---
id: codium-command-katalog
type: command
domain: codium
title: Katalog komandi
summary: Daj `name` (ime repozitorijuma ili pipeline-a) za komande koje ga traže.
status: stable
keywords:
- katalog
- komandi
tags: []
source_path: .ai/atomi/personas/_shared/commands/katalog.md
atom_kreiran: 2026-09-16 05:13:56-04:00
atom_azuriran: 2026-09-16 05:13:56-04:00
---

Pick EXACTLY ONE command when the user wants a repo/pipeline action or a screen.
Give the exact input (`name` = a repository or pipeline name). Never invent commands.

## How to choose
- List repositories / pipelines → **list_repos** / **list_pipelines**
- Status of a repository → **repo_status**
- Sync/pull a repository (CHANGES it) → **sync_repo** (confirm first)
- Run a pipeline (CHANGES it) → **run_pipeline** (confirm first)
- Open a repository's page → **open**

## Inspect — read-only
- list_repos {} — list repositories.
- list_pipelines {} — list pipelines.
- repo_status {name} — status of a repository.

## Act — WRITE, ask for confirmation first
- sync_repo {name} — sync/pull a repository.
- run_pipeline {name} — run a pipeline.

## Navigate
- open {name} — open a repository's page.
- open_second_brain_map {} — open the Second Brain MAPS map (rings/circle/areas/links/timeline/orbit + other systems' spheres).
