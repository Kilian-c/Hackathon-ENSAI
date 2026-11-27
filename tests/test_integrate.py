"""Tests de la méthode integrate (R2), pendule simple de pendule_euler.yaml."""

from __future__ import annotations

import time

import numpy as np
import pytest

import backend.methods.integrate  # noqa: F401  (enregistre la méthode)
from backend.methods.integrate import integrate


def _rhs(y: np.ndarray) -> np.ndarray:
    return np.array([y[1], -9.81 * np.sin(y[0])])


def _run(h: float, scheme: str, theta0: float = 1.2, t_end: float = 5.0):
    dt = 10 ** (-3.5 + 2.5 * h)
    system = {"rhs": _rhs, "y0": [theta0, 0.0], "t_end": t_end}
    return integrate(system=system, dt=dt, scheme=scheme).summary


def test_reference_figures() -> None:
    """Chiffres du cahier : theta0 = 1,2 rad, 5 s, dt = 10 ** (-3.5 + 2.5 h)."""
    assert _run(0.0, "euler")["max_rel_error"] == pytest.approx(0.012, abs=0.004)
    assert _run(0.6, "euler")["max_rel_error"] == pytest.approx(0.45, abs=0.03)


def test_rk4_is_exact_everywhere() -> None:
    for h in (0.0, 0.5, 1.0):
        s = _run(h, "rk4")
        assert s["max_rel_error"] < 0.01


def test_error_grows_with_step() -> None:
    errs = [_run(h, "euler")["max_rel_error"] for h in (0.0, 0.3, 0.6, 0.9)]
    assert errs == sorted(errs)


def test_curves_and_attribute_system() -> None:
    class Sys:
        rhs = staticmethod(_rhs)
        y0 = [1.2, 0.0]
        t_end = 3.0

    res = integrate(system=Sys(), dt=0.01, scheme="euler")
    assert res.curves["t"].shape == (400,) == res.curves["theta"].shape
    assert res.curves["theta"][0] == pytest.approx(1.2)


def test_invalid_args() -> None:
    system = {"rhs": _rhs, "y0": [1.2, 0.0], "t_end": 1.0}
    with pytest.raises(ValueError):
        integrate(system=system, dt=0.01, scheme="autre")
    with pytest.raises(ValueError):
        integrate(system=system, dt=0.0, scheme="euler")


def test_deterministic_and_fast() -> None:
    t0 = time.perf_counter()
    a = _run(0.0, "euler")
    b = _run(0.0, "rk4")
    assert time.perf_counter() - t0 < 1.5
    assert a == _run(0.0, "euler") and b == _run(0.0, "rk4")
