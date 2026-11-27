"""Théorème central limite : moyenne normalisée de chaque échantillon.

Chaque ligne de x est un échantillon centré en 0. Les deux variantes ne diffèrent que par la variance
utilisée pour normaliser la moyenne avant de la comparer à N(0, 1).
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("independance", "dependance")


@register_method(
    "clt_mean",
    provides={"reps": ["z", "inside"], "example": ["x"]},
    cost="repeat * n",
)
def clt_mean(
    *,
    x: np.ndarray,
    sigma: float,
    rho: float,
    kind: str,
    alpha: float = 0.05,
    rng: np.random.Generator | None = None,
) -> MethodResult:
    """Statistique z par répétition ; `inside` vaut 1 si |z| ne dépasse pas le quantile normal.

    - "independance" : z = racine(n) moyenne / sigma (énoncé du TCL pour des variables indépendantes) ;
    - "dependance" : la variance sigma^2 est remplacée par sigma^2 (1 + rho) / (1 - rho), la variance
      limite d'un processus AR(1).
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {_KINDS}, reçu {kind!r}.")
    x = np.asarray(x, dtype=float)
    n = x.shape[1]
    q = float(stats.norm.ppf(1.0 - alpha / 2.0))

    r = float(rho) if kind == "dependance" else 0.0
    with np.errstate(all="ignore"):
        limit_sd = float(sigma) * np.sqrt((1.0 + r) / (1.0 - r))
        z = np.sqrt(n) * x.mean(axis=1) / limit_sd
        inside = (np.abs(z) <= q).astype(float)
        inside[~np.isfinite(z)] = np.nan

    return MethodResult(reps={"z": z, "inside": inside}, example={"x": x[0].copy()})
