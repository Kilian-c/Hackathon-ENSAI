"""Tests de conformité du contrat de méthodes, des lois et des agrégateurs (R2)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.special import ndtri
from scipy.stats import spearmanr

from backend.engine import method_contract
from backend.engine.aggregators import (
    AGGREGATORS,
    agg_bias,
    agg_first,
    agg_mean,
    agg_median,
    agg_quantile,
    agg_rate,
    agg_rmse,
    agg_sd,
    agg_summary,
    agg_var,
    get_aggregator,
)
from backend.engine.laws import get_law, list_laws, sample_law
from backend.engine.method_contract import (
    MethodResult,
    MethodSpec,
    get_method,
    list_methods,
    register_method,
    validate_method_result,
)

# ---------------------------------------------------------------------------
# 1. Contrat des méthodes (method_contract.py)
# ---------------------------------------------------------------------------


def test_register_and_validate_method(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enregistrement, provides_path et validation sur une méthode factice."""
    monkeypatch.setattr(method_contract, "_REGISTRY", {})

    @register_method(
        "dummy_method",
        provides={
            "reps": ["est", "hit"],
            "example": ["x", "resid"],
            "summary": ["score"],
        },
        cost="repeat * n",
    )
    def dummy_method(*, repeat: int, n: int) -> MethodResult:
        return MethodResult(
            reps={"est": np.zeros(repeat), "hit": np.ones(repeat, dtype=bool)},
            example={"x": np.zeros(n), "resid": np.zeros(n)},
            summary={"score": 0.42},
        )

    spec = get_method("dummy_method")
    assert spec.cost == "repeat * n"
    assert spec.provides_path("reps.hit")
    assert spec.provides_path("example.resid")
    assert spec.provides_path("summary.score")
    assert not spec.provides_path("reps.inconnue")
    assert not spec.provides_path("invalid_path")

    res = dummy_method(repeat=10, n=5)
    validate_method_result(spec, res, repeat=10, n=5)

    # Les NaN dans reps sont autorisés (répétitions invalides gérées par le moteur)
    res.reps["est"][0] = np.nan
    validate_method_result(spec, res, repeat=10, n=5)


def test_register_method_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse les blocs inconnus, doublons de noms ou de clés."""
    monkeypatch.setattr(method_contract, "_REGISTRY", {})

    with pytest.raises(ValueError, match="blocs inconnus"):
        register_method("bad_block", provides={"foo": ["a"]}, cost="1")

    with pytest.raises(ValueError, match="en double"):
        register_method("dup_key", provides={"reps": ["a", "a"]}, cost="1")

    @register_method("m1", provides={"summary": ["v"]}, cost="1")
    def _m1() -> MethodResult:
        return MethodResult(summary={"v": 1.0})

    with pytest.raises(ValueError, match="déjà enregistrée"):

        @register_method("m1", provides={"summary": ["v"]}, cost="1")
        def _m1_bis() -> MethodResult:
            return MethodResult(summary={"v": 2.0})


def test_validate_method_result_catches_violations() -> None:
    """Détecte clé manquante, clé en trop, mauvaise forme et mauvais type."""
    spec = MethodSpec(
        name="check",
        fn=lambda: MethodResult(),
        provides={"reps": ("a",), "example": ("x",), "summary": ("s",)},
        cost="repeat * n",
    )

    # Clé manquante dans reps
    bad_missing = MethodResult(
        reps={},
        example={"x": np.zeros(5)},
        summary={"s": 1.0},
    )
    with pytest.raises(ValueError, match="manquantes"):
        validate_method_result(spec, bad_missing, repeat=4, n=5)

    # Clé inattendue dans curves
    bad_extra = MethodResult(
        reps={"a": np.zeros(4)},
        example={"x": np.zeros(5)},
        curves={"t": np.zeros(3)},
        summary={"s": 1.0},
    )
    with pytest.raises(ValueError, match="inattendues"):
        validate_method_result(spec, bad_extra, repeat=4, n=5)

    # Mauvaise forme dans reps
    bad_shape = MethodResult(
        reps={"a": np.zeros(3)},
        example={"x": np.zeros(5)},
        summary={"s": 1.0},
    )
    with pytest.raises(ValueError, match="attendu"):
        validate_method_result(spec, bad_shape, repeat=4, n=5)

    # Booléen interdit dans summary
    bad_bool = MethodResult(
        reps={"a": np.zeros(4)},
        example={"x": np.zeros(5)},
        summary={"s": True},  # type: ignore[dict-item]
    )
    with pytest.raises(TypeError, match="nombre réel"):
        validate_method_result(spec, bad_bool, repeat=4, n=5)


# ---------------------------------------------------------------------------
# 2. Registre des lois (laws.py)
# ---------------------------------------------------------------------------


def test_laws_registry_and_metadata() -> None:
    """Vérifie la présence des 6 lois et leurs métadonnées (espérance, variance)."""
    laws = list_laws()
    expected = {"normal", "uniform", "exponential", "student_2", "cauchy", "bimodal"}
    assert set(laws.keys()) == expected

    assert get_law("normal").has_mean and get_law("normal").has_variance
    assert get_law("uniform").has_mean and get_law("uniform").has_variance
    assert get_law("exponential").has_mean and get_law("exponential").has_variance
    assert get_law("bimodal").has_mean and get_law("bimodal").has_variance
    assert get_law("student_2").has_mean and not get_law("student_2").has_variance
    assert not get_law("cauchy").has_mean and not get_law("cauchy").has_variance

    with pytest.raises(KeyError):
        get_law("loi_inexistante")


@pytest.mark.parametrize(
    "law_name",
    ["normal", "uniform", "exponential", "student_2", "cauchy", "bimodal"],
)
def test_laws_finite_deterministic_and_scaled(law_name: str) -> None:
    """Tirages finis, déterministes et correctement mis à l'échelle."""
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    x1 = sample_law(law_name, rng1, (100, 1000))
    x2 = sample_law(law_name, rng2, (100, 1000))

    assert x1.shape == (100, 1000)
    assert np.all(np.isfinite(x1))
    assert np.array_equal(x1, x2)

    spec = get_law(law_name)
    if spec.has_variance:
        assert abs(float(np.mean(x1))) < 0.03
        assert abs(float(np.var(x1)) - 1.0) < 0.05
    else:
        norm_iqr = float(2.0 * ndtri(0.75))
        q25, q50, q75 = np.quantile(x1, [0.25, 0.50, 0.75])
        assert abs(float(q50)) < 0.03
        assert abs(float(q75 - q25) - norm_iqr) < 0.05


