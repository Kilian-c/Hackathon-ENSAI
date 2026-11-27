"""Tests du moteur (R1). Pour l'instant : schéma YAML et chargeur."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts import (
    RunRequest,
    RunResult,
    SweepRequest,
    SweepResult,
    TrainingRequest,
    TrainingSessionResponse,
)
from backend.engine.loader import ExperimentError, load_experiment, load_experiment_file

EXPERIMENTS = sorted((Path(__file__).parent.parent / "experiments").glob("*.yaml"))
REGRESSION = (Path(__file__).parent.parent / "experiments" / "regression_lineaire.yaml").read_text(
    encoding="utf-8"
)


@pytest.mark.parametrize("path", EXPERIMENTS, ids=lambda p: p.name)
def test_reference_yamls_load(path):
    spec = load_experiment_file(path)
    assert spec.schema_version == 1
    assert sum(m.primary for m in spec.measures.values()) == 1


def _first_issue(text: str):
    with pytest.raises(ExperimentError) as info:
        load_experiment(text)
    return info.value.issues[0]


def test_unknown_field_reports_line():
    issue = _first_issue(REGRESSION.replace('level: "1A/2A"', 'level: "1A/2A"\nbidule: 3'))
    assert (issue.line, issue.path) == (6, "bidule")


def test_unknown_schema_version():
    issue = _first_issue(REGRESSION.replace("schema_version: 1", "schema_version: 2"))
    assert issue.line == 1


def test_unknown_repair_reports_line():
    issue = _first_issue(REGRESSION.replace("repairs: [hetero, relation]", "repairs: [hetero, fantome]"))
    assert issue.path == "methods[1].repairs[1]"
    assert issue.line == 147


def test_repeat_cap():
    issue = _first_issue(REGRESSION.replace("repeat: 500", "repeat: 5000"))
    assert issue.path.endswith("repeat")


def test_oversized_file():
    issue = _first_issue(REGRESSION + "#" * 70_000)
    assert issue.line is None


# --- Contrats d'API : les exemples de l'annexe C du cahier doivent passer tels quels -------------------

CAHIER_RUN_RESULT = {
    "schema_version": 1,
    "state_hash": "a3f09c1e7b2d4e88",
    "methods": [
        {"id": "ols", "role": "method", "label": "MCO classique (IC à 95 %)"},
        {"id": "hc3", "role": "correction", "label": "HC3", "explain": "..."},
        {"id": "nw", "role": "alternative", "label": "Newey-West", "explain": "..."},
    ],
    "measures": {
        "coverage": {
            "label": "Taux de couverture réel", "unit": "%", "scale": 100, "decimals": 1,
            "primary": True, "target": 0.95, "direction": "below",
            "ok_within": 0.03, "broken_beyond": 0.10,
            "values": {"ols": 0.740, "hc3": 0.946, "nw": 0.941},
            "mc_se": {"ols": 0.020, "hc3": 0.010, "nw": 0.011},
            "states": {"ols": "broken", "hc3": "ok", "nw": "ok"},
            "texts": {"ols": "Intervalle non fiable (74,0 %) : ...", "hc3": "...", "nw": "..."},
            "baseline": {"ols": 0.952, "hc3": 0.950, "nw": 0.948},
        }
    },
    "equation": {"terms": {"var": {"violated_by": ["hetero"]}}},
    "challenges": [{"id": "trap-bp-test", "passed": False}],
    "views": [
        {
            "id": "nuage", "type": "scatter", "title": "Nuage et droite ajustée",
            "axes": {"x": [-3.1, 6.4], "y": [-9.8, 11.4]}, "shown": 151, "total": 151, "clipped": 0,
            "series": [
                {"id": "nuage.xy.gen", "slot": "xy", "role": "data", "label": "Obs.", "x": [0.1], "y": [1.0]}
            ],
        }
    ],
    "draw_log": None,
    "invalid_rate": {"ols": 0.0, "hc3": 0.0, "nw": 0.0},
    "warnings": [{"code": "repeat_reduced", "text": "Estimation sur 200 tirages pour tenir le délai."}],
    "repeat_used": 500,
    "compute_ms": 26.4,
}


def test_run_request_from_cahier():
    req = RunRequest.model_validate(
        {
            "experiment_id": "regression-lineaire",
            "raw_content": None,
            "state": {
                "params": {"n": 150, "beta1": 1.5},
                "hypotheses": {"hetero": 0.8, "error_law": "normal", "add_leverage": False},
                "extra_points": [{"x": 4.2, "y": -2.0}],
                "seed": 42,
            },
        }
    )
    assert req.state.seed == 42


def test_run_request_needs_exactly_one_source():
    with pytest.raises(ValidationError):
        RunRequest.model_validate({"state": {}})
    with pytest.raises(ValidationError):
        RunRequest.model_validate({"experiment_id": "a", "raw_content": "schema_version: 1"})


def test_extra_points_capped():
    with pytest.raises(ValidationError):
        RunRequest.model_validate({"experiment_id": "a", "state": {"extra_points": [{"x": 0.0}] * 21}})


def test_run_result_from_cahier():
    result = RunResult.model_validate(CAHIER_RUN_RESULT)
    assert result.measures["coverage"].states["ols"] == "broken"
    assert result.model_dump(mode="json")["views"][0]["series"][0]["id"] == "nuage.xy.gen"


def test_sweep_from_cahier():
    SweepRequest.model_validate(
        {
            "experiment_id": "regression-lineaire",
            "state": {"params": {"n": 150}, "hypotheses": {"hetero": 0.8}, "seed": 42},
            "axes": [{"target": "h.hetero"}],
            "measure": "coverage",
        }
    )
    result = SweepResult.model_validate(
        {
            "axes": [{"target": "h.hetero", "values": [0, 0.1, 0.2], "labels": ["0", "0,1", "0,2"]}],
            "measure": "coverage",
            "values": {"ols": [0.951, 0.948, 0.937], "hc3": [0.949, 0.950, 0.948]},
            "mc_se": {"ols": [0.010, 0.010, 0.011], "hc3": [0.010, 0.010, 0.010]},
            "states": {"ols": ["ok", "ok", "ok"], "hc3": ["ok", "ok", "ok"]},
            "critical": {"ols": {"warning_at": 0.27, "broken_at": 0.58}, "hc3": None},
            "target": 0.95, "ok_within": 0.03, "broken_beyond": 0.10, "direction": "below",
            "current": {"h.hetero": 0.8},
            "repeat_used": 500, "reduced": False, "compute_ms": 2310,
        }
    )
    assert result.critical["hc3"] is None


def test_sweep_two_axes_grid():
    result = SweepResult.model_validate(
        {
            "axes": [
                {"target": "h.hetero", "values": [0, 1], "labels": ["0", "1"]},
                {"target": "p.n", "values": [30, 100], "labels": ["30", "100"]},
            ],
            "measure": "coverage",
            "values": {"ols": [[0.9, 0.8], [0.95, 0.7]]},
            "current": {"h.hetero": 0.0, "p.n": 30},
            "repeat_used": 200, "compute_ms": 1.0,
        }
    )
    assert result.values["ols"][1][1] == 0.7


def test_training_request_defaults():
    req = TrainingRequest.model_validate({})
    assert (req.filter, req.count, req.seed) == ("toutes", 10, None)
    TrainingRequest.model_validate({"filter": "discipline:statistique", "count": 3, "seed": 123})
    with pytest.raises(ValidationError):
        TrainingRequest.model_validate({"count": 11})
    with pytest.raises(ValidationError):
        TrainingRequest.model_validate({"filter": "Régression linéaire"})


def test_training_session_from_cahier():
    session = TrainingSessionResponse.model_validate(
        {
            "id": "regression-lineaire~123",
            "filter": "regression-lineaire",
            "seed": 123,
            "content_hash": "3f09c1",
            "questions": [
                {
                    "qid": "regression-lineaire/reg-q2-diag/0",
                    "experiment_id": "regression-lineaire",
                    "type": "diagnostic_auto",
                    "prompt": "Analysez le graphique des résidus ci-dessous.",
                    "initial_view": {"id": "residus", "type": "residuals", "title": "Résidus"},
                    "hypothesis": "hetero",
                    "k": 2,
                    "confidence": {"guess": 0.5, "fair": 0.725, "sure": 0.95},
                    "choices": [
                        {"id": "c1", "label": "Hétéroscédasticité", "correct": True, "explain": "...",
                         "reveal": {"state": {"hypotheses": {"hetero": 0.9}}, "focus_view": "ic"}},
                        {"id": "c2", "label": "Point levier influent", "correct": False, "explain": "...",
                         "reveal": {"state": {"hypotheses": {"add_leverage": True}}}},
                    ],
                }
            ],
            "dropped": [{"experiment_id": "x", "question_id": "y", "reason": "verify a échoué 5 fois"}],
        }
    )
    assert session.questions[0].choices[0].reveal.state.hypotheses["hetero"] == 0.9


FIXTURES = Path(__file__).parent.parent / "frontend" / "src" / "fixtures"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.name)
def test_fixtures_respect_contracts(path):
    kind = path.stem.rsplit(".", 1)[-1]
    model = {"run": RunResult, "sweep": SweepResult}.get(kind, TrainingSessionResponse)
    model.model_validate_json(path.read_text(encoding="utf-8"))
