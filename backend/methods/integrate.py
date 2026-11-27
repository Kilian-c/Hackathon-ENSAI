"""Intégration d'EDO à pas fixe : Euler explicite et Runge-Kutta d'ordre 4 (annexe D).

Le générateur `ode` (R1) fournit `system`. Cette méthode lit dessus, par attributs
ou par clés (dict) :
- `rhs(y)` : second membre, `y` est un tableau dans l'ordre des variables d'état,
  la valeur renvoyée a la même forme ;
- `y0` : conditions initiales dans le même ordre (la première variable est l'angle) ;
- `t_end` : durée simulée ;
- `t` (facultatif) : grille d'affichage, 400 points de 0 à t_end par défaut ;
- `ref` (facultatif) : solution de référence de l'angle sur `t`. Absente, elle est
  recalculée avec `solve_ivp` (tolérance 1e-10).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicHermiteSpline

from backend.engine.method_contract import MethodResult, register_method

_SCHEMES = ("euler", "rk4")
_MAX_STEPS = 200_000
# RK4 est d'ordre 4 : au-delà, des pas plus fins n'ajoutent que du temps de calcul
# (erreur déjà < 1e-8 pour le pendule), alors qu'Euler doit garder son vrai pas.
_RK4_MAX_STEPS = 4_000
_N_GRID = 400


def _get(system: Any, name: str, default: Any = None) -> Any:
    if isinstance(system, dict):
        return system.get(name, default)
    return getattr(system, name, default)


def _euler(rhs: Any, y: np.ndarray, h: float) -> np.ndarray:
    return y + h * rhs(y)


def _rk4(rhs: Any, y: np.ndarray, h: float) -> np.ndarray:
    k1 = rhs(y)
    k2 = rhs(y + 0.5 * h * k1)
    k3 = rhs(y + 0.5 * h * k2)
    k4 = rhs(y + h * k3)
    return y + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def _derivatives(rhs: Any, ys: np.ndarray) -> np.ndarray:
    """Second membre en tous les nœuds : d'un coup si rhs accepte (p, N), sinon en boucle."""
    try:
        d = np.asarray(rhs(ys.T), dtype=float)
        if d.shape == ys.T.shape:
            return d.T
    except (TypeError, ValueError, IndexError):
        pass
    return np.array([rhs(row) for row in ys])


@register_method(
    "integrate",
    provides={
        "curves": ["t", "theta"],
        "summary": ["max_rel_error", "energy_drift", "full_turn"],
    },
    cost="t_end / dt",
)
def integrate(
    *,
    system: Any,
    dt: float,
    scheme: str,
    rng: np.random.Generator | None = None,
) -> MethodResult:
    """Intègre `system` avec le pas `dt` (arrondi pour tomber pile sur t_end).

    Renvoie l'angle interpolé sur la grille `t`, l'erreur maximale relative à
    |theta0|, la dérive maximale de l'énergie du pendule (relative à l'énergie
    initiale) et `full_turn` (1 si l'angle dépasse pi en valeur absolue).
    """
    if scheme not in _SCHEMES:
        raise ValueError(f"scheme doit valoir l'un de {_SCHEMES}, reçu {scheme!r}.")
    if not dt > 0:
        raise ValueError("Le pas dt doit être strictement positif.")

    rhs = _get(system, "rhs")
    y0 = np.asarray(_get(system, "y0"), dtype=float)
    t_end = float(_get(system, "t_end"))
    t = _get(system, "t")
    t = np.linspace(0.0, t_end, _N_GRID) if t is None else np.asarray(t, dtype=float)

    n_steps = min(max(1, math.ceil(t_end / dt - 1e-9)), _MAX_STEPS)
    if scheme == "rk4":
        n_steps = min(n_steps, _RK4_MAX_STEPS)
    h = t_end / n_steps
    step = _euler if scheme == "euler" else _rk4

    ys = np.empty((n_steps + 1, y0.size))
    ys[0] = y0
    y = y0
    with np.errstate(all="ignore"):
        for i in range(n_steps):
            y = step(rhs, y, h)
            ys[i + 1] = y
        nodes = np.linspace(0.0, t_end, n_steps + 1)
        d = _derivatives(rhs, ys)
        theta = CubicHermiteSpline(nodes, ys[:, 0], d[:, 0])(t)

        ref = _get(system, "ref")
        if ref is None:
            sol = solve_ivp(
                lambda _t, v: rhs(v), (0.0, t_end), y0, t_eval=t, rtol=1e-10, atol=1e-10
            )
            ref = sol.y[0]
        ref = np.asarray(ref, dtype=float)
        theta0 = abs(float(y0[0])) or 1.0
        max_rel_error = float(np.max(np.abs(theta - ref)) / theta0)

        # Énergie du pendule : E = omega^2 / 2 + k (1 - cos theta), avec k = g / L
        # déduit du second membre (omega' = -k sin theta en theta = pi / 2).
        k = -float(rhs(np.array([math.pi / 2, 0.0]))[1])
        energy = 0.5 * ys[:, 1] ** 2 + k * (1.0 - np.cos(ys[:, 0]))
        e0 = float(energy[0])
        drift = float(np.max(np.abs(energy - e0)) / e0) if e0 > 0 else 0.0
        full_turn = float(np.max(np.abs(ys[:, 0])) > math.pi)

    return MethodResult(
        curves={"t": t, "theta": theta},
        summary={
            "max_rel_error": max_rel_error,
            "energy_drift": drift,
            "full_turn": full_turn,
        },
    )
