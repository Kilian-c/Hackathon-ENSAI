"""Méthode `quadrature` : intégrales sur une grille, comparées aux valeurs exactes et à SciPy."""

import numpy as np
import pytest
from scipy import integrate

from backend.contracts import EngineState
from backend.engine import runner
from backend.engine.loader import load_experiment
from backend.methods.quadrature import quadrature

RNG = np.random.default_rng(0)
N = 2000
X = ((np.arange(N) + 0.5) / N)[None, :]


def _est(f: np.ndarray, kind: str, a: float = 0.0, b: float = 1.0, **kw) -> float:
    return float(quadrature(x=X, f=f, a=a, b=b, kind=kind, rng=np.random.default_rng(1), **kw).reps["est"][0])


@pytest.mark.parametrize("kind", ["rectangles", "trapezes", "simpson"])
def test_smooth_functions_are_integrated_accurately(kind: str) -> None:
    for f, exact in ((X**2, 1 / 3), (np.sin(np.pi * X), 2 / np.pi), (np.exp(X), np.e - 1)):
        assert _est(f, kind) == pytest.approx(exact, abs=1e-6), kind


def test_trapezes_and_simpson_match_scipy_inside_the_grid() -> None:
    f = np.cos(3 * X)
    core = float(integrate.simpson(f[0], x=X[0]))
    cap = f[0, 0] * X[0, 0] + f[0, -1] * (1 - X[0, -1])
    assert _est(f, "simpson") == pytest.approx(core + cap, abs=1e-12)
    assert _est(f, "trapezes") == pytest.approx(float(np.trapezoid(f[0], X[0])) + cap, abs=1e-12)


def test_other_interval_and_error_against_truth() -> None:
    x = (2 + 3 * (np.arange(N) + 0.5) / N)[None, :]  # [2, 5]
    result = quadrature(x=x, f=x**2, a=2.0, b=5.0, kind="rectangles", truth=(125 - 8) / 3, rng=RNG)
    assert result.reps["est"][0] == pytest.approx(39.0, abs=1e-4)
    assert abs(result.reps["error"][0]) < 1e-4
    assert np.isnan(quadrature(x=x, f=x, a=2.0, b=5.0, rng=RNG).reps["error"]).all()  # sans truth


def test_monte_carlo_is_noisy_but_unbiased_and_deterministic() -> None:
    f = X**2
    a = _est(f, "monte_carlo", samples=100)
    assert a == _est(f, "monte_carlo", samples=100)  # même flux, même résultat
    def once(seed: int) -> float:
        rng = np.random.default_rng(seed)
        return float(quadrature(x=X, f=f, a=0, b=1, kind="monte_carlo", samples=200, rng=rng).reps["est"][0])

    estimates = [once(s) for s in range(200)]
    assert np.mean(estimates) == pytest.approx(1 / 3, abs=0.01) and np.std(estimates) > 1e-3


def test_discontinuous_function_is_handled() -> None:
    assert _est((X < 0.3) * 1.0, "rectangles") == pytest.approx(0.3, abs=1e-3)


def test_vectorised_over_repetitions_and_example_is_the_first_repetition() -> None:
    x = np.repeat(X, 5, axis=0)
    f = x * np.arange(1, 6)[:, None]
    result = quadrature(x=x, f=f, a=0, b=1, kind="rectangles", rng=RNG)
    assert result.reps["est"] == pytest.approx(np.arange(1, 6) / 2, abs=1e-6)
    assert result.example["x"].shape == (N,) and result.example["f"] == pytest.approx(f[0])


def test_bad_arguments_are_french_errors() -> None:
    with pytest.raises(ValueError, match="kind doit valoir"):
        quadrature(x=X, f=X, a=0, b=1, kind="gauss", rng=RNG)
    with pytest.raises(ValueError, match="a < b"):
        quadrature(x=X, f=X, a=1, b=0, rng=RNG)
    with pytest.raises(ValueError, match="strictement croissants"):
        quadrature(x=X[:, ::-1], f=X, a=0, b=1, rng=RNG)
    with pytest.raises(ValueError, match="même forme"):
        quadrature(x=X, f=X[:, :10], a=0, b=1, rng=RNG)
    with pytest.raises(ValueError, match="samples"):
        quadrature(x=X, f=X, a=0, b=1, kind="monte_carlo", samples=0, rng=RNG)


