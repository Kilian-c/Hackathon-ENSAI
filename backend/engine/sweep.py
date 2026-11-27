"""Balayage (`POST /api/sweep`) : la mesure choisie sur une grille de valeurs d'un ou deux axes.

Un axe = `h.<id>` ou `p.<id>`. Même graine dans toutes les cases (seuls les axes changent). Tout vient du
YAML : aucun code propre à un théorème. Plafonds : 21 points par axe, 144 cases, 15 s.
"""

import math
import time
from typing import Any

import numpy as np

from backend.contracts import (
    MAX_SWEEP_POINTS,
    CriticalPoint,
    EngineState,
    SweepAxis,
    SweepResult,
)
from backend.engine.runner import RunError, _clean, _compute, spec_hash, verdict
from backend.engine.schema import ExperimentSpec
from backend.engine.state import healthy, resolve_state

MAX_CELLS = 144
MAX_SECONDS = 15.0
DEFAULT_POINTS = 11


def _fmt(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def axis_values(spec: ExperimentSpec, target: str) -> tuple[list[float | bool | str], list[str]]:
    """Valeurs et étiquettes d'un axe. `RunError` (français) si l'axe n'est pas balayable."""
    kind, _, name = target.partition(".")
    if kind == "h":
        hyp = spec.hypotheses.get(name)
        if hyp is None:
            raise RunError(f"Hypothèse inconnue : « {name} ».")
        if hyp.type == "choice":
            assert hyp.options is not None
            return list(hyp.options), [o.label for o in hyp.options.values()]
        if hyp.type == "boolean":
            healthy_label = hyp.ok_label or "Oui"
            broken_label = hyp.broken_label or "Non"
            # La valeur saine en premier
            if hyp.healthy_value:
                return [True, False], [healthy_label, broken_label]
            return [False, True], [healthy_label, broken_label]
        lo, hi = hyp.range
        values = [round(float(v), 10) for v in np.linspace(lo, hi, DEFAULT_POINTS)]
        if hyp.step:  # sur la grille du curseur, sans doublon, jamais hors de range
            snapped = (round(round(v / hyp.step) * hyp.step, 10) for v in values)
            values = sorted({min(max(v, lo), hi) for v in snapped})
        return values, [_fmt(v) for v in values]
    if kind == "p":
        param = spec.params.get(name)
        if param is None:
            raise RunError(f"Paramètre inconnu : « {name} ».")
        if param.type == "boolean":
            return [False, True], ["Non", "Oui"]
        if not param.sweep_values:
            raise RunError(f"Le paramètre « {name} » n'est pas balayable (pas de sweep_values).")
        values = [float(v) for v in param.sweep_values]
        return values, [_fmt(v) for v in values]
    raise RunError(f"Axe invalide : « {target} ».")


def _crossing(grid: list[float], gaps: list[float], limit: float) -> float | None:
    """Première valeur de l'axe où l'écart dépasse `limit`, interpolée linéairement."""
    for i in range(1, len(gaps)):
        if gaps[i - 1] <= limit < gaps[i]:
            if math.isinf(gaps[i]):
                return grid[i]
            frac = (limit - gaps[i - 1]) / (gaps[i] - gaps[i - 1])
            return grid[i - 1] + frac * (grid[i] - grid[i - 1])
    return None


def _gap(value: float, target: float, direction: str) -> float:
    if direction == "below":
        return max(target - value, 0.0)
    if direction == "above":
        return max(value - target, 0.0)
    return abs(value - target)


def sweep(
    spec: ExperimentSpec, state: EngineState, targets: list[str], measure: str | None = None
) -> SweepResult:
    t0 = time.perf_counter()
    if not 1 <= len(targets) <= 2:
        raise RunError("Un balayage porte sur un ou deux axes.")
    if len(set(targets)) != len(targets):
        raise RunError("Les deux axes doivent être différents.")
    name = measure or next(k for k, m in spec.measures.items() if m.primary)
    if name not in spec.measures:
        raise RunError(f"Mesure inconnue : « {name} ».")
    ms = spec.measures[name]
    axes = [axis_values(spec, t) for t in targets]
    if any(len(v) > MAX_SWEEP_POINTS for v, _ in axes):
        raise RunError(f"Un axe compte {MAX_SWEEP_POINTS} points au plus.")
    if math.prod(len(v) for v, _ in axes) > MAX_CELLS:
        raise RunError(f"Le balayage compte {MAX_CELLS} cases au plus.")

    key = spec_hash(spec)
    methods = [m.id for m in spec.methods]
    # Cases dans l'ordre [axe 2][axe 1] (une seule ligne pour un axe)
    second: list[Any] = [None] if len(axes) == 1 else list(axes[1][0])
    values: dict[str, list[list[float | None]]] = {m: [] for m in methods}
    mc_se: dict[str, list[list[float | None]]] = {m: [] for m in methods}
    states: dict[str, list[list[str]]] = {m: [] for m in methods}
    cell_targets: dict[str, list[float]] = {m: [] for m in methods}  # première ligne seulement (critical)
    for r, v2 in enumerate(second):
        row_vals: dict[str, list[float | None]] = {m: [] for m in methods}
        row_se: dict[str, list[float | None]] = {m: [] for m in methods}
        row_states: dict[str, list[str]] = {m: [] for m in methods}
        for v1 in axes[0][0]:
            cell = EngineState(
                params=dict(state.params),
                hypotheses=dict(state.hypotheses),
                extra_points=state.extra_points,
                seed=state.seed,
            )
            chosen = [v1] if v2 is None else [v1, v2]
            for target, value in zip(targets, chosen, strict=True):
                (cell.params if target[0] == "p" else cell.hypotheses)[target[2:]] = value
            rs = resolve_state(spec, cell)
            if time.perf_counter() - t0 > MAX_SECONDS:
                raise RunError(
                    "Le balayage est trop long : réduisez le nombre de points ou la taille de l'échantillon."
                )
            comp = _compute(spec, rs, key)
            base = _compute(spec, healthy(spec, rs), key)
            vals, ses, bvals = comp.values(name), comp.mc_se(name), base.values(name)
            for m in methods:
                row_vals[m].append(_clean(vals[m]))
                row_se[m].append(_clean(ses[m]))
                if ms.target is None:
                    continue
                target = bvals[m] if ms.target == "base" else float(ms.target)
                if r == 0:
                    cell_targets[m].append(target)
                row_states[m].append(
                    verdict(vals[m], target, ms.direction, ms.ok_within, ms.broken_beyond)  # type: ignore[arg-type]
                )
        for m in methods:
            values[m].append(row_vals[m])
            mc_se[m].append(row_se[m])
            states[m].append(row_states[m])

    one_axis = len(axes) == 1
    out_values: dict[str, Any] = {m: g[0] if one_axis else g for m, g in values.items()}
    out_se: dict[str, Any] = {m: g[0] if one_axis else g for m, g in mc_se.items()}
    out_states: dict[str, Any] = (
        {} if ms.target is None else {m: g[0] if one_axis else g for m, g in states.items()}
    )

    rs0 = resolve_state(spec, state)
    current = {t: (rs0.params if t[0] == "p" else rs0.hypotheses)[t[2:]] for t in targets}
    base0 = _compute(spec, healthy(spec, rs0), key).values(name)

    critical: dict[str, CriticalPoint | None] | None = None
    kind, _, aname = targets[0].partition(".")
    continuous = one_axis and (
        (kind == "h" and spec.hypotheses[aname].type == "continuous")
        or (kind == "p" and spec.params[aname].type == "number")
    )
    if continuous and ms.target is not None:
        grid = [float(v) for v in axes[0][0]]
        critical = {}
        for m in methods:
            gaps = [
                _gap(v, t, ms.direction) if v is not None else math.inf  # type: ignore[arg-type]
                for v, t in zip(out_values[m], cell_targets[m], strict=True)
            ]
            w = _crossing(grid, gaps, ms.ok_within)  # type: ignore[arg-type]
            b = _crossing(grid, gaps, ms.broken_beyond)  # type: ignore[arg-type]
            critical[m] = (
                CriticalPoint(warning_at=_clean(w), broken_at=_clean(b))
                if (w is not None or b is not None)
                else None
            )

    block: dict[str, Any] = {}
    if ms.target is not None:
        block = {
            "target": base0 if ms.target == "base" else float(ms.target),
            "ok_within": ms.ok_within,
            "broken_beyond": ms.broken_beyond,
            "direction": ms.direction,
        }
    return SweepResult(
        axes=[SweepAxis(target=t, values=v, labels=lab) for t, (v, lab) in zip(targets, axes, strict=True)],
        measure=name,
        values=out_values,
        mc_se=out_se,
        states=out_states,
        critical=critical,
        current=current,
        repeat_used=_compute(spec, rs0, key).n_repeat,
        compute_ms=round((time.perf_counter() - t0) * 1000, 1),
        **block,
    )
