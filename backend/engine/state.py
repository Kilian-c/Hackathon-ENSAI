"""État de calcul canonique (R1) : défauts complétés, continus arrondis au `step`, hash stable.

`EngineState` (contrat) est ce que le client envoie ; `ResolvedState` est ce que le moteur calcule.
Deux états qui diffèrent seulement par ce qui est implicite (valeur par défaut, 0.30000000000000004 contre
0.3) donnent le même `ResolvedState`, donc le même `state_hash` et la même entrée de cache.
"""

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any

from backend.contracts import EngineState
from backend.engine.schema import ExperimentSpec


class StateError(ValueError):
    """État de calcul incompatible avec l'expérience. Le message est en français."""


@dataclass(frozen=True)
class ResolvedState:
    params: dict[str, float | bool]
    hypotheses: dict[str, float | bool | str]
    extra_points: list[dict[str, float]]
    seed: int

    def canonical(self) -> dict[str, Any]:
        return {
            "params": dict(sorted(self.params.items())),
            "hypotheses": dict(sorted(self.hypotheses.items())),
            "extra_points": [dict(sorted(p.items())) for p in self.extra_points],
            "seed": self.seed,
        }

    def hash(self) -> str:
        """16 premiers caractères du SHA-256 de la forme canonique (JSON compact, clés triées)."""
        text = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _snap(value: float, step: float | None) -> float:
    return round(round(value / step) * step, 10) if step else round(value, 10)


def resolve_state(spec: ExperimentSpec, state: EngineState) -> ResolvedState:
    for name in state.params:
        if name not in spec.params:
            raise StateError(f"Paramètre inconnu : « {name} ».")
    for name in state.hypotheses:
        if name not in spec.hypotheses:
            raise StateError(f"Hypothèse inconnue : « {name} ».")

    params: dict[str, float | bool] = {}
    for name, param in spec.params.items():
        value = state.params.get(name, param.default)
        if param.type == "boolean":
            if not isinstance(value, bool):
                raise StateError(f"Le paramètre « {name} » est un interrupteur (true ou false).")
            params[name] = value
        else:
            if isinstance(value, bool):
                raise StateError(f"Le paramètre « {name} » est un nombre.")
            if not param.min <= value <= param.max:
                raise StateError(f"Le paramètre « {name} » doit être entre {param.min} et {param.max}.")
            params[name] = float(value)

    hypotheses: dict[str, float | bool | str] = {}
    for name, hyp in spec.hypotheses.items():
        value = state.hypotheses.get(name, hyp.healthy_value)
        if hyp.type == "boolean":
            if not isinstance(value, bool):
                raise StateError(f"L'hypothèse « {name} » est un interrupteur (true ou false).")
            hypotheses[name] = value
        elif hyp.type == "choice":
            if not isinstance(value, str) or value not in hyp.options:
                raise StateError(f"L'hypothèse « {name} » : options admises {sorted(hyp.options)}.")
            hypotheses[name] = value
        else:
            if isinstance(value, bool | str):
                raise StateError(f"L'hypothèse « {name} » est un nombre.")
            if not hyp.range[0] <= value <= hyp.range[1]:
                raise StateError(f"L'hypothèse « {name} » doit être entre {hyp.range[0]} et {hyp.range[1]}.")
            hypotheses[name] = _snap(float(value), hyp.step)

    return ResolvedState(
        params=params,
        hypotheses=hypotheses,
        extra_points=[{k: float(v) for k, v in p.items()} for p in state.extra_points],
        seed=state.seed,
    )


def healthy(spec: ExperimentSpec, state: ResolvedState) -> ResolvedState:
    """La Référence : hypothèses à leur valeur saine, aucun point ajouté, mêmes paramètres et même graine."""
    return replace(
        state,
        hypotheses={name: hyp.healthy_value for name, hyp in spec.hypotheses.items()},
        extra_points=[],
    )
