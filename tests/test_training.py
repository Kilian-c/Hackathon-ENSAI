"""Fabrication des séries d'Entraînement (training.py) : vérification, diagnostics, retraits."""

from backend.api import registry
from backend.contracts import TrainingSessionResponse
from backend.engine.runner import check_condition
from backend.engine.training import build_session


def _session(filter_: str, seed: int, specs=None, count: int = 10) -> TrainingSessionResponse:
    return build_session(specs or registry.official(), registry.content_digest(), filter_, count, seed)


def test_every_choice_of_a_misconception_passes_its_verify() -> None:
    specs = registry.official()
    s = _session("multicolinearite", 4)
    assert s.questions and not s.dropped
    for q in s.questions:
        if q.type != "misconception":
            continue
        spec = specs[q.experiment_id]
        yaml_q = next(x for x in spec.questions if x.id == q.qid.split("/")[1])
        verify = {c.id: c.verify for c in yaml_q.choices}
        assert sum(c.correct for c in q.choices) == 1
        for c in q.choices:
            assert check_condition(spec, c.reveal.state, verify[c.id])
        assert "{" not in q.prompt  # paramètres procéduraux remplis


def test_confidence_levels_follow_k() -> None:
    for q in _session("regression-lineaire", 3).questions:
        assert q.confidence.guess == 1 / q.k
        assert q.confidence.sure == 0.95
        assert abs(q.confidence.fair - (1 / q.k + 0.95) / 2) < 1e-12


def test_diagnostic_repeats_with_a_different_hidden_pathology() -> None:
    s = _session("regression-lineaire", 7)
    diags = [q for q in s.questions if q.type == "diagnostic_auto"]
    assert len(diags) == 2
    assert {q.qid.rsplit("/", 1)[1] for q in diags} == {"0", "1"}
    hidden = [next(c.label for c in q.choices if c.correct) for q in diags]
    assert hidden[0] != hidden[1]
    for q in diags:
        assert q.initial_view is not None and q.initial_view.id == "residus"
        assert q.k == 4 and any(c.label == "Hypothèses respectées" for c in q.choices)
        assert len({c.reveal.state.seed for c in q.choices}) == 1  # même tirage, seule la pathologie change


def test_question_whose_verify_never_passes_is_dropped() -> None:
    specs = dict(registry.official())
    spec = specs["tests-multiples"].model_copy(deep=True)
    spec.questions[0].choices[0].verify = "1 == 0"
    specs["tests-multiples"] = spec
    s = _session("tests-multiples", 5, specs)
    assert [d.question_id for d in s.dropped] == [spec.questions[0].id]
    assert "verify" in s.dropped[0].reason
    assert len(s.questions) == len(spec.questions) - 1


# --- Questions de prédiction (P1) -------------------------------------------------------------------------


def test_prediction_answer_is_computed_by_the_engine() -> None:
    """Trois choix fixes, un seul juste, calculé en relançant les deux états (simulé avant d'écrire)."""
    expected = {
        "regression-lineaire": "stable",  # couverture sous hétéroscédasticité : n ne répare rien
        "theoreme-central-limite": "down",  # Cauchy : la part dans ±1,96 baisse quand n grandit
        "tests-multiples": "up",  # plus de comparaisons, plus de fausses alarmes
        "multicolinearite": "down",  # X1 et X2 très liées : la puissance chute
    }
    for eid, answer in expected.items():
        preds = [q for q in _session(eid, 5).questions if q.type == "prediction"]
        assert len(preds) == 1, eid
        q = preds[0]
        assert q.k == 3 and [c.id for c in q.choices] == ["up", "down", "stable"]
        assert [c.id for c in q.choices if c.correct] == [answer], eid
        assert all("au départ" in c.explain for c in q.choices)


def test_prediction_is_deterministic() -> None:
    a = _session("tests-multiples", 11).model_dump()
    b = _session("tests-multiples", 11).model_dump()
    assert a == b


def test_no_decimal_number_is_directly_followed_by_a_comma_or_semicolon() -> None:
    """« passe de 0 à 0,98, que devient... » : la virgule de la phrase se confond avec la virgule décimale."""
    import re

    risky = re.compile(r"\d+,\d+(?:\s?(?:%|ddl))?\s?[,;]")
    specs, digest = registry.official(), registry.content_digest()
    for seed in range(1, 31):
        for q in build_session(specs, digest, "toutes", 10, seed).questions:
            for text in [q.prompt, *(c.label for c in q.choices), *(c.explain for c in q.choices)]:
                assert not risky.search(text), f"{q.qid} : « {text} »"
