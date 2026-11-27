"""`run(experiment, state) -> RunResult` : la seule fonction de calcul du moteur (CLAUDE.md, section 8).

Pipeline : état résolu -> monde (générateur `random` ou `ode`) -> TOUTES les méthodes -> agrégateurs
-> verdicts (règle unique ci-dessous) -> Référence (même chose à l'état sain, en cache) -> défis -> vues.

Aucun code propre à un théorème : tout vient du YAML (`measures`, `bind` des vues, `affects`...).
Écrit par R2 (aide à R1), à relire par R1. TODO(passation) : vues `sensitivity` / `validity_domain`
(vides ici : l'interface appelle /api/sweep), segments et calques du nuage (P2).
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

import backend.methods  # noqa: F401  (importer le paquet enregistre toutes les méthodes)
from backend.contracts import (
    SCHEMA_VERSION,
    ChallengeResult,
    DrawLog,
    EngineState,
    EquationResult,
    EquationTermResult,
    MeasureResult,
    MethodInfo,
    RunResult,
    RunWarning,
    Series,
    ViewAxes,
    ViewResult,
)
from backend.engine.aggregators import AGGREGATORS, AggResult
from backend.engine.expr import Env, ExprError, Layered, compile_expr
from backend.engine.fastexpr import compile_fast
from backend.engine.generators.random_world import generate
from backend.engine.method_contract import MethodResult, get_method
from backend.engine.rng import rng_for
from backend.engine.schema import ExperimentSpec, OdeGenerator, RandomGenerator
from backend.engine.state import ResolvedState, healthy, resolve_state

N_GRID = 400  # points de la grille de temps du générateur `ode`
SHOWN_INTERVALS = 100  # intervalles empilés affichés (vue Répétitions)
SHOWN_PATHS = 30  # trajectoires affichées (vue Répétitions, mode trajectoires)
INVALID_WARN = 0.05
_CACHE_SIZE = 48


class RunError(ValueError):
    """Calcul impossible (message en français)."""


# --- Verdict : une seule règle -----------------------------------------------------------------------------


def verdict(value: float, target: float, direction: str, ok_within: float, broken_beyond: float) -> str:
    """CLAUDE.md, section 8 : écart selon la direction, puis ok / warning / broken."""
    if direction == "below":
        gap = max(target - value, 0.0)
    elif direction == "above":
        gap = max(value - target, 0.0)
    else:
        gap = abs(value - target)
    return "ok" if gap <= ok_within else ("broken" if gap > broken_beyond else "warning")


# --- Calcul d'un état (mis en cache : la Référence sert à tous les états du même jeu de paramètres) ------


@dataclass
class Computed:
    results: dict[str, MethodResult]
    aggs: dict[str, dict[str, AggResult]]  # mesure -> méthode -> résultat d'agrégateur
    variables: dict[str, Any]  # variables du générateur (`gen.<nom>`)
    n_repeat: int
    warnings: list[RunWarning] = field(default_factory=list)

    def values(self, measure: str) -> dict[str, float]:
        return {m: a.value for m, a in self.aggs[measure].items()}

    def mc_se(self, measure: str) -> dict[str, float | None]:
        return {m: a.mc_se for m, a in self.aggs[measure].items()}


_CACHE: OrderedDict[tuple[str, str], Computed] = OrderedDict()


def spec_hash(spec: ExperimentSpec) -> str:
    text = f"{SCHEMA_VERSION}|{spec.model_dump_json(by_alias=True)}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _scalar(value: Any, env: Env) -> float:
    return float(compile_expr(value).evaluate(env)) if isinstance(value, str) else float(value)


def _ode_world(spec: ExperimentSpec, rs: ResolvedState) -> dict[str, Any]:
    """Générateur `ode` : `t`, solution de référence par variable d'état, `derived`, `system` (méthodes)."""
    gen = spec.generator
    assert isinstance(gen, OdeGenerator)
    namespaces: dict[str, Any] = {"p": dict(rs.params), "h": dict(rs.hypotheses)}
    env0 = Env(namespaces=namespaces)
    names = list(gen.state)
    y0 = np.array([_scalar(gen.state[k], env0) for k in names])
    t_end = _scalar(gen.t_end, env0)
    compiled = [compile_expr(gen.rhs[k]) for k in names]

    # Boucle chaude : chaque équation devient une fermeture (p.*, h.* et constantes pré-calculés).
    fast = [compile_fast(gen.rhs[k], namespaces, {n: i for i, n in enumerate(names)}) for k in names]
    if all(f is not None for f in fast):

        def rhs(y: np.ndarray) -> np.ndarray:
            return np.array([f(y) for f in fast], dtype=float)  # type: ignore[misc]

    else:  # expression hors du sous-ensemble rapide : évaluateur général
        scope: dict[str, Any] = {}
        env = Env(variables=scope, namespaces=namespaces)

        def rhs(y: np.ndarray) -> np.ndarray:
            for i, k in enumerate(names):
                scope[k] = y[i]
            return np.array([c.evaluate(env) for c in compiled], dtype=float)

    t = np.linspace(0.0, t_end, N_GRID)
    sol = solve_ivp(lambda _t, v: rhs(v), (0.0, t_end), y0, t_eval=t, rtol=1e-10, atol=1e-10)
    variables: dict[str, Any] = {
        "t": t,
        "system": {"rhs": rhs, "y0": y0, "t_end": t_end, "t": t, "ref": sol.y[0]},
    }
    variables.update({k: sol.y[i] for i, k in enumerate(names)})
    for k, expr in (gen.derived or {}).items():
        variables[k] = compile_expr(expr).evaluate(Env(variables=variables, namespaces=namespaces))
    return variables


