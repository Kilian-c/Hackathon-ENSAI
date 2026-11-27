"""Tests du balayage : grilles, seuils interpolés, cible `base`, 2 axes, plafonds, erreurs en français."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.contracts import SweepResult
from backend.main import app

client = TestClient(app)
FIXTURE = (
    Path(__file__).resolve().parent.parent / "frontend" / "src" / "fixtures" / "regression_hetero.sweep.json"
)


def _post(experiment_id: str, axes: list[str], state: dict | None = None, measure: str | None = None):
    body = {"experiment_id": experiment_id, "axes": [{"target": a} for a in axes], "state": state or {}}
    if measure:
        body["measure"] = measure
    return client.post("/api/sweep", json=body)


def test_one_axis_continuous_with_critical() -> None:
    r = _post("regression-lineaire", ["h.hetero"], {"hypotheses": {"hetero": 0.8}})
    assert r.status_code == 200
    res = SweepResult.model_validate(r.json())
    assert len(res.axes[0].values) == 11 and res.measure == "coverage"
    assert res.current == {"h.hetero": 0.8}
    ols, hc3 = res.values["ols"], res.values["hc3"]
    assert ols[0] > 0.9 and ols[-1] < 0.8 and min(hc3) > 0.9  # HC3 reste fiable partout
    assert res.states["ols"][0] == "ok" and res.states["ols"][-1] == "broken"
    crit = res.critical["ols"]
    assert crit is not None and 0 < crit.warning_at < crit.broken_at <= 1
    assert res.critical["hc3"] is None
    assert res.target == 0.95 and res.direction == "below"
    # même forme que la fixture de R1 (contrat respecté)
    assert set(res.model_dump(exclude_none=True)) >= set(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_choice_axis() -> None:
    res = SweepResult.model_validate(_post("theoreme-central-limite", ["h.loi"]).json())
    assert res.axes[0].values[0] == "normal" and len(res.axes[0].labels) == len(res.axes[0].values)
    assert res.critical is None  # axe non continu
    cauchy = res.axes[0].values.index("cauchy")
    assert res.states["moyenne"][0] == "ok" and res.states["moyenne"][cauchy] == "broken"


def test_base_target_is_per_method() -> None:
    res = SweepResult.model_validate(_post("multicolinearite", ["h.rho"]).json())
    assert isinstance(res.target, dict) and set(res.target) == {"complet", "reduit"}
    assert res.states["complet"][0] == "ok" and res.states["complet"][-1] == "broken"
    assert res.critical["complet"] is not None and res.critical["reduit"] is None


def test_two_axes_grid_is_indexed_axis2_then_axis1() -> None:
    res = SweepResult.model_validate(_post("theoreme-central-limite", ["h.loi", "p.n"]).json())
    n_loi, n_n = len(res.axes[0].values), len(res.axes[1].values)
    grid = res.values["moyenne"]
    assert len(grid) == n_n and all(len(row) == n_loi for row in grid)
    assert res.critical is None


def test_parameter_axis_and_informative_measure() -> None:
    res = SweepResult.model_validate(
        _post("multicolinearite", ["p.n"], {"hypotheses": {"rho": 0.9}}, measure="power").json()
    )
    assert res.measure == "power" and res.critical is not None
    info = SweepResult.model_validate(_post("regression-lineaire", ["h.hetero"], measure="width").json())
    assert info.states == {} and info.target is None and info.critical is None


def test_same_seed_same_sweep() -> None:
    a = _post("regression-lineaire", ["h.hetero"]).json()
    b = _post("regression-lineaire", ["h.hetero"]).json()
    a.pop("compute_ms"), b.pop("compute_ms")
    assert a == b


def test_errors_are_french_422() -> None:
    cases = [
        (["h.nimporte"], "Hypothèse inconnue"),
        (["p.beta1"], "n'est pas balayable"),
        (["h.hetero", "h.hetero"], "différents"),
    ]
    for axes, text in cases:
        r = _post("regression-lineaire", axes)
        assert r.status_code == 422 and text in r.json()["detail"], axes
    assert _post("regression-lineaire", ["h.hetero"], measure="zzz").status_code == 422
    assert _post("nexiste-pas", ["h.hetero"]).status_code == 404


def test_caps_points_and_cells(monkeypatch) -> None:
    from backend.engine import sweep as sweep_module

    def fake(n: int):
        return lambda spec, target: (list(range(n)), [str(i) for i in range(n)])

    monkeypatch.setattr(sweep_module, "axis_values", fake(22))  # 22 points > 21
    r = _post("regression-lineaire", ["h.hetero"])
    assert r.status_code == 422 and "21 points" in r.json()["detail"]
    monkeypatch.setattr(sweep_module, "axis_values", fake(13))  # 13 x 13 = 169 cases > 144
    r = _post("regression-lineaire", ["h.hetero", "p.n"])
    assert r.status_code == 422 and "144 cases" in r.json()["detail"]


def test_caps_axes_count_and_duplicates() -> None:
    assert _post("regression-lineaire", ["h.hetero", "p.n", "h.error_law"]).status_code == 422
    r = _post("regression-lineaire", ["h.hetero", "h.hetero"])
    assert r.status_code == 422 and "différents" in r.json()["detail"]


def test_axis_values_stay_inside_range_when_step_does_not_divide_it() -> None:
    from backend.api import registry
    from backend.engine.sweep import axis_values

    spec = registry.official()["regression-lineaire"]
    hyp = spec.hypotheses["hetero"].model_copy(update={"range": (0.0, 0.5), "step": 0.3})
    odd = spec.model_copy(update={"hypotheses": {**spec.hypotheses, "hetero": hyp}})
    values, labels = axis_values(odd, "h.hetero")
    assert len(values) == len(labels) and values == sorted(set(values))
    assert all(0.0 <= v <= 0.5 for v in values) and values[0] == 0.0 and values[-1] == 0.5
