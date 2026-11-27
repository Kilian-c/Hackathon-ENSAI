"""Mini-pipeline de test (R2) : rejoue `run()` avec les briques déjà livrées, sans toucher au code de R1.

Il fait : état résolu -> monde (générateur `random` de R1, ou `ode` minimal ci-dessous) -> méthodes
-> agrégateurs -> verdicts (règle du CLAUDE.md, section 8) -> Référence -> défis.

Ce n'est PAS le moteur : ni cache, ni vues, ni plafonds de durée. Dès que `backend/engine/runner.py`
existe, remplacer `mini_run` par un appel à `run()` dans `tests/test_experiments.py` (une seule
fonction : `run_state`). TODO(passation) : retirer ce fichier à ce moment-là.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

import backend.methods.integrate  # noqa: F401  (enregistrent les méthodes)
import backend.methods.ols_ci  # noqa: F401
import backend.methods.one_sample_test  # noqa: F401
from backend.contracts import EngineState
from backend.engine.aggregators import AGGREGATORS, AggResult
from backend.engine.expr import Env, ExprError, Layered, compile_expr
from backend.engine.generators.random_world import generate
from backend.engine.method_contract import get_method
from backend.engine.rng import rng_for
from backend.engine.schema import ExperimentSpec, OdeGenerator, RandomGenerator
from backend.engine.state import healthy, resolve_state

_N_GRID = 400


@dataclass
class MiniResult:
    values: dict[str, dict[str, float]] = field(default_factory=dict)  # mesure -> méthode -> valeur
    mc_se: dict[str, dict[str, float | None]] = field(default_factory=dict)
    states: dict[str, dict[str, str | None]] = field(default_factory=dict)  # "ok" | "warning" | "broken"
    baseline: dict[str, dict[str, float]] = field(default_factory=dict)
    challenges: dict[str, bool] = field(default_factory=dict)
    primary_measure: str = ""
    primary_method: str = ""
    world: Any = None  # monde `random` (variables par répétition) ou None


def verdict(value: float, target: float, direction: str, ok_within: float, broken_beyond: float) -> str:
    """La règle unique de verdict (CLAUDE.md, section 8)."""
    if direction == "below":
        gap = max(target - value, 0.0)
    elif direction == "above":
        gap = max(value - target, 0.0)
    else:
        gap = abs(value - target)
    return "ok" if gap <= ok_within else ("broken" if gap > broken_beyond else "warning")


def _eval_arg(value: Any, env: Env) -> Any:
    """Un argument YAML : expression si elle s'évalue, sinon texte littéral (« euler », « HC3 »...)."""
    if not isinstance(value, str):
        return value
    try:
        return compile_expr(value).evaluate(env)
    except ExprError:
        return value