def _eval_arg(value: Any, env: Env) -> Any:
    """Un argument YAML : expression si elle s'évalue, sinon texte littéral (« euler », « HC3 »...)."""
    if not isinstance(value, str):
        return value
    try:
        return compile_expr(value).evaluate(env)
    except ExprError:
        return value


def _compute(spec: ExperimentSpec, rs: ResolvedState, key: str) -> Computed:
    cache_key = (key, rs.hash())
    if cache_key in _CACHE:
        _CACHE.move_to_end(cache_key)
        return _CACHE[cache_key]
    out = _compute_uncached(spec, rs)
    _CACHE[cache_key] = out
    while len(_CACHE) > _CACHE_SIZE:
        _CACHE.popitem(last=False)
    return out


def _compute_uncached(spec: ExperimentSpec, rs: ResolvedState) -> Computed:
    namespaces: dict[str, Any] = {"p": dict(rs.params), "h": dict(rs.hypotheses)}
    try:
        if isinstance(spec.generator, RandomGenerator):
            world = generate(spec, rs)
            variables: dict[str, Any] = dict(world.variables)  # points posés : déjà dans generate()
            n_repeat = world.repeat
        elif isinstance(spec.generator, OdeGenerator):
            variables = _ode_world(spec, rs)
            n_repeat = 1
        else:
            raise RunError("Ce type de générateur n'est pas encore pris en charge.")
    except ExprError as exc:
        raise RunError(str(exc)) from exc
    env = Env(variables=variables, namespaces=namespaces)

    results: dict[str, MethodResult] = {}
    for m in spec.methods:
        kwargs = {k: _eval_arg(v, env) for k, v in m.args.items()}
        results[m.id] = get_method(m.call).fn(**kwargs, rng=rng_for(rs.seed, f"method:{m.id}"))

    funcs = {name: (lambda *a, _f=f: _f(*a)) for name, f in AGGREGATORS.items()}
    aggs: dict[str, dict[str, AggResult]] = {k: {} for k in spec.measures}
    for mid, res in results.items():
        aenv = Env(
            variables=dict(res.summary),
            namespaces={**namespaces, "reps": res.reps, "example": res.example, "curves": res.curves},
            functions=funcs,
        )
        for name, measure in spec.measures.items():
            try:
                out = compile_expr(measure.agg).evaluate(aenv)
            except ExprError as exc:
                raise RunError(f"Mesure « {name} » : {exc}") from exc
            if not isinstance(out, AggResult):
                raise RunError(f"Mesure « {name} » : l'agrégateur doit renvoyer un résultat d'agrégation.")
            aggs[name][mid] = out
    return Computed(results, aggs, variables, n_repeat)


# --- Mise en forme ------------------------------------------------------------------------------------------


def _clean(value: float | None) -> float | None:
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _fr(value: float, scale: float, decimals: int, unit: str) -> str:
    text = f"{value * scale:.{decimals}f}".replace(".", ",")
    return f"{text} {unit}".strip() if unit else text


