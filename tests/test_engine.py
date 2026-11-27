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


# --- Évaluateur d'expressions (expr.py) --------------------------------------------------------------------

import numpy as np  # noqa: E402

from backend.engine.expr import Env, ExprError, Layered, ar1, compile_expr, evaluate, ols_match  # noqa: E402

ENV = Env(
    variables={"x": np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), "idx": np.arange(3)},
    namespaces={
        "p": {"n": 25, "beta1": 1.5, "flag": True},
        "h": {"hetero": 0.5, "loi": "cauchy", "add_leverage": True},
        "m": {"power": Layered({"student": 0.1, "wilcoxon": 0.4}, default=0.1)},
        "s": {"power": Layered({"student": "broken"}, default="broken")},
    },
    option=lambda hid: f"option:{hid}",
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("p.n * 2 + 1", 51),
        ("10 ** (-3.5 + 2.5 * h.hetero)", 10 ** (-3.5 + 2.5 * 0.5)),
        ("h.loi == 'cauchy' and p.n >= 5", True),
        ("m.power < 0.5 and s.power == 'broken'", True),
        ("m.power.wilcoxon > m.power.student", True),
        ("where(p.flag, 1.0, 2.0)", 1.0),
        ("sqrt(16) + abs(-2) + pi * 0", 6.0),
        ("@h.relation", "option:relation"),
        ("-p.n if h.add_leverage else 0", -25),
    ],
)
def test_expr_scalars(source, expected):
    assert evaluate(source, ENV) == pytest.approx(expected)


def test_expr_arrays():
    lev = evaluate("h.add_leverage & (idx == 0)", ENV)
    assert lev.tolist() == [True, False, False]
    assert evaluate("where(idx == 0, 6.0, x)", ENV).shape == (2, 3)
    assert evaluate("x > 2 and x < 6", ENV).tolist() == [[False, False, True], [True, True, False]]


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os')",
        "x.__class__",
        "p._secret",
        "[i for i in x]",
        "lambda: 1",
        "open('f')",
        "x[0]",
        "(1).real",
        "p.n.real",
        "exec('1')",
        "a if b else c; d",
        "f'{p.n}'",
        "p",
        "x @ x",
        "sqrt(x, out=x)",
        "2 ** 101",
        "10 ** (p.n * 5)",
        "a" * 301,
        "",
    ],
)
def test_expr_rejects_dangerous_or_invalid(source):
    with pytest.raises(ExprError):
        evaluate(source, ENV)


def test_expr_names_are_collected():
    c = compile_expr("where(h.autocorr, ar1(x_raw, 0.7), x_raw) + @h.relation + p.n + law('normal')")
    assert c.names == {"x_raw"}
    assert ("h", "autocorr") in c.refs and ("p", "n") in c.refs
    assert c.options == {"relation"}
    assert c.calls == {"where", "ar1", "law"}
    assert c.strings == [("law", "normal")]


def test_expr_unknown_name_and_division():
    with pytest.raises(ExprError, match="inconnu"):
        evaluate("p.absent", ENV)
    with pytest.raises(ExprError, match="Division par zéro"):
        evaluate("1 / 0", ENV)


def test_ar1_is_stationary_and_keeps_first_value():
    base = np.random.default_rng(0).standard_normal((2000, 200))
    z = ar1(base, 0.7)
    assert np.allclose(z[:, 0], base[:, 0])
    assert z[:, 50:].var() == pytest.approx(1.0, abs=0.05)
    assert np.corrcoef(z[:, 100], z[:, 101])[0, 1] == pytest.approx(0.7, abs=0.05)
    with pytest.raises(ExprError):
        ar1(base, 1.0)


def test_ols_match_gives_exact_summary():
    rng = np.random.default_rng(1)
    x = rng.standard_normal((5, 80))
    y = 3 * x**2 + rng.standard_normal((5, 80))
    out = ols_match(x, y, 1.0, 1.5, 0.67)
    for xi, yi in zip(x, out, strict=True):
        slope, intercept = np.polyfit(xi, yi, 1)
        assert slope == pytest.approx(1.5, abs=1e-9)
        assert intercept == pytest.approx(1.0, abs=1e-9)
        assert np.corrcoef(xi, yi)[0, 1] ** 2 == pytest.approx(0.67, abs=1e-9)


# --- Vérification des expressions au chargement ----------------------------------------------------


def test_expression_checks_report_lines():
    typo = REGRESSION.replace("ar1(x_raw, 0.7), x_raw)\"", "ar1(x_rw, 0.7), x_raw)\"")
    issue = _first_issue(typo)
    assert "x_rw" in issue.message and issue.path == "generator.variables.x_base.expr"
    issue = _first_issue(REGRESSION.replace("law('normal')", "law('gamma')"))
    assert "Loi inconnue" in issue.message
    issue = _first_issue(REGRESSION.replace("m.bp_pvalue > 0.05", "m.nope > 0.05"))
    assert issue.path == "challenges[0].when"
    issue = _first_issue(REGRESSION.replace('"@h.error_law"', '"eval(1)"'))
    assert "eval" in issue.message


