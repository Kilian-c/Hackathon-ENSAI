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


# --- linsolve ---------------------------------------------------------------------------------------------


def _spd_system(r: int = 12, d: int = 7, shift: float = 3.0):
    rng = np.random.default_rng(11)
    g = rng.standard_normal((r, d, d))
    mat = (g + np.swapaxes(g, 1, 2)) / np.sqrt(2 * d) + shift * np.eye(d)
    return mat, mat @ np.ones(d), np.ones((r, d))


def test_direct_solvers_match_numpy() -> None:
    from backend.methods.linalg.linsolve import _cholesky, _gauss

    mat, b, _ = _spd_system()
    expected = np.linalg.solve(mat, b[..., None])[..., 0]
    solutions = (_gauss(mat.copy(), b, pivot=False), _gauss(mat.copy(), b, pivot=True), _cholesky(mat, b))
    for solution in solutions:
        assert solution == pytest.approx(expected, abs=1e-9)


def test_iterative_solvers_converge_when_the_diagonal_dominates() -> None:
    from backend.methods.linalg.linsolve import _iterate

    mat, b, truth = _spd_system(shift=4.0)
    for kind in ("jacobi", "gauss_seidel", "cg"):
        solution, history = _iterate(kind, mat.copy(), b, 80, truth)
        assert solution == pytest.approx(truth, abs=1e-6), kind
        assert history[-1] < history[0] - 5, kind  # l'erreur (log10) baisse d'au moins cinq ordres


def test_linsolve_failures_are_flagged_and_capped() -> None:
    from backend.methods.linalg.linsolve import FAILED_LOG_ERROR, linsolve

    rng = np.random.default_rng(5)
    a = rng.standard_normal((40, 100))
    weak = dict(a=a, d=10, shift=1.0, iters=60, rng=rng)  # matrice indéfinie : pas de dominance
    jacobi = linsolve(kind="jacobi", **weak)
    assert jacobi.reps["failed"].mean() > 0.5 and jacobi.reps["log_error"].max() <= FAILED_LOG_ERROR
    assert linsolve(kind="cholesky", **weak).reps["failed"].all()  # exige une matrice définie positive
    direct = linsolve(kind="gauss_pivot", **weak)
    assert not direct.reps["failed"].any()  # la méthode directe : aucune condition sur A


def test_linsolve_bad_arguments_are_french_errors() -> None:
    from backend.methods.linalg.linsolve import linsolve

    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="kind doit valoir"):
        linsolve(a=np.zeros((2, 4)), d=2, kind="inconnue", rng=rng)
    with pytest.raises(ValueError, match="d \\* d"):
        linsolve(a=np.zeros((2, 5)), d=2, rng=rng)
    with pytest.raises(ValueError, match="iters"):
        linsolve(a=np.zeros((2, 4)), d=2, iters=0, rng=rng)


def test_linsolve_experiment_jacobi_breaks_but_the_direct_method_does_not() -> None:
    spec = load_experiment_file(WIGNER.parent / "systemes_lineaires.yaml")
    healthy = runner.run(spec, EngineState())
    assert healthy.measures["erreur"].states == {"jacobi": "ok", "gauss_seidel": "ok", "gauss_pivot": "ok"}
    weak = runner.run(spec, EngineState(hypotheses={"dominance": 1.0}))
    expected = {"jacobi": "broken", "gauss_seidel": "broken", "gauss_pivot": "ok"}
    assert weak.measures["erreur"].states == expected
    history = next(v for v in weak.views if v.id == "convergence")
    assert history.series and history.series[0].y is not None


# --- eigen ------------------------------------------------------------------------------------------------


def _spiked(r: int = 15, d: int = 8, spike: float = 3.0):
    rng = np.random.default_rng(21)
    a = rng.standard_normal((r, d * d))
    g = a.reshape(r, d, d)
    mat = (g + np.swapaxes(g, 1, 2)) / np.sqrt(2 * d) + spike / d * np.ones((d, d))
    return a, mat


def test_eigen_direct_is_exact_and_keeps_the_sign_of_the_dominant_eigenvalue() -> None:
    from backend.methods.linalg.eigen import eigen

    for spike in (3.0, -3.0):  # pic négatif : la valeur propre de plus grand module est négative
        a, mat = _spiked(spike=spike)
        result = eigen(a=a, d=8, spike=spike, kind="numpy", rng=np.random.default_rng(0))
        eig = np.linalg.eigvalsh(mat)
        expected = eig[np.arange(len(eig)), np.argmax(np.abs(eig), axis=1)]
        assert result.reps["estimate"] == pytest.approx(expected, abs=1e-12)
        assert (result.reps["estimate"] * np.sign(spike) > 0).all()
        assert result.reps["log_error"].max() <= -15.9 and not result.reps["failed"].any()


def test_power_and_qr_converge_when_the_dominant_eigenvalue_is_isolated() -> None:
    from backend.methods.linalg.eigen import eigen

    a, _ = _spiked(spike=3.0)
    for kind in ("power", "qr"):
        result = eigen(a=a, d=8, spike=3.0, kind=kind, iters=60, rng=np.random.default_rng(1))
        assert np.median(result.reps["log_error"]) < -10, kind
        history = result.curves["history"]
        assert history[-1] < history[0] - 8 and len(history) == len(result.curves["k"]) == 61


