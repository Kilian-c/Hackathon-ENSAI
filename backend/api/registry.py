"""Registre des expériences officielles : tous les YAML de `experiments/`, chargés une fois."""

from functools import lru_cache
from pathlib import Path

from backend.engine.loader import ExperimentError, load_experiment
from backend.engine.schema import ExperimentSpec

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "experiments"
_RAW_CACHE_SIZE = 32


@lru_cache(maxsize=1)
def official() -> dict[str, ExperimentSpec]:
    """id -> expérience validée. Un YAML officiel invalide fait échouer le démarrage (avec la ligne)."""
    specs: dict[str, ExperimentSpec] = {}
    for path in sorted(EXPERIMENTS_DIR.glob("*.yaml")):
        try:
            spec = load_experiment(path.read_text(encoding="utf-8"))
        except ExperimentError as exc:
            raise RuntimeError(f"{path.name} : {exc}") from exc
        specs[spec.id] = spec
    return specs


@lru_cache(maxsize=_RAW_CACHE_SIZE)
def from_raw(content: str) -> ExperimentSpec:
    """Expérience importée (YAML brut) : validée une fois par contenu. `ExperimentError` si invalide."""
    return load_experiment(content)
