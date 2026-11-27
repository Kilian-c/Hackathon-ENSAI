"""Comparaisons deux à deux de moyennes de groupes : sans correction, Bonferroni ou Tukey.

Chaque ligne de y est découpée en `groups` groupes consécutifs de tailles égales à une unité près. La
variance est estimée en commun sur tous les groupes (celle de l'analyse de la variance).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import stats

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("aucune", "bonferroni", "tukey")


@lru_cache(maxsize=256)
def _tukey_quantile(level: float, groups: int, dof: int) -> float:
    """Quantile de la loi de l'étendue studentisée (calcul lent : gardé en mémoire)."""
    return float(stats.studentized_range.ppf(level, groups, dof))


@register_method(
    "pairwise_tests",
    provides={
        "reps": ["any_reject", "n_reject", "max_stat"],
        "example": ["group", "y", "group_mean"],
    },
    cost="repeat * n",
)
def pairwise_tests(
    *,
    y: np.ndarray,
    groups: float,
    alpha: float,
    kind: str,
    rng: np.random.Generator | None = None,
) -> MethodResult:
    """Teste l'égalité des moyennes pour chaque paire de groupes.

    y : (repeat, n). `any_reject` vaut 1 si au moins une paire est déclarée différente,
    `n_reject` compte ces paires, `max_stat` est la plus grande statistique |T| de la répétition.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {_KINDS}, reçu {kind!r}.")
    y = np.asarray(y, dtype=float)
    k = int(round(float(groups)))
    repeat, total = y.shape
    if k < 2 or total < 2 * k:
        raise ValueError(f"Il faut au moins 2 groupes de 2 valeurs (reçu {total} valeurs, {k} groupes).")
    group = (np.arange(total) * k) // total
    sizes = np.bincount(group)
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])

    means = np.add.reduceat(y, starts, axis=1) / sizes
    dof = total - k
    pooled = np.sum((y - means[:, group]) ** 2, axis=1) / dof
    first, second = np.triu_indices(k, 1)
    spread = 1.0 / sizes[first] + 1.0 / sizes[second]
    with np.errstate(all="ignore"):
        t = np.abs(means[:, first] - means[:, second]) / np.sqrt(pooled[:, None] * spread)

    if kind == "tukey":
        threshold = _tukey_quantile(1.0 - alpha, k, dof) / np.sqrt(2.0)
    else:
        level = alpha / len(first) if kind == "bonferroni" else alpha
        threshold = float(stats.t.ppf(1.0 - level / 2.0, dof))
    rejected = t > threshold

    return MethodResult(
        reps={
            "any_reject": rejected.any(axis=1).astype(float),
            "n_reject": rejected.sum(axis=1).astype(float),
            "max_stat": t.max(axis=1),
        },
        example={
            "group": (group + 1).astype(float),
            "y": y[0].copy(),
            "group_mean": means[0, group],
        },
    )
