"""Schéma YAML v1 d'une expérience (R1). FICHIER DE CONTRAT : figé au tag `contracts-v1` (H4).

`ExperimentSpec` décrit tout ce qu'un fichier de `experiments/` peut contenir. Chaque modèle refuse
les champs inconnus (`extra="forbid"`). Les vérifications qui ne demandent que le YAML lui-même sont
faites ici, au chargement : plafonds, références croisées (hypothèses, termes d'équation, vues,
axes de balayage), unicité des identifiants. Elles remontent sous forme de `SpecIssues`, qui porte
un chemin par erreur : le chargeur (`loader.py`) en tire le numéro de ligne.

Ce qui n'est PAS vérifié ici, et ailleurs :
- les noms utilisés dans les expressions et les cycles entre variables : `engine/expr.py` (R1) ;
- l'existence des lois du registre, des méthodes (`call`), des agrégateurs et des clés `provides` :
  `laws.py`, `method_contract.py`, `aggregators.py` (R2).

Les champs `from` du YAML s'appellent `from_` en Python (mot réservé) : sérialiser avec
`model_dump(by_alias=True)`.
"""

import re
from collections import Counter
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCHEMA_VERSION = 1

# Plafonds identiques pour tout YAML (CLAUDE.md, section 8).
MAX_EXPR_LEN = 300
MAX_REPEAT = 1000
MAX_N = 5000
MAX_METHODS = 4
MAX_VARIABLES = 30
MAX_YAML_BYTES = 64 * 1024

# Nom utilisable dans une expression (`p.<id>`, `h.<id>`, variable, mesure, méthode, option).
Ident = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
# Identifiant de contenu (expérience, question, choix, défi, vue, calque, contre-exemple).
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]*$")]
# Axe de balayage : `h.<id>` ou `p.<id>`.
Axis = Annotated[str, StringConstraints(pattern=r"^[hp]\.[A-Za-z_][A-Za-z0-9_]*$")]
Expr = Annotated[str, StringConstraints(max_length=MAX_EXPR_LEN)]
Scalar = bool | float | str

# Noms réservés : racines de l'espace de noms des expressions.
RESERVED_NAMES = frozenset({"p", "h", "m", "s", "base", "idx", "gen", "reps", "example", "curves"})

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_TEMPLATE_FIELD = re.compile(r"\{\{(\w+)\}\}")


class SpecIssues(ValueError):
    """Erreurs de cohérence d'un YAML : liste de (chemin, message), chemin dans le document."""

    def __init__(self, issues: list[tuple[tuple[str | int, ...], str]]):
        self.issues = issues
        super().__init__("; ".join(message for _, message in issues))


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- Théorème et équation -------------------------------------------------------------------------


class Theorem(Strict):
    name: str
    statement: str


class EquationTerm(Strict):
    ok: str
    corrected: str | None = None


class Equation(Strict):
    tex: str
    terms: dict[Ident, EquationTerm]

    @model_validator(mode="after")
    def _check_template(self):
        used = set(_TEMPLATE_FIELD.findall(self.tex))
        for name in sorted(used - set(self.terms)):
            raise ValueError(f"Le gabarit cite {{{{{name}}}}}, qui n'est pas un terme de l'équation.")
        for name in sorted(set(self.terms) - used):
            raise ValueError(f"Le terme « {name} » n'apparaît pas dans le gabarit tex.")
        return self


# --- États (contre-exemples, questions) -------------------------------------------------------------


class State(Strict):
    """Un état partiel : ce qui n'est pas cité prend sa valeur saine ou son défaut."""

    params: dict[Ident, Scalar] = {}
    hypotheses: dict[Ident, Scalar] = {}


# --- Paramètres et hypothèses -----------------------------------------------------------------------


