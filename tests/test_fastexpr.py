"""`compile_fast` donne les mêmes valeurs que l'évaluateur général, et refuse ce qu'il ne gère pas."""

import numpy as np
import pytest

from backend.engine.expr import Env, ExprError, compile_expr
from backend.engine.fastexpr import compile_fast

NS = {"p": {"g": 9.81, "k": 2.0}, "h": {"pas": 0.5}}
INDEX = {"theta": 0, "omega": 1}


@pytest.mark.parametrize(
    "source",
    [
        "omega",
        "-p.g * sin(theta)",
        "-p.g / p.k * sin(theta) - 0.1 * omega",
        "theta ** 2 + h.pas",
        "10 ** (-3.5 + 2.5 * h.pas)",
        "sqrt(abs(theta)) * exp(-omega) + pi",
        "p.k",
    ],
)
def test_same_value_as_general_evaluator(source: str) -> None:
    fast = compile_fast(source, NS, INDEX)
    assert fast is not None
    for y in (np.array([1.2, 0.0]), np.array([-0.4, 2.5])):
        env = Env(variables={"theta": y[0], "omega": y[1]}, namespaces=NS)
        assert fast(y) == pytest.approx(compile_expr(source).evaluate(env), rel=1e-12)


def test_unsupported_nodes_fall_back() -> None:
    assert compile_fast("theta if omega > 0 else -theta", NS, INDEX) is None
    assert compile_fast("inconnue(theta)", NS, INDEX) is None


def test_exponent_limit_and_unknown_name() -> None:
    with pytest.raises(ExprError):
        compile_fast("theta ** p.g * 0 + 2 ** 500", NS, INDEX)
    with pytest.raises(ExprError):
        compile_fast("p.absent * theta", NS, INDEX)
