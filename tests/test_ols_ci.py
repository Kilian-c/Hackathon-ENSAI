"""Tests de la méthode ols_ci (R2) : références statsmodels et chiffres du cahier."""

from __future__ import annotations

import numpy as np
import pytest
import statsmodels.api as sm
from scipy import stats

import backend.methods.ols_ci  # noqa: F401  (enregistre la méthode)
from backend.engine.laws import sample_law
from backend.engine.rng import rng_for
from backend.methods.ols_ci import ols_ci


def _ar1(z: np.ndarray, rho: float) -> np.ndarray:
    out = z.copy()
    for t in range(1, z.shape[1]):
        out[:, t] = rho * out[:, t - 1] + np.sqrt(1 - rho**2) * z[:, t]
    return out


def _world(n, hetero=0.0, autocorr=False, rep=500, seed=42):
    x = sample_law("normal", rng_for(seed, "x_raw"), (rep, n))
    if autocorr:
        x = _ar1(x, 0.7)
    eps = sample_law("normal", rng_for(seed, "base_eps"), (rep, n)) * np.exp(0.9 * hetero * x)
    if autocorr:
        eps = _ar1(eps, 0.7)
    return x, 1.0 + 1.5 * x + eps


def _coverage(se_type: str, n: int = 150, **kw) -> float:
    x, y = _world(n, **kw)
    res = ols_ci(x=x, y=y, truth=1.5, alpha=0.05, se_type=se_type)
    return float(res.reps["hit"].mean())


@pytest.mark.parametrize("se_type", ["classic", "HC3", "HAC"])
def test_matches_statsmodels(se_type: str) -> None:
    n = 60
    x, y = _world(n, hetero=0.5, rep=3)
    lags = int(np.floor(4 * (n / 100) ** (2 / 9)))
    kwargs = {
        "classic": {},
        "HC3": {"cov_type": "HC3"},
        "HAC": {"cov_type": "HAC", "cov_kwds": {"maxlags": lags, "use_correction": False}},
    }[se_type]
    res = ols_ci(x=x, y=y, truth=1.5, alpha=0.05, se_type=se_type)
    for i in range(3):
        m = sm.OLS(y[i], sm.add_constant(x[i])).fit(**kwargs)
        half = stats.t.ppf(0.975, n - 2) * m.bse[1]
        assert res.reps["est"][i] == pytest.approx(m.params[1])
        assert res.reps["low"][i] == pytest.approx(m.params[1] - half)
        assert res.reps["high"][i] == pytest.approx(m.params[1] + half)


def test_breusch_pagan_matches_statsmodels() -> None:
    from statsmodels.stats.diagnostic import het_breuschpagan

    x, y = _world(80, hetero=0.6, rep=2)
    res = ols_ci(x=x, y=y, truth=1.5, alpha=0.05, se_type="classic")
    m = sm.OLS(y[0], sm.add_constant(x[0])).fit()
    assert res.reps["bp_pvalue"][0] == pytest.approx(het_breuschpagan(m.resid, m.model.exog)[1])


def test_example_diagnostics() -> None:
    x, y = _world(50, rep=2)
    res = ols_ci(x=x, y=y, truth=1.5, alpha=0.05, se_type="classic")
    infl = sm.OLS(y[0], sm.add_constant(x[0])).fit().get_influence()
    assert res.example["leverage"] == pytest.approx(infl.hat_matrix_diag)
    assert res.example["cooks_d"] == pytest.approx(infl.cooks_distance[0])
    assert res.example["resid"] == pytest.approx(res.example["y"] - res.example["y_hat"])


def test_reference_coverages() -> None:
    """Ordres de grandeur du cahier (graine 42, 500 répétitions, n = 150)."""
    assert _coverage("classic") > 0.92
    assert _coverage("classic", hetero=0.8) < 0.85
    assert _coverage("HC3", hetero=0.8) > 0.92
    ar = {k: _coverage(k, autocorr=True) for k in ("classic", "HC3", "HAC")}
    assert ar["classic"] < 0.85 and ar["HC3"] < 0.85
    assert ar["HAC"] > ar["HC3"] + 0.07


def test_breusch_pagan_blind_spot() -> None:
    """À n = 30 et hetero = 0,7, environ 1 échantillon sur 5 trompe le test."""
    x, y = _world(30, hetero=0.7)
    p = ols_ci(x=x, y=y, truth=1.5, alpha=0.05, se_type="classic").reps["bp_pvalue"]
    assert 0.10 < float((p > 0.05).mean()) < 0.30


def test_invalid_se_type_and_determinism() -> None:
    x, y = _world(20, rep=4)
    with pytest.raises(ValueError):
        ols_ci(x=x, y=y, truth=1.5, alpha=0.05, se_type="autre")
    a = ols_ci(x=x, y=y, truth=1.5, alpha=0.05, se_type="HAC")
    b = ols_ci(x=x, y=y, truth=1.5, alpha=0.05, se_type="HAC")
    assert np.array_equal(a.reps["low"], b.reps["low"])
