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


# --- Entraînement par discipline (plan de docs/notes/r1.md, étape 1) -----------------------------------


def _experiments_of(session: TrainingSessionResponse) -> set[str]:
    return {q.experiment_id for q in session.questions}


def _choices(session: TrainingSessionResponse) -> list[str]:
    return [c.id for q in session.questions for c in q.choices]


def test_discipline_slug_removes_accents_and_spaces() -> None:
    from backend.engine.training import discipline_slug

    assert discipline_slug("algèbre linéaire") == "algebre-lineaire"
    assert discipline_slug("probabilités") == "probabilites"
    assert discipline_slug("Algèbre  Linéaire") == "algebre-lineaire"  # majuscules et espaces multiples
    assert discipline_slug("statistique") == "statistique"


def test_every_discipline_gives_a_series_made_only_of_its_own_experiments() -> None:
    from backend.engine.training import available_disciplines

    specs = registry.official()
    disciplines = available_disciplines(specs)
    assert {"statistique", "probabilites", "algebre-lineaire", "apprentissage"} <= set(disciplines)
    for slug, name in disciplines.items():
        session = _session(f"discipline:{slug}", 2)
        assert session.questions, slug
        assert all(specs[e].discipline == name for e in _experiments_of(session)), slug


def test_linear_algebra_is_filterable_through_the_api() -> None:
    """Avant : « discipline:algèbre linéaire » était refusé (422) à cause de l'espace."""
    from fastapi.testclient import TestClient

    from backend.main import create_app

    client = TestClient(create_app(None))
    response = client.post("/api/training/session", json={"filter": "discipline:algebre-lineaire", "seed": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["filter"] == "discipline:algebre-lineaire" and len(body["questions"]) == 10


def test_several_disciplines_give_the_union_of_their_experiments() -> None:
    specs = registry.official()
    one = {e for e in specs if specs[e].discipline == "apprentissage"}
    two = {e for e in specs if specs[e].discipline in ("apprentissage", "probabilités")}
    both = _session("discipline:apprentissage,probabilites", 3)
    assert _experiments_of(both) <= two and len(_experiments_of(both)) > len(one)
    assert len(both.questions) == 10  # plus de questions disponibles que dans une seule discipline


def test_spelling_and_order_of_disciplines_do_not_change_the_series() -> None:
    reference = _session("discipline:algebre-lineaire,statistique", 7)
    for variant in (
        "discipline:statistique,algebre-lineaire",
        "discipline:Statistique,Algèbre Linéaire",  # ancien nom exact, comme dans un ancien lien
        "discipline:statistique,statistique,algebre-lineaire",
    ):
        again = _session(variant, 7)
        assert [q.qid for q in again.questions] == [q.qid for q in reference.questions], variant
        assert _choices(again) == _choices(reference), variant


def test_same_discipline_and_seed_give_the_same_series_and_other_seeds_differ() -> None:
    a = [q.qid for q in _session("discipline:statistique", 11).questions]
    assert a == [q.qid for q in _session("discipline:statistique", 11).questions]
    assert a != [q.qid for q in _session("discipline:statistique", 12).questions]


def test_unknown_or_empty_discipline_is_a_french_error_that_lists_the_choices() -> None:
    import pytest

    from backend.engine.runner import RunError

    with pytest.raises(RunError, match="Discipline inconnue.*algebre-lineaire"):
        _session("discipline:chimie", 1)
    with pytest.raises(RunError, match="Discipline inconnue"):
        _session("discipline:statistique,chimie", 1)
    with pytest.raises(RunError, match="au moins une discipline"):
        _session("discipline:", 1)
    with pytest.raises(RunError, match="Discipline inconnue"):
        _session("discipline:chimie,", 1)  # une virgule finale ne masque pas l'erreur


def test_existing_filters_are_unchanged() -> None:
    assert len(_session("toutes", 1).questions) == 10
    assert {q.experiment_id for q in _session("regression-lineaire", 1).questions} == {"regression-lineaire"}


# --- Tirage équilibré entre expériences (plan de docs/notes/r1.md, étape 2) -----------------------------


def _first_slots(filter_: str, seed: int, count: int = 10):
    """Les `count` premiers emplacements tirés, sans fabriquer les questions (rapide)."""
    from backend.engine.rng import rng_for
    from backend.engine.training import _pool, _round_robin, canonical_filter, select_experiments

    specs = registry.official()
    stream = f"training:{canonical_filter(specs, filter_)}:{registry.content_digest()}"
    pool = _pool(select_experiments(specs, filter_))
    return _round_robin(pool, rng_for(seed, stream))[: min(count, len(pool))]


def test_round_robin_serves_every_experiment_once_before_repeating_one() -> None:
    from collections import Counter
    from math import ceil

    specs = registry.official()
    filters = ("toutes", "discipline:statistique", "discipline:algebre-lineaire", "discipline:apprentissage")
    for filter_ in filters:
        n_experiments = len([s for s in specs.values() if filter_ == "toutes" or _slug_matches(s, filter_)])
        for seed in range(60):
            counts = Counter(slot.spec.id for slot in _first_slots(filter_, seed))
            assert max(counts.values()) <= ceil(10 / n_experiments), (filter_, seed, dict(counts))


def _slug_matches(spec, filter_: str) -> bool:
    from backend.engine.training import discipline_slug

    return discipline_slug(spec.discipline) == filter_.removeprefix("discipline:")


def test_all_fifteen_experiments_can_open_a_series_and_ten_are_all_different() -> None:
    from collections import Counter

    opening = Counter()
    for seed in range(120):
        slots = _first_slots("toutes", seed)
        assert len({s.spec.id for s in slots}) == 10, seed  # 10 questions : 10 expériences différentes
        opening[slots[0].spec.id] += 1
    assert len(opening) >= 12  # la première question n'est pas toujours celle des mêmes expériences


def test_every_experiment_of_a_discipline_is_represented_in_a_ten_question_series() -> None:
    from backend.engine.training import discipline_slug

    specs = registry.official()
    expected = {s.id for s in specs.values() if discipline_slug(s.discipline) == "algebre-lineaire"}
    for seed in range(40):
        assert {s.spec.id for s in _first_slots("discipline:algebre-lineaire", seed)} == expected


def test_a_single_experiment_uses_all_its_questions_in_a_shuffled_order() -> None:
    orders = set()
    for seed in range(30):
        orders.add(tuple((s.question.id, s.index) for s in _first_slots("tests-multiples", seed, 99)))
    assert len(orders) > 5  # l'ordre dépend de la graine
    assert all(len(o) == len(set(o)) for o in orders)  # aucune question deux fois


def test_a_real_series_is_balanced_and_in_a_shuffled_order() -> None:
    session = _session("toutes", 4)
    experiments = [q.experiment_id for q in session.questions]
    assert len(session.questions) == 10 and len(set(experiments)) == 10
    assert experiments != sorted(experiments)  # remélangée : pas rangée par expérience
