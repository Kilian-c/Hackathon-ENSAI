"""Méthode générique `classifier` (catalogue, archétype 6 « score et seuil »).

Pour l'instant un seul `kind` : « seuil » (positif si le score dépasse le seuil). Les autres classifieurs du
catalogue (knn, lda, qda, nb, tree, forest) viendront comme d'autres valeurs de `kind`, sans nouvelle méthode.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from backend.engine.method_contract import MethodResult, register_method

_KINDS = ("seuil",)
_ROC_POINTS = 101


def _best_error(score: np.ndarray, label: np.ndarray) -> np.ndarray:
    """Plus petit taux d'erreur atteignable par un seuil, sur chaque échantillon (formule fermée, triée)."""
    order = np.argsort(score, axis=1, kind="stable")
    lab = np.take_along_axis(label, order, axis=1).astype(float)
    n = lab.shape[1]
    zeros = np.zeros((lab.shape[0], 1))
    pos_below = np.concatenate([zeros, np.cumsum(lab, axis=1)], axis=1)  # malades déclarés sains
    neg_below = np.concatenate([zeros, np.cumsum(1.0 - lab, axis=1)], axis=1)
    neg_above = neg_below[:, -1:] - neg_below  # sains déclarés malades
    return (pos_below + neg_above).min(axis=1) / n


def _roc(score: np.ndarray, label: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Courbe ROC sur toutes les répétitions réunies, du coin (0, 0) au coin (1, 1)."""
    pos, neg = score[label], score[~label]
    if pos.size == 0 or neg.size == 0:
        nan = np.full(_ROC_POINTS + 2, np.nan)
        return nan, nan
    cuts = np.quantile(score, np.linspace(1.0, 0.0, _ROC_POINTS))
    cuts = np.concatenate([[np.inf], cuts, [-np.inf]])
    pos_sorted, neg_sorted = np.sort(pos), np.sort(neg)
    tpr = 1.0 - np.searchsorted(pos_sorted, cuts, side="right") / pos.size
    fpr = 1.0 - np.searchsorted(neg_sorted, cuts, side="right") / neg.size
    return fpr, tpr


@register_method(
    "classifier",
    provides={
        "reps": ["error", "best_error", "excess", "sens", "spec", "accuracy", "auc"],
        "example": ["score_neg", "score_pos"],
        "curves": ["fpr", "tpr"],
    },
    cost="repeat * n",
)
def classifier(
    *,
    score: np.ndarray,
    label: np.ndarray,
    threshold: float,
    kind: str = "seuil",
    rng: np.random.Generator | None = None,
) -> MethodResult:
    """Classe positif si `score > threshold`. Par répétition : taux d'erreur, meilleur taux atteignable par
    un seuil sur ce même échantillon, excès d'erreur, sensibilité, spécificité, exactitude et AUC.

    `example` : scores des négatifs et des positifs de la répétition 0 (NaN à la place de l'autre classe).
    `curves` : courbe ROC (taux de faux positifs, sensibilité), toutes répétitions réunies.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind doit valoir l'une de {_KINDS}, reçu {kind!r}.")
    score = np.asarray(score, dtype=float)
    label = np.asarray(label).astype(bool)
    n = score.shape[1]
    with np.errstate(divide="ignore", invalid="ignore"):
        n_pos = label.sum(axis=1).astype(float)
        n_neg = n - n_pos
        pred = score > float(threshold)
        error = (pred != label).mean(axis=1)
        sens = (pred & label).sum(axis=1) / n_pos
        spec = (~pred & ~label).sum(axis=1) / n_neg
        best = _best_error(score, label)
        ranks = stats.rankdata(score, axis=1)
        auc = ((ranks * label).sum(axis=1) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
        empty = (n_pos == 0) | (n_neg == 0)
        sens[n_pos == 0] = np.nan
        spec[n_neg == 0] = np.nan
        auc[empty] = np.nan
    fpr, tpr = _roc(score, label)
    first_score, first_label = score[0], label[0]
    return MethodResult(
        reps={
            "error": error,
            "best_error": best,
            "excess": error - best,
            "sens": sens,
            "spec": spec,
            "accuracy": 1.0 - error,
            "auc": auc,
        },
        example={
            "score_neg": np.where(first_label, np.nan, first_score),
            "score_pos": np.where(first_label, first_score, np.nan),
        },
        curves={"fpr": fpr, "tpr": tpr},
    )
