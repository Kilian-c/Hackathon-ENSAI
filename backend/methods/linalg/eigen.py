"""Méthode `eigen` : la valeur propre de plus grand module d'une matrice symétrique aléatoire, par la
méthode de la puissance, par l'algorithme QR, ou directement (LAPACK), vectorisée sur les répétitions.

La matrice est construite ici à partir des entrées aléatoires `a` (forme `(repeat, d * d)`) :
A = (G + Gᵀ) / sqrt(2 d) + spike * v vᵀ, où v = (1, ..., 1) / sqrt(d). Sans pic (`spike = 0`), c'est une
matrice de Wigner : son spectre remplit [-2, 2] et les valeurs propres de plus grand module, proches de +2
et de -2, ont presque le même module. Avec un pic `spike > 1`, une valeur propre se détache, vers
spike + 1 / spike. La méthode de la puissance et l'algorithme QR convergent à la vitesse |λ₂ / λ₁| : lentement
quand le plus grand module n'est pas isolé ; avec deux valeurs propres opposées de même module, le vecteur
oscille.
"""

from __future__ import annotations

import numpy as np

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("power", "qr", "numpy")
MAX_ITERS = 200
FLOOR_LOG_ERROR = -16.0
FAILED_LOG_ERROR = 16.0


def _dominant(eig: np.ndarray) -> np.ndarray:
    """Valeur propre de plus grand module (signe conservé), pour chaque ligne de `eig`."""
    index = np.argmax(np.abs(eig), axis=1)
    return eig[np.arange(eig.shape[0]), index]


def _log_error(estimate: np.ndarray, truth: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        err = np.abs(estimate - truth) / np.abs(truth)
        log = np.log10(np.maximum(err, 10.0**FLOOR_LOG_ERROR))
    return np.where(np.isfinite(log), np.minimum(log, FAILED_LOG_ERROR), FAILED_LOG_ERROR)


def _median(estimate: np.ndarray, truth: np.ndarray) -> float:
    return float(np.median(_log_error(estimate, truth)))


def _power(a: np.ndarray, start: np.ndarray, iters: int, truth: np.ndarray):
    v = start / np.linalg.norm(start, axis=1, keepdims=True)
    estimate = np.einsum("ri,ri->r", v, np.einsum("rij,rj->ri", a, v))
    history = [_median(estimate, truth)]
    for _ in range(iters):
        w = np.einsum("rij,rj->ri", a, v)
        v = w / np.linalg.norm(w, axis=1, keepdims=True)
        estimate = np.einsum("ri,ri->r", v, np.einsum("rij,rj->ri", a, v))  # quotient de Rayleigh
        history.append(_median(estimate, truth))
    return estimate, history


def _qr(a: np.ndarray, iters: int, truth: np.ndarray):
    """Algorithme QR sans décalage : A_{k+1} = R_k Q_k. La diagonale tend vers les valeurs propres."""
    current = a.copy()
    estimate = _dominant(np.diagonal(current, axis1=1, axis2=2))
    history = [_median(estimate, truth)]
    for _ in range(iters):
        q, r = np.linalg.qr(current)
        current = r @ q
        estimate = _dominant(np.diagonal(current, axis1=1, axis2=2))
        history.append(_median(estimate, truth))
    return estimate, history


@register_method(
    "eigen",
    provides={
        "reps": ["log_error", "estimate", "failed"],
        "curves": ["matrix", "k", "history"],
    },
    cost="repeat * iters * d**3",
)
def eigen(
    *,
    a: np.ndarray,
    d: float,
    spike: float = 3.0,
    kind: str = "numpy",
    iters: float = 60,
    rng: np.random.Generator,
) -> MethodResult:
    """Estime la valeur propre de plus grand module de A = Wigner + spike v vᵀ.

    `estimate` : l'estimation ; `log_error` : log10 de l'erreur relative à la valeur exacte (LAPACK), entre
    -16 et 16 ; `failed` : vrai si l'estimation n'est pas un nombre fini. `kind` : power (puissance, vecteur
    de départ aléatoire, quotient de Rayleigh), qr (algorithme QR, `iters` itérations) ou numpy (directe).
    `matrix` : A de la répétition 0 ; `k`, `history` : erreur médiane (log10) après k itérations (constante
    pour la méthode directe).
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {sorted(_KINDS)}, reçu {kind!r}.")
    size = int(round(float(d)))
    steps = int(round(float(iters)))
    if not 1 <= steps <= MAX_ITERS:
        raise ValueError(f"iters doit être compris entre 1 et {MAX_ITERS}.")
    a = np.asarray(a, dtype=float)
    if a.ndim != 2 or a.shape[1] != size * size:
        raise ValueError(
            f"eigen : a doit avoir d * d = {size * size} colonnes (une matrice d x d par répétition), "
            f"reçu la forme {a.shape}. Écrivez n: p.d * p.d dans le générateur."
        )
    g = a.reshape(a.shape[0], size, size)
    mat = (g + np.swapaxes(g, 1, 2)) / np.sqrt(2.0 * size) + float(spike) / size * np.ones((size, size))
    truth = _dominant(np.linalg.eigvalsh(mat))
    with np.errstate(all="ignore"):
        if kind == "power":
            estimate, history = _power(mat, rng.standard_normal((mat.shape[0], size)), steps, truth)
        elif kind == "qr":
            estimate, history = _qr(mat, steps, truth)
        else:
            estimate = truth.copy()
            history = [_median(estimate, truth)] * (steps + 1)
    log_error = _log_error(estimate, truth)
    return MethodResult(
        reps={"log_error": log_error, "estimate": estimate, "failed": ~np.isfinite(estimate)},
        curves={
            "matrix": mat[0],
            "k": np.arange(len(history), dtype=float),
            "history": np.asarray(history, dtype=float),
        },
    )
