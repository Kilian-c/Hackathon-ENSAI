"""Contrat entre le moteur (R1) et les méthodes mathématiques (R2).

Ce fichier est un contrat figé après contracts-v1 (annexe D du cahier).
Il définit :
- MethodResult : la structure de retour unique de toutes les méthodes ;
- MethodSpec et @register_method : l'enregistrement et les métadonnées (provides, cost) ;
- Les fonctions de vérification utilisées au chargement YAML et à l'exécution.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

VALID_BLOCKS: frozenset[str] = frozenset({"reps", "example", "curves", "summary"})


@dataclass
class MethodResult:
    """Structure de retour standard d'une méthode (annexe D.2).

    Attributes:
        reps: Un tableau 1D de forme (repeat,) par grandeur (ex: est, low, high, hit).
              Vide pour les méthodes déterministes (ode, function).
        example: Un tableau 1D de forme (n,) par grandeur pour la répétition 0
                 (ex: x, y, y_hat, resid). Vide pour les méthodes déterministes.
        curves: Tableaux NumPy de courbes déjà calculées (ex: t, theta, paths).
        summary: Grandeurs scalaires globales lues par l'agrégateur summary(k).
    """

    reps: dict[str, np.ndarray] = field(default_factory=dict)
    example: dict[str, np.ndarray] = field(default_factory=dict)
    curves: dict[str, np.ndarray] = field(default_factory=dict)
    summary: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class MethodSpec:
    """Métadonnées et fonction associée d'une méthode enregistrée."""

    name: str
    fn: Callable[..., MethodResult]
    provides: dict[str, tuple[str, ...]]
    cost: str

    def provides_path(self, path: str) -> bool:
        """Vérifie si un chemin de type 'reps.hit' ou 'example.resid' est déclaré."""
        parts = path.split(".", 1)
        if len(parts) != 2:
            return False
        block, key = parts
        return block in self.provides and key in self.provides[block]


_REGISTRY: dict[str, MethodSpec] = {}


def register_method(
    name: str,
    *,
    provides: dict[str, list[str] | tuple[str, ...]],
    cost: str,
) -> Callable[[Callable[..., MethodResult]], Callable[..., MethodResult]]:
    """Décorateur enregistrant une méthode dans le registre du moteur (annexe D.1).

    Args:
        name: Identifiant appelé dans le YAML (champ `call`).
        provides: Dictionnaire {bloc: [clés...]} parmi reps, example, curves, summary.
        cost: Expression de coût de calcul (ex: "repeat * n" ou "t_end / dt").
    """
    if not name or not isinstance(name, str):
        raise ValueError("Le nom d'une méthode doit être une chaîne non vide.")

    unknown_blocks = set(provides.keys()) - VALID_BLOCKS
    if unknown_blocks:
        raise ValueError(
            f"Méthode '{name}' : blocs inconnus dans provides : {sorted(unknown_blocks)}. "
            f"Blocs autorisés : {sorted(VALID_BLOCKS)}."
        )

    if not cost or not isinstance(cost, str):
        raise ValueError(f"Méthode '{name}' : cost doit être une expression non vide.")

    normalized_provides: dict[str, tuple[str, ...]] = {}
    for block, keys in provides.items():
        if not isinstance(keys, (list, tuple)) or not all(
            isinstance(k, str) and k for k in keys
        ):
            raise ValueError(
                f"Méthode '{name}' : les clés du bloc '{block}' doivent être des chaînes non vides."
            )
        if len(set(keys)) != len(keys):
            raise ValueError(
                f"Méthode '{name}' : clés en double dans provides['{block}']."
            )
        normalized_provides[block] = tuple(keys)

    def decorator(fn: Callable[..., MethodResult]) -> Callable[..., MethodResult]:
        if name in _REGISTRY:
            raise ValueError(f"La méthode '{name}' est déjà enregistrée.")
        _REGISTRY[name] = MethodSpec(
            name=name,
            fn=fn,
            provides=normalized_provides,
            cost=cost,
        )
        return fn

    return decorator