def test_variable_cycle_is_refused():
    issue = _first_issue(REGRESSION.replace("law('normal')\" }", "x + 1\" }", 1))
    assert "Cycle" in issue.message


# --- État canonique et générateur `random` ------------------------------------------------------------------

from backend.contracts import EngineState  # noqa: E402
from backend.engine.generators.random_world import generate  # noqa: E402
from backend.engine.state import StateError, healthy, resolve_state  # noqa: E402

REG_SPEC = load_experiment(REGRESSION)


def world_for(hypotheses=None, params=None, seed=42, points=None, spec=REG_SPEC):
    state = resolve_state(
        spec,
        EngineState(params=params or {}, hypotheses=hypotheses or {}, seed=seed, extra_points=points or []),
    )
    return generate(spec, state)


def test_state_defaults_rounding_and_hash():
    a = resolve_state(REG_SPEC, EngineState(hypotheses={"hetero": 0.30000000000000004}))
    explicit = EngineState(params={"n": 150}, hypotheses={"hetero": 0.3, "error_law": "normal"})
    b = resolve_state(REG_SPEC, explicit)
    assert a.hypotheses["hetero"] == 0.3 and a.hash() == b.hash() and len(a.hash()) == 16
    assert resolve_state(REG_SPEC, EngineState(seed=7)).hash() != a.hash()
    ref = healthy(REG_SPEC, resolve_state(REG_SPEC, EngineState(hypotheses={"hetero": 0.9}, seed=3)))
    assert ref.hypotheses["hetero"] == 0.0 and ref.seed == 3


@pytest.mark.parametrize(
    "state",
    [
        EngineState(params={"zzz": 1}),
        EngineState(params={"n": 5000.0}),
        EngineState(hypotheses={"hetero": 1.5}),
        EngineState(hypotheses={"error_law": "gamma"}),
        EngineState(hypotheses={"add_leverage": 1.0}),
    ],
)
def test_state_errors(state):
    with pytest.raises(StateError):
        resolve_state(REG_SPEC, state)


def test_generator_shapes_and_determinism():
    w1, w2 = world_for(), world_for()
    assert (w1.repeat, w1.n) == (500, 150)
    assert all(v.shape == (500, 150) for v in w1.variables.values())
    assert all(np.array_equal(w1.variables[k], w2.variables[k]) for k in w1.variables)
    assert not np.array_equal(w1.variables["x"], world_for(seed=43).variables["x"])
    assert world_for(params={"n": 30.0}).variables["y"].shape == (500, 30)


def test_generator_shares_draws_across_hypotheses():
    sain, hetero = world_for(), world_for({"hetero": 0.8})
    assert np.array_equal(sain.variables["x"], hetero.variables["x"])
    assert np.array_equal(sain.variables["base_eps"], hetero.variables["base_eps"])
    assert not np.allclose(sain.variables["y"], hetero.variables["y"])
    # La variance de l'erreur croît avec x quand hetero > 0.
    x, eps = hetero.variables["x"], hetero.variables["eps"]
    assert eps[x > 1].std() > 2 * eps[x < -1].std()


def test_generator_options_leverage_and_autocorr():
    expo = world_for({"error_law": "exponential"}).variables["base_eps"]
    assert expo.min() > -1.01 and expo.max() > 4  # asymétrique : loi exponentielle centrée réduite
    lev = world_for({"add_leverage": True}).variables
    assert lev["lev"][:, 0].all() and not lev["lev"][:, 1:].any() and (lev["x"][:, 0] == 6.0).all()
    quad = world_for({"relation": "quadratic"}).variables["signal"]
    x = world_for().variables["x"]
    assert np.allclose(quad, x + 0.5 * (x**2 - 1))
    ar = world_for({"autocorr": True}).variables["x"]
    assert np.corrcoef(ar[:, 1:].ravel(), ar[:, :-1].ravel())[0, 1] == pytest.approx(0.7, abs=0.03)


def test_generator_extra_points_only_in_current_state():
    pts = [{"x": 4.2, "y": -2.0}, {"x": 5.0, "y": 1.0}]
    w = world_for(points=pts)
    assert (w.n, w.variables["x"].shape, w.variables["y"].shape) == (152, (500, 152), (500, 152))
    assert (w.variables["x"][:, -2] == 4.2).all() and (w.variables["y"][:, -1] == 1.0).all()
    state = resolve_state(REG_SPEC, EngineState(extra_points=pts))
    assert generate(REG_SPEC, healthy(REG_SPEC, state)).n == 150
    with pytest.raises(ExprError):
        world_for(points=[{"x": 1.0}])
