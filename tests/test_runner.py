"""Tests de `run()` (runner.py) sur les 3 expériences P0 : forme du résultat, vues, équation, déterminisme."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.contracts import EngineState, RunResult
from backend.engine import runner
from backend.engine.loader import load_experiment_file

EXP = Path(__file__).resolve().parent.parent / "experiments"


def _spec(name: str):
    return load_experiment_file(EXP / f"{name}.yaml")


def test_regression_result_matches_contract() -> None:
    res = runner.run(_spec("regression_lineaire"), EngineState(hypotheses={"hetero": 0.8}))
    RunResult.model_validate(res.model_dump())
    cov = res.measures["coverage"]
    assert cov.states["ols"] == "broken" and cov.states["hc3"] == "ok"
    assert res.equation.terms["var"].violated_by == ["hetero"]
    ic = next(v for v in res.views if v.id == "ic")
    assert (ic.shown, ic.total) == (100, 500)
    est = next(s for s in ic.series if s.slot == "est")
    assert est.low and est.high and est.hit and len(est.x) == 100
    assert not any(s.slot in ("low", "high", "hit") for s in ic.series)
    nuage = next(v for v in res.views if v.id == "nuage")
    assert {s.role for s in nuage.series} >= {"data", "method", "reference"}


def test_healthy_state_has_no_violation() -> None:
    res = runner.run(_spec("regression_lineaire"))
    assert res.equation.terms["var"].violated_by == []
    assert res.measures["coverage"].states["ols"] == "ok"


def test_student_target_base_and_draw_log() -> None:
    res = runner.run(_spec("test_student"), EngineState(hypotheses={"loi": "cauchy"}))
    power = res.measures["power"]
    assert power.target == "base" and power.baseline["student"] > power.values["student"]
    assert res.draw_log is not None
    assert [s.method for s in next(v for v in res.views if v.id == "echantillon").series] == [
        "student",
        "student",
    ]


def test_pendulum_truth_and_time_axis() -> None:
    res = runner.run(_spec("pendule_euler"), EngineState(hypotheses={"pas": 0.3}))
    view = next(v for v in res.views if v.id == "trajectoire")
    assert view.axes.x == [0.0, 5.0]
    assert any(s.role == "truth" for s in view.series)
    assert res.repeat_used == 1


@pytest.mark.parametrize("name", ["regression_lineaire", "test_student"])
def test_same_state_same_result_byte_for_byte(name: str) -> None:
    spec = _spec(name)
    a = runner.run(spec).model_dump(exclude={"compute_ms"})
    runner._CACHE.clear()
    b = runner.run(spec).model_dump(exclude={"compute_ms"})
    assert a == b


def test_slider_does_not_shift_draws() -> None:
    """Un curseur ne change pas la graine : la Référence reste identique d'un état à l'autre."""
    spec = _spec("regression_lineaire")
    a = runner.run(spec, EngineState(hypotheses={"hetero": 0.2}))
    b = runner.run(spec, EngineState(hypotheses={"hetero": 0.8}))
    assert a.measures["coverage"].baseline == b.measures["coverage"].baseline
