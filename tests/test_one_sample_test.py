"""Tests de la méthode one_sample_test (R2)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

import backend.methods.one_sample_test  # noqa: F401  (enregistre la méthode)
from backend.engine.laws import sample_law
from backend.engine.rng import rng_for
from backend.methods.one_sample_test import one_sample_test


def _power(law: str, kind: str, n: int = 25) -> float:
    x0 = sample_law(law, rng_for(42, "x0"), (500, n))
    res = one_sample_test(x0=x0, x1=x0 + 0.5, alpha=0.05, kind=kind)
    return float(res.reps["reject_h1"].mean())


def test_matches_scipy_row_by_row() -> None:
    x0 = np.random.default_rng(1).standard_normal((5, 20))
    for kind, ref in (("student", stats.ttest_1samp), ("wilcoxon", None)):
        res = one_sample_test(x0=x0, x1=x0 + 1, alpha=0.05, kind=kind)
        for i in range(5):
            p = ref(x0[i], 0.0).pvalue if ref else stats.wilcoxon(x0[i]).pvalue
            assert res.reps["pvalue"][i] == pytest.approx(p)


def test_unknown_kind() -> None:
    x = np.zeros((2, 5))
    with pytest.raises(ValueError):
        one_sample_test(x0=x, x1=x, alpha=0.05, kind="autre")


def test_reference_figures() -> None:
    """Ordres de grandeur du cahier (graine 42, 500 répétitions, n = 25)."""
    base = _power("normal", "student")
    assert 0.60 < base < 0.74
    assert _power("cauchy", "student") < 0.20
    assert base - _power("student_2", "student") > 0.29  # Student Rompu
    w_loss = _power("normal", "wilcoxon") - _power("cauchy", "wilcoxon")
    assert 0.15 < w_loss < 0.29  # Wilcoxon Fragile, pas Rompu


def test_deterministic() -> None:
    assert _power("cauchy", "wilcoxon") == _power("cauchy", "wilcoxon")