def _floats(arr: Any) -> list[float | None]:
    return [_clean(v) for v in np.asarray(arr, dtype=float).ravel()]


def _stable_range(values: np.ndarray) -> list[float] | None:
    """Bornes stables : quantiles 0,5 % et 99,5 % de la Référence, plus 10 % de marge."""
    v = np.asarray(values, dtype=float).ravel()
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    lo, hi = np.quantile(v, [0.005, 0.995])
    pad = (hi - lo) * 0.1 or 0.5
    return [float(lo - pad), float(hi + pad)]


def _namespaces(spec: ExperimentSpec, rs: ResolvedState, comp: Computed, base: Computed) -> dict[str, Any]:
    primary = next(m.id for m in spec.methods if m.role == "method")
    ns: dict[str, Any] = {"p": dict(rs.params), "h": dict(rs.hypotheses), "m": {}, "s": {}, "base": {}}
    for name, measure in spec.measures.items():
        vals, bvals = comp.values(name), base.values(name)
        ns["m"][name] = Layered(vals, default=vals[primary])
        se = comp.mc_se(name)
        ns["m"][f"{name}_se"] = Layered(se, default=se[primary])
        ns["base"][name] = Layered(bvals, default=bvals[primary])
        if measure.target is not None:
            states = {
                mid: verdict(
                    v,
                    bvals[mid] if measure.target == "base" else float(measure.target),
                    measure.direction,
                    measure.ok_within,
                    measure.broken_beyond,
                )  # type: ignore[arg-type]
                for mid, v in vals.items()
            }
            ns["s"][name] = Layered(states, default=states[primary])
    return ns


def _measure_results(spec: ExperimentSpec, comp: Computed, base: Computed) -> dict[str, MeasureResult]:
    out: dict[str, MeasureResult] = {}
    for name, ms in spec.measures.items():
        vals, bvals, se = comp.values(name), base.values(name), comp.mc_se(name)
        block = MeasureResult(
            label=ms.label,
            unit=ms.unit,
            scale=ms.scale,
            decimals=ms.decimals,
            primary=ms.primary,
            values={m: _clean(v) for m, v in vals.items()},
            mc_se={m: _clean(v) for m, v in se.items()},
            baseline={m: _clean(v) for m, v in bvals.items()},
        )
        if ms.target is not None:
            block.target, block.direction = ms.target, ms.direction
            block.ok_within, block.broken_beyond = ms.ok_within, ms.broken_beyond
            for mid, v in vals.items():
                target = bvals[mid] if ms.target == "base" else float(ms.target)
                if not math.isfinite(v):
                    state = "broken"
                else:
                    state = verdict(v, target, ms.direction, ms.ok_within, ms.broken_beyond)  # type: ignore[arg-type]
                block.states[mid] = state  # type: ignore[assignment]
                if ms.texts is not None and math.isfinite(v):
                    block.texts[mid] = getattr(ms.texts, state).replace(
                        "{value}", _fr(v, ms.scale, ms.decimals, ms.unit)
                    )
        out[name] = block
    return out


def _equation(spec: ExperimentSpec, rs: ResolvedState) -> EquationResult:
    """`violated_by` d'un terme : les hypothèses cassées (≠ valeur saine) dont `affects` le cite."""
    terms: dict[str, EquationTermResult] = {
        t: EquationTermResult(violated_by=[]) for t in spec.equation.terms
    }
    for hid, hyp in spec.hypotheses.items():
        if rs.hypotheses[hid] == hyp.healthy_value:
            continue
        for term in hyp.affects:
            if term in terms:
                terms[term].violated_by.append(hid)
    return EquationResult(terms=terms)


# --- Vues ---------------------------------------------------------------------------------------------------

_SPECIAL_VIEWS = {"sensitivity", "validity_domain"}


def _path(comp: Computed, method: str, path: str, rs: ResolvedState) -> Any | None:
    """Résout un chemin (`reps.est`, `example.y`, `curves.t`, `gen.theta`, `p.beta1`)."""
    root, _, key = path.partition(".")
    if root == "gen":
        return comp.variables.get(key)
    if root == "p":
        return rs.params.get(key)
    res = comp.results[method]
    block = {"reps": res.reps, "example": res.example, "curves": res.curves}.get(root)
    return None if block is None else block.get(key)