class Param(Strict):
    type: Literal["number", "boolean"]
    label: str
    default: bool | float
    min: float | None = None
    max: float | None = None
    step: float | None = None
    sweep_values: list[float] | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.type == "number":
            if isinstance(self.default, bool):
                raise ValueError("Le défaut d'un paramètre numérique doit être un nombre.")
            if self.min is None or self.max is None or self.step is None:
                raise ValueError("Un paramètre numérique exige min, max et step.")
            if self.min >= self.max or self.step <= 0:
                raise ValueError("Il faut min < max et step > 0.")
            if not self.min <= self.default <= self.max:
                raise ValueError("Le défaut doit être compris entre min et max.")
            if self.sweep_values and not all(self.min <= v <= self.max for v in self.sweep_values):
                raise ValueError("Les valeurs de sweep_values doivent être comprises entre min et max.")
        else:
            if not isinstance(self.default, bool):
                raise ValueError("Le défaut d'un paramètre booléen doit être true ou false.")
            if any(v is not None for v in (self.min, self.max, self.step, self.sweep_values)):
                raise ValueError("Un paramètre booléen n'a ni min, ni max, ni step, ni sweep_values.")
        return self


class Option(Strict):
    """Option d'une hypothèse de type `choice` : une loi du registre OU une expression libre."""

    label: str
    law: str | None = None
    expr: Expr | None = None
    robust_expected: bool = False

    @model_validator(mode="after")
    def _one_source(self):
        if (self.law is None) == (self.expr is None):
            raise ValueError("Une option porte soit `law`, soit `expr` (exactement un des deux).")
        return self


class Hypothesis(Strict):
    type: Literal["continuous", "choice", "boolean"]
    healthy_value: bool | float | str
    label: str
    category: str
    statement_tex: str
    why: str
    when_broken: str
    affects: list[Ident] = []
    range: tuple[float, float] = (0.0, 1.0)
    step: float | None = None
    ok_label: str | None = None
    broken_label: str | None = None
    options: dict[Ident, Option] | None = None
    robust_expected: bool = False  # niveau hypothèse ; une option peut aussi le porter
    disabled_when: Expr | None = None
    disabled_text: str | None = None

    @model_validator(mode="after")
    def _check(self):
        hv = self.healthy_value
        if self.type == "continuous":
            if self.options is not None:
                raise ValueError("Une hypothèse continue n'a pas d'options.")
            if isinstance(hv, bool | str):
                raise ValueError("La valeur saine d'une hypothèse continue doit être un nombre.")
            if self.range[0] >= self.range[1]:
                raise ValueError("Il faut range[0] < range[1].")
            if not self.range[0] <= hv <= self.range[1]:
                raise ValueError("La valeur saine doit être dans range.")
            if self.step is not None and self.step <= 0:
                raise ValueError("step doit être positif.")
        elif self.type == "boolean":
            if self.options is not None:
                raise ValueError("Une hypothèse booléenne n'a pas d'options.")
            if not isinstance(hv, bool):
                raise ValueError("La valeur saine d'une hypothèse booléenne doit être true ou false.")
        else:
            if not self.options or len(self.options) < 2:
                raise ValueError("Une hypothèse de type choice exige au moins 2 options.")
            if not isinstance(hv, str) or hv not in self.options:
                raise ValueError("La valeur saine doit être la clé d'une des options.")
        return self


class Counterexample(Strict):
    id: Slug
    label: str
    explain: str
    state: State
    expect: Literal["same_summary"] | None = None


# --- Générateurs ---------------------------------------------------------------------------------------


class Variable(Strict):
    expr: Expr
    dims: Literal["sample", "obs_p"] | None = None


class RandomGenerator(Strict):
    type: Literal["random"]
    n: int | Expr
    repeat: int = Field(ge=1, le=MAX_REPEAT)
    variables: dict[Ident, Variable] = Field(min_length=1, max_length=MAX_VARIABLES)
    inject: dict[Ident, Ident] | None = None  # emplacement -> variable qui reçoit les points posés

    @model_validator(mode="after")
    def _check(self):
        if isinstance(self.n, int) and not 1 <= self.n <= MAX_N:
            raise ValueError(f"n doit être compris entre 1 et {MAX_N}.")
        for name in self.variables:
            if name in RESERVED_NAMES:
                raise ValueError(f"« {name} » est un nom réservé : choisissez un autre nom de variable.")
        for slot, var in (self.inject or {}).items():
            if var not in self.variables:
                raise ValueError(f"inject.{slot} cite une variable inconnue : « {var} ».")
        return self


