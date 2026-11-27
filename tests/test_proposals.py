"""Seuils proposés par `/api/validate` : recopiés tels quels, ils ne doivent jamais casser l'état sain
(régression trouvée par R4 : `seuil_roc`, `maximum_uniformes` et `carres_residus` sortaient de Fiable)."""

import re
from pathlib import Path

import pytest

from backend.contracts import EngineState
from backend.engine import runner
from backend.engine.loader import load_experiment
from backend.engine.validate import validate

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
FILES = sorted(EXPERIMENTS_DIR.glob("*.yaml"))
PATTERN = re.compile(r"Seuils proposés : ok_within = ([\d.e-]+)(?: ; broken_beyond = ([\d.e-]+))?")


def _proposals(raw: str) -> dict[str, tuple[float, float | None]]:
    out = {}
    for warning in validate(raw).warnings:
        match = PATTERN.match(warning.message)
        if match:
            out[warning.path.removeprefix("measures.")] = (
                float(match[1]),
                float(match[2]) if match[2] else None,
            )
    return out


@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_proposed_thresholds_keep_the_healthy_state_reliable(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    spec = load_experiment(raw)
    proposals = _proposals(raw)
    measures = {
        mid: m.model_copy(
            update={
                "ok_within": proposals[mid][0],
                "broken_beyond": proposals[mid][1] if proposals[mid][1] is not None else m.broken_beyond,
            }
        )
        if mid in proposals
        else m
        for mid, m in spec.measures.items()
    }
    main = next(m.id for m in spec.methods if m.role == "method")
    result = runner.run(spec.model_copy(update={"measures": measures}), EngineState())
    for mid in proposals:
        verdict = result.measures[mid].states[main]
        assert verdict == "ok", f"{path.stem}.{mid} : état sain {verdict}."
        ok, broken = proposals[mid]
        assert broken is None or broken >= 1.5 * ok, f"{path.stem}.{mid} : zone Fragile quasi vide."


def test_the_reason_is_given_when_no_broken_threshold_is_proposed() -> None:
    raw = (EXPERIMENTS_DIR / "regression_lineaire.yaml").read_text(encoding="utf-8")
    messages = [w.message for w in validate(raw).warnings if w.path == "measures.bias"]
    assert messages and "pas de broken_beyond proposé" in messages[0]