def _bind_paths(bind: dict[str, Any]) -> dict[str, str]:
    """Aplatit un `bind` : emplacement -> chemin. Les formes `{path, layer}` et `[{y, label}]` sont lues ;
    les segments (calques du nuage, P2) sont ignorés."""
    out: dict[str, str] = {}
    for slot, spec in bind.items():
        if slot == "segments":
            continue
        if isinstance(spec, str):
            out[slot] = spec
        elif isinstance(spec, dict) and isinstance(spec.get("path"), str):
            out[slot] = spec["path"]
        elif isinstance(spec, list):  # series: [{y: path, label}]
            for item in spec:
                if isinstance(item, dict) and isinstance(item.get("y"), str):
                    out[slot] = item["y"]
    return out


def _method_role(spec: ExperimentSpec) -> dict[str, str]:
    roles: dict[str, str] = {}
    alt = 0
    for m in spec.methods:
        if m.role == "alternative":
            alt += 1
            roles[m.id] = f"alternative_{alt}"
        else:
            roles[m.id] = m.role
    return roles


_COMPANIONS = ("low", "high", "hit")  # emplacements lus par la série `est` d'une vue Répétitions
# Emplacements lus sur la méthode principale seulement (annexe E du cahier), dessinés comme une donnée fixe.
_MAIN_ONLY = {"h1": "Sous l'alternative", "observed": "Valeur observée"}
# Libellés et rôles par défaut des emplacements scalaires (`p.<id>`) ; `ui.labels` les remplace.
_SCALAR_LABELS = {"threshold": "Seuil", "truth": "Valeur vraie"}
_SCALAR_ROLES = {"threshold": "rupture"}


def _paths_series(
    view_id: str, method: str, role: str, label: str, grid: np.ndarray | None, arr: np.ndarray
) -> Series:
    """Série `paths` : une liste par trajectoire (SHOWN_PATHS au plus), abscisse commune facultative."""
    return Series(
        id=f"{view_id}.paths.{method}",
        slot="paths",
        method=method,
        role=role,  # type: ignore[arg-type]
        label=label,
        x=_floats(grid) if grid is not None else None,
        paths=[_floats(row) for row in arr[:SHOWN_PATHS]],
    )


def _arr(value: Any) -> np.ndarray | None:
    return None if value is None else np.asarray(value, dtype=float)


