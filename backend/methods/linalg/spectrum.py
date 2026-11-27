"""Méthode `spectrum` : spectre d'une matrice symétrique aléatoire (matrices de Wigner).

Chaque répétition tire d² entrées (`x` de forme `(repeat, d * d)`), les range en matrice d x d et les
symétrise : W = (G + Gᵀ) / sqrt(2 d). Si les entrées sont centrées réduites, le spectre se répartit
selon la loi du demi-cercle sur [-2, 2] quand d grandit, et la plus grande valeur propre tend vers 2.
Des entrées à queue lourde (Cauchy) cassent ces deux résultats : c'est l'hypothèse que l'on casse.
"""

from __future__ import annotations

import numpy as np

from backend.engine.method_contract import MethodResult, register_method

SHOWN_REPEATS = 40  # répétitions dont les valeurs propres sont servies pour l'histogramme


def _semicircle_cdf(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, -2.0, 2.0)
    return 0.5 + (t * np.sqrt(4.0 - t * t)) / (4.0 * np.pi) + np.arcsin(t / 2.0) / np.pi


@register_method(
    "spectrum",
    provides={
        "reps": ["lmax", "lmin", "radius"],
        "curves": ["matrix", "eigenvalues"],
        "summary": ["semicircle_ks"],
    },
    cost="repeat * d**3",
)
def spectrum(*, x: np.ndarray, d: float, rng: np.random.Generator) -> MethodResult:
    """`lmax`, `lmin`, `radius` : plus grande, plus petite valeur propre et rayon spectral par répétition.

    `matrix` : la matrice W de la répétition 0 (d, d) ; `eigenvalues` : valeurs propres des premières
    répétitions, mises bout à bout ; `semicircle_ks` : distance de Kolmogorov entre ces valeurs propres
    et la loi du demi-cercle.
    """
    size = int(round(float(d)))
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != size * size:
        raise ValueError(
            f"spectrum : x doit avoir d * d = {size * size} colonnes (une matrice d x d par répétition), "
            f"reçu la forme {x.shape}. Écrivez n: p.d * p.d dans le générateur."
        )
    g = x.reshape(x.shape[0], size, size)
    w = (g + np.swapaxes(g, 1, 2)) / np.sqrt(2.0 * size)
    with np.errstate(all="ignore"):
        eig = np.linalg.eigvalsh(w)  # (repeat, d), croissantes ; vectorisé sur les répétitions
    pooled = np.sort(eig[:SHOWN_REPEATS].ravel())
    cdf = _semicircle_cdf(pooled)
    k = np.arange(1, pooled.size + 1) / pooled.size
    ks = float(np.max(np.maximum(np.abs(k - cdf), np.abs(k - 1.0 / pooled.size - cdf))))
    return MethodResult(
        reps={"lmax": eig[:, -1], "lmin": eig[:, 0], "radius": np.max(np.abs(eig), axis=1)},
        curves={"matrix": w[0], "eigenvalues": pooled},
        summary={"semicircle_ks": ks},
    )
