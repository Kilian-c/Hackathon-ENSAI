"""Tests des routes P0 : liste, lecture, `/api/run` (officielle ou YAML brut), erreurs en français."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.contracts import RunResult
from backend.main import app

client = TestClient(app)
YAML = Path(__file__).resolve().parent.parent / "experiments" / "archives" / "test_student.yaml"


def test_list_and_filter() -> None:
    all_ = client.get("/api/experiments").json()
    assert {e["id"] for e in all_} >= {"regression-lineaire", "multicolinearite"}
    assert "test-student" not in {e["id"] for e in all_}  # archivée : hors de l'accueil
    assert client.get("/api/experiments", params={"q": "zzz"}).json() == []
    first = all_[0]
    assert all(
        e["discipline"] == first["discipline"]
        for e in client.get("/api/experiments", params={"discipline": first["discipline"]}).json()
    )


def test_get_spec_and_404() -> None:
    spec = client.get("/api/experiments/multicolinearite").json()
    assert spec["id"] == "multicolinearite" and "hypotheses" in spec
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
        "/api/run", json={"experiment_id": "multicolinearite", "state": {"hypotheses": {"nimporte": 1}}}
    )
    assert bad_state.status_code == 422 and "Hypothèse inconnue" in bad_state.json()["detail"]
    bad_yaml = client.post("/api/run", json={"raw_content": "schema_version: 1\nid: [\n"})
    assert bad_yaml.status_code == 422 and bad_yaml.json()["detail"]["issues"]
    both = client.post("/api/run", json={"experiment_id": "multicolinearite", "raw_content": "x"})
    assert both.status_code == 422


# --- POST /api/training/session (CLAUDE.md, section 12) -------------------------------------------------


def _session(**body):
    r = client.post("/api/training/session", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_training_count_is_min_of_10_and_available() -> None:
    from backend.api.registry import official
    from backend.engine.training import _pool, select_experiments

    for filter_ in ("toutes", "regression-lineaire", "tests-multiples"):
        available = len(_pool(select_experiments(official(), filter_)))
        s = _session(filter=filter_, seed=11)
        assert len(s["questions"]) + len(s["dropped"]) >= min(10, available)
        assert len(s["questions"]) <= min(10, available)
    assert len(_session(filter="tests-multiples", count=2, seed=11)["questions"]) == 2


def test_training_misconception_never_twice() -> None:
    for seed in (1, 2, 3):
        s = _session(filter="toutes", seed=seed)
        ids = [q["qid"].rsplit("/", 1)[0] for q in s["questions"] if q["type"] == "misconception"]
        assert len(ids) == len(set(ids))
        qids = [q["qid"] for q in s["questions"]]
        assert len(qids) == len(set(qids))


def test_training_seed_is_returned_when_absent() -> None:
    s = _session(filter="theoreme-central-limite")
    assert isinstance(s["seed"], int) and s["id"] == f"theoreme-central-limite~{s['seed']}"


def test_training_same_seed_same_series() -> None:
    a = _session(filter="regression-lineaire", seed=99)
    b = _session(filter="regression-lineaire", seed=99)
    assert a == b
    # Une autre graine change la série (sur « toutes », assez de questions pour que l'ordre diffère).
    d = _session(filter="toutes", seed=99)
    e = _session(filter="toutes", seed=100)
    assert [q["qid"] for q in d["questions"]] != [q["qid"] for q in e["questions"]]


def test_training_unknown_filter_is_french_422() -> None:
    r = client.post("/api/training/session", json={"filter": "nexiste-pas"})
    assert r.status_code == 422 and "Aucune expérience" in r.json()["detail"]