def _build_view(
    spec: ExperimentSpec, view: Any, rs: ResolvedState, comp: Computed, base: Computed
) -> ViewResult:
    mode = view.mode if view.mode in ("intervals", "paths") else None
    result = ViewResult(id=view.id, type=view.type, title=view.title, mode=mode, ui=view.ui)
    if view.type in _SPECIAL_VIEWS or not view.bind:
        return result
    paths = _bind_paths(view.bind)
    roles, labels = _method_role(spec), {m.id: m.label for m in spec.methods}
    primary = next(m.id for m in spec.methods if m.role == "method")
    ui_labels = dict((view.ui or {}).get("labels") or {})  # champ libre `ui` : nom de chaque emplacement
    for slot, items in view.bind.items():  # `series: [{ y, label }]` (annexe E) : le libellé du YAML
        if isinstance(items, list) and slot != "segments":
            named = [i["label"] for i in items if isinstance(i, dict) and i.get("label")]
            if named:
                ui_labels.setdefault(slot, named[-1])

    def label_for(slot: str, method: str) -> str:
        if slot not in ui_labels:
            return labels[method]
        return str(ui_labels[slot]) if method == primary else f"{ui_labels[slot]} : {labels[method]}"

    x_path = paths.get("x") or paths.get("t")
    is_distribution = view.type == "distribution"
    is_intervals = view.type == "repetitions"
    paired = "y" in paths  # nuage : (x, y) = données du générateur, communes à toutes les méthodes
    xs: list[np.ndarray] = []  # valeurs qui fixent les bornes (Référence d'abord)
    ys: list[np.ndarray] = []
    seen: set[tuple[str, bytes]] = set()
    ref_done: set[str] = set()
    shown = total = 0
    path_arrays: list[np.ndarray] = []  # trajectoires (vue Répétitions, mode trajectoires)
    ref_paths: np.ndarray | None = None
    ref_x: np.ndarray | None = None

    for slot, path in paths.items():
        root = path.split(".")[0]
        if slot in ("x", "t") or (is_intervals and slot in _COMPANIONS):
            continue
        if root == "p":  # valeur scalaire : vraie valeur d'un paramètre, seuil
            result.series.append(
                Series(
                    id=f"{view.id}.{slot}.gen",
                    slot=slot,
                    role=_SCALAR_ROLES.get(slot, "truth"),  # type: ignore[arg-type]
                    label=str(ui_labels.get(slot) or _SCALAR_LABELS.get(slot, "Valeur vraie")),
                    value=_clean(_path(comp, primary, path, rs)),
                )
            )
            continue
        if slot in _MAIN_ONLY:  # h1, observed : lus sur la méthode principale, toujours affichés
            yv = _arr(_path(comp, primary, path, rs))
            if yv is None:
                continue
            if is_distribution:  # une grandeur : x porte les valeurs
                sx, sy = _floats(yv), None
                xs.append(yv)
            else:
                xv = _arr(_path(comp, primary, x_path, rs)) if x_path else None
                sx, sy = (_floats(xv) if xv is not None else None), _floats(yv)
                ys.append(yv)
            result.series.append(
                Series(
                    id=f"{view.id}.{slot}.{primary}",
                    slot=slot,
                    method=primary,
                    role="truth",
                    label=str(ui_labels.get(slot) or _MAIN_ONLY[slot]),
                    x=sx,
                    y=sy,
                )
            )
            continue
        if root == "gen":  # tableau du générateur (solution exacte), tracé contre `t`
            yt = _arr(_path(comp, primary, path, rs))
            xt = _arr(_path(comp, primary, x_path, rs)) if x_path else None
            if yt is not None:
                result.series.append(
                    Series(
                        id=f"{view.id}.{slot}.gen",
                        slot=slot,
                        role="truth",
                        label="Solution de référence",
                        x=_floats(xt) if xt is not None else None,
                        y=_floats(yt),
                    )
                )
                ys.append(yt)
                if xt is not None:
                    xs.append(xt)
            continue
        if slot == "paths":  # faisceau de trajectoires : tableau (trajectoires, k), une série par méthode
            for m in spec.methods:
                grid = _arr(_path(comp, m.id, x_path, rs)) if x_path else None
                arr = _arr(_path(comp, m.id, path, rs))
                if arr is None or arr.ndim != 2:
                    continue
                fingerprint = (slot, np.ascontiguousarray(arr).tobytes())
                if fingerprint in seen:  # trajectoires identiques pour deux méthodes : dessinées une fois
                    continue
                seen.add(fingerprint)
                result.series.append(_paths_series(view.id, m.id, roles[m.id], labels[m.id], grid, arr))
                shown, total = min(arr.shape[0], SHOWN_PATHS), comp.n_repeat
                path_arrays.append(arr)
            ref_m = base.results.get(primary)
            ref_arr = _arr(_path(base, primary, path, rs)) if ref_m is not None else None
            if ref_arr is not None and ref_arr.ndim == 2:
                ref_grid = _arr(_path(base, primary, x_path, rs)) if x_path else None
                ref = _paths_series(view.id, primary, "reference", "Référence (état sain)", ref_grid, ref_arr)
                ref.id = f"{view.id}.paths.{primary}.ref"
                result.series.insert(0, ref)
                ref_paths = ref_arr
                ref_x = ref_grid
            continue
        for m in spec.methods:
            yv = _arr(_path(comp, m.id, path, rs))
            if yv is None:
                continue
            # Intervalles : `est` identique ne suffit pas (low / high / hit diffèrent selon la méthode).
            extra = b"".join(
                np.ascontiguousarray(arr).tobytes()
                for key in ("low", "high", "hit")
                if is_intervals and key in paths and (arr := _path(comp, m.id, paths[key], rs)) is not None
            )
            fingerprint = (slot, np.ascontiguousarray(yv).tobytes() + extra)
            if fingerprint in seen:  # même tableau produit par une autre méthode : dessiné une seule fois
                continue
            seen.add(fingerprint)
            role = roles[m.id]
            xv = _arr(_path(comp, m.id, x_path, rs)) if x_path else None
            if root == "reps" and is_intervals:  # intervalles empilés : `est` porte low / high / hit
                k = min(SHOWN_INTERVALS, yv.shape[0])
                s = Series(
                    id=f"{view.id}.{slot}.{m.id}",
                    slot=slot,
                    method=m.id,
                    role=role,
                    label=labels[m.id],  # type: ignore[arg-type]
                    x=_floats(yv[:k]),
                )
                for comp_slot in _COMPANIONS:
                    arr = _arr(_path(comp, m.id, paths[comp_slot], rs)) if comp_slot in paths else None
                    if arr is not None:
                        setattr(
                            s,
                            comp_slot,
                            [bool(v) for v in arr[:k]] if comp_slot == "hit" else _floats(arr[:k]),
                        )
                result.series.append(s)
                shown, total = k, int(yv.shape[0])
                continue
            if is_distribution:  # une grandeur : x porte les valeurs
                result.series.append(
                    Series(
                        id=f"{view.id}.{slot}.{m.id}",
                        slot=slot,
                        method=m.id,
                        role=role,  # type: ignore[arg-type]
                        label=label_for(slot, m.id),
                        x=_floats(yv),
                    )
                )
            elif paired and slot == "y":
                result.series.append(
                    Series(
                        id=f"{view.id}.xy.gen",
                        slot="xy",
                        role="data",
                        label="Observations",
                        x=_floats(xv) if xv is not None else None,
                        y=_floats(yv),
                    )
                )
            else:
                result.series.append(
                    Series(
                        id=f"{view.id}.{slot}.{m.id}",
                        slot=slot,
                        method=m.id,
                        role=role,  # type: ignore[arg-type]
                        label=label_for(slot, m.id),
                        x=_floats(xv) if xv is not None else None,
                        y=_floats(yv),
                    )
                )
            shown = total = int(yv.shape[0])
            # Référence : même grandeur à l'état sain (une fois par emplacement), pas pour les données
            if root in ("example", "curves") and slot not in ref_done and not (paired and slot == "y"):
                ref_done.add(slot)
                by = _arr(_path(base, m.id, path, rs))
                bx = _arr(_path(base, m.id, x_path, rs)) if x_path else None
                if by is not None:
                    result.series.append(
                        Series(
                            id=f"{view.id}.{slot}.{m.id}.ref",
                            slot=slot,
                            method=m.id,
                            role="reference",
                            label="Référence (état sain)",
                            x=_floats(by if is_distribution else bx)
                            if (is_distribution or bx is not None)
                            else None,
                            y=None if is_distribution else _floats(by),
                        )
                    )
                    if is_distribution:
                        xs.append(by)
                    else:
                        ys.append(by)
                        if bx is not None:
                            xs.append(bx)
            (xs if is_distribution else ys).append(yv)
            if xv is not None and not is_distribution:
                xs.append(xv)

    # Segments du nuage (annexe E) : un segment vertical par observation, de `from` à `to`, lus sur la
    # méthode principale. Série : x, low (= from), high (= to), et le calque éventuel.
    segments = view.bind.get("segments")
    if isinstance(segments, list) and x_path:
        sx = _arr(_path(comp, primary, x_path, rs))
        for i, item in enumerate(segments):
            if not isinstance(item, dict) or sx is None:
                continue
            start = _arr(_path(comp, primary, str(item.get("from", "")), rs))
            end = _arr(_path(comp, primary, str(item.get("to", "")), rs))
            if start is None or end is None:
                continue
            result.series.append(
                Series(
                    id=f"{view.id}.segments-{i}.{primary}",
                    slot="segments",
                    method=primary,
                    role=roles[primary],  # type: ignore[arg-type]
                    label=str(item.get("label") or "Segments"),
                    layer=item.get("layer"),
                    x=_floats(sx),
                    low=_floats(start),
                    high=_floats(end),
                )
            )

    result.shown, result.total = shown, total or shown
    if "paths" in paths:  # bornes sur la Référence : les trajectoires de l'état sain
        reference = ref_paths if ref_paths is not None else (path_arrays[0] if path_arrays else None)
        result.axes = ViewAxes(
            x=[float(np.nanmin(ref_x)), float(np.nanmax(ref_x))] if ref_x is not None else None,
            y=_stable_range(reference.ravel()) if reference is not None else None,
        )
        return result
    if is_intervals:  # bornes sur la Référence : intervalles sains
        ends = [_arr(_path(base, primary, paths[k], rs)) for k in ("low", "high") if k in paths]
        ends = [e[:SHOWN_INTERVALS] for e in ends if e is not None]
        result.axes = ViewAxes(
            x=_stable_range(np.concatenate([e for e in ends if e is not None])) if ends else None
        )
        return result
    ui_x = (view.ui or {}).get("x_range")
    if ui_x:
        xr: list[float] | None = [float(ui_x[0]), float(ui_x[1])]
    elif xs and x_path and x_path.startswith("curves."):  # axe du temps : bornes exactes
        allx = np.concatenate([a.ravel() for a in xs])
        xr = [float(np.nanmin(allx)), float(np.nanmax(allx))]
    else:
        xr = _stable_range(np.concatenate([a.ravel() for a in xs])) if xs else None
    yr = _stable_range(np.concatenate([a.ravel() for a in ys])) if ys else None
    result.axes = ViewAxes(x=xr, y=yr)
    return result


