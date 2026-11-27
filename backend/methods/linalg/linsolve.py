"""Méthode `linsolve` : résoudre A x = b, directement (Gauss, Gauss avec pivot, Cholesky) ou par itérations
(Jacobi, Gauss-Seidel, gradient conjugué), vectorisée sur les répétitions.

Le système est construit ici à partir des entrées aléatoires `a` (forme `(repeat, d * d)`) :
A = (G + Gᵀ) / sqrt(2 d) + shift * I (symétrique, spectre de G dans [-2, 2] puis décalé de `shift`), et
b = A 1 : la solution exacte est le vecteur de 1, ce qui donne l'erreur sans second calcul.
A est définie positive si et seulement si `shift > 2`. Jacobi converge si et seulement si son rayon spectral
(environ 2 / shift) est inférieur à 1 ; Cholesky exige une matrice définie positive ; Gauss avec pivot et la
méthode directe fonctionnent toujours quand A est inversible.
"""

from __future__ import annotations

import numpy as np

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("gauss", "gauss_pivot", "cholesky", "jacobi", "gauss_seidel", "cg")
_ITERATIVE = ("jacobi", "gauss_seidel", "cg")
MAX_ITERS = 200
FAILED_LOG_ERROR = 16.0  # erreur 10^16 : échec (division par zéro, divergence, matrice non définie positive)


def _matvec(a: np.ndarray, v: np.ndarray) -> np.ndarray:
    return np.einsum("rij,rj->ri", a, v)


def _back_substitution(u: np.ndarray, y: np.ndarray) -> np.ndarray:
    d = u.shape[1]
    x = np.zeros_like(y)
    for i in range(d - 1, -1, -1):
        x[:, i] = (y[:, i] - np.einsum("rj,rj->r", u[:, i, i + 1 :], x[:, i + 1 :])) / u[:, i, i]
    return x


def _forward_substitution(low: np.ndarray, y: np.ndarray) -> np.ndarray:
    d = low.shape[1]
    x = np.zeros_like(y)
    for i in range(d):
        x[:, i] = (y[:, i] - np.einsum("rj,rj->r", low[:, i, :i], x[:, :i])) / low[:, i, i]
    return x


def _gauss(a: np.ndarray, b: np.ndarray, pivot: bool) -> np.ndarray:
    r, d, _ = a.shape
    m = np.concatenate([a, b[:, :, None]], axis=2)
    rows = np.arange(r)
    for k in range(d):
        if pivot:
            best = np.argmax(np.abs(m[:, k:, k]), axis=1) + k
            swap = m[rows, k].copy()
            m[rows, k] = m[rows, best]
            m[rows, best] = swap
        factors = m[:, k + 1 :, k] / m[:, k, k][:, None]
        m[:, k + 1 :, :] -= factors[:, :, None] * m[:, k, None, :]
    return _back_substitution(m[:, :, :d], m[:, :, d])


def _cholesky(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    low = np.full_like(a, np.nan)
    for i in range(a.shape[0]):
        try:
            low[i] = np.linalg.cholesky(a[i])
        except np.linalg.LinAlgError:  # pas définie positive : cette répétition échoue
            pass
    y = _forward_substitution(low, b)
    return _back_substitution(np.swapaxes(low, 1, 2), y)


def _iterate(kind: str, a: np.ndarray, b: np.ndarray, iters: int, truth: np.ndarray):
    """Jacobi, Gauss-Seidel ou gradient conjugué ; renvoie x et l'erreur médiane (log10) par itération."""
    r, d, _ = a.shape
    diag = np.diagonal(a, axis1=1, axis2=2)
    x = np.zeros((r, d))
    history = [_median_log_error(x, truth)]
    if kind == "cg":
        res, p = b.copy(), b.copy()
    for _ in range(iters):
        if kind == "jacobi":
            x = (b - (_matvec(a, x) - diag * x)) / diag
        elif kind == "gauss_seidel":
            for i in range(d):
                before = np.einsum("rj,rj->r", a[:, i, :i], x[:, :i])
                after = np.einsum("rj,rj->r", a[:, i, i + 1 :], x[:, i + 1 :])
                s = before + after
                x[:, i] = (b[:, i] - s) / a[:, i, i]
        else:  # gradient conjugué
            ap = _matvec(a, p)
            rr = np.einsum("ri,ri->r", res, res)
            denom = np.einsum("ri,ri->r", p, ap)
            alpha = np.divide(rr, denom, out=np.zeros_like(rr), where=denom != 0)
            x = x + alpha[:, None] * p
            res = res - alpha[:, None] * ap
            beta = np.divide(np.einsum("ri,ri->r", res, res), rr, out=np.zeros_like(rr), where=rr != 0)
            p = res + beta[:, None] * p
        history.append(_median_log_error(x, truth))
    return x, history


def _log_error(x: np.ndarray, truth: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        err = np.linalg.norm(x - truth, axis=1) / np.linalg.norm(truth, axis=1)
        log = np.log10(np.maximum(err, 1e-16))
    return np.where(np.isfinite(log), np.minimum(log, FAILED_LOG_ERROR), FAILED_LOG_ERROR)


def _median_log_error(x: np.ndarray, truth: np.ndarray) -> float:
    return float(np.median(_log_error(x, truth)))


@register_method(
    "linsolve",
    provides={
        "reps": ["log_error", "failed"],
        "curves": ["matrix", "k", "history"],
    },
    cost="repeat * d**3",
)
def linsolve(
    *,
    a: np.ndarray,
    d: float,
    shift: float = 3.0,
    kind: str = "gauss_pivot",
    iters: float = 60,
    rng: np.random.Generator,
) -> MethodResult:
    """Résout A x = b pour A = (G + Gᵀ) / sqrt(2 d) + shift I et b = A 1 (solution exacte : le vecteur de 1).

    `log_error` : log10 de l'erreur relative ||x - 1|| / ||1||, au plus 16 (échec : division par zéro,
    divergence ou matrice non définie positive pour Cholesky) ; `failed` : vrai pour un échec.
    `kind` : gauss, gauss_pivot, cholesky (directes) ; jacobi, gauss_seidel, cg (`iters` itérations).
    `matrix` : A de la répétition 0 ; `k`, `history` : erreur médiane (log10) après k itérations
    (constante pour une méthode directe).
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
            f"linsolve : a doit avoir d * d = {size * size} colonnes (une matrice d x d par répétition), "
            f"reçu la forme {a.shape}. Écrivez n: p.d * p.d dans le générateur."
        )
    g = a.reshape(a.shape[0], size, size)
    mat = (g + np.swapaxes(g, 1, 2)) / np.sqrt(2.0 * size) + float(shift) * np.eye(size)
    truth = np.ones((a.shape[0], size))
    b = _matvec(mat, truth)
    with np.errstate(all="ignore"):
        if kind in _ITERATIVE:
            solution, history = _iterate(kind, mat.copy(), b, steps, truth)
        else:
            if kind == "cholesky":
                solution = _cholesky(mat, b)
            else:
                solution = _gauss(mat.copy(), b, pivot=kind == "gauss_pivot")
            history = [_median_log_error(solution, truth)] * (steps + 1)
    log_error = _log_error(solution, truth)
    return MethodResult(
        reps={"log_error": log_error, "failed": log_error >= FAILED_LOG_ERROR},
        curves={
            "matrix": mat[0],
            "k": np.arange(len(history), dtype=float),
            "history": np.asarray(history, dtype=float),
        },
    )