def _ode_world(spec: ExperimentSpec, rs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Générateur `ode` minimal : renvoie (variables pour les arguments, None)."""
    gen = spec.generator
    assert isinstance(gen, OdeGenerator)
    namespaces = {"p": dict(rs.params), "h": dict(rs.hypotheses)}
    env0 = Env(namespaces=namespaces)

    def scalar(v: Any) -> float:
        return float(compile_expr(v).evaluate(env0)) if isinstance(v, str) else float(v)

    names = list(gen.state)
    y0 = np.array([scalar(gen.state[k]) for k in names])
    t_end = scalar(gen.t_end)
    compiled = [compile_expr(gen.rhs[k]) for k in names]

    def rhs(y: np.ndarray) -> np.ndarray:
        env = Env(variables={k: y[i] for i, k in enumerate(names)}, namespaces=namespaces)
        return np.array([c.evaluate(env) for c in compiled], dtype=float)

    t = np.linspace(0.0, t_end, _N_GRID)
    sol = solve_ivp(lambda _t, v: rhs(v), (0.0, t_end), y0, t_eval=t, rtol=1e-10, atol=1e-10)
    system = {"rhs": rhs, "y0": y0, "t_end": t_end, "t": t, "ref": sol.y[0]}
    variables: dict[str, Any] = {"system": system, "t": t}
    variables.update({k: sol.y[i] for i, k in enumerate(names)})
    for k, expr in (gen.derived or {}).items():
        variables[k] = compile_expr(expr).evaluate(Env(variables=variables, namespaces=namespaces))
    return variables, {}


_CACHE: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any], Any]] = {}


def _compute(spec: ExperimentSpec, rs: Any) -> tuple[dict[str, Any], dict[str, Any], Any]:
    """Applique toutes les méthodes (avec un cache par état, pour la Référence)."""
    key = (spec.id, rs.hash())
    if key not in _CACHE:
        _CACHE[key] = _compute_uncached(spec, rs)
    return _CACHE[key]


def _compute_uncached(spec: ExperimentSpec, rs: Any) -> tuple[dict[str, Any], dict[str, Any], Any]:
    """Renvoie (valeurs, erreurs MC, monde) : mesure -> méthode -> nombre."""
    namespaces = {"p": dict(rs.params), "h": dict(rs.hypotheses)}
    if isinstance(spec.generator, RandomGenerator):
        world = generate(spec, rs)
        variables: dict[str, Any] = dict(world.variables)
    else:
        variables, _ = _ode_world(spec, rs)
        world = None
    env = Env(variables=variables, namespaces=namespaces)

    results = {}
    for m in spec.methods:
        kwargs = {k: _eval_arg(v, env) for k, v in m.args.items()}
        method = get_method(m.call)
        results[m.id] = method.fn(**kwargs, rng=rng_for(rs.seed, f"method:{m.id}"))

    values: dict[str, dict[str, float]] = {k: {} for k in spec.measures}
    mc_se: dict[str, dict[str, float | None]] = {k: {} for k in spec.measures}
    for mid, res in results.items():
        funcs = {name: (lambda *a, _f=f: _f(*a)) for name, f in AGGREGATORS.items()}
        aenv = Env(
            variables=dict(res.summary),
            namespaces={**namespaces, "reps": res.reps, "example": res.example, "curves": res.curves},
            functions=funcs,
        )
        for name, measure in spec.measures.items():
            out = compile_expr(measure.agg).evaluate(aenv)
            assert isinstance(out, AggResult), f"{name} : l'agrégateur doit renvoyer un AggResult."
            values[name][mid] = out.value
            mc_se[name][mid] = out.mc_se
    return values, mc_se, world


def mini_run(spec: ExperimentSpec, state: dict[str, Any] | EngineState | None = None) -> MiniResult:
    """Équivalent de `run(experiment, state)` pour les tests de contenu."""
    if not isinstance(state, EngineState):
        state = EngineState(**(state or {}))
    rs = resolve_state(spec, state)
    values, mc_se, world = _compute(spec, rs)
    base_values, _, _ = _compute(spec, healthy(spec, rs))

    primary_method = next(m.id for m in spec.methods if m.role == "method")
    primary_measure = next((k for k, m in spec.measures.items() if m.primary), next(iter(spec.measures)))
    states: dict[str, dict[str, str | None]] = {}
    for name, measure in spec.measures.items():
        states[name] = {}
        for mid, val in values[name].items():
            if measure.direction is None or measure.target is None:
                states[name][mid] = None
                continue
            target = base_values[name][mid] if measure.target == "base" else float(measure.target)
            states[name][mid] = verdict(
                val, target, measure.direction, measure.ok_within or 0.0, measure.broken_beyond or 0.0
            )

    res = MiniResult(values, mc_se, states, base_values, {}, primary_measure, primary_method, world)
    ns = namespaces_for(spec, rs, res)
    for ch in spec.challenges:
        res.challenges[ch.id] = bool(compile_expr(ch.when).evaluate(Env(namespaces=ns)))
    return res


def namespaces_for(spec: ExperimentSpec, rs: Any, res: MiniResult) -> dict[str, Any]:
    """Espaces de noms `p`, `h`, `m`, `s`, `base` pour les défis et les conditions `verify`."""
    pm = res.primary_method
    return {
        "p": dict(rs.params),
        "h": dict(rs.hypotheses),
        "m": {k: Layered(v, default=v[pm]) for k, v in res.values.items()},
        "s": {k: Layered(v, default=v[pm]) for k, v in res.states.items()},
        "base": {k: Layered(v, default=v[pm]) for k, v in res.baseline.items()},
    }


def check_verify(spec: ExperimentSpec, state: dict[str, Any], expr: str) -> bool:
    """Lance l'état et évalue une condition `verify` (ou un `when`) dessus."""
    rs = resolve_state(spec, EngineState(**state))
    res = mini_run(spec, state)
    return bool(compile_expr(expr).evaluate(Env(namespaces=namespaces_for(spec, rs, res))))


__all__ = ["MiniResult", "check_verify", "mini_run", "verdict"]