def test_laws_common_uniforms_monotone() -> None:
    """Les lois à 1 uniforme partagent exactement les mêmes rangs (uniformes communes)."""
    ref = sample_law("normal", np.random.default_rng(123), (500,))
    for other in ("uniform", "exponential", "student_2", "cauchy"):
        arr = sample_law(other, np.random.default_rng(123), (500,))
        corr = spearmanr(ref, arr).statistic
        assert corr > 0.999999


# ---------------------------------------------------------------------------
# 3. Agrégateurs (aggregators.py)
# ---------------------------------------------------------------------------


def test_aggregators_registry() -> None:
    """Vérifie que les 10 agrégateurs de la Table 8 sont enregistrés, plus `kurtosis` (catalogue)."""
    expected = {
        "kurtosis",
        "rate",
        "mean",
        "bias",
        "rmse",
        "sd",
        "var",
        "median",
        "quantile",
        "first",
        "summary",
    }
    assert set(AGGREGATORS.keys()) == expected
    with pytest.raises(KeyError):
        get_aggregator("inexistant")


def test_kurtosis_is_zero_for_normal_and_flat_for_uniform() -> None:
    rng = np.random.default_rng(0)
    assert abs(AGGREGATORS["kurtosis"](rng.standard_normal(200_000)).value) < 0.05
    assert abs(AGGREGATORS["kurtosis"](rng.uniform(size=200_000)).value + 1.2) < 0.02
    assert AGGREGATORS["kurtosis"]([1.0, 1.0, 1.0, 1.0]).mc_se is None


def test_aggregators_values_and_mc_se() -> None:
    """Vérifie les calculs et erreurs Monte Carlo avec exclusion des NaN."""
    # rate : 3 vrais sur 4 valides (1 NaN exclu)
    r = agg_rate(np.array([1.0, 0.0, 1.0, 1.0, np.nan]))
    assert r.n_valid == 4 and r.n_total == 5
    assert math.isclose(r.value, 0.75)
    assert r.mc_se is not None
    assert math.isclose(r.mc_se, math.sqrt(0.75 * 0.25 / 4))

    # mean et bias
    vals = np.array([2.0, 4.0, 6.0, np.nan, np.inf])
    m = agg_mean(vals)
    assert m.n_valid == 3 and m.n_total == 5
    assert math.isclose(m.value, 4.0)
    assert m.mc_se is not None
    assert math.isclose(m.mc_se, 2.0 / math.sqrt(3.0))

    b = agg_bias(vals, truth=1.5)
    assert math.isclose(b.value, 2.5)
    assert b.mc_se == m.mc_se

    # rmse, sd, var, median, quantile, first
    assert math.isclose(agg_rmse(np.array([1.0, 3.0]), truth=2.0).value, 1.0)
    assert math.isclose(agg_sd(vals).value, 2.0)
    assert math.isclose(agg_var(vals).value, 4.0)
    assert math.isclose(agg_median(vals).value, 4.0)
    assert math.isclose(agg_quantile(np.array([0.0, 10.0]), 0.25).value, 2.5)
    assert math.isclose(agg_first(np.array([7.5, 1.0, 2.0])).value, 7.5)

    # summary (les deux formes d'appel)
    assert math.isclose(agg_summary("err", {"err": 0.12}).value, 0.12)
    assert math.isclose(agg_summary(0.12).value, 0.12)


