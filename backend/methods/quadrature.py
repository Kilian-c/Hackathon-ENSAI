"""Méthode `quadrature` (R1, catégorie Intégration) : l'intégrale d'une fonction sur une grille.

La fonction est évaluée par le générateur sur une grille de points croissants `x` (forme `(repeat, n)`,
par exemple `x: (idx + 0.5) / n`) ; la méthode en calcule l'intégrale sur [a, b] par la règle choisie.
`example` rend `x` et `f` de la répétition 0 : une vue `curves` avec
`bind: { t: example.x, series: [{ y: example.f }] }` dessine la courbe ET sa Référence (état sain), ce que
ne fait pas une courbe lue dans le générateur.

Règles (`kind`) :
- `rectangles` : la grille est celle des milieux de cellules, intégrale = (b - a) * moyenne de f ;
- `trapezes` : règle des trapèzes entre les points, plus un rectangle à chaque bord jusqu'à a et b ;
- `simpson` : règle de Simpson entre les points, mêmes bords ;
- `monte_carlo` : (b - a) * moyenne de f sur `samples` points de la grille tirés au hasard
  (flux aléatoire de la méthode).
"""

from __future__ import annotations

import numpy as np
from scipy import integrate

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("rectangles", "trapezes", "simpson", "monte_carlo")


def _edges(x: np.ndarray, f: np.ndarray, a: float, b: float) -> np.ndarray:
    """Rectangles de bord : f(premier point) sur [a, x0] et f(dernier point) sur [x_{n-1}, b]."""
    return f[:, 0] * (x[:, 0] - a) + f[:, -1] * (b - x[:, -1])


@register_method(
    "quadrature",
    provides={"reps": ["est", "error"], "example": ["x", "f"]},
    cost="repeat * n",
)
def quadrature(
    *,
    x: np.ndarray,
    f: np.ndarray,
    a: float,
    b: float,
    kind: str = "rectangles",
    truth: float | None = None,
    samples: float = 200,
    rng: np.random.Generator,
) -> MethodResult:
    """`est` : l'intégrale de f sur [a, b] ; `error` : `est - truth` (NaN sans `truth`).

    `x`, `f` : tableaux `(repeat, n)` ; `a < b` ; `samples` : points tirés pour `monte_carlo` (au plus n).
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {list(_KINDS)}, reçu {kind!r}.")
    x = np.atleast_2d(np.asarray(x, dtype=float))
    f = np.atleast_2d(np.asarray(f, dtype=float))
    if x.shape != f.shape and x.shape[1] == f.shape[1]:
        x = np.broadcast_to(x, f.shape)  # une seule grille pour toutes les répétitions
    if x.shape != f.shape or x.ndim != 2 or x.shape[1] < 2:
        raise ValueError(
            f"quadrature : x et f doivent avoir la même forme (repeat, n) avec n >= 2, "
            f"reçu {x.shape} et {f.shape}."
        )
    a, b = float(a), float(b)
    if not a < b:
        raise ValueError("quadrature : il faut a < b.")
    if np.any(np.diff(x, axis=1) <= 0):
        raise ValueError("quadrature : les points x doivent être strictement croissants.")

    n = x.shape[1]
    with np.errstate(all="ignore"):
        if kind == "rectangles":
            est = (b - a) * f.mean(axis=1)
        elif kind == "trapezes":
            est = np.trapezoid(f, x, axis=1) + _edges(x, f, a, b)
        elif kind == "simpson":
            est = integrate.simpson(f, x=x, axis=1) + _edges(x, f, a, b)
        else:
            m = int(round(float(samples)))
            if not 1 <= m <= n:
                raise ValueError(f"quadrature : samples doit être compris entre 1 et n = {n}.")
            picked = np.sort(rng.choice(n, size=m, replace=False))
            est = (b - a) * f[:, picked].mean(axis=1)
    error = est - float(truth) if truth is not None else np.full_like(est, np.nan)
    return MethodResult(
        reps={"est": est.astype(float), "error": error.astype(float)},
        example={"x": x[0].copy(), "f": f[0].copy()},
    )