class OdeGenerator(Strict):
    type: Literal["ode"]
    t_end: Expr | float
    state: dict[Ident, Expr | float] = Field(min_length=1)  # conditions initiales
    rhs: dict[Ident, Expr]
    derived: dict[Ident, Expr] | None = None

    @model_validator(mode="after")
    def _check(self):
        if set(self.rhs) != set(self.state):
            raise ValueError("rhs et state doivent porter exactement les mêmes variables d'état.")
        return self


class FunctionGenerator(Strict):
    """P2 : le format seulement."""

    type: Literal["function"]
    grid: Any = None
    variables: Any = None


Generator = Annotated[RandomGenerator | OdeGenerator | FunctionGenerator, Field(discriminator="type")]


# --- Méthodes, mesures, défis ----------------------------------------------------------------------------


class Method(Strict):
    id: Ident
    role: Literal["method", "correction", "alternative"]
    call: Ident
    label: str
    args: dict[Ident, Any] = {}
    explain: str | None = None
    repairs: list[Ident] = []

    @model_validator(mode="after")
    def _check(self):
        if self.role != "method" and not self.explain:
            raise ValueError("`explain` est obligatoire pour une correction ou une alternative.")
        if self.role == "method" and self.repairs:
            raise ValueError("La méthode principale ne répare rien : `repairs` est réservé aux autres rôles.")
        for key, value in self.args.items():
            if isinstance(value, str) and len(value) > MAX_EXPR_LEN:
                raise ValueError(f"L'argument « {key} » dépasse {MAX_EXPR_LEN} caractères.")
        return self


class MeasureTexts(Strict):
    ok: str
    warning: str
    broken: str


class Measure(Strict):
    agg: Expr
    label: str
    unit: str = ""
    scale: float = 1.0
    decimals: int = Field(default=2, ge=0, le=6)
    primary: bool = False
    # Bloc verdict : target, direction, ok_within, broken_beyond vont ensemble (ou sont tous absents).
    target: float | Literal["base"] | None = None
    direction: Literal["below", "above", "both"] | None = None
    ok_within: float | None = Field(default=None, ge=0)
    broken_beyond: float | None = Field(default=None, ge=0)
    texts: MeasureTexts | None = None

    @model_validator(mode="after")
    def _check(self):
        block = (self.target, self.direction, self.ok_within, self.broken_beyond)
        given = [v is not None for v in block]
        if any(given) and not all(given):
            raise ValueError("target, direction, ok_within et broken_beyond vont ensemble (tous ou aucun).")
        if not any(given):
            if self.texts is not None:
                raise ValueError("`texts` n'a de sens que pour une mesure avec cible.")
            if self.primary:
                raise ValueError("La mesure primaire doit avoir une cible et des seuils.")
        elif self.ok_within > self.broken_beyond:
            raise ValueError("ok_within doit être inférieur ou égal à broken_beyond.")
        return self


class Challenge(Strict):
    id: Slug
    goal: str
    when: Expr
    unlock: str
    hint: str | None = None


# --- Vues --------------------------------------------------------------------------------------------------


class ViewSweep(Strict):
    axes: list[Axis] = Field(min_length=1, max_length=2)


class Layer(Strict):
    id: Slug
    label: str


class View(Strict):
    id: Slug
    type: str  # volontairement libre : un type inconnu retombe sur la vue de secours `measures_table`
    title: str
    bind: dict[str, Any] | None = None
    sweep: ViewSweep | None = None
    axes: dict[str, Any] | None = None
    layers: list[Layer] | None = None
    inspect: bool = False
    allow_point_injection: bool = False
    mode: str | None = None
    ui: dict[str, Any] | None = None


# --- Questions ---------------------------------------------------------------------------------------------


