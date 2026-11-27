"""Méthodes génériques `formula_*` (R1) : une méthode écrite dans le YAML, sans Python.

Les arguments sont des expressions évaluées par le moteur (même liste blanche que les variables du
générateur : `mean(x, axis=1)`, `sort(x, axis=1)`, `quantile(x, 0.5, axis=1)`...). Une expression qui
réduit l'axe des observations donne une valeur par répétition, forme `(repeat,)` : c'est ce que ces
méthodes reçoivent. Elles n'ajoutent que ce qui rend la valeur lisible par les agrégateurs : écart à la
valeur vraie, rejet d'un test, couverture d'un intervalle.

    - { id: moy, role: method, call: formula_estimate, label: "Moyenne",
        args: { est: "mean(x, axis=1)", truth: "0" } }
"""

from __future__ import annotations

from typing import Any

import numpy as np

from backend.engine.method_contract import MethodResult, register_method


def _vectors(**named: Any) -> dict[str, np.ndarray | None]:
    """Chaque argument devient un tableau `(repeat,)` ; un scalaire est répété. `None` reste `None`."""
    arrays: dict[str, np.ndarray | None] = {}
    size = 1
    for name, value in named.items():
        if value is None:
            arrays[name] = None
            continue
        arr = np.asarray(value, dtype=float)
        if arr.ndim > 1:
            raise ValueError(
                f"La formule « {name} » donne un tableau de forme {arr.shape} : il faut une valeur par "
                "répétition. Réduisez l'axe des observations (par exemple mean(x, axis=1))."
            )
        if arr.ndim == 1:
            size = max(size, arr.shape[0])
        arrays[name] = arr
    return {
        name: None if arr is None else np.broadcast_to(arr, (size,)).astype(float).copy()
        for name, arr in arrays.items()
    }


@register_method(
    "formula_estimate",
    provides={"reps": ["est", "error"]},
    cost="repeat",
)
def formula_estimate(*, est: Any, truth: Any = None, rng: np.random.Generator) -> MethodResult:
    """`est` : l'estimation de chaque répétition (formule) ; `error` : `est - truth` (NaN sans `truth`)."""
    v = _vectors(est=est, truth=truth)
    est_v = v["est"]
    assert est_v is not None
    error = est_v - v["truth"] if v["truth"] is not None else np.full_like(est_v, np.nan)
    return MethodResult(reps={"est": est_v, "error": error})


@register_method(
    "formula_test",
    provides={"reps": ["stat", "pvalue", "reject"]},
    cost="repeat",
)
def formula_test(
    *,
    stat: Any = None,
    pvalue: Any = None,
    critical: Any = None,
    alpha: float = 0.05,
    rng: np.random.Generator,
) -> MethodResult:
    """Un test défini par formule. Donnez `pvalue` (rejet si `pvalue < alpha`) ou `stat` et `critical`
    (rejet si `|stat| > critical`). Sans `stat` (resp. `pvalue`), cette colonne vaut NaN."""
    if pvalue is None and (stat is None or critical is None):
        raise ValueError("formula_test : donnez `pvalue`, ou bien `stat` et `critical`.")
    v = _vectors(stat=stat, pvalue=pvalue, critical=critical)
    size = next(a.shape[0] for a in v.values() if a is not None)
    nan = np.full(size, np.nan)
    if v["pvalue"] is not None:
        reject = v["pvalue"] < alpha
    else:
        assert v["stat"] is not None and v["critical"] is not None
        reject = np.abs(v["stat"]) > v["critical"]
    return MethodResult(
        reps={
            "stat": v["stat"] if v["stat"] is not None else nan,
            "pvalue": v["pvalue"] if v["pvalue"] is not None else nan,
            "reject": np.asarray(reject, dtype=bool),
        }
    )


@register_method(
    "formula_interval",
    provides={"reps": ["est", "low", "high", "hit", "width"]},
    cost="repeat",
)
def formula_interval(
    *, est: Any, low: Any, high: Any, truth: Any, rng: np.random.Generator
) -> MethodResult:
    """Un intervalle par formule : `hit` vaut vrai si `low <= truth <= high`, `width` = `high - low`."""
    v = _vectors(est=est, low=low, high=high, truth=truth)
    est_v, lo, hi, tr = v["est"], v["low"], v["high"], v["truth"]
    assert est_v is not None and lo is not None and hi is not None and tr is not None
    return MethodResult(
        reps={"est": est_v, "low": lo, "high": hi, "hit": (lo <= tr) & (tr <= hi), "width": hi - lo}
    )
