"""Agrégateurs de mesures et calcul des erreurs Monte Carlo (Table 8).

Chaque agrégateur exclut les répétitions invalides (NaN / ±inf) avant de calculer
la mesure et renvoie un AggResult contenant la valeur, l'erreur Monte Carlo
éventuelle, et le nombre de répétitions valides.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class AggResult:
    """Résultat d'un agrégateur sur une série de répétitions ou un résumé."""

    value: float
    mc_se: float | None
    n_valid: int
    n_total: int


def _extract_valid(values: Any) -> tuple[np.ndarray, int]:
    """Convertit en tableau float 1D et filtre les valeurs non finies (NaN, ±inf)."""
    arr = np.asarray(values, dtype=float).ravel()
    n_total = int(arr.size)
    valid = arr[np.isfinite(arr)]
    return valid, n_total


def agg_rate(values: Any) -> AggResult:
    """Part des répétitions où `values` est vrai (non nul). Erreur MC : sqrt(p(1-p)/n)."""
    valid, n_total = _extract_valid(values)
    n_valid = int(valid.size)
    if n_valid == 0:
        return AggResult(value=math.nan, mc_se=None, n_valid=0, n_total=n_total)

    p = float(np.mean(valid != 0.0))
    mc_se = float(math.sqrt(max(p * (1.0 - p), 0.0) / n_valid))
    return AggResult(value=p, mc_se=mc_se, n_valid=n_valid, n_total=n_total)


def agg_mean(values: Any) -> AggResult:
    """Moyenne des répétitions valides. Erreur MC : écart type / sqrt(n)."""
    valid, n_total = _extract_valid(values)
    n_valid = int(valid.size)
    if n_valid == 0:
        return AggResult(value=math.nan, mc_se=None, n_valid=0, n_total=n_total)

    val = float(np.mean(valid))
    mc_se = float(np.std(valid, ddof=1) / math.sqrt(n_valid)) if n_valid > 1 else None
    return AggResult(value=val, mc_se=mc_se, n_valid=n_valid, n_total=n_total)


def agg_bias(values: Any, truth: float) -> AggResult:
    """Biais : moyenne de `values` moins la vraie valeur `truth`. Erreur MC : sd / sqrt(n)."""
    res = agg_mean(values)
    if math.isnan(res.value):
        return res
    return AggResult(
        value=res.value - float(truth),
        mc_se=res.mc_se,
        n_valid=res.n_valid,
        n_total=res.n_total,
    )


def agg_rmse(values: Any, truth: float) -> AggResult:
    """Racine de l'erreur quadratique moyenne par rapport à `truth`."""
    valid, n_total = _extract_valid(values)
    n_valid = int(valid.size)
    if n_valid == 0:
        return AggResult(value=math.nan, mc_se=None, n_valid=0, n_total=n_total)

    err = valid - float(truth)
    val = float(np.sqrt(np.mean(err * err)))
    return AggResult(value=val, mc_se=None, n_valid=n_valid, n_total=n_total)


def agg_sd(values: Any) -> AggResult:
    """Écart type empirique corrigé (ddof=1) des répétitions valides."""
    valid, n_total = _extract_valid(values)
    n_valid = int(valid.size)
    if n_valid < 2:
        return AggResult(value=math.nan, mc_se=None, n_valid=n_valid, n_total=n_total)

    val = float(np.std(valid, ddof=1))
    return AggResult(value=val, mc_se=None, n_valid=n_valid, n_total=n_total)


def agg_var(values: Any) -> AggResult:
    """Variance empirique corrigée (ddof=1) des répétitions valides."""
    valid, n_total = _extract_valid(values)
    n_valid = int(valid.size)
    if n_valid < 2:
        return AggResult(value=math.nan, mc_se=None, n_valid=n_valid, n_total=n_total)

    val = float(np.var(valid, ddof=1))
    return AggResult(value=val, mc_se=None, n_valid=n_valid, n_total=n_total)


