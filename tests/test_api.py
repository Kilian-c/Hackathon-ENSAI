"""Tests des routes P0 : liste, lecture, `/api/run` (officielle ou YAML brut), erreurs en français."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.contracts import RunResult
from backend.main import app

client = TestClient(app)
YAML = Path(__file__).resolve().parent.parent / "experiments" / "test_student.yaml"


def test_list_and_filter() -> None:
    all_ = client.get("/api/experiments").json()
    assert {e["id"] for e in all_} >= {"regression-lineaire", "test-student"}
    assert client.get("/api/experiments", params={"q": "zzz"}).json() == []
    first = all_[0]
    assert all(
        e["discipline"] == first["discipline"]
        for e in client.get("/api/experiments", params={"discipline": first["discipline"]}).json()
    )


def test_get_spec_and_404() -> None:
    spec = client.get("/api/experiments/test-student").json()
    assert spec["id"] == "test-student" and "hypotheses" in spec
    assert client.get("/api/experiments/nexiste-pas").status_code == 404


def test_run_official() -> None:
    body = {"experiment_id": "regression-lineaire", "state": {"hypotheses": {"hetero": 0.8}, "seed": 42}}
    r = client.post("/api/run", json=body)
    assert r.status_code == 200
    res = RunResult.model_validate(r.json())
    assert res.measures["coverage"].states["ols"] == "broken"
    assert client.post("/api/run", json=body).json()["state_hash"] == res.state_hash


def test_run_raw_content() -> None:
    r = client.post("/api/run", json={"raw_content": YAML.read_text(encoding="utf-8")})
    assert r.status_code == 200 and r.json()["methods"][0]["id"] == "student"


def test_run_errors_are_french_and_422() -> None:
    bad_state = client.post(
        "/api/run", json={"experiment_id": "test-student", "state": {"hypotheses": {"nimporte": 1}}}
    )
    assert bad_state.status_code == 422 and "Hypothèse inconnue" in bad_state.json()["detail"]
    bad_yaml = client.post("/api/run", json={"raw_content": "schema_version: 1\nid: [\n"})
    assert bad_yaml.status_code == 422 and bad_yaml.json()["detail"]["issues"]
    both = client.post("/api/run", json={"experiment_id": "test-student", "raw_content": "x"})
    assert both.status_code == 422
