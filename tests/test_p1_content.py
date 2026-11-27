"""Tests P1 de contenu (R1, section 4.10 du cahier) : 5 (défis atteignables), 7 (pathologies distinctes),
9 (état par défaut en moins de 500 ms). Les tests 2 et 6 sont dans `test_experiments.py`.
"""

import itertools
import time
from pathlib import Path

import pytest

from backend.contracts import EngineState
from backend.engine import runner
from backend.engine.loader import load_experiment_file
from backend.engine.sweep import axis_values
from backend.engine.training import _full_state, _partial, _pathologies

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
FILES = sorted(EXPERIMENTS_DIR.glob("*.yaml"))


@pytest.fixture(scope="module", params=FILES, ids=[p.stem for p in FILES])
def experiment(request):
    return load_experiment_file(request.param)


def _param_values(param) -> list:
    if param.type == "boolean":
        return [True, False]
    return sorted({param.min, param.default, param.max, *(param.sweep_values or [])})


# Test 5 : chaque défi est atteignable par un balayage (un axe, ou deux axes dont une hypothèse).
def test_5_every_challenge_is_reachable(experiment) -> None:
    axes = [("h", k, axis_values(experiment, f"h.{k}")[0]) for k in experiment.hypotheses]
    axes += [("p", k, _param_values(p)) for k, p in experiment.params.items()]
    wanted = {c.id for c in experiment.challenges}
    reached: set[str] = set()

    def visit(state: EngineState) -> None:
        for ch in runner.run(experiment, state).challenges:
            if ch.passed:
                reached.add(ch.id)

    visit(EngineState())
    for kind, name, values in axes:
        for v in values:
            visit(EngineState(**{"params" if kind == "p" else "hypotheses": {name: v}}))
    for (k1, n1, v1s), (k2, n2, v2s) in itertools.combinations(axes, 2):
        if wanted <= reached:
            break
        for v1, v2 in itertools.product(v1s, v2s):
            state = {"params": {}, "hypotheses": {}}
            state["params" if k1 == "p" else "hypotheses"][n1] = v1
            state["params" if k2 == "p" else "hypotheses"][n2] = v2
            visit(EngineState(**state))
    assert wanted <= reached, f"{experiment.id} : défis jamais atteints : {sorted(wanted - reached)}."


# Test 7 : les pathologies d'un diagnostic diffèrent d'au moins 3 mc_se sur une mesure principale.
def test_7_pathologies_are_distinguishable(experiment) -> None:
    main = next(m.id for m in experiment.methods if m.role == "method")
    for q in experiment.questions:
        if q.type != "diagnostic_auto":
            continue
        params, hyps = _partial(q.state, {k: p.min for k, p in q.procedural_params.items()})
        options = _pathologies(experiment, q)
        results = {
            p.key: runner.run(experiment, _full_state(experiment, params, {**hyps, **p.hypotheses}, 42))
            for p in options
        }
        for a, b in itertools.combinations(options, 2):
            ra, rb = results[a.key], results[b.key]
            separated = False
            for mid, ma in ra.measures.items():
                va, vb = ma.values.get(main), rb.measures[mid].values.get(main)
                if va is None or vb is None:
                    continue
                se = max(ma.mc_se.get(main) or 0.0, rb.measures[mid].mc_se.get(main) or 0.0)
                separated |= abs(va - vb) >= 3 * se and abs(va - vb) > 0
            assert separated, f"{experiment.id}/{q.id} : « {a.key} » et « {b.key} » ne se distinguent pas."


# Test 9 : l'état par défaut répond en moins de 500 ms (hors premier appel : tables de Tukey, imports).
def test_9_default_state_is_fast(experiment) -> None:
    runner.run(experiment, EngineState())  # échauffement
    runner._CACHE.clear()
    t0 = time.perf_counter()
    runner.run(experiment, EngineState())
    assert time.perf_counter() - t0 < 0.5, f"{experiment.id} : l'état par défaut dépasse 500 ms."
