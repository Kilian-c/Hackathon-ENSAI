"""MCO à deux variables explicatives : coefficient de x1, son intervalle de confiance et le VIF.

Modèle complet y sur (1, x1, x2), ou modèle réduit y sur (1, x1) quand on retire x2.
Formules fermées sur les variables centrées, vectorisées sur les répétitions (axe 0).
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("complet", "reduit")


@register_method(
    "ols_two",
    provides={
        "reps": ["est", "low", "high", "hit", "reject", "width", "vif", "pred_error"],
        "example": ["x1", "x2", "y", "y_hat", "resid"],
    },
    cost="repeat * n",
)
def ols_two(
    *,
    x1: np.ndarray,
    x2: np.ndarray,
    y: np.ndarray,
    signal: np.ndarray,
    truth: float,
    alpha: float,
    kind: str,
    rng: np.random.Generator | None = None,
) -> MethodResult:
    """Estime le coefficient de x1 ; `reject` vaut 1 si le test de Student le déclare non nul.

    x1, x2, y, signal : (repeat, n). `signal` est E(Y), connu parce que les données sont simulées :
    `pred_error` est la distance quadratique moyenne entre la prévision et lui. `vif` vaut
    1 / (1 - r^2) avec r la corrélation empirique de x1 et x2, quel que soit le modèle ajusté.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {_KINDS}, reçu {kind!r}.")
    x1 = np.asarray(x1, dtype=float)
    x2 = np.asarray(x2, dtype=float)
    y = np.asarray(y, dtype=float)
    n = x1.shape[1]

    with np.errstate(all="ignore"):
        m1 = x1.mean(axis=1, keepdims=True)
        m2 = x2.mean(axis=1, keepdims=True)
        my = y.mean(axis=1, keepdims=True)
        c1, c2, cy = x1 - m1, x2 - m2, y - my
        s11 = np.sum(c1**2, axis=1)
        s22 = np.sum(c2**2, axis=1)
        s12 = np.sum(c1 * c2, axis=1)
        s1y = np.sum(c1 * cy, axis=1)
        vif = 1.0 / (1.0 - s12**2 / (s11 * s22))

        if kind == "complet":
            s2y = np.sum(c2 * cy, axis=1)
            det = s11 * s22 - s12**2
            b1 = (s22 * s1y - s12 * s2y) / det
            b2 = (s11 * s2y - s12 * s1y) / det
            dof = n - 3
            inverse_11 = s22 / det
        else:
            b1 = s1y / s11
            b2 = np.zeros_like(b1)
            dof = n - 2
            inverse_11 = 1.0 / s11

        y_hat = my + b1[:, None] * c1 + b2[:, None] * c2
        e = y - y_hat
        se = np.sqrt(np.sum(e**2, axis=1) / dof * inverse_11)
        half = stats.t.ppf(1.0 - alpha / 2.0, dof) * se
        low, high = b1 - half, b1 + half
        hit = ((low <= truth) & (truth <= high)).astype(float)
        reject = ((low > 0.0) | (high < 0.0)).astype(float)
        hit[~np.isfinite(half)] = np.nan
        reject[~np.isfinite(half)] = np.nan
        pred_error = np.sqrt(np.mean((y_hat - np.asarray(signal, dtype=float)) ** 2, axis=1))

    return MethodResult(
        reps={
            "est": b1,
            "low": low,
            "high": high,
            "hit": hit,
            "reject": reject,
            "width": high - low,
            "vif": vif,
            "pred_error": pred_error,
        },
        example={
            "x1": x1[0].copy(),
            "x2": x2[0].copy(),
            "y": y[0].copy(),
            "y_hat": y_hat[0],
            "resid": e[0],
        },
    )
