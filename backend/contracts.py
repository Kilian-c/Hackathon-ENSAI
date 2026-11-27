"""Contrats de l'API (R1) : requêtes et réponses de `/api/run`, `/api/sweep`, `/api/training/session`.

FICHIER DE CONTRAT : figé au tag `contracts-v1` (H4). `frontend/src/lib/types.gen.ts` en est généré
(`scripts/gen_types.sh`) : pas de type Python exotique ici, uniquement des modèles Pydantic, des
`Literal`, des listes et des dictionnaires. Source : annexe C du cahier, avec les écarts de CLAUDE.md
(une seule route d'Entraînement, `POST` avec `seed` facultative).

Conventions :
- toutes les valeurs d'une mesure sont données **par méthode** (clé = `Method.id`) ;
- NaN et Infinity sortent en `null` (d'où les `float | None`) ;
- une mesure sans cible (informative) n'a ni `target`, ni `direction`, ni seuils, ni `states`, ni `texts` ;
- `target: "base"` : la cible de chaque méthode est sa propre valeur à l'état sain, lue dans `baseline`.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCHEMA_VERSION: Literal[1] = 1
MAX_EXTRA_POINTS = 20
MAX_SWEEP_POINTS = 21
MAX_TRAINING_COUNT = 10
MAX_YAML_CHARS = 64 * 1024

Verdict = Literal["ok", "warning", "broken"]
Direction = Literal["below", "above", "both"]
MethodRole = Literal["method", "correction", "alternative"]
# Rôle d'une série (lib/roles.ts, lib/views.ts) : celui de sa méthode (les alternatives reçoivent leur
# rang dans l'ordre du YAML), ou `reference` (même série à l'état sain), `truth` (vraie valeur, solution
# exacte), `data` (données du générateur, communes à toutes les méthodes), `rupture`, `injected`.
SeriesRole = Literal[
    "method", "correction", "alternative_1", "alternative_2",
    "reference", "truth", "data", "rupture", "injected",
]
# Axe de balayage : `h.<id>` (hypothèse) ou `p.<id>` (paramètre).
Axis = Annotated[str, StringConstraints(pattern=r"^[hp]\.[A-Za-z_][A-Za-z0-9_]*$")]
# Filtre d'Entraînement : `toutes`, un identifiant d'expérience ou `discipline:<nom>`.
TrainingFilter = Annotated[
    str, StringConstraints(pattern=r"^(toutes|[a-z0-9][a-z0-9_-]*|discipline:\S{1,60})$")
]
# Une grille de résultats : 1 axe -> liste ; 2 axes -> liste de listes, indexées [axe 2][axe 1].
Grid = list[float | None] | list[list[float | None]]
VerdictGrid = list[Verdict | None] | list[list[Verdict | None]]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- État de calcul ---------------------------------------------------------------------------------------


class EngineState(Contract):
    """Ce que le moteur reçoit : tout ce qui change le calcul (et rien de l'affichage)."""

    params: dict[str, float | bool] = {}
    hypotheses: dict[str, float | bool | str] = {}
    # Points posés au clic (P1) : un dictionnaire {emplacement: valeur} par point, ex. {"x": 4.2, "y": -2.0}.
    extra_points: list[dict[str, float]] = Field(default=[], max_length=MAX_EXTRA_POINTS)
    seed: int = Field(default=42, ge=0)


# --- GET /api/experiments ---------------------------------------------------------------------------------


class ExperimentSummary(Contract):
    id: str
    title: str
    discipline: str
    level: str
    concepts: list[str]


# --- POST /api/run ----------------------------------------------------------------------------------------


class RunRequest(Contract):
    """Expérience officielle (`experiment_id`) OU partagée (`raw_content`, YAML)."""

    experiment_id: str | None = None
    raw_content: str | None = Field(default=None, max_length=MAX_YAML_CHARS)
    state: EngineState = Field(default_factory=EngineState)

    @model_validator(mode="after")
    def _exactly_one_source(self):
        if (self.experiment_id is None) == (self.raw_content is None):
            raise ValueError("Indiquez soit experiment_id, soit raw_content (exactement un des deux).")
        return self


class MethodInfo(Contract):
    id: str
    role: MethodRole
    label: str
    explain: str | None = None


class MeasureResult(Contract):
    label: str
    unit: str = ""
    scale: float = 1.0
    decimals: int = 2
    primary: bool = False
    # Bloc verdict : absent pour une mesure informative.
    target: float | Literal["base"] | None = None
    direction: Direction | None = None
    ok_within: float | None = None
    broken_beyond: float | None = None
    # Un dictionnaire par mesure, clé = identifiant de méthode.
    values: dict[str, float | None]
    mc_se: dict[str, float | None] = {}  # erreur Monte Carlo ; null quand elle n'existe pas
    states: dict[str, Verdict] = {}
    texts: dict[str, str] = {}
    baseline: dict[str, float | None] = {}  # valeur de la Référence (état sain)


class EquationTermResult(Contract):
    violated_by: list[str]  # hypothèses cassées qui mettent ce terme en cause


class EquationResult(Contract):
    terms: dict[str, EquationTermResult]


class ChallengeResult(Contract):
    id: str
    passed: bool


class Series(Contract):
    """Série prête à dessiner : le moteur a résolu les `bind` du YAML (format proposé par R3, views.ts)."""

    id: str  # stable : <vue>.<emplacement>.<methode>
    slot: str  # emplacement du `bind` : x/y, fit, resid, est, stat, series, truth...
    method: str | None = None  # null pour les données du générateur
    role: SeriesRole
    label: str
    layer: str | None = None  # calque pas à pas (P2)
    x: list[float | None] | None = None
    y: list[float | None] | None = None
    # Vue Répétitions (intervalles) : bornes et succès par répétition ; `x` porte l'estimation.
    low: list[float | None] | None = None
    high: list[float | None] | None = None
    hit: list[bool] | None = None
    value: float | None = None  # scalaire : vraie valeur d'un paramètre, seuil
    paths: list[list[float | None]] | None = None  # Répétitions (trajectoires) : une liste par trajectoire


class ViewAxes(Contract):
    """Bornes [min, max] calculées sur la Référence (ou fixées dans le YAML) ; null = automatique."""

    x: list[float] | None = None
    y: list[float] | None = None


class ViewResult(Contract):
    id: str
    type: str
    title: str
    mode: Literal["intervals", "paths"] | None = None  # vue Répétitions
    axes: ViewAxes = Field(default_factory=ViewAxes)
    shown: int = 0  # ce qui est affiché
    total: int = 0  # ce qui a été calculé
    clipped: int = 0  # points hors cadre
    ui: dict[str, Any] | None = None  # champ libre du YAML, transmis tel quel
    series: list[Series] = []  # vide pour `sensitivity` : l'interface appelle /api/sweep


class DrawLog(Contract):
    """Test du premier échantillon (répétition 0) de la méthode principale."""

    reject: bool | None = None
    pvalue: float | None = None


class RunWarning(Contract):
    code: str  # stable : l'interface peut s'y appuyer
    text: str  # en français


class RunResult(Contract):
    schema_version: Literal[1] = SCHEMA_VERSION
    state_hash: str  # 16 premiers caractères du SHA-256 de l'état canonique
    methods: list[MethodInfo]
    measures: dict[str, MeasureResult]
    equation: EquationResult
    challenges: list[ChallengeResult] = []
    views: list[ViewResult] = []
    draw_log: DrawLog | None = None
    invalid_rate: dict[str, float] = {}
    warnings: list[RunWarning] = []
    repeat_used: int
    compute_ms: float


# --- POST /api/sweep --------------------------------------------------------------------------------------


class SweepAxisRequest(Contract):
    target: Axis


class SweepRequest(Contract):
    experiment_id: str
    state: EngineState = Field(default_factory=EngineState)
    axes: list[SweepAxisRequest] = Field(min_length=1, max_length=2)  # 2 axes : P1
    measure: str | None = None  # défaut : la mesure primaire


class SweepAxis(Contract):
    target: Axis
    values: list[float | bool | str]
    labels: list[str]


class CriticalPoint(Contract):
    warning_at: float | None = None
    broken_at: float | None = None


class SweepResult(Contract):
    axes: list[SweepAxis]
    measure: str
    values: dict[str, Grid]
    mc_se: dict[str, Grid] = {}
    states: dict[str, VerdictGrid] = {}
    # Un seul axe continu : seuil interpolé par méthode (null si jamais franchi). Absent sinon.
    critical: dict[str, CriticalPoint | None] | None = None
    # Bloc verdict de la mesure ; `target` est un dictionnaire par méthode quand la cible est « base ».
    target: float | dict[str, float] | None = None
    ok_within: float | None = None
    broken_beyond: float | None = None
    direction: Direction | None = None
    current: dict[str, float | bool | str]  # {"h.hetero": 0.8, ...} : l'état courant sur les axes
    repeat_used: int
    reduced: bool = False  # repeat réduit pour tenir le délai (P1)
    compute_ms: float


# --- POST /api/training/session ---------------------------------------------------------------------------


class TrainingRequest(Contract):
    filter: TrainingFilter = "toutes"
    count: int = Field(default=MAX_TRAINING_COUNT, ge=1, le=MAX_TRAINING_COUNT)
    seed: int | None = Field(default=None, ge=0)  # absente : le serveur en tire une et la renvoie


class Confidence(Contract):
    guess: float  # Je devine = 1/k
    fair: float  # Plutôt sûr = (1/k + 0,95)/2
    sure: float  # Certain = 0,95


class Reveal(Contract):
    state: EngineState  # état de calcul complet, à envoyer à /api/run pour la validation
    focus_view: str | None = None


class TrainingChoice(Contract):
    id: str
    label: str
    correct: bool
    explain: str
    reveal: Reveal


class TrainingQuestion(Contract):
    qid: str  # <experience>/<question>/<indice>
    experiment_id: str
    type: Literal["misconception", "diagnostic_auto", "prediction"]
    prompt: str
    initial_view: ViewResult | None = None  # vue affichée avec l'énoncé (diagnostic) ; null pour du texte
    hypothesis: str | None = None  # hypothèse expliquée après la réponse
    k: int = Field(ge=2)  # nombre de choix
    confidence: Confidence
    choices: list[TrainingChoice] = Field(min_length=2)  # déjà mélangés


class DroppedQuestion(Contract):
    experiment_id: str
    question_id: str
    reason: str


class TrainingSessionResponse(Contract):
    id: str  # <filtre>~<graine>
    filter: str
    seed: int  # toujours renseignée, même si la requête n'en donnait pas
    content_hash: str  # 6 premiers caractères du hash du contenu des YAML
    stale_link: bool = False  # réservé au lien partagé avec h=<hash6> (P1)
    questions: list[TrainingQuestion]
    dropped: list[DroppedQuestion] = []


# --- POST /api/validate (P1) ------------------------------------------------------------------------------


class ValidateRequest(Contract):
    raw_content: str = Field(max_length=MAX_YAML_CHARS)


class ValidateIssue(Contract):
    line: int | None = None
    path: str = ""
    message: str


class ValidateTest(Contract):
    id: int
    name: str
    passed: bool
    detail: str | None = None


class ValidateResponse(Contract):
    ok: bool
    errors: list[ValidateIssue] = []
    warnings: list[ValidateIssue] = []
    tests: list[ValidateTest] = []
