"""Méthodes `formula_*` : une méthode écrite dans le YAML égale son équivalent Python."""

from pathlib import Path

import numpy as np
import pytest

from backend.contracts import EngineState
from backend.engine import runner
from backend.engine.expr import BASE_FUNCTIONS
from backend.engine.loader import load_experiment
from backend.engine.method_contract import get_method
from backend.methods.formula import formula_estimate, formula_interval, formula_test

RNG = np.random.default_rng(0)
SOURCE = (Path(__file__).resolve().parent.parent / "experiments" / "moyenne_mediane.yaml").read_text(
    encoding="utf-8"
)


def _as_formulas() -> str:
    mean = 'args: { est: "mean(x, axis=1)", truth: 0 }'
    median = 'args: { est: "quantile(x, 0.5, axis=1)", truth: 0 }'
    text = SOURCE.replace("call: statistic", "call: formula_estimate")
    text = text.replace('args: { x: x, kind: "mean" }', mean)
    text = text.replace('args: { x: x, kind: "median" }', median)
    return text.replace("reps.stat", "reps.est")


@pytest.mark.parametrize("state", [{}, {"hypotheses": {"extreme": 1.0}}, {"params": {"n": 100}}])
def test_formula_experiment_matches_the_statistic_experiment(state) -> None:
    reference = runner.run(load_experiment(SOURCE), EngineState(**state))
    written = runner.run(load_experiment(_as_formulas()), EngineState(**state))
    for mid, measure in reference.measures.items():
        assert written.measures[mid].values == pytest.approx(measure.values, abs=1e-12)
        assert written.measures[mid].states == measure.states


def test_formula_estimate_error_and_scalar_broadcast() -> None:
    result = formula_estimate(est=np.array([1.0, 2.0, 4.0]), truth=1.0, rng=RNG)
    assert result.reps["error"].tolist() == [0.0, 1.0, 3.0]
    assert np.isnan(formula_estimate(est=np.array([1.0, 2.0]), rng=RNG).reps["error"]).all()


def test_formula_test_by_pvalue_or_critical_value() -> None:
    by_p = formula_test(pvalue=np.array([0.01, 0.2]), alpha=0.05, rng=RNG)
    assert by_p.reps["reject"].tolist() == [True, False] and np.isnan(by_p.reps["stat"]).all()
    by_c = formula_test(stat=np.array([-3.0, 1.0]), critical=1.96, rng=RNG)
    assert by_c.reps["reject"].tolist() == [True, False] and np.isnan(by_c.reps["pvalue"]).all()
    with pytest.raises(ValueError, match="pvalue"):
        formula_test(stat=np.array([1.0]), rng=RNG)


def test_formula_interval_hit_and_width() -> None:
    result = formula_interval(
        est=np.array([0.0, 0.0]), low=np.array([-1.0, 0.5]), high=np.array([1.0, 2.0]), truth=0.0, rng=RNG
    )
    assert result.reps["hit"].tolist() == [True, False] and result.reps["width"].tolist() == [2.0, 1.5]


def test_formula_must_reduce_the_observation_axis_with_a_french_error() -> None:
    with pytest.raises(ValueError, match="une valeur par répétition"):
        formula_estimate(est=np.ones((3, 5)), rng=RNG)
    bad = _as_formulas().replace('"mean(x, axis=1)"', '"x"')
    with pytest.raises(runner.RunError, match="une valeur par répétition"):
        runner.run(load_experiment(bad))


def test_registered_with_the_contract_and_new_functions_available() -> None:
    for name in ("formula_estimate", "formula_test", "formula_interval"):
        assert get_method(name).provides["reps"]
    x = np.array([[3.0, 1.0, 2.0]])
    assert BASE_FUNCTIONS["sort"](x, axis=1).tolist() == [[1.0, 2.0, 3.0]]
    assert BASE_FUNCTIONS["cumprod"](x, axis=1).tolist() == [[3.0, 3.0, 6.0]]
    assert BASE_FUNCTIONS["quantile"](x, 0.5, axis=1).tolist() == [2.0]
