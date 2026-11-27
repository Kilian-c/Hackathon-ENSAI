"""Registre des lois de probabilité tirées depuis des uniformes communes (Table 7).

Toutes les lois sont comparées à échelle égale :
- moyenne 0 et variance 1 quand elles existent (normal, uniform, exponential, bimodal) ;
- médiane 0 et écart interquartile (IQR) de la loi normale sinon (student_2, cauchy).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.special import ndtri

# Bornes numériques pour éviter u = 0 ou u = 1 (qui produiraient ±inf ou NaN)
_U_EPS: float = 1e-12

# Quartile supérieur de N(0, 1) : Φ⁻¹(0.75) ≈ 0.67448975 (IQR = 2 * _NORM_Q75)
_NORM_Q75: float = float(ndtri(0.75))

# Facteurs de mise à l'échelle pour aligner l'IQR sur celui de N(0, 1) :
# - t_2 brute a son Q75 en sqrt(2/3)
# - Cauchy brute a son Q75 en tan(pi/4) = 1
_STUDENT2_SCALE: float = _NORM_Q75 / float(np.sqrt(2.0 / 3.0))
_CAUCHY_SCALE: float = _NORM_Q75

# Paramètres du mélange symétrique 0.5 * N(-mu, sigma^2) + 0.5 * N(+mu, sigma^2)
# Variance totale = mu^2 + sigma^2 = 1.0, modes bien séparés (mu / sigma > 2)
_BIMODAL_MU: float = 0.9
_BIMODAL_SIGMA: float = float(np.sqrt(1.0 - _BIMODAL_MU**2))


@dataclass(frozen=True)
class LawSpec:
    """Spécification d'une loi du registre."""

    name: str
    has_mean: bool
    has_variance: bool
    n_uniforms: int
    transform: Callable[..., np.ndarray]


def _normal(u: np.ndarray) -> np.ndarray:
    """Loi normale centrée réduite N(0, 1)."""
    return ndtri(u)


def _uniform(u: np.ndarray) -> np.ndarray:
    """Loi uniforme sur [-sqrt(3), +sqrt(3)] : moyenne 0, variance 1."""
    return np.sqrt(3.0) * (2.0 * u - 1.0)


def _exponential(u: np.ndarray) -> np.ndarray:
    """Loi exponentielle centrée réduite : moyenne 0, variance 1."""
    return -np.log(1.0 - u) - 1.0


def _student_2(u: np.ndarray) -> np.ndarray:
    """Loi de Student à 2 ddl, mise à l'échelle sur l'IQR de N(0, 1)."""
    raw = (2.0 * u - 1.0) / np.sqrt(2.0 * u * (1.0 - u))
    return _STUDENT2_SCALE * raw


def _cauchy(u: np.ndarray) -> np.ndarray:
    """Loi de Cauchy centrée, mise à l'échelle sur l'IQR de N(0, 1)."""
    raw = np.tan(np.pi * (u - 0.5))
    return _CAUCHY_SCALE * raw


def _bimodal(u_comp: np.ndarray, u_pos: np.ndarray) -> np.ndarray:
    """Mélange symétrique de deux normales : moyenne 0, variance 1.

    u_comp choisit le mode (-mu si < 0.5, +mu sinon), ce qui conserve le signe
    par rapport à la loi normale de référence ; u_pos tire la position dans le mode.
    """
    sign = np.where(u_comp < 0.5, -1.0, 1.0)
    return sign * _BIMODAL_MU + _BIMODAL_SIGMA * ndtri(u_pos)


_LAWS: dict[str, LawSpec] = {
    "normal": LawSpec(
        name="normal",
        has_mean=True,
        has_variance=True,
        n_uniforms=1,
        transform=_normal,
    ),
    "uniform": LawSpec(
        name="uniform",
        has_mean=True,
        has_variance=True,
        n_uniforms=1,
        transform=_uniform,
    ),
    "exponential": LawSpec(
        name="exponential",
        has_mean=True,
        has_variance=True,
        n_uniforms=1,
        transform=_exponential,
    ),
    "student_2": LawSpec(
        name="student_2",
        has_mean=True,
        has_variance=False,
        n_uniforms=1,
        transform=_student_2,
    ),
    "cauchy": LawSpec(
        name="cauchy",
        has_mean=False,
        has_variance=False,
        n_uniforms=1,
        transform=_cauchy,
    ),
    "bimodal": LawSpec(
        name="bimodal",
        has_mean=True,
        has_variance=True,
        n_uniforms=2,
        transform=_bimodal,
    ),
}


def get_law(name: str) -> LawSpec:
    """Retourne la spécification d'une loi du registre."""
    if name not in _LAWS:
        available = ", ".join(sorted(_LAWS))
        raise KeyError(f"Loi inconnue : '{name}'. Lois disponibles : {available}.")
    return _LAWS[name]


def list_laws() -> dict[str, LawSpec]:
    """Retourne une copie du registre des lois."""
    return dict(_LAWS)


def sample_law(
    name: str,
    rng: np.random.Generator,
    shape: tuple[int, ...],
) -> np.ndarray:
    """Tire un tableau de forme `shape` selon la loi `name` depuis le flux `rng`.

    Utilise des uniformes communes bornées dans [_U_EPS, 1 - _U_EPS] pour éviter
    toute valeur ±inf ou NaN aux extrémités des fonctions quantiles.
    """
    spec = get_law(name)
    if spec.n_uniforms == 1:
        u = np.clip(rng.random(shape), _U_EPS, 1.0 - _U_EPS)
        return spec.transform(u)
    u1 = np.clip(rng.random(shape), _U_EPS, 1.0 - _U_EPS)
    u2 = np.clip(rng.random(shape), _U_EPS, 1.0 - _U_EPS)
    return spec.transform(u1, u2)
