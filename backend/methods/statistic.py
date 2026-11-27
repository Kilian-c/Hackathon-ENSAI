"""Méthode générique `statistic` (catalogue, archétype 1 « loi d'une statistique »).

Une statistique calculée sur chaque échantillon (somme, moyenne, maximum, minimum, médiane). L'expérience
ne change que le générateur : somme de dés, maximum d'uniformes, moyenne d'une loi donnée...
"""

from __future__ import annotations

import numpy as np

from backend.engine.method_contract import MethodResult, register_method

_KINDS = {
    "sum": np.sum,
    "mean": np.mean,
    "max": np.max,
    "min": np.min,
    "median": np.median,
}


@register_method(
    "statistic",
    provides={"reps": ["stat"], "example": ["x"]},
    cost="repeat * n",
)
def statistic(
    *,
    x: np.ndarray,
    kind: str,
    continuity: bool = False,
    rng: np.random.Generator,
) -> MethodResult:
    """`stat` : la statistique `kind` de chaque ligne de x, forme (repeat,).

    `continuity` : correction de continuité pour une statistique à valeurs entières (somme de dés) :
    chaque valeur est répartie uniformément sur sa case [v - 0,5 ; v + 0,5]. L'histogramme dessine alors
    la loi discrète en barres jointives, et les mesures de forme la comparent à une loi continue.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {sorted(_KINDS)}, reçu {kind!r}.")
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[None, :]
    stat = _KINDS[kind](x, axis=1).astype(float)
    if continuity:
        stat = stat + rng.uniform(-0.5, 0.5, size=stat.shape)
    return MethodResult(reps={"stat": stat}, example={"x": x[0].copy()})
