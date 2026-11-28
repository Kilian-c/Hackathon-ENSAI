"""Séries d'Entraînement (`POST /api/training/session`, CLAUDE.md section 8) : questions tirées des YAML,
paramètres procéduraux tirés, choix vérifiés par simulation, puis mélangés.

Une série est déterminée par (filtre, graine, empreinte du contenu des YAML) : même entrée, même série.
- `misconception` : une seule fois par série. Chaque choix est vérifié (`reveal_state` lancé par `run()`,
  condition `verify`) ; 5 tirages au plus, sinon la question est retirée et listée dans `dropped`.
- `diagnostic_auto` : peut revenir (2 fois au plus par série), avec une pathologie cachée différente ;
  le `qid` se termine par l'indice de l'occurrence.
- `prediction` (P1) : une seule fois par série. Le moteur lance l'état de départ et l'état d'arrivée
  (même graine) et compare la mesure de la méthode principale : « reste stable » si l'écart est sous
  2 erreurs Monte Carlo, « augmente » ou « diminue » s'il dépasse 4 ; entre les deux, nouveau tirage
  (5 au plus), sinon question retirée. La bonne réponse n'est jamais écrite dans le YAML.

Aucun code propre à un théorème : libellés et états viennent des hypothèses du YAML.
Écrit par R2 (aide à R1), à relire par R1.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from backend.contracts import (
    MAX_TRAINING_COUNT,
    Confidence,
    DroppedQuestion,
    EngineState,
    Reveal,
    TrainingChoice,
    TrainingQuestion,
    TrainingSessionResponse,
)
from backend.engine.expr import Env, ExprError, evaluate
from backend.engine.rng import rng_for
from backend.engine.runner import RunError, check_condition, run
from backend.engine.schema import (
    DiagnosticAuto,
    ExperimentSpec,
    Misconception,
    Prediction,
    ProcParam,
    State,
)
from backend.engine.state import StateError, resolve_state

MAX_TRIES = 5  # tirages au plus pour qu'une question passe `verify`
MAX_SECONDS = 15.0  # délai de fabrication d'une série
DIAG_REPEAT = 2  # occurrences au plus d'un même diagnostic dans une série
SEED_RANGE = 1_000_000  # graines courtes : elles apparaissent dans les liens
HEALTHY_KEY = "sain"
HEALTHY_LABEL = "Hypothèses respectées"
STABLE_SE = 2.0  # écart sous 2 erreurs Monte Carlo : « reste stable »
CHANGE_SE = 4.0  # écart au-delà de 4 erreurs Monte Carlo : « augmente » ou « diminue »
STABLE_REL = 0.02  # mesure sans erreur Monte Carlo : stable sous 2 % d'écart relatif
PREDICTION_CHOICES = (("up", "Elle augmente"), ("down", "Elle diminue"), ("stable", "Elle reste stable"))

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_WHOLE_PLACEHOLDER = re.compile(r"^\{(\w+)\}$")


# --- Petits outils ---------------------------------------------------------------------------------------


def _fmt(value: float) -> str:
    """Nombre lisible en français : 150, 0,5."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}".replace(".", ",")


def _confidence(k: int) -> Confidence:
    """Crans de confiance (CLAUDE.md, section 10) : 1/k, (1/k + 0,95)/2, 0,95."""
    return Confidence(guess=1 / k, fair=(1 / k + 0.95) / 2, sure=0.95)


def _draw_params(procedural: Mapping[str, ProcParam], rng: np.random.Generator) -> dict[str, float]:
    """Un tirage des paramètres procéduraux, sur leur grille (min, min + step, ..., max)."""
    out: dict[str, float] = {}
    for name in sorted(procedural):
        p = procedural[name]
        steps = int(np.floor((p.max - p.min) / p.step + 1e-9))
        value = round(p.min + int(rng.integers(0, steps + 1)) * p.step, 10)
        out[name] = float(int(value)) if float(value).is_integer() else value
    return out


def _fill_text(text: str, values: Mapping[str, float]) -> str:
    return _PLACEHOLDER.sub(lambda m: _fmt(values[m.group(1)]) if m.group(1) in values else m.group(0), text)