def get_method(name: str) -> MethodSpec:
    """Retourne la spécification d'une méthode enregistrée."""
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY)) or "(aucune)"
        raise KeyError(
            f"Méthode inconnue : '{name}'. Méthodes disponibles : {available}."
        )
    return _REGISTRY[name]


def list_methods() -> dict[str, MethodSpec]:
    """Retourne une copie du registre de toutes les méthodes enregistrées."""
    return dict(_REGISTRY)


def _is_real_scalar(value: Any) -> bool:
    """Vérifie qu'une valeur est un scalaire numérique (int/float/np.number, hors bool)."""
    return isinstance(value, (int, float, np.number)) and not isinstance(value, bool)


def validate_method_result(
    spec: MethodSpec,
    result: MethodResult,
    *,
    repeat: int | None = None,
    n: int | None = None,
) -> None:
    """Vérifie qu'un MethodResult respecte exactement ce que déclare la méthode (annexe D.3).

    Lève ValueError ou TypeError au moindre écart (clé manquante, clé en trop,
    mauvais type ou mauvaise forme de tableau).
    """
    if not isinstance(result, MethodResult):
        raise TypeError(
            f"Méthode '{spec.name}' : doit renvoyer un MethodResult, reçu {type(result).__name__}."
        )

    for block in VALID_BLOCKS:
        actual_dict: dict[str, Any] = getattr(result, block)
        if not isinstance(actual_dict, dict):
            raise TypeError(
                f"Méthode '{spec.name}' : le bloc '{block}' doit être un dict."
            )

        expected_keys = set(spec.provides.get(block, ()))
        actual_keys = set(actual_dict.keys())

        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        if missing or extra:
            details: list[str] = []
            if missing:
                details.append(f"manquantes={sorted(missing)}")
            if extra:
                details.append(f"inattendues={sorted(extra)}")
            raise ValueError(
                f"Méthode '{spec.name}' : clés non conformes dans '{block}' "
                f"({', '.join(details)})."
            )

    # Vérification des formes et types bloc par bloc
    for key, arr in result.reps.items():
        if not isinstance(arr, np.ndarray):
            raise TypeError(
                f"Méthode '{spec.name}' : reps['{key}'] doit être un np.ndarray."
            )
        if arr.ndim != 1:
            raise ValueError(
                f"Méthode '{spec.name}' : reps['{key}'] doit être 1D, reçu forme {arr.shape}."
            )
        if repeat is not None and arr.shape != (repeat,):
            raise ValueError(
                f"Méthode '{spec.name}' : reps['{key}'] attendu ({repeat},), reçu {arr.shape}."
            )

    for key, arr in result.example.items():
        if not isinstance(arr, np.ndarray):
            raise TypeError(
                f"Méthode '{spec.name}' : example['{key}'] doit être un np.ndarray."
            )
        if arr.ndim != 1:
            raise ValueError(
                f"Méthode '{spec.name}' : example['{key}'] doit être 1D, reçu forme {arr.shape}."
            )
        if n is not None and arr.shape != (n,):
            raise ValueError(
                f"Méthode '{spec.name}' : example['{key}'] attendu ({n},), reçu {arr.shape}."
            )

    for key, arr in result.curves.items():
        if not isinstance(arr, np.ndarray):
            raise TypeError(
                f"Méthode '{spec.name}' : curves['{key}'] doit être un np.ndarray."
            )
        if arr.ndim < 1:
            raise ValueError(
                f"Méthode '{spec.name}' : curves['{key}'] doit avoir au moins 1 dimension."
            )

    for key, val in result.summary.items():
        if not _is_real_scalar(val):
            raise TypeError(
                f"Méthode '{spec.name}' : summary['{key}'] doit être un nombre réel, "
                f"reçu {type(val).__name__}."
            )