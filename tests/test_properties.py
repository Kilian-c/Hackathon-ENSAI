"""Propriétés du moteur (R1, P1) : état canonique, hash stable, déterminisme, graine."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from backend.api import registry
from backend.contracts import EngineState
from backend.engine import runner
from backend.engine.state import resolve_state

SPEC = registry.official()["regression-lineaire"]
FAST = settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
hetero = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
seeds = st.integers(min_value=0, max_value=10**6)


@FAST
@given(h=hetero, seed=seeds)
def test_hash_ignores_key_order_and_defaults(h: float, seed: int) -> None:
    a = resolve_state(SPEC, EngineState(hypotheses={"hetero": h}, seed=seed))
    full = {**a.params}
    reordered = dict(reversed(list(full.items())))
    b = resolve_state(SPEC, EngineState(params=reordered, hypotheses={"hetero": h}, seed=seed))
    assert a.hash() == b.hash() and len(a.hash()) == 16


@FAST
@given(h=hetero)
def test_resolve_is_idempotent_and_snaps_to_step(h: float) -> None:
    a = resolve_state(SPEC, EngineState(hypotheses={"hetero": h}))
    b = resolve_state(SPEC, EngineState(params=a.params, hypotheses=a.hypotheses, seed=a.seed))
    assert a == b


@FAST
@given(seed=seeds)
def test_seed_changes_hash_not_validity(seed: int) -> None:
    a = resolve_state(SPEC, EngineState(seed=seed))
    b = resolve_state(SPEC, EngineState(seed=seed + 1))
    assert a.hash() != b.hash()


@settings(max_examples=8, deadline=None)
@given(h=hetero, seed=seeds)
def test_run_is_deterministic_and_cache_independent(h: float, seed: int) -> None:
    state = EngineState(params={"n": 30}, hypotheses={"hetero": h}, seed=seed)
    first = runner.run(SPEC, state)
    runner._CACHE.clear()
    second = runner.run(SPEC, state)
    assert first.state_hash == second.state_hash
    values = {k: m.values for k, m in first.measures.items()}
    assert values == {k: m.values for k, m in second.measures.items()}
    assert [v.model_dump() for v in first.views] == [v.model_dump() for v in second.views]
