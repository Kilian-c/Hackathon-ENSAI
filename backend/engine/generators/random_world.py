"""Générateur `random` (R1) : Monte Carlo vectorisé, `repeat` échantillons de taille `n` d'un coup.

Les variables du YAML sont calculées dans l'ordre de leurs dépendances. Chaque variable tire dans son
propre flux (`rng_for(seed, <variable>)`) : changer une hypothèse ne décale jamais les tirages des
autres variables, donc la Référence et l'état courant partagent les mêmes aléas.

Formes : `(repeat, n)` par défaut ; `dims: sample` donne `(repeat,)`. (`obs_p`, P2, n'est pas géré.)
"""

from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from typing import Any

import numpy as np

from backend.engine.expr import Compiled, Env, ExprError, compile_expr
from backend.engine.laws import sample_law
from backend.engine.rng import rng_for
from backend.engine.schema import MAX_N, MAX_REPEAT, ExperimentSpec, RandomGenerator
from backend.engine.state import ResolvedState


@dataclass
class World:
    """Le monde simulé : une matrice par variable, plus ce qu'il faut pour y ajouter des points."""

    variables: dict[str, np.ndarray]
    repeat: int
    n: int
    inject: dict[str, str] = field(default_factory=dict)  # emplacement -> variable

    def first(self, name: str) -> np.ndarray:
        """Premier échantillon (répétition 0) : `gen.<variable>`."""
        return self.variables[name][0]

    def with_extra_points(self, points: list[dict[str, float]]) -> "World":
        """Ajoute les points posés au clic à toutes les répétitions (jamais à la Référence).

        Seules les variables de `inject` grandissent ; chaque point fournit une valeur par emplacement.
        """
        if not points:
            return self
        if not self.inject:
            raise ExprError("Cette expérience n'accepte pas de points ajoutés (pas de `inject`).")
        grown = dict(self.variables)
        for slot, var in self.inject.items():
            try:
                column = np.array([p[slot] for p in points], dtype=float)
            except KeyError as exc:
                raise ExprError(f"Un point ajouté doit donner une valeur pour « {slot} ».") from exc
            grown[var] = np.concatenate(
                [self.variables[var], np.broadcast_to(column, (self.repeat, len(points)))], axis=-1
            )
        return World(grown, self.repeat, self.n + len(points), self.inject)


def _order(generator: RandomGenerator, compiled: dict[str, Compiled], option_deps: dict[str, set[str]]):
    graph: dict[str, set[str]] = {}
    for name, c in compiled.items():
        deps = c.names & set(generator.variables)
        for hid in c.options:
            deps |= option_deps.get(hid, set()) & set(generator.variables)
        graph[name] = deps
    try:
        return list(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        raise ExprError(f"Cycle entre variables : {' -> '.join(exc.args[1])}.") from exc


def _scalar_namespaces(state: ResolvedState) -> dict[str, dict[str, Any]]:
    return {"p": dict(state.params), "h": dict(state.hypotheses)}


def generate(spec: ExperimentSpec, state: ResolvedState) -> World:
    generator = spec.generator
    if not isinstance(generator, RandomGenerator):
        raise ExprError("generate() ne gère que le générateur `random`.")
    namespaces = _scalar_namespaces(state)

    n = generator.n
    if isinstance(n, str):
        n = compile_expr(n).evaluate(Env(namespaces=namespaces))
    n = int(round(float(n)))
    repeat = generator.repeat
    if not 1 <= n <= MAX_N:
        raise ExprError(f"La taille d'échantillon doit être comprise entre 1 et {MAX_N}.")
    if not 1 <= repeat <= MAX_REPEAT:
        raise ExprError(f"Le nombre de répétitions doit être compris entre 1 et {MAX_REPEAT}.")

    compiled = {name: compile_expr(var.expr) for name, var in generator.variables.items()}
    option_exprs = {
        (hid, oid): compile_expr(opt.expr)
        for hid, hyp in spec.hypotheses.items()
        for oid, opt in (hyp.options or {}).items()
        if opt.expr is not None
    }
    option_deps: dict[str, set[str]] = {}
    for (hid, _), c in option_exprs.items():
        option_deps.setdefault(hid, set()).update(c.names)

    values: dict[str, np.ndarray] = {}
    idx = np.arange(n)
    for name in _order(generator, compiled, option_deps):
        var = generator.variables[name]
        if var.dims == "obs_p":
            raise ExprError(f"La variable « {name} » : `dims: obs_p` n'est pas pris en charge (P2).")
        shape = (repeat,) if var.dims == "sample" else (repeat, n)
        rng = rng_for(state.seed, name)

        def law(law_name: str, _rng=rng, _shape=shape) -> np.ndarray:
            return sample_law(law_name, _rng, _shape)

        holder: dict[str, Env] = {}

        def option(hid: str, _rng=rng, _shape=shape, _holder=holder) -> Any:
            hyp = spec.hypotheses[hid]
            chosen = hyp.options[state.hypotheses[hid]]
            if chosen.law is not None:
                return sample_law(chosen.law, _rng, _shape)
            return option_exprs[(hid, state.hypotheses[hid])].evaluate(_holder["env"])

        env = Env(
            variables={**values, "idx": idx},
            namespaces=namespaces,
            functions={
                "law": law,
                "normal": lambda: law("normal"),
                "uniform": lambda: law("uniform"),
                "bernoulli": lambda p, _rng=rng, _shape=shape: _rng.random(_shape) < p,
            },
            option=option,
        )
        holder["env"] = env
        result = np.asarray(compiled[name].evaluate(env))
        try:
            values[name] = np.array(np.broadcast_to(result, shape))
        except ValueError as exc:
            raise ExprError(
                f"La variable « {name} » a une forme {result.shape} incompatible avec {shape}."
            ) from exc

    world = World(values, repeat, n, dict(generator.inject or {}))
    return world.with_extra_points(state.extra_points)
