"""Tests de contenu des expériences (R2, section 4.10 du cahier). P0 : 1, 3, 4, 8, 10.

Les tests 10 et 'au moins 3 questions' ne lisent que le YAML. Les tests 1, 3, 4 et 8
ont besoin de `run()` (backend/engine/runner.py, R1) : ils sont ignorés tant qu'il n'existe pas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.engine.loader import load_experiment_file

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
P0_FILES = sorted(EXPERIMENTS_DIR.glob("*.yaml"))
P0_IDS = [p.stem for p in P0_FILES]


@pytest.fixture(scope="module", params=P0_FILES, ids=P0_IDS)
def experiment(request):
    return load_experiment_file(request.param)


# Test 10 : chaque hypothèse a why et when_broken, chaque correction et alternative a explain.
def test_10_every_hypothesis_is_documented(experiment) -> None:
    for hid, h in experiment.hypotheses.items():
        assert h.why and h.why.strip(), f"{experiment.id} : l'hypothèse {hid} n'a pas de why."
        assert h.when_broken and h.when_broken.strip(), (
            f"{experiment.id} : l'hypothèse {hid} n'a pas de when_broken."
        )


def test_10_every_correction_and_alternative_has_explain(experiment) -> None:
    for m in experiment.methods:
        if m.role != "method":
            assert m.explain and m.explain.strip(), (
                f"{experiment.id} : la méthode {m.id} ({m.role}) n'a pas d'explain."
            )


def test_methods_limits(experiment) -> None:
    roles = [m.role for m in experiment.methods]
    assert roles.count("method") == 1
    assert roles.count("correction") <= 1
    assert roles.count("alternative") <= 2
    assert len(roles) <= 4


def test_repairs_refer_to_existing_hypotheses(experiment) -> None:
    for m in experiment.methods:
        for hid in m.repairs or []:
            assert hid in experiment.hypotheses, f"{experiment.id} : {m.id} répare {hid}, inconnue."


def test_at_least_three_questions_with_p0_types(experiment) -> None:
    kinds = [q.type for q in experiment.questions]
    assert len(kinds) >= 3, f"{experiment.id} : {len(kinds)} question(s), il en faut 3 au moins."
    assert kinds.count("misconception") + kinds.count("diagnostic_auto") >= 2


def test_texts_are_in_french_without_tutoiement(experiment) -> None:
    texts = [experiment.title]
    texts += [h.why for h in experiment.hypotheses.values()]
    texts += [h.when_broken for h in experiment.hypotheses.values()]
    texts += [c.explain for c in experiment.counterexamples]
    for q in experiment.questions:
        texts.append(q.prompt)
        texts += [c.label + " " + c.explain for c in getattr(q, "choices", [])]
    for t in texts:
        padded = f" {t.lower()} "
        for tu in (" tu ", " ton ", " ta ", " tes ", " toi "):
            assert tu not in padded, f"{experiment.id} : tutoiement ({tu.strip()}) dans « {t} »."


# Tests 1, 3, 4 et 8 : ils exigent run() de R1 (importorskip dans chaque test, pas au niveau du module).
def _runner():
    return pytest.importorskip(
        "backend.engine.runner", reason="run() de R1 pas encore disponible"
    )


def test_1_healthy_state_is_ok(experiment) -> None:
    _runner()
    pytest.skip("TODO(passation) : à écrire dès que run(experiment, state) existe")


def test_3_corrections_repair_their_hypotheses(experiment) -> None:
    _runner()
    pytest.skip("TODO(passation) : à écrire dès que run(experiment, state) existe")


def test_4_counterexamples_break_a_measure(experiment) -> None:
    _runner()
    pytest.skip("TODO(passation) : à écrire dès que run(experiment, state) existe")


def test_8_same_state_same_result(experiment) -> None:
    _runner()
    pytest.skip("TODO(passation) : à écrire dès que run(experiment, state) existe")
