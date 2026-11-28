"""Point d'entrée FastAPI (R1). Routes dans backend/api/routes.py.

Version locale de secours sur un seul port : si `frontend/dist` existe (après `npm run build`, construit
SANS `VITE_API_URL`), le moteur sert aussi l'interface sur `/` ; les routes `/api/...` restent prioritaires.
Sans ce dossier, rien ne change : l'interface tourne à part (Vite en local, Cloudflare en ligne).
`CRASHTEST_DIST` désigne un autre dossier.
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import registry
from backend.api.routes import router

DEFAULT_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def mount_frontend(application: FastAPI, dist: Path) -> bool:
    """Sert l'interface construite sur `/`, après les routes de l'API. Faux si `dist/index.html` manque."""
    if not (dist / "index.html").is_file():
        return False
    # Monté en dernier : une route déclarée avant (toutes celles de /api) gagne toujours.
    application.mount("/", StaticFiles(directory=dist, html=True), name="interface")
    return True


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Charge les expériences au démarrage (environ 3 s) : sinon le premier clic d'un utilisateur les paie.
    Un YAML officiel invalide fait échouer le démarrage, avec son numéro de ligne."""
    registry.official()
    registry.content_digest()
    yield


def create_app(dist: Path | None = None) -> FastAPI:
    application = FastAPI(title="Crash-Test", lifespan=lifespan)

    # Domaine Cloudflare de l'interface, séparé par des virgules (ex. "https://crash-test.pages.dev").
    origins = [o for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
    application.add_middleware(
        CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"]
    )

    application.include_router(router)

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if dist is None:
        dist = Path(os.environ.get("CRASHTEST_DIST", DEFAULT_DIST))
    if mount_frontend(application, dist):
        logging.getLogger("uvicorn.error").info("Interface servie sur / (depuis %s).", dist)
    return application


app = create_app()
