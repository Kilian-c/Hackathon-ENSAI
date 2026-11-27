"""Méthode générique `regressor` (catalogue, archétype 9 « régression »).

Deux `kind` pour l'instant :
- « ols » : la droite des moindres carrés ;
- « manuelle » : une droite de pente imposée (`slope`), qui passe par le point moyen (x barre, y barre),
  comme une droite tracée à la main.
Pour comparer, chaque répétition donne aussi la somme des carrés minimale (celle des MCO).
"""

from __future__ import annotations

import numpy as np

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("ols", "manuelle")


@register_method(
    "regressor",
    provides={"reps": ["slope", "sse", "excess"], "example": ["x", "y", "y_hat"]},
    cost="repeat * n",
)
def regressor(
    *,
    x: np.ndarray,
    y: np.ndarray,
    kind: str,
    slope: float | None = None,
    rng: np.random.Generator | None = None,
) -> MethodResult:
    """Par répétition : pente, somme des carrés des résidus (`sse`), et `excess` = sse / sse des MCO - 1
    (0 pour la droite des MCO, positif pour toute autre droite)."""
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {_KINDS}, reçu {kind!r}.")
    if kind == "manuelle" and slope is None:
        raise ValueError("kind « manuelle » : indiquez la pente (`slope`).")
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_mean = x.mean(axis=1, keepdims=True)
    y_mean = y.mean(axis=1, keepdims=True)
    dx, dy = x - x_mean, y - y_mean
    with np.errstate(divide="ignore", invalid="ignore"):
        ols_slope = (dx * dy).sum(axis=1) / (dx**2).sum(axis=1)
        sse_min = ((dy - ols_slope[:, None] * dx) ** 2).sum(axis=1)
        b = ols_slope if kind == "ols" else np.full(x.shape[0], float(slope))  # type: ignore[arg-type]
        y_hat = y_mean + b[:, None] * dx
        sse = ((y - y_hat) ** 2).sum(axis=1)
        excess = np.where(sse_min > 0, sse / sse_min - 1.0, np.nan)
    if kind == "ols":
        excess = np.where(np.isfinite(excess), np.maximum(excess, 0.0), excess)  # arrondis
    return MethodResult(
        reps={"slope": b, "sse": sse, "excess": excess},
        example={"x": x[0].copy(), "y": y[0].copy(), "y_hat": y_hat[0].copy()},
    )