def _fill_values(values: Mapping[str, Any], drawn: Mapping[str, float]) -> dict[str, Any]:
    """Remplace `"{n}"` par le nombre tiré ; les autres valeurs (clés d'options...) restent telles quelles."""
    out: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, str):
            match = _WHOLE_PLACEHOLDER.match(value)
            if match:
                if match.group(1) not in drawn:
                    raise RunError(f"Paramètre procédural inconnu : « {match.group(1)} ».")
                value = drawn[match.group(1)]
        out[key] = value
    return out


def _full_state(
    spec: ExperimentSpec, params: Mapping[str, Any], hypotheses: Mapping[str, Any], seed: int
) -> EngineState:
    """État complet (défauts complétés, continus arrondis) : celui que l'interface renverra à /api/run."""
    rs = resolve_state(spec, EngineState(params=dict(params), hypotheses=dict(hypotheses), seed=seed))
    return EngineState(params=dict(rs.params), hypotheses=dict(rs.hypotheses), seed=seed)


def _partial(state: State | None, drawn: Mapping[str, float]) -> tuple[dict[str, Any], dict[str, Any]]:
    if state is None:
        return {}, {}
    return _fill_values(state.params, drawn), _fill_values(state.hypotheses, drawn)


# --- Fabrication d'une question --------------------------------------------------------------------------


class _Dropped(Exception):
    """Question retirée de la série (raison en français)."""


def _misconception(spec: ExperimentSpec, q: Misconception, rng: np.random.Generator) -> TrainingQuestion:
    for _ in range(MAX_TRIES):
        drawn = _draw_params(q.procedural_params, rng)
        seed = int(rng.integers(0, SEED_RANGE))
        states = {c.id: _full_state(spec, *_partial(c.reveal_state, drawn), seed) for c in q.choices}
        try:
            verified = all(check_condition(spec, states[c.id], c.verify) for c in q.choices)
        except ExprError as exc:
            raise _Dropped(f"Condition verify illisible : {exc}") from exc
        if verified:
            k = len(q.choices)
            choices = [
                TrainingChoice(
                    id=c.id,
                    label=c.label,
                    correct=c.correct,
                    explain=c.explain,
                    reveal=Reveal(state=states[c.id], focus_view=c.focus_view),
                )
                for c in (q.choices[i] for i in rng.permutation(k))
            ]
            return TrainingQuestion(
                qid=f"{spec.id}/{q.id}/0",
                experiment_id=spec.id,
                type="misconception",
                prompt=_fill_text(q.prompt, drawn),
                hypothesis=q.hypothesis,
                k=k,
                confidence=_confidence(k),
                choices=choices,
            )
    raise _Dropped(f"La condition verify a échoué sur {MAX_TRIES} tirages.")


def _bound(q: Prediction, raw: float | str, drawn: Mapping[str, float], spec: ExperimentSpec) -> Any:
    """Une borne du balayage : clé d'option pour une hypothèse à choix, sinon expression numérique."""
    kind, _, name = q.sweep.target.partition(".")
    # Expression : nombres tirés écrits avec un point (« 0.94 »), pas avec la virgule de l'affichage.
    text = _PLACEHOLDER.sub(lambda m: repr(drawn[m.group(1)]), raw) if isinstance(raw, str) else raw
    hyp = spec.hypotheses.get(name) if kind == "h" else None
    if hyp is not None and hyp.type == "choice":
        return text
    if hyp is not None and hyp.type == "boolean":
        return text in (True, "true", "1")
    if isinstance(text, str):
        try:
            text = evaluate(text, Env())
        except ExprError as exc:
            raise _Dropped(f"Borne de balayage illisible : {exc}") from exc
    return float(text)


def _measure_text(spec: ExperimentSpec, measure_id: str, value: float) -> str:
    m = spec.measures[measure_id]
    shown = f"{value * m.scale:.{m.decimals}f}".replace(".", ",")
    return f"{shown}{(' ' + m.unit) if m.unit else ''}"


