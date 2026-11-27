"""Validation d'un YAML importé (R1, P1) : `POST /api/validate` (cahier, annexe C).

Schéma d'abord (erreurs par ligne, celles du chargeur), puis, seulement si le schéma est valide, les
tests P0 de la section 4.10 lancés sur le YAML reçu : 1, 3, 4 et 10, avec 200 répétitions au plus
pour répondre en quelques secondes. Même logique que `tests/test_experiments.py`, sans pytest.
"""

from __future__ import annotations

from typing import Any

import yaml

from backend.contracts import EngineState, RunResult, ValidateIssue, ValidateResponse, ValidateTest
from backend.engine import runner
from backend.engine.loader import ExperimentError, _line, load_experiment
from backend.engine.schema import ExperimentSpec, RandomGenerator
from backend.engine.sweep import _gap as sweep_gap

VALIDATE_REPEAT = 200

TEST_NAMES = {
    1: "Le théorème tient à l'état sain",
    3: "Chaque correction répare ce qu'elle annonce",
    4: "Les contre-exemples font ce qu'ils annoncent",
    10: "Les explications sont complètes",
}

_VERDICT_WORDS = {"ok": "Fiable", "warning": "Fragile", "broken": "Rompu"}


def _fewer_repeats(spec: ExperimentSpec) -> ExperimentSpec:
    gen = spec.generator
    if isinstance(gen, RandomGenerator) and gen.repeat > VALIDATE_REPEAT:
        return spec.model_copy(update={"generator": gen.model_copy(update={"repeat": VALIDATE_REPEAT})})
    return spec


def _primary(spec: ExperimentSpec) -> tuple[str, str]:
    method = next(m.id for m in spec.methods if m.role == "method")
    measure = next(k for k, m in spec.measures.items() if m.primary)
    return method, measure


def _fmt(spec: ExperimentSpec, measure_id: str, value: float | None) -> str:
    if value is None:
        return "valeur indisponible"
    m = spec.measures[measure_id]
    text = f"{value * m.scale:.{m.decimals}f}".replace(".", ",")
    return f"{m.label} {text}{(' ' + m.unit) if m.unit else ''}"


def _broken_values(hyp) -> list[Any]:
    if hyp.type == "choice":
        return [k for k in hyp.options if k != hyp.healthy_value]
    if hyp.type == "boolean":
        return [not hyp.healthy_value]
    return [hyp.range[1]]


def _run(spec: ExperimentSpec, state: dict[str, Any] | None = None) -> RunResult:
    return runner.run(spec, EngineState(**(state or {})))


def _test_1(spec: ExperimentSpec) -> tuple[bool, str | None, RunResult]:
    method, measure = _primary(spec)
    res = _run(spec)
    m = res.measures[measure]
    st = m.states.get(method)
    if st == "ok":
        return True, None, res
    word = _VERDICT_WORDS.get(st or "", "sans verdict")
    value = _fmt(spec, measure, m.values.get(method))
    return False, f"État sain : la méthode principale est {word} ({value}).", res


def _test_3(spec: ExperimentSpec) -> tuple[bool, str | None]:
    _, measure = _primary(spec)
    failures = []
    for m in spec.methods:
        for hid in m.repairs:
            for v in _broken_values(spec.hypotheses[hid]):
                res = _run(spec, {"hypotheses": {hid: v}})
                mr = res.measures[measure]
                st = mr.states.get(m.id)
                if st not in ("ok", "warning"):
                    word = _VERDICT_WORDS.get(st or "", "sans verdict")
                    value = _fmt(spec, measure, mr.values.get(m.id))
                    failures.append(f"{hid} = {v} : {m.label} reste {word} ({value}).")
    return (not failures), (" ".join(failures[:3]) or None)


def _test_4(spec: ExperimentSpec) -> tuple[bool, str | None]:
    method, _ = _primary(spec)
    failures = []
    for ce in spec.counterexamples:
        if ce.expect == "same_summary":
            # TODO(passation) : pente et R² identiques, vérifiés seulement par tests/test_experiments.py
            continue
        res = _run(spec, ce.state.model_dump())
        if not any(mr.states.get(method) == "broken" for mr in res.measures.values()):
            failures.append(f"Le contre-exemple « {ce.label} » ne rompt aucune mesure.")
    return (not failures), (" ".join(failures[:3]) or None)


def _test_10(spec: ExperimentSpec) -> tuple[bool, str | None]:
    hyps = spec.hypotheses.values()
    missing = [f"l'hypothèse « {h.label} » n'a pas de why" for h in hyps if not h.why.strip()]
    missing += [f"l'hypothèse « {h.label} » n'a pas de when_broken" for h in spec.hypotheses.values()
                if not h.when_broken.strip()]
    missing += [f"la méthode « {m.label} » n'a pas d'explain" for m in spec.methods
                if m.role != "method" and not (m.explain or "").strip()]
    if not missing:
        return True, None
    return False, "Il manque : " + " ; ".join(missing[:4]) + "."