def agg_median(values: Any) -> AggResult:
    """Médiane des répétitions valides."""
    valid, n_total = _extract_valid(values)
    n_valid = int(valid.size)
    if n_valid == 0:
        return AggResult(value=math.nan, mc_se=None, n_valid=0, n_total=n_total)

    val = float(np.median(valid))
    return AggResult(value=val, mc_se=None, n_valid=n_valid, n_total=n_total)


def agg_quantile(values: Any, q: float) -> AggResult:
    """Quantile d'ordre `q` (dans [0, 1]) des répétitions valides."""
    qf = float(q)
    if not 0.0 <= qf <= 1.0:
        raise ValueError(f"Le quantile q doit être dans [0, 1], reçu {q}.")

    valid, n_total = _extract_valid(values)
    n_valid = int(valid.size)
    if n_valid == 0:
        return AggResult(value=math.nan, mc_se=None, n_valid=0, n_total=n_total)

    val = float(np.quantile(valid, qf))
    return AggResult(value=val, mc_se=None, n_valid=n_valid, n_total=n_total)


def agg_first(values: Any) -> AggResult:
    """Valeur sur la répétition 0 (l'échantillon affiché dans les vues)."""
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        return AggResult(value=math.nan, mc_se=None, n_valid=0, n_total=0)

    val = float(arr[0])
    is_valid = math.isfinite(val)
    return AggResult(
        value=val if is_valid else math.nan,
        mc_se=None,
        n_valid=1 if is_valid else 0,
        n_total=1,
    )


def agg_summary(
    key_or_value: str | float,
    summary_dict: dict[str, float] | None = None,
) -> AggResult:
    """Lit une grandeur globale renvoyée dans `MethodResult.summary`.

    Accepte soit (clé, dictionnaire summary), soit directement la valeur float
    si l'évaluateur d'expressions a déjà résolu le nom dans le namespace.
    """
    if isinstance(key_or_value, str):
        if summary_dict is None:
            raise ValueError(
                f"summary('{key_or_value}') nécessite le dictionnaire summary de la méthode."
            )
        if key_or_value not in summary_dict:
            raise KeyError(f"Clé '{key_or_value}' absente de summary.")
        val = float(summary_dict[key_or_value])
    else:
        val = float(key_or_value)

    is_valid = math.isfinite(val)
    return AggResult(
        value=val if is_valid else math.nan,
        mc_se=None,
        n_valid=1 if is_valid else 0,
        n_total=1,
    )


def agg_kurtosis(values: Any) -> AggResult:
    """Aplatissement (kurtosis en excès) des répétitions valides : 0 pour une loi normale, -1,2 pour une
    loi uniforme. Pas d'erreur MC (CLAUDE.md, section 8 : seulement pour rate, mean et bias)."""
    valid, n_total = _extract_valid(values)
    n_valid = int(valid.size)
    if n_valid < 4:
        return AggResult(value=math.nan, mc_se=None, n_valid=n_valid, n_total=n_total)
    centered = valid - valid.mean()
    m2 = float(np.mean(centered**2))
    if m2 == 0.0:
        return AggResult(value=math.nan, mc_se=None, n_valid=n_valid, n_total=n_total)
    val = float(np.mean(centered**4) / m2**2 - 3.0)
    return AggResult(value=val, mc_se=None, n_valid=n_valid, n_total=n_total)


AGGREGATORS: dict[str, Callable[..., AggResult]] = {
    "kurtosis": agg_kurtosis,
    "rate": agg_rate,
    "mean": agg_mean,
    "bias": agg_bias,
    "rmse": agg_rmse,
    "sd": agg_sd,
    "var": agg_var,
    "median": agg_median,
    "quantile": agg_quantile,
    "first": agg_first,
    "summary": agg_summary,
}


def get_aggregator(name: str) -> Callable[..., AggResult]:
    """Retourne la fonction d'agrégation correspondant à `name`."""
    if name not in AGGREGATORS:
        available = ", ".join(sorted(AGGREGATORS))
        raise KeyError(
            f"Agrégateur inconnu : '{name}'. Agrégateurs disponibles : {available}."
        )
    return AGGREGATORS[name]


def list_aggregators() -> dict[str, Callable[..., AggResult]]:
    """Retourne une copie du registre des agrégateurs."""
    return dict(AGGREGATORS)