def test_power_is_slow_without_an_isolated_eigenvalue() -> None:
    from backend.methods.linalg.eigen import eigen

    a = np.random.default_rng(2).standard_normal((15, 144))
    isolated = eigen(a=a, d=12, spike=3.0, kind="power", iters=20, rng=np.random.default_rng(1))
    flat = eigen(a=a, d=12, spike=0.0, kind="power", iters=20, rng=np.random.default_rng(1))
    gap = np.median(flat.reps["log_error"]) - np.median(isolated.reps["log_error"])
    assert gap > 5


def test_eigen_bad_arguments_are_french_errors() -> None:
    from backend.methods.linalg.eigen import eigen

    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="kind doit valoir"):
        eigen(a=np.zeros((2, 4)), d=2, kind="jacobi", rng=rng)
    with pytest.raises(ValueError, match="d \\* d"):
        eigen(a=np.zeros((2, 5)), d=2, rng=rng)
    with pytest.raises(ValueError, match="iters"):
        eigen(a=np.zeros((2, 4)), d=2, iters=500, rng=rng)


def test_eigen_experiment_power_fails_without_a_spike_but_the_direct_method_does_not() -> None:
    spec = load_experiment_file(WIGNER.parent / "valeurs_propres.yaml")
    healthy = runner.run(spec, EngineState())
    assert healthy.measures["erreur"].states == {"puissance": "ok", "qr": "ok", "directe": "ok"}
    flat = runner.run(spec, EngineState(hypotheses={"separation": 1.0}))
    assert flat.measures["erreur"].states == {"puissance": "broken", "qr": "broken", "directe": "ok"}


# --- orthonormalize ---------------------------------------------------------------------------------------


def _ortho(kind: str, decades: float, r: int = 20, d: int = 8):
    from backend.methods.linalg.orthonormalize import orthonormalize

    a = np.random.default_rng(31).standard_normal((r, d * d))
    return orthonormalize(a=a, d=d, decades=decades, kind=kind, rng=np.random.default_rng(0))


def test_orthonormalize_all_methods_agree_when_well_conditioned() -> None:
    for kind in ("cgs", "mgs", "householder"):
        result = _ortho(kind, decades=0.0)
        assert np.median(result.reps["log_ortho"]) < -14, kind
        assert np.median(result.reps["log_resid"]) < -14, kind
        assert np.allclose(result.curves["matrix"], np.eye(8), atol=1e-12), kind  # QᵀQ = I
        assert not result.reps["failed"].any()


def test_orthonormalize_loss_grows_like_cond_squared_then_cond_then_flat() -> None:
    kinds = ("cgs", "mgs", "householder")
    losses = {kind: np.median(_ortho(kind, decades=6.0).reps["log_ortho"]) for kind in kinds}
    assert losses["householder"] < -14  # Householder : epsilon, quel que soit le conditionnement
    assert -11 < losses["mgs"] < -8  # epsilon * cond : 1e-16 * 1e6 = 1e-10
    assert losses["cgs"] > -6  # epsilon * cond^2 : 1e-16 * 1e12 = 1e-4
    assert losses["householder"] < losses["mgs"] < losses["cgs"]


def test_orthonormalize_factorisation_keeps_reproducing_a_even_when_q_is_not_orthogonal() -> None:
    result = _ortho("cgs", decades=9.0)
    assert np.median(result.reps["log_ortho"]) > -3  # Q n'est plus orthogonale
    assert np.median(result.reps["log_resid"]) < -6  # mais A = Q R reste vrai


def test_orthonormalize_bad_arguments_are_french_errors() -> None:
    from backend.methods.linalg.orthonormalize import orthonormalize

    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="kind doit valoir"):
        orthonormalize(a=np.zeros((2, 4)), d=2, kind="qr", rng=rng)
    with pytest.raises(ValueError, match="d \\* d"):
        orthonormalize(a=np.zeros((2, 5)), d=2, rng=rng)
    with pytest.raises(ValueError, match="decades"):
        orthonormalize(a=np.zeros((2, 4)), d=2, decades=20.0, rng=rng)


def test_orthonormalisation_experiment_classic_breaks_modified_resists_householder_never() -> None:
    spec = load_experiment_file(WIGNER.parent / "orthonormalisation.yaml")
    healthy = runner.run(spec, EngineState())
    assert healthy.measures["orthogonalite"].states == {"cgs": "ok", "mgs": "ok", "householder": "ok"}
    middle = runner.run(spec, EngineState(hypotheses={"conditionnement": 0.55}))
    assert middle.measures["orthogonalite"].states == {"cgs": "broken", "mgs": "ok", "householder": "ok"}
    gram = next(v for v in middle.views if v.id == "gram")
    assert [s.role for s in gram.series] == ["method", "alternative_1", "correction", "reference"]