# --- run() --------------------------------------------------------------------------------------------------


def run(spec: ExperimentSpec, state: EngineState | None = None) -> RunResult:
    t0 = time.perf_counter()
    state = state or EngineState()
    rs = resolve_state(spec, state)
    key = spec_hash(spec)
    comp = _compute(spec, rs, key)
    base = _compute(spec, healthy(spec, rs), key)

    # Défis
    ns = _namespaces(spec, rs, comp, base)
    challenges = []
    for ch in spec.challenges:
        try:
            passed = bool(compile_expr(ch.when).evaluate(Env(namespaces=ns)))
        except ExprError:
            passed = False
        challenges.append(ChallengeResult(id=ch.id, passed=passed))

    # Répétitions invalides et avertissements
    invalid: dict[str, float] = {}
    warnings: list[RunWarning] = []
    for mid in comp.results:
        worst = 0.0
        for name in spec.measures:
            a = comp.aggs[name][mid]
            if a.n_total:
                worst = max(worst, 1.0 - a.n_valid / a.n_total)
        invalid[mid] = worst
        if worst > INVALID_WARN:
            label = next(m.label for m in spec.methods if m.id == mid)
            warnings.append(
                RunWarning(
                    code="invalid_repeats",
                    text=f"{label} : {worst * 100:.0f} % des répétitions sont inutilisables (exclues).",
                )
            )

    # Journal du premier tirage (P1, mais peu coûteux : répétition 0 de la méthode principale)
    draw_log = None
    if spec.draw_log:
        primary = next(m.id for m in spec.methods if m.role == "method")
        reps = comp.results[primary].reps
        try:
            draw_log = DrawLog(
                reject=bool(reps[spec.draw_log["reject"].split(".")[1]][0])
                if "reject" in spec.draw_log
                else None,
                pvalue=_clean(reps[spec.draw_log["pvalue"].split(".")[1]][0])
                if "pvalue" in spec.draw_log
                else None,
            )
        except (KeyError, IndexError):
            draw_log = None

    return RunResult(
        state_hash=rs.hash(),
        methods=[MethodInfo(id=m.id, role=m.role, label=m.label, explain=m.explain) for m in spec.methods],
        measures=_measure_results(spec, comp, base),
        equation=_equation(spec, rs),
        challenges=challenges,
        views=[_build_view(spec, v, rs, comp, base) for v in spec.views],
        draw_log=draw_log,
        invalid_rate=invalid,
        warnings=warnings,
        repeat_used=comp.n_repeat,
        compute_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


def namespaces_for(spec: ExperimentSpec, state: EngineState | None = None) -> dict[str, Any]:
    """Espaces de noms `p`, `h`, `m`, `s`, `base` d'un état : pour `verify` (Entraînement) et les tests."""
    rs = resolve_state(spec, state or EngineState())
    key = spec_hash(spec)
    return _namespaces(spec, rs, _compute(spec, rs, key), _compute(spec, healthy(spec, rs), key))


def check_condition(spec: ExperimentSpec, state: EngineState | dict[str, Any], expr: str) -> bool:
    """Lance l'état et évalue une condition `verify` (ou un `when`) dessus."""
    if not isinstance(state, EngineState):
        state = EngineState(**state)
    return bool(compile_expr(expr).evaluate(Env(namespaces=namespaces_for(spec, state))))


__all__ = ["RunError", "check_condition", "namespaces_for", "run", "verdict"]