class ProcParam(Strict):
    min: float
    max: float
    step: float

    @model_validator(mode="after")
    def _check(self):
        if self.min > self.max or self.step <= 0:
            raise ValueError("Il faut min <= max et step > 0.")
        return self


class Choice(Strict):
    id: Slug
    label: str
    correct: bool
    reveal_state: State
    verify: Expr
    focus_view: Slug
    explain: str


def _placeholders_of_state(state: State | None) -> set[str]:
    found: set[str] = set()
    if state is not None:
        for values in (state.params, state.hypotheses):
            for v in values.values():
                if isinstance(v, str):
                    found |= set(_PLACEHOLDER.findall(v))
    return found


def _check_placeholders(used: set[str], declared: dict[str, ProcParam], where: str) -> None:
    missing = sorted(used - set(declared))
    if missing:
        raise ValueError(f"{where} utilise {{{missing[0]}}}, absent de procedural_params.")


class Misconception(Strict):
    id: Slug
    type: Literal["misconception"]
    prompt: str
    hypothesis: Ident
    procedural_params: dict[Ident, ProcParam] = {}
    choices: list[Choice] = Field(min_length=2)

    @model_validator(mode="after")
    def _check(self):
        if sum(c.correct for c in self.choices) != 1:
            raise ValueError("Une question de type misconception a exactement un choix correct.")
        if len({c.id for c in self.choices}) != len(self.choices):
            raise ValueError("Les identifiants de choix doivent être uniques.")
        _check_placeholders(set(_PLACEHOLDER.findall(self.prompt)), self.procedural_params, "L'énoncé")
        for c in self.choices:
            _check_placeholders(
                _placeholders_of_state(c.reveal_state), self.procedural_params, f"Le choix « {c.id} »"
            )
        return self


class Pathologies(Strict):
    # `from` dans le YAML : « hyp » ou « hyp.option ».
    from_: list[str] = Field(alias="from", min_length=1)


class DiagnosticAuto(Strict):
    id: Slug
    type: Literal["diagnostic_auto"]
    prompt: str
    view: Slug
    state: State | None = None
    pathologies: Pathologies
    procedural_params: dict[Ident, ProcParam] = {}

    @model_validator(mode="after")
    def _check(self):
        _check_placeholders(set(_PLACEHOLDER.findall(self.prompt)), self.procedural_params, "L'énoncé")
        _check_placeholders(_placeholders_of_state(self.state), self.procedural_params, "L'état")
        return self


class PredictionSweep(Strict):
    target: Axis
    from_: float | str = Field(alias="from")
    to: float | str


class Prediction(Strict):
    """P1 : le format est figé dès maintenant."""

    id: Slug
    type: Literal["prediction"]
    prompt: str
    procedural_params: dict[Ident, ProcParam] = {}
    state: State | None = None
    sweep: PredictionSweep
    measure: Ident

    @model_validator(mode="after")
    def _check(self):
        used = set(_PLACEHOLDER.findall(self.prompt)) | _placeholders_of_state(self.state)
        for bound in (self.sweep.from_, self.sweep.to):
            if isinstance(bound, str):
                used |= set(_PLACEHOLDER.findall(bound))
        _check_placeholders(used, self.procedural_params, "La question")
        return self


Question = Annotated[Misconception | DiagnosticAuto | Prediction, Field(discriminator="type")]


# --- L'expérience ------------------------------------------------------------------------------------------


