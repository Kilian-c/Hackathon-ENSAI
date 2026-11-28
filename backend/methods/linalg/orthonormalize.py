"""Méthode `orthonormalize` : factorisation A = Q R d'une matrice aux colonnes presque dépendantes, par
Gram-Schmidt classique (cgs), Gram-Schmidt modifié (mgs) ou réflexions de Householder, vectorisée sur les
répétitions.

La matrice est construite ici à partir des entrées aléatoires `a` (forme `(repeat, d * d)`) :
A = U diag(σ) Uᵀ, où U est orthogonale (factorisation QR des entrées) et les valeurs singulières σ décroissent
de 1 à 10^(-decades) : le conditionnement vaut 10^decades. Plus il est grand, plus les colonnes de A sont
presque dépendantes. La perte d'orthogonalité ||QᵀQ - I|| vaut environ ε · cond² pour Gram-Schmidt classique,
ε · cond pour Gram-Schmidt modifié et ε pour Householder (ε = 1,1e-16).
"""

from __future__ import annotations

import numpy as np

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("cgs", "mgs", "householder")
FLOOR_LOG = -16.0
FAILED_LOG = 16.0


def _gram_schmidt(a: np.ndarray, modified: bool) -> np.ndarray:
    """Colonnes orthonormées de `a` (forme `(repeat, d, d)`), une colonne après l'autre."""
    r, d, _ = a.shape
    q = np.zeros_like(a)
    for j in range(d):
        v = a[:, :, j].copy()
        previous = q[:, :, :j]
        if modified:  # chaque projection utilise le vecteur déjà corrigé
            for i in range(j):
                coefficient = np.einsum("rd,rd->r", q[:, :, i], v)
                v -= coefficient[:, None] * q[:, :, i]
        else:  # tous les coefficients sont calculés sur le vecteur d'origine
            coefficients = np.einsum("rdi,rd->ri", previous, a[:, :, j])
            v -= np.einsum("rdi,ri->rd", previous, coefficients)
        q[:, :, j] = v / np.linalg.norm(v, axis=1, keepdims=True)
    return q


def _log(values: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        out = np.log10(np.maximum(values, 10.0**FLOOR_LOG))
    return np.where(np.isfinite(out), np.minimum(out, FAILED_LOG), FAILED_LOG)


@register_method(
    "orthonormalize",
    provides={
        "reps": ["log_ortho", "log_resid", "failed"],
        "curves": ["matrix"],
    },
    cost="repeat * d**3",
)
def orthonormalize(
    *,
    a: np.ndarray,
    d: float,
    decades: float = 1.0,
    kind: str = "householder",
    rng: np.random.Generator,
) -> MethodResult:
    """Factorise A = Q R et mesure ce que vaut Q.

    `log_ortho` : log10 de ||QᵀQ - I||_F (perte d'orthogonalité), entre -16 et 16 ; `log_resid` : log10 de
    ||A - Q R||_F / ||A||_F (la factorisation reproduit bien A) ; `failed` : vrai si Q n'est pas un nombre
    fini. `kind` : cgs, mgs ou householder (LAPACK). `matrix` : QᵀQ de la répétition 0, qui vaut l'identité
    quand Q est orthonormée.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {sorted(_KINDS)}, reçu {kind!r}.")
    size = int(round(float(d)))
    a = np.asarray(a, dtype=float)
    if a.ndim != 2 or a.shape[1] != size * size:
        raise ValueError(
            f"orthonormalize : a doit avoir d * d = {size * size} colonnes (une matrice d x d par "
            f"répétition), reçu la forme {a.shape}. Écrivez n: p.d * p.d dans le générateur."
        )
    if not 0.0 <= float(decades) <= 15.0:
        raise ValueError("decades doit être compris entre 0 et 15 (conditionnement de 1 à 10^15).")
    g = a.reshape(a.shape[0], size, size)
    u, _ = np.linalg.qr(g)
    sigma = 10.0 ** (-float(decades) * np.arange(size) / max(size - 1, 1))
    mat = np.einsum("rij,j,rkj->rik", u, sigma, u)  # U diag(sigma) Uᵀ
    with np.errstate(all="ignore"):
        if kind == "householder":
            q, _ = np.linalg.qr(mat)
        else:
            q = _gram_schmidt(mat, modified=kind == "mgs")
        gram = np.einsum("rdi,rdj->rij", q, q)
        loss = np.linalg.norm(gram - np.eye(size), axis=(1, 2))
        upper = np.einsum("rdi,rdj->rij", q, mat)  # R = Qᵀ A
        rebuilt = np.einsum("rdi,rij->rdj", q, np.triu(upper))
        resid = np.linalg.norm(mat - rebuilt, axis=(1, 2)) / np.linalg.norm(mat, axis=(1, 2))
    log_ortho = _log(loss)
    return MethodResult(
        reps={
            "log_ortho": log_ortho,
            "log_resid": _log(resid),
            "failed": ~np.isfinite(q).all(axis=(1, 2)),
        },
        curves={"matrix": gram[0]},
    )
