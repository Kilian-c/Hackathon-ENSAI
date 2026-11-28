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


@register_method(
    "iterated_integral",
    provides={"reps": ["est", "error"], "curves": ["matrix"]},
    cost="repeat * n",
)
def iterated_integral(
    *,
    x: np.ndarray,
    y: np.ndarray,
    f: np.ndarray,
    truth: float | None = None,
    rng: np.random.Generator,
) -> MethodResult:
    """Intégrale double de f sur [0, 1]², sommée sur une grille rectangulaire A × B de milieux de cellules.

    Le générateur numérote les points `idx` de façon que `x` prenne A valeurs et `y` B valeurs, avec
    `n = A * B` (x varie lentement, y vite). Choisir A petit et B grand revient à intégrer d'abord en y
    (intégrale intérieure presque exacte), puis en x : c'est l'intégrale itérée dy puis dx ; A grand et
    B petit donne l'ordre inverse. `est` : la moyenne de f (l'aire du carré vaut 1) ;
    `error` : `est - truth` (NaN sans `truth`) ; `matrix` : f de la répétition 0 sur la grille,
    sous-échantillonnée à 64 lignes et colonnes au plus.
    """
    x = np.atleast_2d(np.asarray(x, dtype=float))
    y = np.atleast_2d(np.asarray(y, dtype=float))
    f = np.atleast_2d(np.asarray(f, dtype=float))
    if x.shape != f.shape and x.shape[1] == f.shape[1]:
        x = np.broadcast_to(x, f.shape)
    if y.shape != f.shape and y.shape[1] == f.shape[1]:
        y = np.broadcast_to(y, f.shape)
    if x.shape != f.shape or y.shape != f.shape or f.ndim != 2:
        raise ValueError(
            f"iterated_integral : x, y et f doivent avoir la même forme (repeat, n), "
            f"reçu {x.shape}, {y.shape} et {f.shape}."
        )
    n = f.shape[1]
    a = len(np.unique(x[0]))
    if a < 1 or n % a != 0:
        raise ValueError("iterated_integral : n doit être un multiple du nombre de valeurs de x.")
    b = n // a
    if len(np.unique(y[0])) != b:
        raise ValueError("iterated_integral : la grille doit être rectangulaire (A valeurs de x, B de y).")
    est = f.mean(axis=1)
    error = est - float(truth) if truth is not None else np.full_like(est, np.nan)
    grid = f[0].reshape(a, b)
    grid = grid[:: max(1, -(-a // 64)), :: max(1, -(-b // 64))]
    return MethodResult(
        reps={"est": est.astype(float), "error": error.astype(float)},
        curves={"matrix": grid.copy()},
    )


@register_method(
    "iterated_integrals",
    provides={"reps": ["dy_dx", "dx_dy", "gap"], "curves": ["t", "dy", "dx"]},
    cost="repeat * n",
)
def iterated_integrals(
    *,
    x: np.ndarray,
    y: np.ndarray,
    f: np.ndarray,
    rng: np.random.Generator,
) -> MethodResult:
    """Les deux intégrales itérées de f sur [0, 1]², chacune sur une grille adaptée à son ordre.

    Les `n` points se coupent en deux moitiés. La première est une grille A × B (x lent, A petit, B grand) :
    la moyenne de f par ligne approche l'intégrale intérieure F(x) = ∫ f(x, y) dy avec précision, puis la
    moyenne des F donne `dy_dx` (d'abord en y). La seconde est la grille transposée (A' grand, B' petit) :
    la moyenne par colonne approche G(y) = ∫ f(x, y) dx, puis `dx_dy` (d'abord en x). `gap` = `dy_dx - dx_dy`.
    `curves` (répétition 0) : `t` (101 points de [0, 1]), `dy` = F et `dx` = G, interpolées sur `t`.
    """
    x = np.atleast_2d(np.asarray(x, dtype=float))
    y = np.atleast_2d(np.asarray(y, dtype=float))
    f = np.atleast_2d(np.asarray(f, dtype=float))
    if x.shape != f.shape and x.shape[1] == f.shape[1]:
        x = np.broadcast_to(x, f.shape)
    if y.shape != f.shape and y.shape[1] == f.shape[1]:
        y = np.broadcast_to(y, f.shape)
    if x.shape != f.shape or y.shape != f.shape or f.ndim != 2:
        raise ValueError(
            f"iterated_integrals : x, y et f doivent avoir la même forme (repeat, n), "
            f"reçu {x.shape}, {y.shape} et {f.shape}."
        )
    reps, n = f.shape
    half = n // 2
    if n % 2 or half < 2:
        raise ValueError("iterated_integrals : n doit être pair (deux grilles de n / 2 points).")
    a = len(np.unique(x[0, :half]))
    a2 = len(np.unique(x[0, half:]))
    if a < 1 or half % a != 0 or half % a2 != 0:
        raise ValueError("iterated_integrals : chaque moitié doit former une grille rectangulaire.")
    b2 = half // a2
    f_rows = f[:, :half].reshape(reps, a, half // a)
    f_cols = f[:, half:].reshape(reps, a2, b2)
    inner_dy = f_rows.mean(axis=2)  # (reps, a) : F(x_i)
    inner_dx = f_cols.mean(axis=1)  # (reps, b2) : G(y_j)
    dy_dx = inner_dy.mean(axis=1)
    dx_dy = inner_dx.mean(axis=1)
    xs = x[0, :half].reshape(a, -1)[:, 0]
    ys = y[0, half:].reshape(a2, b2)[0]
    t = np.linspace(0.0, 1.0, 101)
    return MethodResult(
        reps={
            "dy_dx": dy_dx.astype(float),
            "dx_dy": dx_dy.astype(float),
            "gap": (dy_dx - dx_dy).astype(float),
        },
        curves={"t": t, "dy": np.interp(t, xs, inner_dy[0]), "dx": np.interp(t, ys, inner_dx[0])},
    )