def _warnings(
    spec: ExperimentSpec, healthy: RunResult, root: yaml.Node | None, se_factor: float
) -> list[ValidateIssue]:
    def line(*loc: Any) -> int | None:
        return _line(root, loc) if root is not None else None

    out: list[ValidateIssue] = []
    method, _ = _primary(spec)
    for mid, mr in healthy.measures.items():
        se = mr.mc_se.get(method)
        se = se * se_factor if se is not None else None  # erreur au `repeat` du fichier, pas à 200
        if mr.ok_within is not None and se is not None and mr.ok_within < 2 * se:
            out.append(ValidateIssue(
                line=line("measures", mid, "ok_within"),
                path=f"measures.{mid}.ok_within",
                message="La tolérance est inférieure à deux erreurs Monte Carlo : le verdict sera instable.",
            ))
    if len(spec.questions) < 3:
        out.append(ValidateIssue(
            line=line("questions"),
            path="questions",
            message=f"{len(spec.questions)} question(s) : il en faut 3 pour l'Entraînement.",
        ))
    return out


def _round2(value: float) -> float:
    """Deux chiffres significatifs : un seuil lisible dans un YAML."""
    return float(f"{value:.2g}")


def _gap(value: float | None, target: float | None, direction: str) -> float | None:
    if value is None or target is None:
        return None
    return sweep_gap(value, target, direction)


def _proposals(
    spec: ExperimentSpec, healthy: RunResult, root: yaml.Node | None, se_factor: float
) -> list[ValidateIssue]:
    """Seuils proposés d'après la simulation, un avertissement par mesure à verdict.

    Format stable (lu par l'interface) : le chemin est `measures.<id>` et le message commence par
    « Seuils proposés : ok_within = <x> ; broken_beyond = <y> » (la seconde partie peut manquer).
    - `ok_within` : 3 erreurs Monte Carlo de la méthode principale à l'état sain, au `repeat` du fichier.
    - `broken_beyond` : moyenne géométrique entre `ok_within` et le plus petit écart des contre-exemples ;
      sans contre-exemple, des hypothèses cassées au maximum qui ne sont pas `robust_expected`.
    """
    method, _ = _primary(spec)
    perturbed = [_run(spec, ce.state.model_dump()) for ce in spec.counterexamples if ce.expect is None]
    if not perturbed:
        for hid, hyp in spec.hypotheses.items():
            for v in _broken_values(hyp):
                robust = hyp.robust_expected or (
                    hyp.type == "choice" and hyp.options[v].robust_expected
                )
                if not robust:
                    perturbed.append(_run(spec, {"hypotheses": {hid: v}}))
    out: list[ValidateIssue] = []
    for mid, mr in healthy.measures.items():
        se = mr.mc_se.get(method)
        if mr.direction is None or se is None or se <= 1e-6 or mr.target is None:
            continue  # pas de bruit mesurable (mesure déterministe) : rien à proposer
        ok = _round2(3 * se * se_factor)
        gaps = []
        for res in perturbed:
            pm = res.measures[mid]
            target = pm.baseline.get(method) if pm.target == "base" else pm.target
            g = _gap(pm.values.get(method), target, pm.direction or mr.direction)
            if g is not None and g > ok:
                gaps.append(g)
        text = f"Seuils proposés : ok_within = {ok:g}"
        if gaps:
            text += f" ; broken_beyond = {_round2((ok * min(gaps)) ** 0.5):g}"
        else:
            text += " (aucune perturbation du fichier ne la dépasse : pas de broken_beyond proposé)"
        text += f" (fichier : ok_within = {mr.ok_within:g} ; broken_beyond = {mr.broken_beyond:g})."
        out.append(ValidateIssue(
            line=_line(root, ("measures", mid)) if root is not None else None,
            path=f"measures.{mid}",
            message=text,
        ))
    return out


def validate(raw: str) -> ValidateResponse:
    try:
        spec = load_experiment(raw)
    except ExperimentError as exc:
        errors = [ValidateIssue(line=i.line, path=i.path, message=i.message) for i in exc.issues]
        return ValidateResponse(ok=False, errors=errors)

    try:
        root = yaml.compose(raw, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        root = None
    fast = _fewer_repeats(spec)
    tests: list[ValidateTest] = []
    errors: list[ValidateIssue] = []
    healthy: RunResult | None = None

    def record(tid: int, fn) -> None:
        nonlocal healthy
        try:
            out = fn()
        except Exception as exc:  # noqa: BLE001 : YAML reçu de l'extérieur, toute erreur est rapportée
            tests.append(ValidateTest(id=tid, name=TEST_NAMES[tid], passed=False,
                                      detail=f"Le calcul a échoué : {exc}"))
            return
        if tid == 1:
            passed, detail, healthy = out
        else:
            passed, detail = out
        tests.append(ValidateTest(id=tid, name=TEST_NAMES[tid], passed=passed, detail=detail))

    record(1, lambda: _test_1(fast))
    if healthy is None:
        # L'état sain ne se calcule pas : les autres tests échoueraient pour la même raison.
        errors.append(ValidateIssue(path="", message=tests[0].detail or "Le calcul a échoué."))
        return ValidateResponse(ok=False, errors=errors, tests=tests)
    record(3, lambda: _test_3(fast))
    record(4, lambda: _test_4(fast))
    record(10, lambda: _test_10(spec))
    gen_full, gen_fast = spec.generator, fast.generator
    se_factor = 1.0
    if isinstance(gen_full, RandomGenerator) and isinstance(gen_fast, RandomGenerator):
        se_factor = (gen_fast.repeat / gen_full.repeat) ** 0.5
    warnings = _warnings(fast, healthy, root, se_factor)
    try:
        warnings += _proposals(fast, healthy, root, se_factor)
    except Exception:  # noqa: BLE001 : les propositions sont facultatives, jamais bloquantes
        pass
    return ValidateResponse(ok=all(t.passed for t in tests), errors=errors, warnings=warnings, tests=tests)
