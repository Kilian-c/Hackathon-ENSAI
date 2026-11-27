"""Tests à un échantillon : Student et Wilcoxon (rangs signés), annexe D du cahier."""

from __future__ import annotations

import numpy as np
from scipy import stats

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("student", "wilcoxon")


def _test(x: np.ndarray, kind: str) -> tuple[np.ndarray, np.ndarray]:
    """Statistique et p-value bilatérale, une par ligne de x (forme (repeat, n))."""
    if kind == "student":
        res = stats.ttest_1samp(x, 0.0, axis=1)
    else:
        res = stats.wilcoxon(x, axis=1)
    return np.asarray(res.statistic, dtype=float), np.asarray(res.pvalue, dtype=float)


@register_method(
    "one_sample_test",
    provides={
        "reps": ["reject", "reject_h1", "pvalue", "stat"],
        "example": ["x0"],
    },
    cost="repeat * n",
)
def one_sample_test(
    *,
    x0: np.ndarray,
    x1: np.ndarray,
    alpha: float,
    kind: str,
    rng: np.random.Generator | None = None,
) -> MethodResult:
    """Teste H0 : centre = 0 sur x0 (sous H0) et sur x1 (sous H1).

    x0, x1 : (repeat, n). `reject` vaut 1 si H0 est rejetée sur x0 (faux positif),
    `reject_h1` si elle l'est sur x1 (puissance). `pvalue` et `stat` portent sur x0.
    Wilcoxon teste le centre de symétrie, pas la moyenne.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {_KINDS}, reçu {kind!r}.")
    stat0, p0 = _test(x0, kind)
    _, p1 = _test(x1, kind)
    return MethodResult(
        reps={
            "reject": (p0 < alpha).astype(float),
            "reject_h1": (p1 < alpha).astype(float),
            "pvalue": p0,
            "stat": stat0,
        },
        example={"x0": np.asarray(x0[0], dtype=float)},
    )