def _prediction(spec: ExperimentSpec, q: Prediction, rng: np.random.Generator) -> TrainingQuestion:
    if q.measure not in spec.measures:
        raise _Dropped(f"Mesure inconnue : « {q.measure} ».")
    kind, _, name = q.sweep.target.partition(".")
    if (kind == "p" and name not in spec.params) or (kind == "h" and name not in spec.hypotheses):
        raise _Dropped(f"Axe inconnu : « {q.sweep.target} ».")
    main = next(m.id for m in spec.methods if m.role == "method")
    for _ in range(MAX_TRIES):
        drawn = _draw_params(q.procedural_params, rng)
        seed = int(rng.integers(0, SEED_RANGE))
        params, hyps = _partial(q.state, drawn)
        group = params if kind == "p" else hyps
        ends = []
        for raw in (q.sweep.from_, q.sweep.to):
            values = {**group, name: _bound(q, raw, drawn, spec)}
            p, h = (values, hyps) if kind == "p" else (params, values)
            state = _full_state(spec, p, h, seed)
            mr = run(spec, state).measures[q.measure]
            ends.append((state, mr.values.get(main), mr.mc_se.get(main)))
        (s0, v0, se0), (s1, v1, se1) = ends
        if v0 is None or v1 is None:
            continue
        delta = v1 - v0
        if se0 is not None and se1 is not None:
            se = float(np.hypot(se0, se1))
            stable, changed = abs(delta) <= STABLE_SE * se, abs(delta) >= CHANGE_SE * se
        else:
            ref = max(abs(v0), abs(v1), 1e-12)
            stable, changed = abs(delta) <= STABLE_REL * ref, abs(delta) > STABLE_REL * ref
        if not (stable or changed):
            continue  # écart ambigu : un autre tirage
        answer = "stable" if stable else ("up" if delta > 0 else "down")
        label = spec.measures[q.measure].label
        facts = (
            # « puis », pas une virgule : une virgule de liste à côté de virgules décimales prête à confusion.
            f"{label} : {_measure_text(spec, q.measure, v0)} au départ puis "
            f"{_measure_text(spec, q.measure, v1)} à l'arrivée."
        )
        verdict = {"up": "elle augmente", "down": "elle diminue", "stable": "elle reste stable"}[answer]
        choices = [
            TrainingChoice(
                id=cid,
                label=text,
                correct=cid == answer,
                explain=(f"Exact : {verdict}. " if cid == answer else f"Non : {verdict}. ") + facts,
                reveal=Reveal(state=s1, focus_view=None),
            )
            for cid, text in PREDICTION_CHOICES
        ]
        k = len(choices)
        return TrainingQuestion(
            qid=f"{spec.id}/{q.id}/0",
            experiment_id=spec.id,
            type="prediction",
            prompt=_fill_text(q.prompt, drawn),
            hypothesis=None,
            k=k,
            confidence=_confidence(k),
            choices=choices,
        )
    raise _Dropped(f"Aucune réponse nette sur {MAX_TRIES} tirages (écart trop proche du bruit Monte Carlo).")


@dataclass(frozen=True)
class _Pathology:
    key: str  # « hyp », « hyp.option » ou « sain »
    label: str
    hypotheses: dict[str, Any]  # valeurs qui cassent l'hypothèse
    hypothesis: str | None  # hypothèse expliquée après la réponse


def _pathologies(spec: ExperimentSpec, q: DiagnosticAuto) -> list[_Pathology]:
    """Les pathologies du YAML, plus « Hypothèses respectées » ajoutée d'office."""
    out = [_Pathology(HEALTHY_KEY, HEALTHY_LABEL, {}, None)]
    for ref in q.pathologies.from_:
        hid, _, option = ref.partition(".")
        hyp = spec.hypotheses.get(hid)
        if hyp is None:
            raise _Dropped(f"Pathologie inconnue : « {ref} ».")
        if hyp.type == "choice":
            assert hyp.options is not None  # garanti par le schéma
            key = option or next(k for k in hyp.options if k != hyp.healthy_value)
            if key not in hyp.options:
                raise _Dropped(f"Option inconnue : « {ref} ».")
            out.append(_Pathology(ref, f"{hyp.label} : {hyp.options[key].label}", {hid: key}, hid))
        else:
            broken: Any = (not hyp.healthy_value) if hyp.type == "boolean" else hyp.range[1]
            what = hyp.broken_label or "hypothèse cassée"
            out.append(_Pathology(ref, f"{hyp.label} : {what}", {hid: broken}, hid))
    return out


