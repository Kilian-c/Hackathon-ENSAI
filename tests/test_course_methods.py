"""Méthodes des expériences de cours (TCL, multicolinéarité, tests multiples), contre des références."""

from __future__ import annotations

import numpy as np
import statsmodels.api as sm
from scipy import stats

from backend.methods.clt_mean import clt_mean
from backend.methods.ols_two import ols_two
from backend.methods.pairwise_tests import pairwise_tests

_RNG = np.random.default_rng(3)
_X1 = _RNG.standard_normal((4, 40))
_X2 = 0.8 * _X1 + 0.6 * _RNG.standard_normal((4, 40))
_SIGNAL = 1.0 + 0.3 * _X1 + 0.3 * _X2
_Y = _SIGNAL + _RNG.standard_normal((4, 40))


def test_ols_two_matches_statsmodels() -> None:
    for kind, columns in (("complet", (_X1, _X2)), ("reduit", (_X1,))):
        res = ols_two(x1=_X1, x2=_X2, y=_Y, signal=_SIGNAL, truth=0.3, alpha=0.05, kind=kind)
        for i in range(_Y.shape[0]):
            design = sm.add_constant(np.column_stack([c[i] for c in columns]))
            fit = sm.OLS(_Y[i], design).fit()
            assert np.isclose(res.reps["est"][i], fit.params[1])
            assert np.allclose([res.reps["low"][i], res.reps["high"][i]], fit.conf_int()[1])
        r = np.corrcoef(_X1[0], _X2[0])[0, 1]
        assert np.isclose(res.reps["vif"][0], 1.0 / (1.0 - r**2))


def test_pairwise_tests_match_scipy_tukey() -> None:
    y = _RNG.standard_normal((30, 43))  # tailles inégales : 11, 11, 11, 10
    y[:, :11] += 0.8
    res = pairwise_tests(y=y, groups=4, alpha=0.05, kind="tukey")
    sizes = np.bincount((np.arange(43) * 4) // 43)
    blocks = np.split(y, np.cumsum(sizes)[:-1], axis=1)
    for i in range(y.shape[0]):
        p = stats.tukey_hsd(*[b[i] for b in blocks]).pvalue
        assert res.reps["n_reject"][i] == np.sum(p[np.triu_indices(4, 1)] < 0.05)


def test_pairwise_two_groups_is_student() -> None:
    y = _RNG.standard_normal((50, 24))
    p = stats.ttest_ind(y[:, :12], y[:, 12:], axis=1).pvalue
    for kind in ("aucune", "bonferroni", "tukey"):
        res = pairwise_tests(y=y, groups=2, alpha=0.05, kind=kind)
        assert np.array_equal(res.reps["any_reject"], (p < 0.05).astype(float))


def test_clt_mean_normalisation() -> None:
    free = clt_mean(x=_X1, sigma=1.0, rho=0.5, kind="independance")
    assert np.allclose(free.reps["z"], np.sqrt(40) * _X1.mean(axis=1))
    dependent = clt_mean(x=_X1, sigma=1.0, rho=0.5, kind="dependance")
    assert np.allclose(dependent.reps["z"], free.reps["z"] / np.sqrt(3.0))
