"""Pente des MCO et son intervalle de confiance : classique, HC3 ou HAC (annexe D).

Régression simple avec constante, vectorisée sur les répétitions (axe 0).
Les trois variantes ne diffèrent que par l'estimateur de la variance de la pente.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from backend.engine.method_contract import MethodResult, register_method

_SE_TYPES = ("classic", "HC3", "HAC")


def _slope_variance(
    se_type: str,
    xc: np.ndarray,
    e: np.ndarray,
    sxx: np.ndarray,
    lev: np.ndarray,
) -> np.ndarray:
    """Variance estimée de la pente, une valeur par répétition."""
    n = xc.shape[1]
    if se_type == "classic":
        s2 = np.sum(e**2, axis=1) / (n - 2)
        return s2 / sxx
    if se_type == "HC3":
        u = xc * e / (1.0 - lev)
        return np.sum(u**2, axis=1) / sxx**2
    # HAC (Newey-West, noyau de Bartlett, fenêtre de Newey-West 1994)
    u = xc * e
    n_lags = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    s = np.sum(u**2, axis=1)
    for lag in range(1, min(n_lags, n - 1) + 1):
        w = 1.0 - lag / (n_lags + 1.0)
        s = s + 2.0 * w * np.sum(u[:, lag:] * u[:, :-lag], axis=1)
    return np.maximum(s, 0.0) / sxx**2


@register_method(
    "ols_ci",
    provides={
        "reps": ["est", "low", "high", "hit", "width", "bp_pvalue"],
        "example": ["x", "y", "y_hat", "y_mean", "resid", "leverage", "cooks_d"],
    },
    cost="repeat * n",
)
def ols_ci(
    *,
    x: np.ndarray,
    y: np.ndarray,
    truth: float,
    alpha: float,
    se_type: str,
    rng: np.random.Generator | None = None,
) -> MethodResult:
    """MCO de y sur (1, x) et IC à (1 - alpha) de la pente, par répétition.

    x, y : (repeat, n). `hit` vaut 1 si l'IC contient `truth`. `bp_pvalue` est la
    p-value du test de Breusch-Pagan (version de Koenker) sur chaque échantillon.
    Le taux de couverture est calculé par l'agrégateur, pas ici.
    """
    if se_type not in _SE_TYPES:
        raise ValueError(f"se_type doit valoir l'un de {_SE_TYPES}, reçu {se_type!r}.")
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = x.shape[1]

    with np.errstate(all="ignore"):
        x_mean = x.mean(axis=1, keepdims=True)
        y_mean = y.mean(axis=1, keepdims=True)
        xc = x - x_mean
        sxx = np.sum(xc**2, axis=1)
        est = np.sum(xc * (y - y_mean), axis=1) / sxx
        intercept = y_mean[:, 0] - est * x_mean[:, 0]
        y_hat = intercept[:, None] + est[:, None] * x
        e = y - y_hat
        lev = 1.0 / n + xc**2 / sxx[:, None]

        se = np.sqrt(_slope_variance(se_type, xc, e, sxx, lev))
        half = stats.t.ppf(1.0 - alpha / 2.0, n - 2) * se
        low, high = est - half, est + half
        hit = ((low <= truth) & (truth <= high)).astype(float)
        hit[~np.isfinite(half)] = np.nan

        # Breusch-Pagan (Koenker) : LM = n R^2 de la régression de e^2 sur (1, x)
        e2 = e**2
        e2c = e2 - e2.mean(axis=1, keepdims=True)
        b = np.sum(xc * e2c, axis=1) / sxx
        r2 = b**2 * sxx / np.sum(e2c**2, axis=1)
        bp_p = stats.chi2.sf(n * r2, 1)

        s2 = np.sum(e**2, axis=1) / (n - 2)
        cooks = e[0] ** 2 / (2.0 * s2[0]) * lev[0] / (1.0 - lev[0]) ** 2

    return MethodResult(
        reps={
            "est": est,
            "low": low,
            "high": high,
            "hit": hit,
            "width": high - low,
            "bp_pvalue": bp_p,
        },
        example={
            "x": x[0].copy(),
            "y": y[0].copy(),
            "y_hat": y_hat[0],
            "y_mean": np.full(n, y_mean[0, 0]),
            "resid": e[0],
            "leverage": lev[0],
            "cooks_d": cooks,
        },
    )