def test_aggregators_edge_cases() -> None:
    """Tableaux entièrement NaN, taille 1 et quantile hors bornes."""
    all_nan = np.array([np.nan, np.nan])
    for fn in (agg_rate, agg_mean, agg_sd, agg_var, agg_median, agg_first):
        res = fn(all_nan)
        assert math.isnan(res.value)
        assert res.mc_se is None
        assert res.n_valid == 0

    one_val = np.array([3.0])
    assert agg_mean(one_val).mc_se is None
    assert math.isnan(agg_sd(one_val).value)

    with pytest.raises(ValueError):
        agg_quantile(np.array([1.0, 2.0]), 1.5)


# ---------------------------------------------------------------------------
# 4. Conformité de toutes les méthodes enregistrées dans backend/methods/
# ---------------------------------------------------------------------------

# À compléter au fur et à mesure que tu codes ols_ci, one_sample_test, integrate.
# Chaque entrée associe le nom de la méthode à (kwargs, repeat_attendu, n_attendu).
_X0 = np.random.default_rng(0).standard_normal((20, 15))
_SAMPLE_CALLS: dict[str, tuple[dict, int | None, int | None]] = {
    "one_sample_test": (
        {"x0": _X0, "x1": _X0 + 0.5, "alpha": 0.05, "kind": "student"},
        20,
        15,
    ),
    "clt_mean": (
        {"x": _X0, "sigma": 1.0, "rho": 0.0, "kind": "independance"},
        20,
        15,
    ),
    "ols_two": (
        {"x1": _X0, "x2": _X0[::-1], "y": _X0 + _X0[::-1] + _X0[:, ::-1], "signal": _X0 + _X0[::-1],
         "truth": 1.0, "alpha": 0.05, "kind": "complet"},
        20,
        15,
    ),
    "pairwise_tests": (
        {"y": _X0, "groups": 4, "alpha": 0.05, "kind": "tukey"},
        20,
        15,
    ),
    "ols_ci": (
        {"x": _X0, "y": 1.0 + 1.5 * _X0 + _X0[::-1], "truth": 1.5, "alpha": 0.05, "se_type": "HC3"},
        20,
        15,
    ),
    "statistic": (
        {"x": _X0, "kind": "sum", "continuity": True, "rng": np.random.default_rng(0)},
        20,
        15,
    ),
    "classifier": (
        {"score": _X0, "label": _X0[::-1] > 0, "threshold": 0.0, "kind": "seuil"},
        20,
        15,
    ),
    "regressor": (
        {"x": _X0, "y": 1.0 + 1.5 * _X0 + _X0[::-1], "kind": "manuelle", "slope": 1.0},
        20,
        15,
    ),
    "eigen": (
        {
            "a": np.random.default_rng(4).standard_normal((20, 9)),
            "d": 3,
            "spike": 3.0,
            "kind": "power",
            "iters": 10,
            "rng": np.random.default_rng(0),
        },
        20,
        None,
    ),
    "linsolve": (
        {
            "a": np.random.default_rng(2).standard_normal((20, 9)),
            "d": 3,
            "shift": 3.0,
            "kind": "gauss_pivot",
            "iters": 10,
            "rng": np.random.default_rng(0),
        },
        20,
        None,
    ),
    "spectrum": (
        {"x": np.random.default_rng(1).standard_normal((20, 9)), "d": 3, "rng": np.random.default_rng(0)},
        20,
        None,
    ),
    "formula_estimate": (
        {"est": _X0.mean(axis=1), "truth": 0.0, "rng": np.random.default_rng(0)},
        20,
        None,
    ),
    "formula_test": (
        {"stat": _X0.mean(axis=1), "critical": 1.96, "rng": np.random.default_rng(0)},
        20,
        None,
    ),
    "formula_interval": (
        {
            "est": _X0.mean(axis=1),
            "low": _X0.mean(axis=1) - 1.0,
            "high": _X0.mean(axis=1) + 1.0,
            "truth": 0.0,
            "rng": np.random.default_rng(0),
        },
        20,
        None,
    ),
    "integrate": (
        {
            "system": {
                "rhs": lambda y: np.array([y[1], -9.81 * np.sin(y[0])]),
                "y0": [1.2, 0.0],
                "t_end": 2.0,
            },
            "dt": 0.01,
            "scheme": "rk4",
        },
        None,
        None,
    ),
}


def test_all_registered_methods_respect_contract() -> None:
    """Chaque méthode enregistrée dans le registre doit passer validate_method_result."""
    registered = list_methods()
    for name, spec in registered.items():
        assert name in _SAMPLE_CALLS, (
            f"Méthode '{name}' enregistrée mais absente de _SAMPLE_CALLS "
            "dans tests/test_method_contract.py."
        )
        kwargs, expected_repeat, expected_n = _SAMPLE_CALLS[name]
        result = spec.fn(**kwargs)
        validate_method_result(spec, result, repeat=expected_repeat, n=expected_n)
