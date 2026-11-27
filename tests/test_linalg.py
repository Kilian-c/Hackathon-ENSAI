"""Algèbre linéaire (`backend/methods/linalg/`) : comparaison à `np.linalg`, vectorisation, temps de calcul,
et vue `heatmap` servie par `runner.py`."""

import time
from pathlib import Path

import numpy as np
import pytest

from backend.contracts import EngineState
from backend.engine import runner
from backend.engine.loader import load_experiment_file
from backend.methods.linalg.spectrum import spectrum

WIGNER = Path(__file__).resolve().parent.parent / "experiments" / "matrices_wigner.yaml"


def test_spectrum_matches_numpy_eigvalsh_on_each_repetition() -> None:
    rng = np.random.default_rng(3)
    d = 6
    x = rng.standard_normal((25, d * d))
    result = spectrum(x=x, d=d, rng=rng)
    g = x.reshape(25, d, d)
    w = (g + np.swapaxes(g, 1, 2)) / np.sqrt(2 * d)
    for i in range(25):
        eig = np.linalg.eigvalsh(w[i])
        assert result.reps["lmax"][i] == pytest.approx(eig[-1], abs=1e-12)
        assert result.reps["lmin"][i] == pytest.approx(eig[0], abs=1e-12)
        assert result.reps["radius"][i] == pytest.approx(np.abs(eig).max(), abs=1e-12)
    assert result.curves["matrix"] == pytest.approx(w[0], abs=1e-12)
    assert np.allclose(result.curves["matrix"], result.curves["matrix"].T)  # symétrique


def test_spectrum_converges_to_the_semicircle() -> None:
    rng = np.random.default_rng(0)
    d = 40
    result = spectrum(x=rng.standard_normal((200, d * d)), d=d, rng=rng)
    assert result.summary["semicircle_ks"] < 0.02
    assert 1.85 < result.reps["lmax"].mean() < 2.0


def test_spectrum_wrong_shape_is_a_french_error() -> None:
    with pytest.raises(ValueError, match="d \\* d"):
        spectrum(x=np.zeros((5, 10)), d=3, rng=np.random.default_rng(0))


def test_spectrum_is_vectorised_and_fast() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal((500, 900))
    t0 = time.perf_counter()
    spectrum(x=x, d=30, rng=rng)
    assert time.perf_counter() - t0 < 0.5


def test_heatmap_view_serves_one_matrix_per_method_and_the_reference() -> None:
    spec = load_experiment_file(WIGNER)
    res = runner.run(spec, EngineState(params={"d": 12}, hypotheses={"entrees": "cauchy"}))
    view = next(v for v in res.views if v.id == "matrice")
    assert [(s.id, s.role, s.slot) for s in view.series] == [
        ("matrice.matrix.spectre", "method", "matrix"),
        ("matrice.matrix.spectre.ref", "reference", "matrix"),
    ]
    assert all(len(s.paths) == 12 and len(s.paths[0]) == 12 for s in view.series)
    method, ref = view.series
    assert method.paths != ref.paths  # Cauchy contre l'état sain : pas la même matrice
    assert max(abs(v) for row in method.paths for v in row if v is not None) > 5


def test_heatmap_matrix_is_cropped_to_the_cap() -> None:
    spec = load_experiment_file(WIGNER)
    d_param = spec.params["d"].model_copy(update={"max": 80})
    big = spec.model_copy(update={"params": {**spec.params, "d": d_param}})
    res = runner.run(big, EngineState(params={"d": 70}))
    view = next(v for v in res.views if v.id == "matrice")
    assert len(view.series[0].paths) == runner.MAX_MATRIX
