"""Tests de contenu des expériences (R2, section 4.10 du cahier). P0 : 1, 3, 4, 8, 10.

Les tests de contenu lisent le YAML. Les tests qui calculent (1, 2, 3, 4, 6, 8) passent par
`run_state`, branché pour l'instant sur le mini-pipeline `tests/_mini_run.py` (le vrai `run()` de R1,
backend/engine/runner.py, n'existe pas encore). TODO(passation) : brancher `run_state` sur `run()`.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from backend.engine.loader import load_experiment_file
from tests import _mini_run
from tests._mini_run import check_verify, mini_run

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



# --- Tests qui calculent -------------------------------------------------------------------------------


def run_state(experiment, state: dict | None = None):
    """Point d'entrée unique des tests : à brancher sur run() de R1 quand il existera."""
    return mini_run(experiment, state)


def _broken_values(hyp) -> list:
    """Les valeurs non saines d'une hypothèse : toutes les options, l'autre booléen, ou le maximum."""
    if hyp.type == "choice":
        return [k for k in hyp.options if k != hyp.healthy_value]
    if hyp.type == "boolean":
        return [not hyp.healthy_value]
    return [hyp.range[1]]


def _is_robust(hyp, value) -> bool:
    """`robust_expected` : lu sur l'option d'abord, puis sur l'hypothèse (CLAUDE.md, section 7)."""
    if hyp.type == "choice" and hyp.options[value].robust_expected:
        return True
    return hyp.robust_expected


def _main_states(experiment, result) -> list[str]:
    main = result.primary_method
    return [st[main] for st in result.states.values() if st.get(main) is not None]


# Test 1 : à l'état sain, la mesure primaire de la méthode principale est « ok ».
def test_1_healthy_state_is_ok(experiment) -> None:
    res = run_state(experiment)
    assert res.states[res.primary_measure][res.primary_method] == "ok"


# Test 2 (P1) : une hypothèse cassée seule rompt au moins une mesure, sauf `robust_expected`.
# Pour un choix, au moins une option doit rompre (l'option « rupture de pente » n'est que Fragile).
def test_2_each_broken_hypothesis_breaks_a_measure(experiment) -> None:
    for hid, hyp in experiment.hypotheses.items():
        values = [v for v in _broken_values(hyp) if not _is_robust(hyp, v)]
        if not values:
            continue
        outcomes = []
        for v in values:
            res = run_state(experiment, {"hypotheses": {hid: v}})
            outcomes.append("broken" in _main_states(experiment, res))
        assert any(outcomes), f"{experiment.id} : casser {hid} ({values}) ne rompt aucune mesure."


def test_2_robust_expected_stays_reliable(experiment) -> None:
    for hid, hyp in experiment.hypotheses.items():
        for v in _broken_values(hyp):
            if _is_robust(hyp, v):
                res = run_state(experiment, {"hypotheses": {hid: v}})
                st = res.states[res.primary_measure][res.primary_method]
                assert st == "ok", f"{experiment.id} : {hid}={v} est attendue robuste, verdict {st}."


# Test 3 : chaque méthode ramène à « ok » ou « warning » les hypothèses de son `repairs`.
def test_3_methods_repair_their_hypotheses(experiment) -> None:
    for m in experiment.methods:
        for hid in m.repairs:
            for v in _broken_values(experiment.hypotheses[hid]):
                res = run_state(experiment, {"hypotheses": {hid: v}})
                st = res.states[res.primary_measure][m.id]
                assert st in ("ok", "warning"), (
                    f"{experiment.id} : {m.id} ne répare pas {hid}={v} (verdict {st})."
                )


def _slope_r2(experiment, world) -> tuple[np.ndarray, np.ndarray]:
    inject = experiment.generator.inject
    x, y = world.variables[inject["x"]], world.variables[inject["y"]]
    xc, yc = x - x.mean(axis=1, keepdims=True), y - y.mean(axis=1, keepdims=True)
    sxy, sxx, syy = (xc * yc).sum(1), (xc**2).sum(1), (yc**2).sum(1)
    return sxy / sxx, sxy**2 / (sxx * syy)


# Test 4 : chaque contre-exemple rompt une mesure, sauf `expect: same_summary` (pente et R2 identiques).
def test_4_counterexamples_break_a_measure(experiment) -> None:
    for ce in experiment.counterexamples:
        state = ce.state.model_dump()
        res = run_state(experiment, state)
        if ce.expect == "same_summary":
            ref_state = {"params": state.get("params", {}), "hypotheses": {}}
            ref = run_state(experiment, ref_state)
            slope, r2 = _slope_r2(experiment, res.world)
            slope0, r20 = _slope_r2(experiment, ref.world)
            assert np.allclose(slope, slope0, atol=1e-9), f"{ce.id} : pente différente."
            assert np.allclose(r2, r20, atol=1e-9), f"{ce.id} : R2 différent."
        else:
            assert "broken" in _main_states(experiment, res), (
                f"{experiment.id} : le contre-exemple {ce.id} ne rompt aucune mesure."
            )


# Test 8 : deux exécutions du même état donnent exactement le même résultat.
def test_8_same_state_same_result(experiment) -> None:
    state = {"hypotheses": {next(iter(experiment.hypotheses)): _broken_values(
        next(iter(experiment.hypotheses.values())))[0]}}
    a = run_state(experiment, state)
    _mini_run._CACHE.clear()
    b = run_state(experiment, state)
    assert repr(a.values) == repr(b.values) and a.states == b.states and a.challenges == b.challenges


# Test 6 : `verify` passe sur au moins 90 % de tirages des paramètres procéduraux.
def _draw_state(state: dict, procedural: dict, rng: np.random.Generator) -> dict:
    drawn = {}
    for name, p in procedural.items():
        k = int(rng.integers(0, int(round((p.max - p.min) / p.step)) + 1))
        drawn[name] = round(p.min + k * p.step, 10)
    out = {"params": dict(state.get("params", {})), "hypotheses": dict(state.get("hypotheses", {}))}
    for key in ("params", "hypotheses"):
        for k, v in out[key].items():
            if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                out[key][k] = drawn[v[1:-1]]
    return out


def test_6_verify_passes_on_most_draws(experiment) -> None:
    # Le cahier demande 50 tirages ; EDO déterministe (lent) : 2 tirages par défaut.
    # Pour la vérification complète : CRASHTEST_DRAWS=50 uv run pytest tests/test_experiments.py -k test_6
    default = 2 if experiment.generator.type == "ode" else 10
    n_draws = int(os.environ.get("CRASHTEST_DRAWS", default))
    for q in experiment.questions:
        if q.type != "misconception":
            continue
        seen = set()
        for c in q.choices:
            state = c.reveal_state.model_dump()
            key = (repr(state), c.verify)
            if key in seen:
                continue
            seen.add(key)
            rng = np.random.default_rng(7)
            passed = 0
            for i in range(n_draws):
                drawn = _draw_state(state, q.procedural_params, rng)
                drawn["seed"] = 42 + i
                passed += check_verify(experiment, drawn, c.verify)
            assert passed / n_draws >= 0.9, (
                f"{experiment.id} : verify de {q.id}/{c.id} passe {passed}/{n_draws} fois."
            )