def _layer_refs(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "layer" and isinstance(value, str):
                found.append(value)
            else:
                found += _layer_refs(value)
    elif isinstance(node, list):
        for value in node:
            found += _layer_refs(value)
    return found


class ExperimentSpec(Strict):
    schema_version: Literal[1]
    id: Slug
    title: str
    discipline: str
    level: str
    concepts: list[str] = []
    theorem: Theorem
    equation: Equation
    params: dict[Ident, Param] = {}
    hypotheses: dict[Ident, Hypothesis] = Field(min_length=1)
    counterexamples: list[Counterexample] = []
    generator: Generator
    methods: list[Method] = Field(min_length=1)
    measures: dict[Ident, Measure] = Field(min_length=1)
    challenges: list[Challenge] = []
    auto_sweep: list[Axis] = []
    draw_log: dict[str, Any] | None = None  # P1
    views: list[View] = Field(min_length=1)
    opening_question: Slug | None = None  # P1
    questions: list[Question] = []

    @model_validator(mode="after")
    def _check_references(self):
        issues: list[tuple[tuple[str | int, ...], str]] = []

        def add(loc: tuple[str | int, ...], message: str) -> None:
            issues.append((loc, message))

        def unique(loc: tuple[str | int, ...], ids: list[str], what: str) -> None:
            seen: set[str] = set()
            for i, ident in enumerate(ids):
                if ident in seen:
                    add((*loc, i, "id"), f"Identifiant de {what} en double : « {ident} ».")
                seen.add(ident)

        # Méthodes : 1 principale, au plus 1 correction, 2 alternatives, 4 au total.
        roles = Counter(m.role for m in self.methods)
        if roles["method"] != 1:
            add(("methods",), "Il faut exactement une méthode principale (`role: method`).")
        if roles["correction"] > 1:
            add(("methods",), "Une seule correction (`role: correction`) au plus.")
        if roles["alternative"] > 2:
            add(("methods",), "Deux alternatives (`role: alternative`) au plus.")
        if len(self.methods) > MAX_METHODS:
            add(("methods",), f"{MAX_METHODS} méthodes au plus.")
        unique(("methods",), [m.id for m in self.methods], "méthode")
        for i, method in enumerate(self.methods):
            for j, name in enumerate(method.repairs):
                if name not in self.hypotheses:
                    add(("methods", i, "repairs", j), f"Hypothèse inconnue : « {name} ».")

        # Mesures : une seule primaire.
        primaries = [k for k, m in self.measures.items() if m.primary]
        if len(primaries) != 1:
            add(("measures",), "Il faut exactement une mesure `primary: true`.")

        # Équation : chaque terme est cité par au moins une hypothèse.
        cited = {t for h in self.hypotheses.values() for t in h.affects}
        for name, hyp in self.hypotheses.items():
            for j, term in enumerate(hyp.affects):
                if term not in self.equation.terms:
                    add(("hypotheses", name, "affects", j), f"Terme d'équation inconnu : « {term} ».")
        for term in self.equation.terms:
            if term not in cited:
                add(("equation", "terms", term), f"Aucune hypothèse ne cite le terme « {term} » (`affects`).")

        # Taille d'échantillon bornée.
        if isinstance(self.generator, RandomGenerator) and isinstance(self.generator.n, str):
            m = re.fullmatch(r"p\.(\w+)", self.generator.n.strip())
            if m:
                param = self.params.get(m.group(1))
                if param is None:
                    add(("generator", "n"), f"Paramètre inconnu : « {m.group(1)} ».")
                elif param.max is not None and param.max > MAX_N:
                    add(("params", m.group(1), "max"), f"La taille d'échantillon est limitée à {MAX_N}.")

        # États (contre-exemples, questions) et axes de balayage.
        def check_state(loc: tuple[str | int, ...], state: State | None) -> None:
            if state is None:
                return
            for name, value in state.params.items():
                param = self.params.get(name)
                if param is None:
                    add((*loc, "params", name), f"Paramètre inconnu : « {name} ».")
                elif isinstance(value, str):
                    if not _PLACEHOLDER.fullmatch(value):
                        add((*loc, "params", name), "Un nombre, un booléen ou {nom} est attendu.")
                elif param.type == "boolean" and not isinstance(value, bool):
                    add((*loc, "params", name), "Ce paramètre est booléen.")
                elif param.type == "number" and (
                    isinstance(value, bool) or not param.min <= value <= param.max
                ):
                    add((*loc, "params", name), f"Valeur hors de [{param.min}, {param.max}].")
            for name, value in state.hypotheses.items():
                hyp = self.hypotheses.get(name)
                if hyp is None:
                    add((*loc, "hypotheses", name), f"Hypothèse inconnue : « {name} ».")
                elif isinstance(value, str) and _PLACEHOLDER.fullmatch(value):
                    continue
                elif hyp.type == "choice":
                    if value not in hyp.options:
                        add((*loc, "hypotheses", name), f"Option inconnue : « {value} ».")
                elif hyp.type == "boolean":
                    if not isinstance(value, bool):
                        add((*loc, "hypotheses", name), "Cette hypothèse est booléenne.")
                elif isinstance(value, bool | str) or not hyp.range[0] <= value <= hyp.range[1]:
                    add((*loc, "hypotheses", name), f"Valeur hors de {list(hyp.range)}.")

        def check_axis(loc: tuple[str | int, ...], axis: str) -> None:
            kind, name = axis.split(".", 1)
            if kind == "h":
                if name not in self.hypotheses:
                    add(loc, f"Hypothèse inconnue : « {name} ».")
            elif name not in self.params:
                add(loc, f"Paramètre inconnu : « {name} ».")
            elif self.params[name].type == "number" and not self.params[name].sweep_values:
                add(loc, f"Le paramètre « {name} » n'est pas balayable (pas de `sweep_values`).")

        for i, ce in enumerate(self.counterexamples):
            check_state(("counterexamples", i, "state"), ce.state)
        unique(("counterexamples",), [c.id for c in self.counterexamples], "contre-exemple")
        unique(("challenges",), [c.id for c in self.challenges], "défi")
        unique(("views",), [v.id for v in self.views], "vue")
        unique(("questions",), [q.id for q in self.questions], "question")
        for i, axis in enumerate(self.auto_sweep):
            check_axis(("auto_sweep", i), axis)

        # Vues : axes, calques.
        view_ids = {v.id for v in self.views}
        for i, view in enumerate(self.views):
            if view.sweep:
                for j, axis in enumerate(view.sweep.axes):
                    check_axis(("views", i, "sweep", "axes", j), axis)
            layer_ids = [layer.id for layer in view.layers or []]
            unique(("views", i, "layers"), layer_ids, "calque")
            for ref in _layer_refs(view.bind):
                if ref not in layer_ids:
                    add(("views", i, "bind"), f"Calque inconnu : « {ref} » (absent de `layers`).")

        # Questions.
        for i, q in enumerate(self.questions):
            here = ("questions", i)
            if isinstance(q, Misconception):
                if q.hypothesis not in self.hypotheses:
                    add((*here, "hypothesis"), f"Hypothèse inconnue : « {q.hypothesis} ».")
                for j, choice in enumerate(q.choices):
                    check_state((*here, "choices", j, "reveal_state"), choice.reveal_state)
                    if choice.focus_view not in view_ids:
                        add((*here, "choices", j, "focus_view"), f"Vue inconnue : « {choice.focus_view} ».")
            elif isinstance(q, DiagnosticAuto):
                if q.view not in view_ids:
                    add((*here, "view"), f"Vue inconnue : « {q.view} ».")
                check_state((*here, "state"), q.state)
                for j, path in enumerate(q.pathologies.from_):
                    name, _, option = path.partition(".")
                    hyp = self.hypotheses.get(name)
                    if hyp is None:
                        add((*here, "pathologies", "from", j), f"Hypothèse inconnue : « {name} ».")
                    elif option and (hyp.options is None or option not in hyp.options):
                        add((*here, "pathologies", "from", j), f"Option inconnue : « {option} ».")
            else:
                check_state((*here, "state"), q.state)
                check_axis((*here, "sweep", "target"), q.sweep.target)
                if q.measure not in self.measures:
                    add((*here, "measure"), f"Mesure inconnue : « {q.measure} ».")
        if self.opening_question and self.opening_question not in {q.id for q in self.questions}:
            add(("opening_question",), f"Question inconnue : « {self.opening_question} ».")

        if issues:
            raise SpecIssues(issues)
        return self
