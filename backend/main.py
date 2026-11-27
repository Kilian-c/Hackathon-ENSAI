"""Point d'entrée FastAPI (R1). Routes P0 dans backend/api/routes.py."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

app = FastAPI(title="Crash-Test")

# Domaine Cloudflare de l'interface, séparé par des virgules (ex. "https://crash-test.pages.dev").
_origins = [o for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"])

app.include_router(router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
