"""Tests de `run()` (runner.py) sur les 3 expériences P0 : forme du résultat, vues, équation, déterminisme."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.contracts import EngineState, RunResult
from backend.engine import runner
from backend.engine.loader import load_experiment_file

EXP = Path(__file__).resolve().parent.parent / "experiments"
ARCHIVES = EXP / "archives"  # Student et pendule : hors de l'accueil, gardés pour tester le moteur


def _spec(name: str, folder: Path = EXP):
    return load_experiment_file(folder / f"{name}.yaml")


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
    res = runner.run(_spec("test_student", ARCHIVES), EngineState(hypotheses={"loi": "cauchy"}))
    power = res.measures["power"]
    assert power.target == "base" and power.baseline["student"] > power.values["student"]
    assert res.draw_log is not None
    assert [s.method for s in next(v for v in res.views if v.id == "echantillon").series] == [
        "student",
        "student",
    ]


def test_pendulum_truth_and_time_axis() -> None:
    res = runner.run(_spec("pendule_euler", ARCHIVES), EngineState(hypotheses={"pas": 0.3}))
    view = next(v for v in res.views if v.id == "trajectoire")
    assert view.axes.x == [0.0, 5.0]
    assert any(s.role == "truth" for s in view.series)
    assert res.repeat_used == 1


@pytest.mark.parametrize("name", ["regression_lineaire", "test_student"])
def test_same_state_same_result_byte_for_byte(name: str) -> None:
    spec = _spec(name, ARCHIVES if name == "test_student" else EXP)
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


def test_intervals_view_keeps_every_method_even_with_identical_estimates() -> None:
    """MCO et HC3 ont la même estimation de pente mais des intervalles différents."""
    res = runner.run(_spec("regression_lineaire"), EngineState(hypotheses={"hetero": 0.8}))
    ic = next(v for v in res.views if v.id == "ic")
    methods = [s.method for s in ic.series if s.slot == "est"]
    assert methods == ["ols", "hc3"]
    widths = [sum(h - lo for lo, h in zip(s.low, s.high, strict=True)) for s in ic.series if s.slot == "est"]
    assert len(set(round(w, 6) for w in widths)) == 2


def test_view_axis_titles_come_from_the_yaml() -> None:
    res = runner.run(_spec("regression_lineaire"))
    assert next(v for v in res.views if v.id == "residus").ui == {"x_title": "x", "y_title": "Résidu"}


def test_extra_points_added_once() -> None:
    """Un point posé au clic entre une seule fois dans l'échantillon (generate() l'ajoute déjà)."""
    spec = _spec("regression_lineaire")
    base = runner.run(spec, EngineState())
    res = runner.run(spec, EngineState(extra_points=[{"x": 4.2, "y": 30.0}]))
    data = lambda r: next(s for s in next(v for v in r.views if v.id == "nuage").series if s.role == "data")  # noqa: E731
    before, after = data(base), data(res)
    assert len(after.x) == len(before.x) + 1
    assert after.x.count(4.2) == 1 and after.y[-1] == 30.0


def test_clt_paths_view_serves_a_bundle_of_trajectories() -> None:
    """Vue Répétitions en mode trajectoires : une liste par trajectoire, Référence, bornes de l'état sain."""
    res = runner.run(_spec("theoreme_central_limite"), EngineState(hypotheses={"loi": "cauchy"}))
    RunResult.model_validate(res.model_dump())
    view = next(v for v in res.views if v.id == "trajectoires")
    assert view.mode == "paths" and (view.shown, view.total) == (30, 500)
    series = {s.role: s for s in view.series}
    # Les deux méthodes ont les mêmes trajectoires : une seule série, plus la Référence.
    assert set(series) == {"reference", "method"}
    s = series["method"]
    assert len(s.paths) == 30 and len(s.paths[0]) == len(s.x) == 50
    assert view.axes.x == [1.0, 50.0] and view.axes.y is not None
    healthy = runner.run(_spec("theoreme_central_limite"))
    healthy_view = next(v for v in healthy.views if v.id == "trajectoires")
    assert healthy_view.axes == view.axes  # bornes sur la Référence : elles ne bougent pas avec l'état
