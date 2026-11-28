"""Méthodes génériques du catalogue (statistic, classifier, regressor) et emplacements de vue associés."""

from pathlib import Path

import numpy as np
from scipy import stats

from backend.contracts import EngineState
from backend.engine import runner
from backend.engine.loader import load_experiment_file
from backend.methods.classifier import classifier
from backend.methods.regressor import regressor
from backend.methods.statistic import statistic

EXP = Path(__file__).resolve().parent.parent / "experiments"


def test_statistic_kinds_and_continuity() -> None:
    x = np.array([[1.0, 2.0, 6.0], [3.0, 3.0, 4.0]])
    rng = np.random.default_rng(0)
    assert statistic(x=x, kind="sum", rng=rng).reps["stat"].tolist() == [9.0, 10.0]
    assert statistic(x=x, kind="max", rng=rng).reps["stat"].tolist() == [6.0, 4.0]
    jittered = statistic(x=x, kind="sum", continuity=True, rng=rng).reps["stat"]
    assert np.all(np.abs(jittered - [9.0, 10.0]) <= 0.5)


def test_classifier_against_theory() -> None:
    rng = np.random.default_rng(1)
    label = rng.random((200, 400)) < 0.5
    score = rng.standard_normal((200, 400)) + 2.0 * label
    r = classifier(score=score, label=label, threshold=1.0)
    assert np.all(r.reps["best_error"] <= r.reps["error"] + 1e-12)
    assert np.all(r.reps["excess"] >= -1e-12)
    # Théorie : sensibilité = spécificité = Phi(1) au seuil milieu ; AUC = Phi(2 / racine(2)).
    assert abs(np.mean(r.reps["sens"]) - stats.norm.cdf(1.0)) < 0.01
    assert abs(np.mean(r.reps["spec"]) - stats.norm.cdf(1.0)) < 0.01
    assert abs(np.mean(r.reps["auc"]) - stats.norm.cdf(2.0 / np.sqrt(2.0))) < 0.01
    fpr, tpr = r.curves["fpr"], r.curves["tpr"]
    assert (fpr[0], tpr[0]) == (0.0, 0.0) and (fpr[-1], tpr[-1]) == (1.0, 1.0)
    assert np.all(np.diff(fpr) >= 0) and np.all(np.diff(tpr) >= 0)
    # Exemple : chaque classe séparée, NaN à la place de l'autre.
    assert np.isnan(r.example["score_pos"][~label[0]]).all()
    assert np.isnan(r.example["score_neg"][label[0]]).all()


def test_regressor_ols_is_the_minimum() -> None:
    rng = np.random.default_rng(2)
    x = rng.standard_normal((50, 30))
    y = 1.0 + 1.5 * x + rng.standard_normal((50, 30))
    ols = regressor(x=x, y=y, kind="ols")
    assert np.allclose(ols.reps["slope"], [np.polyfit(a, b, 1)[0] for a, b in zip(x, y, strict=True)])
    assert np.allclose(ols.reps["excess"], 0.0)
    for slope in (0.0, 1.0, 2.5):
        assert np.all(regressor(x=x, y=y, kind="manuelle", slope=slope).reps["excess"] > 0)


def test_new_view_slots_threshold_h1_segments_and_labels() -> None:
    roc = runner.run(load_experiment_file(EXP / "seuil_roc.yaml"))
    scores = next(v for v in roc.views if v.id == "scores")
    by_slot = {s.slot: s for s in scores.series if s.role != "reference"}
    assert by_slot["threshold"].value == 1.25 and by_slot["threshold"].label == "Seuil"
    assert by_slot["h1"].label == "Malades" and by_slot["stat"].label == "Sains"
    assert next(v for v in roc.views if v.id == "roc").series[0].label == "Courbe ROC"

    sq = runner.run(load_experiment_file(EXP / "carres_residus.yaml"), EngineState(params={"pente": 0.5}))
    seg = next(s for s in next(v for v in sq.views if v.id == "nuage").series if s.slot == "segments")
    assert seg.x is not None and seg.low is not None and seg.high is not None and seg.y is None
    assert len(seg.x) == len(seg.low) == len(seg.high) == 20


def test_fast_tukey_quantile_matches_scipy_and_is_fast() -> None:
    import time

    from scipy import stats

    from backend.methods.pairwise_tests import _tukey_quantile

    _tukey_quantile.cache_clear()
    for groups, dof in ((3, 57), (6, 114), (2, 8)):
        t0 = time.perf_counter()
        fast = _tukey_quantile(0.95, groups, dof)
        elapsed = time.perf_counter() - t0
        reference = float(stats.studentized_range.ppf(0.95, groups, dof))
        assert abs(fast - reference) / reference < 1e-9
        assert elapsed < 0.5, f"quantile de Tukey ({groups}, {dof}) : {elapsed:.2f} s"