YAML = """
schema_version: 1
id: "essai-quadrature"
title: "Essai : quadrature"
discipline: "intégration"
level: "2"
concepts: ["intégrale"]
theorem: { name: "Somme de Riemann", statement: "La somme de Riemann converge vers l'intégrale." }
equation: { tex: '\\int_0^1 f = {{val}}', terms: { val: { ok: '\\int_0^1 f' } } }
params:
  k: { type: number, label: "Rang k", min: 1, max: 200, step: 1, default: 5 }
hypotheses:
  forme:
    type: choice
    healthy_value: "lisse"
    label: "Forme de f"
    category: "forme"
    options:
      lisse: { label: "Lisse", expr: "x" }
      pic:   { label: "Pic étroit", expr: "p.k * (x < 1 / p.k)" }
    statement_tex: 'f \\in C^0'
    why: "a"
    when_broken: "b"
    affects: [val]
counterexamples: [ { id: "pic", label: "Pic", explain: "c", state: { hypotheses: { forme: "pic" } } } ]
generator:
  type: random
  n: 2000
  repeat: 1
  variables:
    x: { expr: "(idx + 0.5) / 2000" }
    f: { expr: "@h.forme" }
methods:
  - id: rect
    role: method
    call: quadrature
    label: "Rectangles"
    args: { x: x, f: f, a: 0, b: 1, kind: "rectangles", truth: 0.5 }
measures:
  ecart:
    agg: "mean(reps.error)"
    label: "Écart"
    decimals: 3
    primary: true
    target: 0
    direction: both
    ok_within: 0.01
    broken_beyond: 0.1
challenges: []
views:
  - { id: courbe, type: curves, title: "f", bind: { t: example.x, series: [ { y: example.f, label: "f" } ] } }
questions: []
"""


def test_curve_gets_its_reference_when_read_from_example() -> None:
    spec = load_experiment(YAML)
    healthy = runner.run(spec, EngineState())
    assert healthy.measures["ecart"].states["rect"] == "ok"
    broken = runner.run(spec, EngineState(hypotheses={"forme": "pic"}, params={"k": 20}))
    view = next(v for v in broken.views if v.id == "courbe")
    assert {s.role for s in view.series} == {"method", "reference"}  # la Référence saine est superposée
    assert broken.measures["ecart"].states["rect"] == "broken"


LOCKED = """  mesurable:
    type: boolean
    healthy_value: true
    label: "f mesurable"
    category: "mesurabilite"
    ok_label: "Mesurable"
    broken_label: "Non mesurable"
    robust_expected: true
    disabled_when: "True"
    disabled_text: "Toujours vraie ici : une fonction non mesurable ne se simule pas."
    statement_tex: 'f^{-1}(B) \\in \\mathcal{A}'
    why: "Sans mesurabilité, l'intégrale n'a pas de sens."
    when_broken: "Elle ne peut pas être cassée numériquement."
    affects: []
"""


def test_a_locked_hypothesis_is_shown_but_changes_no_verdict() -> None:
    """Mesurabilité : `disabled_when` et `robust_expected`, sans effet sur le calcul (plan, étape 2)."""
    spec = load_experiment(YAML.replace("counterexamples:", LOCKED + "counterexamples:", 1))
    hypothesis = spec.hypotheses["mesurable"]
    assert hypothesis.disabled_when == "True" and "ne se simule pas" in (hypothesis.disabled_text or "")
    reference = runner.run(spec, EngineState())
    for value in (True, False):
        result = runner.run(spec, EngineState(hypotheses={"mesurable": value}))
        assert result.measures["ecart"].values == reference.measures["ecart"].values
        assert result.measures["ecart"].states == {"rect": "ok"}
