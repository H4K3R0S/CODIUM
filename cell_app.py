"""Ulazna tačka ćelije codium.

Jedan proces služi ceo API domena i GUI build na istom originu. Putanje se
preusmeravaju i baza inicijalizuje PRE uvoza routera: `apps/api/dependencies.py`
pravi repozitorijume i servise već pri uvozu, pa bi inače gađali CORE putanje.
"""

import importlib
import sys
from pathlib import Path

CELL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(CELL_ROOT))

from core.cell.database import initialize_cell_database
from core.cell.manifest import load_cell_manifest
from core.cell.paths import apply_cell_paths
from core.cell.rag_bootstrap import ensure_cell_rag_db

MANIFEST = load_cell_manifest(CELL_ROOT)
apply_cell_paths(MANIFEST)
initialize_cell_database(MANIFEST)
# Sopstvena RAG baza celije (opciono, tolerantno).
ensure_cell_rag_db()

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from apps.api.routers import cell as cell_router
from apps.api.routers import cell_brain as cell_brain_router

API_ROUTERS = ('apps.api.routers.system', 'apps.api.routers.solve', 'apps.api.routers.codium', 'apps.api.routers.codium_agents', 'apps.api.routers.codium_ai', 'apps.api.routers.codium_analytics', 'apps.api.routers.codium_audit', 'apps.api.routers.codium_automations', 'apps.api.routers.codium_assistant', 'apps.api.routers.codium_deployments', 'apps.api.routers.codium_infrastructure', 'apps.api.routers.codium_integrations', 'apps.api.routers.codium_monitoring', 'apps.api.routers.codium_pipelines', 'apps.api.routers.codium_repositories', 'apps.api.routers.codium_approvals', 'apps.api.routers.codium_jobs', 'apps.api.routers.codium_health', 'apps.api.routers.voice')

# Ćelija NAMERNO nema CORS: GUI se servira sa istog origina, a CORE ćeliju
# zove iz svog Python servera (spec §8), ne iz browsera. Bez nepoznatih
# origina nijedna strana stranica ne sme da vozi ~90 nezaštićenih ruta za
# upis (kopiranje fajlova, torenti, brisanje, pokretanje VLC-a, persone).
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

app = FastAPI(title=MANIFEST.name, version=MANIFEST.domain_version)

# Provera `Host` zaglavlja zatvara DNS rebinding: stranica sa tuđeg domena
# koji se razreši na 127.0.0.1 i dalje šalje `Host: tudji.domen`, pa dobija 400.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

cell_router.bind_manifest(MANIFEST)
app.include_router(cell_router.router)
app.include_router(cell_brain_router.router)

for module_name in API_ROUTERS:
    app.include_router(importlib.import_module(module_name).router)

GUI_DIST = CELL_ROOT / "gui" / "dist"
if (GUI_DIST / "index.html").is_file():
    # Poslednje, da GUI nikad ne zakloni API rutu.
    app.mount("/", StaticFiles(directory=GUI_DIST, html=True), name="gui")
