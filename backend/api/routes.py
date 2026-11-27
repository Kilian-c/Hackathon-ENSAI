"""Routes P0 de l'API (R1/R2) : expériences, `/api/run`, `/api/sweep`, `/api/training/session`.

Toutes en `def` (pas `async def`) : le calcul NumPy est bloquant, FastAPI les passe dans un pool de threads.
"""

import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.api import registry
from backend.contracts import (
    ExperimentSummary,
    RunRequest,
    RunResult,
    SweepRequest,
    SweepResult,
    TrainingRequest,
    TrainingSessionResponse,
)
from backend.engine.loader import ExperimentError
from backend.engine.runner import RunError, run
from backend.engine.schema import ExperimentSpec
from backend.engine.state import StateError
from backend.engine.sweep import sweep
from backend.engine.training import SEED_RANGE, build_session

router = APIRouter(prefix="/api")


def _get_spec(experiment_id: str) -> ExperimentSpec:
    spec = registry.official().get(experiment_id)
    if spec is None:
        raise HTTPException(404, f"Expérience inconnue : « {experiment_id} ».")
    return spec


@router.get("/experiments", response_model=list[ExperimentSummary])
def list_experiments(
    discipline: str | None = None,
    level: str | None = None,
    concept: str | None = None,
    q: str | None = Query(default=None, description="Texte cherché dans le titre."),
) -> list[ExperimentSummary]:
    out = []
    for spec in registry.official().values():
        if discipline and spec.discipline != discipline:
            continue
        if level and spec.level != level:
            continue
        if concept and concept not in spec.concepts:
            continue
        if q and q.lower() not in spec.title.lower():
            continue
        out.append(
            ExperimentSummary(
                id=spec.id,
                title=spec.title,
                discipline=spec.discipline,
                level=spec.level,
                concepts=spec.concepts,
            )
        )
    return out


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str) -> dict[str, Any]:
    """`ExperimentSpec` : le YAML validé (les champs `from` gardent leur nom d'origine)."""
    return _get_spec(experiment_id).model_dump(mode="json", by_alias=True)


@router.post("/run", response_model=RunResult)
def post_run(request: RunRequest) -> RunResult:
    if request.experiment_id is not None:
        spec = _get_spec(request.experiment_id)
    else:
        assert request.raw_content is not None  # garanti par RunRequest
        try:
            spec = registry.from_raw(request.raw_content)
        except ExperimentError as exc:
            detail = [{"line": i.line, "path": i.path, "message": i.message} for i in exc.issues]
            raise HTTPException(422, {"message": "Fichier d'expérience invalide.", "issues": detail}) from exc
    try:
        return run(spec, request.state)
    except (StateError, RunError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/sweep", response_model=SweepResult)
def post_sweep(request: SweepRequest) -> SweepResult:
    spec = _get_spec(request.experiment_id)
    try:
        return sweep(spec, request.state, [a.target for a in request.axes], request.measure)
    except (StateError, RunError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/training/session", response_model=TrainingSessionResponse)
def post_training_session(request: TrainingRequest) -> TrainingSessionResponse:
    """Série vérifiée. Sans `seed`, le serveur en tire une (hors calcul : elle ne fixe que la série)."""
    seed = request.seed if request.seed is not None else secrets.randbelow(SEED_RANGE)
    try:
        return build_session(
            registry.official(), registry.content_digest(), request.filter, request.count, seed
        )
    except RunError as exc:
        raise HTTPException(422, str(exc)) from exc