def _diagnostic(
    spec: ExperimentSpec, q: DiagnosticAuto, index: int, rng: np.random.Generator, used: set[str]
) -> tuple[TrainingQuestion, str]:
    options = _pathologies(spec, q)
    drawn = _draw_params(q.procedural_params, rng)
    seed = int(rng.integers(0, SEED_RANGE))
    hidden = next((options[i] for i in rng.permutation(len(options)) if options[i].key not in used), None)
    if hidden is None:
        raise _Dropped("Toutes les pathologies de ce diagnostic sont déjà dans la série.")
    params, hyps = _partial(q.state, drawn)
    states = {p.key: _full_state(spec, params, {**hyps, **p.hypotheses}, seed) for p in options}

    view = next((v for v in run(spec, states[hidden.key]).views if v.id == q.view), None)
    if view is None:
        raise _Dropped(f"Vue inconnue : « {q.view} ».")

    def explain(p: _Pathology) -> str:
        if p.key == hidden.key:
            if p.hypothesis is None:
                return "Exact : aucune hypothèse n'était cassée ; le graphique ressemble à la Référence."
            return f"Exact : la simulation cassait l'hypothèse « {spec.hypotheses[p.hypothesis].label} »."
        truth = (
            "aucune hypothèse n'était cassée"
            if hidden.hypothesis is None
            else f"la situation était « {hidden.label} »"
        )
        return f"Ce n'était pas « {p.label} » : {truth}."

    k = len(options)
    choices = [
        TrainingChoice(
            id=f"c{n + 1}",
            label=p.label,
            correct=p.key == hidden.key,
            explain=explain(p),
            reveal=Reveal(state=states[p.key], focus_view=q.view),
        )
        for n, p in enumerate(options[i] for i in rng.permutation(k))
    ]
    question = TrainingQuestion(
        qid=f"{spec.id}/{q.id}/{index}",
        experiment_id=spec.id,
        type="diagnostic_auto",
        prompt=_fill_text(q.prompt, drawn),
        initial_view=view,
        hypothesis=hidden.hypothesis,
        k=k,
        confidence=_confidence(k),
        choices=choices,
    )
    return question, hidden.key


# --- La série ----------------------------------------------------------------------------------------------


def discipline_slug(name: str) -> str:
    """Identifiant court d'une discipline : sans accent ni espace (« algebre-lineaire »).

    Le contrat de filtre refuse les espaces ; l'identifiant court permet de filtrer toutes les disciplines et
    reste lisible dans une URL. L'ancien nom exact donne le même identifiant : les anciens liens marchent.
    """
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")


def available_disciplines(specs: Mapping[str, ExperimentSpec]) -> dict[str, str]:
    """Identifiant court -> nom de la discipline, pour les expériences officielles."""
    return {discipline_slug(s.discipline): s.discipline for s in sorted(specs.values(), key=lambda s: s.id)}


def _wanted_disciplines(specs: Mapping[str, ExperimentSpec], filter_: str) -> list[str]:
    """Identifiants courts de `discipline:<a>[,<b>...]`, triés, sans doublon. `RunError` si inconnu."""
    known = available_disciplines(specs)
    parts = filter_.removeprefix("discipline:").split(",")
    wanted = {discipline_slug(part) for part in parts if part.strip()}
    if not wanted:
        raise RunError("Indiquez au moins une discipline (par exemple « discipline:statistique »).")
    unknown = sorted(w for w in wanted if w not in known)
    if unknown:
        raise RunError(
            f"Discipline inconnue : « {unknown[0]} ». Disciplines disponibles : {', '.join(sorted(known))}."
        )
    return sorted(wanted)


def canonical_filter(specs: Mapping[str, ExperimentSpec], filter_: str) -> str:
    """Forme unique d'un filtre : l'ordre et l'orthographe des disciplines (accents, majuscules) ne
    changent pas la série, qui dépend de la graine, de cette forme et du contenu des YAML."""
    if filter_.startswith("discipline:"):
        return "discipline:" + ",".join(_wanted_disciplines(specs, filter_))
    return filter_


def select_experiments(specs: Mapping[str, ExperimentSpec], filter_: str) -> list[ExperimentSpec]:
    """`toutes`, un identifiant d'expérience, ou `discipline:<id>[,<id>...]` (une ou plusieurs)."""
    if filter_ == "toutes":
        chosen = list(specs.values())
    elif filter_.startswith("discipline:"):
        wanted = set(_wanted_disciplines(specs, filter_))
        chosen = [s for s in specs.values() if discipline_slug(s.discipline) in wanted]
    else:
        chosen = [specs[filter_]] if filter_ in specs else []
    return sorted(chosen, key=lambda s: s.id)


