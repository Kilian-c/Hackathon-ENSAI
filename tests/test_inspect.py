"""Inspecteur d'observation (cahier, fiche F.6) : séries `inspect.*` du moteur et contrat des YAML officiels.

L'interface lit la fiche d'une observation dans ces séries ; elle n'y calcule que ce qui est générique
(résidu au carré sur la somme, seuils 2 × moyenne des leviers et 4 / n).
"""

from pathlib import Path

import numpy as np
import pytest

from backend.contracts import EngineState
from backend.engine.loader import load_experiment_file
from backend.engine.method_contract import get_method
from backend.engine.runner import INSPECT_KEYS, run
from backend.engine.training import build_session

ROOT = Path(__file__).parent.parent / "experiments"
SPECS = {p.stem: load_experiment_file(p) for p in sorted(ROOT.glob("*.yaml"))}
INSPECTABLE = {name: s for name, s in SPECS.items() if any(v.inspect for v in s.views)}
REGRESSION = SPECS["regression_lineaire"]
SPECS_BY_ID = {s.id: s for s in SPECS.values()}


def _inspect(result, view_id: str) -> dict[str, list]:
    view = next(v for v in result.views if v.id == view_id)
    return {s.slot.removeprefix("inspect."): s for s in view.series if s.slot.startswith("inspect.")}


def test_the_regression_scatter_and_residuals_views_are_inspectable():
    assert "regression_lineaire" in INSPECTABLE
    assert {v.id for v in REGRESSION.views if v.inspect} == {"nuage", "residus"}


@pytest.mark.parametrize("name", sorted(INSPECTABLE))
def test_inspectable_views_have_leverage_and_cooks_distance(name: str):
    """Cahier, fiche F.6 : la méthode principale fournit `example.leverage` et `example.cooks_d`."""
    spec = INSPECTABLE[name]
    main = next(m for m in spec.methods if m.role == "method")
    provided = get_method(main.call).provides["example"]
    assert {"leverage", "cooks_d"} <= set(provided), f"{name} : {main.call} ne fournit pas tout"


def test_series_only_in_inspectable_views():
    result = run(REGRESSION, EngineState())
    for view in REGRESSION.views:
        served = _inspect(result, view.id)
        if view.inspect:
            assert set(served) == set(INSPECT_KEYS)
        else:
            assert served == {}


def test_series_follow_the_sample_order_and_size():
    result = run(REGRESSION, EngineState(params={"n": 150}))
    nuage = next(v for v in result.views if v.id == "nuage")
    data = next(s for s in nuage.series if s.slot == "xy")
    served = _inspect(result, "nuage")
    # Les abscisses ne voyagent qu'une fois, sur la première série.
    assert [key for key, serie in served.items() if serie.x is not None] == [INSPECT_KEYS[0]]
    assert served["y"].x == data.x
    for key, serie in served.items():
        assert len(serie.y) == 150, key
    assert served["y"].y == data.y
    resid = np.array(served["y"].y) - np.array(served["y_hat"].y)
    assert np.allclose(resid, served["resid"].y, atol=1e-6)


def test_leverages_sum_to_the_number_of_coefficients():
    """La règle générique de l'interface (levier élevé au-delà de 2 × la moyenne) vaut 2p/n : somme = p."""
    served = _inspect(run(REGRESSION, EngineState(params={"n": 60})), "nuage")
    assert sum(served["leverage"].y) == pytest.approx(2.0, abs=1e-6)


def test_added_points_are_the_last_observations_and_stand_out():
    state = EngineState(params={"n": 50}, extra_points=[{"x": 6.0, "y": -8.0}, {"x": 0.0, "y": 0.5}])
    served = _inspect(run(REGRESSION, state), "nuage")
    assert len(served["leverage"].y) == 52
    assert served["y"].x[-2:] == [6.0, 0.0]
    assert served["y"].y[-2:] == [-8.0, 0.5]
    leverage = np.array(served["leverage"].y)
    cooks = np.array(served["cooks_d"].y)
    far = 50  # le point posé loin à droite
    assert leverage[far] > 2 * leverage.mean()
    assert cooks[far] > 4 / len(cooks)


def test_both_views_describe_the_same_observations():
    result = run(REGRESSION, EngineState())
    assert _inspect(result, "nuage")["leverage"].y == _inspect(result, "residus")["leverage"].y


def test_training_questions_carry_no_inspection_data():
    """L'Entraînement n'a pas d'inspecteur : le graphique d'un diagnostic part sans ses données."""
    views = []
    for seed in range(1, 6):
        session = build_session(SPECS_BY_ID, "digest", "regression-lineaire", 10, seed)
        views += [q.initial_view for q in session.questions if q.initial_view is not None]
    assert views, "la série de la régression doit contenir un diagnostic avec graphique"
    for view in views:
        assert not [s.slot for s in view.series if s.slot.startswith("inspect.")]
        assert view.series, "le graphique garde ses séries dessinées"
