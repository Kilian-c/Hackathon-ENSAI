"""Tests de démarrage : à remplacer au fur et à mesure par test_loader.py, test_engine.py, etc."""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from backend.main import app

EXPERIMENTS = sorted((Path(__file__).parent.parent / "experiments").glob("*.yaml"))


def test_health():
    assert TestClient(app).get("/api/health").json() == {"status": "ok"}


def test_reference_yamls_parse():
    assert len(EXPERIMENTS) >= 3
    for path in EXPERIMENTS:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == 1, path.name
        assert data["id"], path.name
