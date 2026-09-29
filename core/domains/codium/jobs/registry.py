# core/domains/codium/jobs/registry.py
# ==========          REGISTAR POSLOVA — CODIUM          ==========
"""Modulski singleton `REGISTRY` (v. core/cell/jobs.py). Registracija samo
pravi lagane objekte (Lock/Event) — NE pokrece nista pri uvozu (v. duh
"lenji importi runtime-a": boot ne sme da cheka na ovo)."""
from __future__ import annotations

from core.cell.jobs import JobRegistry
from core.domains.codium.jobs.atom_reindex import AtomReindexJob

REGISTRY = JobRegistry(domain="codium")
REGISTRY.register(AtomReindexJob())
