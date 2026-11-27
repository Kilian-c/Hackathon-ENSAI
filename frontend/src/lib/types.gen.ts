/**
 * FICHIER GÉNÉRÉ par scripts/gen_types.sh depuis backend/contracts.py et backend/engine/schema.py.
 * Ne pas modifier à la main : modifiez le contrat Python, puis relancez « bash scripts/gen_types.sh ».
 */

export interface Schema {
  [k: string]: unknown;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Challenge".
 */
export interface Challenge {
  goal: string;
  hint: string | null;
  id: string;
  unlock: string;
  when: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ChallengeResult".
 */
export interface ChallengeResult {
  id: string;
  passed: boolean;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Choice".
 */
export interface Choice {
  correct: boolean;
  explain: string;
  focus_view: string;
  id: string;
  label: string;
  reveal_state: State;
  verify: string;
}
/**
 * Un état partiel : ce qui n'est pas cité prend sa valeur saine ou son défaut.
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "State".
 */
export interface State {
  hypotheses: {
    /**
     * This interface was referenced by `undefined`'s JSON-Schema definition
     * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
     */
    [k: string]: boolean | number | string;
  };
  params: {
    /**
     * This interface was referenced by `undefined`'s JSON-Schema definition
     * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
     */
    [k: string]: boolean | number | string;
  };
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Confidence".
 */
export interface Confidence {
  fair: number;
  guess: number;
  sure: number;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Counterexample".
 */
export interface Counterexample {
  expect: "same_summary" | null;
  explain: string;
  id: string;
  label: string;
  state: State;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "CriticalPoint".
 */
export interface CriticalPoint {
  broken_at: number | null;
  warning_at: number | null;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "DiagnosticAuto".
 */
export interface DiagnosticAuto {
  id: string;
  pathologies: Pathologies;
  procedural_params: {
    [k: string]: ProcParam;
  };
  prompt: string;
  state: State | null;
  type: "diagnostic_auto";
  view: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Pathologies".
 */
export interface Pathologies {
  /**
   * @minItems 1
   */
  from: [string, ...string[]];
}
/**
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ProcParam".
 */
export interface ProcParam {
  max: number;
  min: number;
  step: number;
}
/**
 * Test du premier échantillon (répétition 0) de la méthode principale.
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "DrawLog".
 */
export interface DrawLog {
  pvalue: number | null;
  reject: boolean | null;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "DroppedQuestion".
 */
export interface DroppedQuestion {
  experiment_id: string;
  question_id: string;
  reason: string;
}
/**
 * Ce que le moteur reçoit : tout ce qui change le calcul (et rien de l'affichage).
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "EngineState".
 */
export interface EngineState {
  /**
   * @maxItems 20
   */
  extra_points: {
    [k: string]: number;
  }[];
  hypotheses: {
    [k: string]: number | boolean | string;
  };
  params: {
    [k: string]: number | boolean;
  };
  seed: number;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Equation".
 */
export interface Equation {
  terms: {
    [k: string]: EquationTerm;
  };
  tex: string;
}
/**
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "EquationTerm".
 */
export interface EquationTerm {
  corrected: string | null;
  ok: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "EquationResult".
 */
export interface EquationResult {
  terms: {
    [k: string]: EquationTermResult;
  };
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "EquationTermResult".
 */
export interface EquationTermResult {
  violated_by: string[];
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ExperimentSpec".
 */
export interface ExperimentSpec {
  auto_sweep: string[];
  challenges: Challenge[];
  concepts: string[];
  counterexamples: Counterexample[];
  discipline: string;
  draw_log: {
    [k: string]: unknown;
  } | null;
  equation: Equation;
  generator: RandomGenerator | OdeGenerator | FunctionGenerator;
  hypotheses: {
    [k: string]: Hypothesis;
  };
  id: string;
  level: string;
  measures: {
    [k: string]: Measure;
  };
  /**
   * @minItems 1
   */
  methods: [Method, ...Method[]];
  opening_question: string | null;
  params: {
    [k: string]: Param;
  };
  questions: (Misconception | DiagnosticAuto | Prediction)[];
  schema_version: 1;
  theorem: Theorem;
  title: string;
  /**
   * @minItems 1
   */
  views: [View, ...View[]];
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "RandomGenerator".
 */
export interface RandomGenerator {
  inject: {
    /**
     * This interface was referenced by `undefined`'s JSON-Schema definition
     * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
     */
    [k: string]: string;
  } | null;
  n: number | string;
  repeat: number;
  type: "random";
  variables: {
    [k: string]: Variable;
  };
}
/**
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Variable".
 */
export interface Variable {
  dims: ("sample" | "obs_p") | null;
  expr: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "OdeGenerator".
 */
export interface OdeGenerator {
  derived: {
    /**
     * This interface was referenced by `undefined`'s JSON-Schema definition
     * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
     */
    [k: string]: string;
  } | null;
  rhs: {
    /**
     * This interface was referenced by `undefined`'s JSON-Schema definition
     * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
     */
    [k: string]: string;
  };
  state: {
    /**
     * This interface was referenced by `undefined`'s JSON-Schema definition
     * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
     */
    [k: string]: string | number;
  };
  t_end: string | number;
  type: "ode";
}
/**
 * P2 : le format seulement.
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "FunctionGenerator".
 */
export interface FunctionGenerator {
  grid: {
    [k: string]: unknown;
  };
  type: "function";
  variables: {
    [k: string]: unknown;
  };
}
/**
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Hypothesis".
 */
export interface Hypothesis {
  affects: string[];
  broken_label: string | null;
  category: string;
  disabled_text: string | null;
  disabled_when: string | null;
  healthy_value: boolean | number | string;
  label: string;
  ok_label: string | null;
  options: {
    [k: string]: Option;
  } | null;
  /**
   * @minItems 2
   * @maxItems 2
   */
  range: [number, number, ...number[]];
  robust_expected: boolean;
  statement_tex: string;
  step: number | null;
  type: "continuous" | "choice" | "boolean";
  when_broken: string;
  why: string;
}
/**
 * Option d'une hypothèse de type `choice` : une loi du registre OU une expression libre.
 *
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Option".
 */
export interface Option {
  expr: string | null;
  label: string;
  law: string | null;
  robust_expected: boolean;
}
/**
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Measure".
 */
export interface Measure {
  agg: string;
  broken_beyond: number | null;
  decimals: number;
  direction: ("below" | "above" | "both") | null;
  label: string;
  ok_within: number | null;
  primary: boolean;
  scale: number;
  target: number | "base" | null;
  texts: MeasureTexts | null;
  unit: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "MeasureTexts".
 */
export interface MeasureTexts {
  broken: string;
  ok: string;
  warning: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Method".
 */
export interface Method {
  args: {
    /**
     * This interface was referenced by `undefined`'s JSON-Schema definition
     * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
     */
    [k: string]: unknown;
  };
  call: string;
  explain: string | null;
  id: string;
  label: string;
  repairs: string[];
  role: "method" | "correction" | "alternative";
}
/**
 * This interface was referenced by `undefined`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z_][A-Za-z0-9_]*$".
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Param".
 */
export interface Param {
  default: boolean | number;
  label: string;
  max: number | null;
  min: number | null;
  step: number | null;
  sweep_values: number[] | null;
  type: "number" | "boolean";
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Misconception".
 */
export interface Misconception {
  /**
   * @minItems 2
   */
  choices: [Choice, Choice, ...Choice[]];
  hypothesis: string;
  id: string;
  procedural_params: {
    [k: string]: ProcParam;
  };
  prompt: string;
  type: "misconception";
}
/**
 * P1 : le format est figé dès maintenant.
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Prediction".
 */
export interface Prediction {
  id: string;
  measure: string;
  procedural_params: {
    [k: string]: ProcParam;
  };
  prompt: string;
  state: State | null;
  sweep: PredictionSweep;
  type: "prediction";
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "PredictionSweep".
 */
export interface PredictionSweep {
  from: number | string;
  target: string;
  to: number | string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Theorem".
 */
export interface Theorem {
  name: string;
  statement: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "View".
 */
export interface View {
  allow_point_injection: boolean;
  axes: {
    [k: string]: unknown;
  } | null;
  bind: {
    [k: string]: unknown;
  } | null;
  id: string;
  inspect: boolean;
  layers: Layer[] | null;
  mode: string | null;
  sweep: ViewSweep | null;
  title: string;
  type: string;
  ui: {
    [k: string]: unknown;
  } | null;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Layer".
 */
export interface Layer {
  id: string;
  label: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ViewSweep".
 */
export interface ViewSweep {
  /**
   * @minItems 1
   * @maxItems 2
   */
  axes: [string, ...string[]];
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ExperimentSummary".
 */
export interface ExperimentSummary {
  concepts: string[];
  discipline: string;
  id: string;
  level: string;
  title: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "MeasureResult".
 */
export interface MeasureResult {
  baseline: {
    [k: string]: number | null;
  };
  broken_beyond: number | null;
  decimals: number;
  direction: ("below" | "above" | "both") | null;
  label: string;
  mc_se: {
    [k: string]: number | null;
  };
  ok_within: number | null;
  primary: boolean;
  scale: number;
  states: {
    [k: string]: "ok" | "warning" | "broken";
  };
  target: number | "base" | null;
  texts: {
    [k: string]: string;
  };
  unit: string;
  values: {
    [k: string]: number | null;
  };
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "MethodInfo".
 */
export interface MethodInfo {
  explain: string | null;
  id: string;
  label: string;
  role: "method" | "correction" | "alternative";
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Reveal".
 */
export interface Reveal {
  focus_view: string | null;
  state: EngineState;
}
/**
 * Expérience officielle (`experiment_id`) OU partagée (`raw_content`, YAML).
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "RunRequest".
 */
export interface RunRequest {
  experiment_id: string | null;
  raw_content: string | null;
  state: EngineState;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "RunResult".
 */
export interface RunResult {
  challenges: ChallengeResult[];
  compute_ms: number;
  draw_log: DrawLog | null;
  equation: EquationResult;
  invalid_rate: {
    [k: string]: number;
  };
  measures: {
    [k: string]: MeasureResult;
  };
  methods: MethodInfo[];
  repeat_used: number;
  schema_version: 1;
  state_hash: string;
  views: ViewResult[];
  warnings: RunWarning[];
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ViewResult".
 */
export interface ViewResult {
  axes: ViewAxes;
  clipped: number;
  id: string;
  mode: ("intervals" | "paths") | null;
  series: Series[];
  shown: number;
  title: string;
  total: number;
  type: string;
  ui: {
    [k: string]: unknown;
  } | null;
}
/**
 * Bornes [min, max] calculées sur la Référence (ou fixées dans le YAML) ; null = automatique.
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ViewAxes".
 */
export interface ViewAxes {
  x: number[] | null;
  y: number[] | null;
}
/**
 * Série prête à dessiner : le moteur a résolu les `bind` du YAML (format proposé par R3, views.ts).
 *
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "Series".
 */
export interface Series {
  high: (number | null)[] | null;
  hit: boolean[] | null;
  id: string;
  label: string;
  layer: string | null;
  low: (number | null)[] | null;
  method: string | null;
  paths: (number | null)[][] | null;
  role:
    | "method"
    | "correction"
    | "alternative_1"
    | "alternative_2"
    | "reference"
    | "truth"
    | "data"
    | "rupture"
    | "injected";
  slot: string;
  value: number | null;
  x: (number | null)[] | null;
  y: (number | null)[] | null;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "RunWarning".
 */
export interface RunWarning {
  code: string;
  text: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "SweepAxis".
 */
export interface SweepAxis {
  labels: string[];
  target: string;
  values: (number | boolean | string)[];
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "SweepAxisRequest".
 */
export interface SweepAxisRequest {
  target: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "SweepRequest".
 */
export interface SweepRequest {
  /**
   * @minItems 1
   * @maxItems 2
   */
  axes: [SweepAxisRequest, ...SweepAxisRequest[]];
  experiment_id: string;
  measure: string | null;
  state: EngineState;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "SweepResult".
 */
export interface SweepResult {
  axes: SweepAxis[];
  broken_beyond: number | null;
  compute_ms: number;
  critical: {
    [k: string]: CriticalPoint | null;
  } | null;
  current: {
    [k: string]: number | boolean | string;
  };
  direction: ("below" | "above" | "both") | null;
  mc_se: {
    [k: string]: (number | null)[] | (number | null)[][];
  };
  measure: string;
  ok_within: number | null;
  reduced: boolean;
  repeat_used: number;
  states: {
    [k: string]: (("ok" | "warning" | "broken") | null)[] | (("ok" | "warning" | "broken") | null)[][];
  };
  target:
    | number
    | {
        [k: string]: number;
      }
    | null;
  values: {
    [k: string]: (number | null)[] | (number | null)[][];
  };
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "TrainingChoice".
 */
export interface TrainingChoice {
  correct: boolean;
  explain: string;
  id: string;
  label: string;
  reveal: Reveal;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "TrainingQuestion".
 */
export interface TrainingQuestion {
  /**
   * @minItems 2
   */
  choices: [TrainingChoice, TrainingChoice, ...TrainingChoice[]];
  confidence: Confidence;
  experiment_id: string;
  hypothesis: string | null;
  initial_view: ViewResult | null;
  k: number;
  prompt: string;
  qid: string;
  type: "misconception" | "diagnostic_auto" | "prediction";
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "TrainingRequest".
 */
export interface TrainingRequest {
  count: number;
  filter: string;
  seed: number | null;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "TrainingSessionResponse".
 */
export interface TrainingSessionResponse {
  content_hash: string;
  dropped: DroppedQuestion[];
  filter: string;
  id: string;
  questions: TrainingQuestion[];
  seed: number;
  stale_link: boolean;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ValidateIssue".
 */
export interface ValidateIssue {
  line: number | null;
  message: string;
  path: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ValidateRequest".
 */
export interface ValidateRequest {
  raw_content: string;
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ValidateResponse".
 */
export interface ValidateResponse {
  errors: ValidateIssue[];
  ok: boolean;
  tests: ValidateTest[];
  warnings: ValidateIssue[];
}
/**
 * This interface was referenced by `Schema`'s JSON-Schema
 * via the `definition` "ValidateTest".
 */
export interface ValidateTest {
  detail: string | null;
  id: number;
  name: string;
  passed: boolean;
}