@dataclass(frozen=True)
class _Slot:
    spec: ExperimentSpec
    question: Misconception | DiagnosticAuto | Prediction
    index: int


def _pool(experiments: list[ExperimentSpec]) -> list[_Slot]:
    slots: list[_Slot] = []
    for spec in experiments:
        for q in spec.questions:
            if isinstance(q, Misconception | Prediction):
                slots.append(_Slot(spec, q, 0))
            elif isinstance(q, DiagnosticAuto):
                repeat = min(DIAG_REPEAT, len(q.pathologies.from_) + 1)
                slots += [_Slot(spec, q, i) for i in range(repeat)]
    return slots


def _round_robin(pool: list[_Slot], rng: np.random.Generator) -> list[_Slot]:
    """Ordre de tirage équilibré : les expériences sont mélangées, puis chacune donne une question à son
    tour (ses questions étant elles-mêmes mélangées). Une série ne retombe sur une même expérience qu'une
    fois toutes les autres servies : 10 questions sur 15 expériences = 10 expériences différentes."""
    by_experiment: dict[str, list[_Slot]] = {}
    for slot in pool:
        by_experiment.setdefault(slot.spec.id, []).append(slot)
    ids = sorted(by_experiment)
    queues = [[by_experiment[i][j] for j in rng.permutation(len(by_experiment[i]))] for i in ids]
    queues = [queues[k] for k in rng.permutation(len(queues))]
    order: list[_Slot] = []
    for rank in range(max(len(q) for q in queues)):
        order += [q[rank] for q in queues if rank < len(q)]
    return order


def build_session(
    specs: Mapping[str, ExperimentSpec], digest: str, filter_: str, count: int, seed: int
) -> TrainingSessionResponse:
    t0 = time.perf_counter()
    experiments = select_experiments(specs, filter_)
    if not experiments:
        raise RunError(f"Aucune expérience ne correspond au filtre « {filter_} ».")
    pool = _pool(experiments)
    if not pool:
        raise RunError("Aucune question disponible pour ce filtre.")
    target = min(count, MAX_TRAINING_COUNT, len(pool))
    stream = f"training:{canonical_filter(specs, filter_)}:{digest}"
    order = _round_robin(pool, rng_for(seed, stream))

    questions: list[TrainingQuestion] = []
    dropped: list[DroppedQuestion] = []
    used: dict[tuple[str, str], set[str]] = {}
    for slot in order:
        if len(questions) == target:
            break
        if time.perf_counter() - t0 > MAX_SECONDS:
            dropped.append(
                DroppedQuestion(
                    experiment_id=slot.spec.id,
                    question_id=slot.question.id,
                    reason=f"Délai de fabrication de la série dépassé ({MAX_SECONDS:.0f} s).",
                )
            )
            break
        rng = rng_for(seed, f"{stream}:{slot.spec.id}/{slot.question.id}/{slot.index}")
        try:
            if isinstance(slot.question, Misconception):
                questions.append(_misconception(slot.spec, slot.question, rng))
            elif isinstance(slot.question, Prediction):
                questions.append(_prediction(slot.spec, slot.question, rng))
            else:
                seen = used.setdefault((slot.spec.id, slot.question.id), set())
                made, hidden = _diagnostic(slot.spec, slot.question, slot.index, rng, seen)
                seen.add(hidden)
                questions.append(made)
        except (_Dropped, RunError, StateError, ExprError) as exc:
            dropped.append(
                DroppedQuestion(experiment_id=slot.spec.id, question_id=slot.question.id, reason=str(exc))
            )

    # Le tirage à tour de rôle range les questions par tour : on remélange la série.
    questions = [questions[j] for j in rng_for(seed, f"{stream}:ordre").permutation(len(questions))]

    return TrainingSessionResponse(
        id=f"{filter_}~{seed}",
        filter=filter_,
        seed=seed,
        content_hash=digest[:6],
        questions=questions,
        dropped=dropped,
    )


__all__ = [
    "available_disciplines",
    "build_session",
    "canonical_filter",
    "discipline_slug",
    "select_experiments",
]
