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


def _all_specs() -> list[str]:
    return sorted(p.stem for p in EXP.glob("*.yaml")) + ["archives/test_student"]


@pytest.mark.parametrize("name", _all_specs())
def test_same_state_same_result_byte_for_byte(name: str) -> None:
    """Test 8 sur toutes les expériences officielles (et Student, archivée) : même état, même JSON."""
    spec = _spec(Path(name).name, ARCHIVES if name.startswith("archives/") else EXP)
    a = runner.run(spec).model_dump_json(exclude={"compute_ms"})
    runner._CACHE.clear()
    b = runner.run(spec).model_dump_json(exclude={"compute_ms"})
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


def test_non_finite_value_is_always_broken() -> None:
    """Une seule règle : NaN et infini sont `broken`, comme dans l'affichage, les défis et le balayage."""
    for bad in (float("nan"), float("inf"), float("-inf")):
        for direction in ("below", "above", "both"):
            assert runner.verdict(bad, 0.95, direction, 0.02, 0.10) == "broken"
    assert runner.verdict(0.95, 0.95, "below", 0.02, 0.10) == "ok"


def test_method_failure_is_a_french_run_error() -> None:
    """Une méthode inconnue ou qui échoue ne donne pas un 500 anglais mais une `RunError`."""
    spec = _spec("regression_lineaire")
    main = next(m for m in spec.methods if m.role == "method")
    methods = [m.model_copy(update={"call": "inexistante"}) if m is main else m for m in spec.methods]
    broken = spec.model_copy(update={"methods": methods})
    with pytest.raises(runner.RunError, match="a échoué"):
        runner.run(broken, EngineState())


def test_cache_survives_concurrent_runs_with_evictions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le pool de threads de FastAPI partage le cache : des évictions en parallèle ne doivent pas planter."""
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setattr(runner, "_CACHE_SIZE", 2)
    spec = _spec("somme_des")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda seed: runner.run(spec, EngineState(seed=seed)), range(40)))
    assert len(results) == 40
    assert runner.run(spec, EngineState(seed=3)).state_hash == results[3].state_hash


def test_draw_log_served_only_when_declared_and_matches_first_repetition() -> None:
    from backend.engine.runner import _compute, spec_hash
    from backend.engine.state import resolve_state

    spec = _spec("test_student", ARCHIVES)
    state = EngineState(hypotheses={"loi": "cauchy"})
    res = runner.run(spec, state)
    reps = _compute(spec, resolve_state(spec, state), spec_hash(spec)).results["student"].reps
    assert res.draw_log is not None
    assert res.draw_log.reject == bool(reps["reject"][0])
    assert res.draw_log.pvalue == pytest.approx(float(reps["pvalue"][0]), abs=1e-5)
    assert runner.run(spec, state).draw_log == res.draw_log  # déterministe
    assert runner.run(_spec("regression_lineaire")).draw_log is None  # non déclaré : null


def test_misspelled_reference_in_method_args_is_a_french_error() -> None:
    spec = _spec("regression_lineaire")
    args = {**spec.methods[0].args, "truth": "p.beta_inconnu"}
    methods = [spec.methods[0].model_copy(update={"args": args}), *spec.methods[1:]]
    bad = spec.model_copy(update={"methods": methods})
    with pytest.raises(runner.RunError, match="p.beta_inconnu"):
        runner.run(bad)
    runner.run(spec)  # les textes littéraux (« classic », « HC3 ») restent acceptés


def test_total_size_cap_is_a_french_error() -> None:
    spec = _spec("regression_lineaire")
    heavy = spec.generator.model_copy(update={"repeat": 1000, "n": 5000})
    with pytest.raises(runner.RunError, match="trop lourde"):
        runner.run(spec.model_copy(update={"generator": heavy}))
