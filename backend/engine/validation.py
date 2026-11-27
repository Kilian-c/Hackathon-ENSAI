"""Validation d'une expérience importée (`POST /api/validate`) : erreurs par ligne et tests 1, 3, 4, 10.

Les tests de contenu de `tests/test_experiments.py` (section 4.10 du cahier) rejoués sur le YAML reçu.
Un test qui ne peut pas s'exécuter (erreur de calcul) échoue avec le message de l'erreur.
"""

from backend.contracts import EngineState, ValidateIssue, ValidateResponse, ValidateTest
from backend.engine.loader import ExperimentError, load_experiment
from backend.engine.runner import RunError, run
from backend.engine.schema import ExperimentSpec
from backend.engine.state import StateError

_ERRORS = (RunError, StateError)


def _broken_values(hyp) -> list:
    if hyp.type == "choice":
        return [k for k in hyp.options if k != hyp.healthy_value]
    if hyp.type == "boolean":
        return [not hyp.healthy_value]
    return [hyp.range[1]]


def _primary_state(result, method: str) -> str | None:
    for measure in result.measures.values():
        if measure.primary:
            return measure.states.get(method)
    return None


def _main_method(spec: ExperimentSpec) -> str:
    return next(m.id for m in spec.methods if m.role == "method")


def _test_1(spec: ExperimentSpec) -> ValidateTest:
    name = "État sain : la mesure principale est fiable"
    state = _primary_state(run(spec, EngineState()), _main_method(spec))
    ok = state == "ok"
    detail = None if ok else f"Verdict à l'état sain : {state}."
    return ValidateTest(id=1, name=name, passed=ok, detail=detail)


def _test_3(spec: ExperimentSpec) -> ValidateTest:
    name = "Chaque méthode répare les hypothèses annoncées"
    failures = []
    for method in spec.methods:
        for hid in method.repairs or []:
            for value in _broken_values(spec.hypotheses[hid]):
                result = run(spec, EngineState(hypotheses={hid: value}))
                verdict = _primary_state(result, method.id)
                if verdict not in ("ok", "warning"):
                    failures.append(f"{method.id} ne répare pas {hid}={value} (verdict {verdict})")
    return ValidateTest(id=3, name=name, passed=not failures, detail="; ".join(failures) or None)


def _test_4(spec: ExperimentSpec) -> ValidateTest:
    name = "Chaque contre-exemple rompt une mesure"
    failures = []
    main = _main_method(spec)
    for ce in spec.counterexamples:
        if ce.expect == "same_summary":
            continue  # vérifié sur la pente et le R², propre à la régression : non rejoué ici
        result = run(spec, EngineState(**ce.state.model_dump()))
        if not any(m.states.get(main) == "broken" for m in result.measures.values()):
            failures.append(f"{ce.id} ne rompt aucune mesure")
    return ValidateTest(id=4, name=name, passed=not failures, detail="; ".join(failures) or None)


def _test_10(spec: ExperimentSpec) -> ValidateTest:
    name = "Hypothèses et méthodes sont documentées"
    hyps = spec.hypotheses.items()
    missing = [f"{hid} : why" for hid, h in hyps if not (h.why or "").strip()]
    missing += [f"{hid} : when_broken" for hid, h in hyps if not (h.when_broken or "").strip()]
    others = [m for m in spec.methods if m.role != "method"]
    missing += [f"{m.id} : explain" for m in others if not (m.explain or "").strip()]
    return ValidateTest(id=10, name=name, passed=not missing, detail="; ".join(missing) or None)


def validate(raw_content: str) -> ValidateResponse:
    try:
        spec = load_experiment(raw_content)
    except ExperimentError as exc:
        errors = [ValidateIssue(line=i.line, path=i.path, message=i.message) for i in exc.issues]
        return ValidateResponse(ok=False, errors=errors)
    tests = []
    for test in (_test_1, _test_3, _test_4, _test_10):
        try:
            tests.append(test(spec))
        except _ERRORS as exc:
            number = int(test.__name__.removeprefix("_test_"))
            tests.append(ValidateTest(id=number, name=f"Test {number}", passed=False, detail=str(exc)))
    return ValidateResponse(ok=all(t.passed for t in tests), tests=tests)
