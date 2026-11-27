"""Registre des expériences officielles : tous les YAML de `experiments/`, chargés une fois."""

from functools import lru_cache
from pathlib import Path

from backend.engine.loader import ExperimentError, content_hash, load_experiment
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


@lru_cache(maxsize=1)
def content_digest() -> str:
    """Empreinte du contenu des YAML officiels : elle entre dans la graine des séries d'Entraînement."""
    texts = [path.read_text(encoding="utf-8") for path in sorted(EXPERIMENTS_DIR.glob("*.yaml"))]
    return content_hash("".join(texts))


@lru_cache(maxsize=_RAW_CACHE_SIZE)
def from_raw(content: str) -> ExperimentSpec:
    """Expérience importée (YAML brut) : validée une fois par contenu. `ExperimentError` si invalide."""
    return load_experiment(content)


# --- Expériences importées (P1) ------------------------------------------------------------------------
# Un YAML importé dont le schéma est valide est retenu sous la clé `import-<16 premiers caractères du
# SHA-256 du contenu>`. L'interface calcule la même clé : elle lit la spécification par
# `GET /api/experiments/{clé}` et lance `/api/sweep` avec `experiment_id = clé`, sans changer les contrats.
# Mémoire seulement : après un redémarrage, l'interface renvoie le YAML à `/api/validate`.

IMPORT_PREFIX = "import-"
_IMPORTED_MAX = 64
_imported: dict[str, ExperimentSpec] = {}


def import_key(content: str) -> str:
    return IMPORT_PREFIX + content_hash(content)[:16]


def register_import(content: str) -> str:
    """Valide (`ExperimentError` sinon) et retient le YAML ; renvoie sa clé."""
    spec = from_raw(content)
    key = import_key(content)
    _imported.pop(key, None)
    _imported[key] = spec
    while len(_imported) > _IMPORTED_MAX:
        _imported.pop(next(iter(_imported)))
    return key


def imported(key: str) -> ExperimentSpec | None:
    return _imported.get(key)
