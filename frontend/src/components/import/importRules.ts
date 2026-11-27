/**
 * importRules.ts : règles de l'écran Import (R4). Logique pure, testée dans importRules.test.ts.
 *
 * Cahier, section « Créer une expérience sans payer d'API » : prompt à copier, éditeur avec validation
 * ligne par ligne, prévisualisation. La validation passe par `POST /api/validate` (P1, R1) ; tant que cette
 * route n'existe pas, `POST /api/run` avec `raw_content` sert de repli : il renvoie les mêmes erreurs du
 * chargeur, ligne par ligne (code 422), mais pas les tests scientifiques.
 */

import { ApiError } from '../../lib/executor'
import type { EngineState, RunResult, ValidateIssue, ValidateResponse } from '../../lib/types.gen'

/** Plafond du moteur (`MAX_YAML_CHARS` de backend/contracts.py). */
export const MAX_YAML_CHARS = 64 * 1024

/** Message bloquant avant tout appel au moteur, ou null si le texte peut partir. */
export function inputProblem(text: string): string | null {
  if (text.trim() === '') return 'Collez ou déposez un fichier YAML.'
  if (text.length > MAX_YAML_CHARS) {
    return `Le fichier fait ${Math.ceil(text.length / 1024)} Ko : le moteur en accepte 64 au plus.`
  }
  return null
}

/** Le fichier déposé ressemble-t-il à un YAML ? (extension, sinon type MIME texte) */
export function looksLikeYaml(name: string, type: string): boolean {
  return /\.ya?ml$/i.test(name) || type.startsWith('text/') || type === 'application/x-yaml'
}

/**
 * Erreurs du chargeur portées par une réponse 422 de `/api/run` :
 * `{ detail: { message, issues: [{ line, path, message }] } }`. null si l'erreur est d'une autre nature.
 */
export function issuesFromError(err: unknown): ValidateIssue[] | null {
  if (!(err instanceof ApiError) || err.status !== 422) return null
  const detail = (err.detail as { detail?: { issues?: unknown } } | null)?.detail
  if (!detail || !Array.isArray(detail.issues)) return null
  return detail.issues
    .filter((i): i is Record<string, unknown> => typeof i === 'object' && i !== null)
    .map((i) => ({
      line: typeof i.line === 'number' ? i.line : null,
      path: typeof i.path === 'string' ? i.path : '',
      message: typeof i.message === 'string' ? i.message : 'Erreur inconnue.',
    }))
}

/** Erreur de syntaxe YAML : le parseur la repère parfois une ligne plus bas que la vraie faute. */
export function isSyntaxIssue(issue: ValidateIssue): boolean {
  return issue.message.startsWith('YAML invalide')
}

/** « Ligne 38 », « Vers la ligne 61 » (syntaxe), « Fichier entier ». */
export function issuePlace(issue: ValidateIssue): string {
  if (issue.line === null) return 'Fichier entier'
  return isSyntaxIssue(issue) ? `Vers la ligne ${issue.line}` : `Ligne ${issue.line}`
}

/** Erreurs triées par numéro de ligne (celles sans ligne en premier). */
export function sortIssues(issues: readonly ValidateIssue[]): ValidateIssue[] {
  return [...issues].sort((a, b) => (a.line ?? 0) - (b.line ?? 0))
}

/** Début et fin (en caractères) de la ligne `line` (à partir de 1), pour la sélectionner dans l'éditeur. */
export function lineRange(text: string, line: number): [number, number] {
  const lines = text.split('\n')
  const target = Math.min(Math.max(1, line), lines.length)
  let start = 0
  for (let i = 0; i < target - 1; i++) start += lines[i].length + 1
  return [start, start + lines[target - 1].length]
}

/** Nombre de lignes du texte (au moins 1), pour la gouttière de l'éditeur. */
export function lineCount(text: string): number {
  return text.split('\n').length
}

/** Résultat de la validation affiché par l'écran. */
export interface ImportCheck {
  /** `validate` : vraie route P1 ; `run` : repli sur `/api/run` (pas de tests scientifiques). */
  mode: 'validate' | 'run'
  ok: boolean
  errors: ValidateIssue[]
  warnings: ValidateIssue[]
  tests: ValidateResponse['tests']
  /** Mesures de l'état par défaut, pour la prévisualisation (null si le YAML est refusé). */
  preview: RunResult | null
}

/** Réponse de la route manquante : 404 (route inconnue) ou 405 (méthode refusée). */
export function isMissingRoute(err: unknown): boolean {
  return err instanceof ApiError && (err.status === 404 || err.status === 405)
}

/** Le prompt à copier dans un assistant IA externe : aucun appel IA depuis l'application. */
export const IMPORT_PROMPT = `Vous allez écrire une expérience pour Crash-Test, une application de révision où la correction est une simulation : on casse une hypothèse d'un théorème, on mesure ce qui cède, puis on applique une correction.

Répondez uniquement par un fichier YAML, sans texte autour. Règles :
- Toutes les chaînes de texte entre guillemets, en français, au vouvoiement.
- Clés de premier niveau : schema_version (1), id, title, discipline, level (« 1 » Découverte, « 2 » Intermédiaire, « 3 » Avancé), concepts, theorem, equation, params, hypotheses, counterexamples, generator, methods, measures, challenges, auto_sweep, views, questions.
- Hypothèses : type continuous, choice ou boolean ; healthy_value obligatoire ; label, category, why, when_broken, statement_tex, affects (termes de l'équation). Une option de choix porte label et law: (normal, uniform, exponential, student_2, cauchy, bimodal) ou expr:.
- Paramètres : type number ou boolean, label, default ; pour un nombre min, max, step, et sweep_values pour le balayer.
- Expressions : p.<id> pour un paramètre, h.<id> pour une hypothèse, noms nus pour les variables du générateur, @h.<id> pour la loi ou l'expression de l'option choisie. Fonctions permises : sqrt, exp, log, abs, where, normal(), uniform(), bernoulli(), law(nom), ar1(base, rho), idx. Pas de boucle.
- Méthodes : exactement une role: method, au plus une role: correction et deux role: alternative ; chaque correction et alternative a un explain et la liste repairs des hypothèses qu'elle répare. Appels existants : ols_ci, clt_mean, ols_two, pairwise_tests, statistic, classifier, regressor.
- Mesures : agg (rate, mean, bias, rmse, sd, var, median, quantile, first, summary, kurtosis), label, une seule primary: true, target, direction (below, above, both), ok_within, broken_beyond, et texts { ok, warning, broken } avec {value}, jamais un chiffre écrit en dur.
- Au moins 3 questions de type misconception, chaque choix avec reveal_state, verify, focus_view et explain.
- Plafonds : repeat ≤ 1000, n ≤ 5000, 4 méthodes, 30 variables, expressions ≤ 300 caractères, fichier ≤ 64 Ko.

Exemple valide (somme de dés et théorème central limite), raccourci à une seule question : suivez sa forme, mais écrivez-en au moins trois.

schema_version: 1
id: "somme-de-des"
title: "Somme de dés : quand la cloche apparaît-elle ?"
discipline: "probabilites"
level: "1"
concepts: ["somme-de-variables", "theoreme-central-limite", "independance"]
theorem:
  name: "Somme de dés et théorème central limite"
  statement: |
    On lance k dés indépendants et on additionne les faces. Dès quelques dés, l'histogramme
    des sommes prend la forme d'une cloche. Il faut que les dés soient indépendants.
equation:
  tex: '{{somme}} \\;\\approx\\; \\mathcal{N}\\!\\left(3{,}5\\,k,\\ \\tfrac{35}{12}\\,k\\right)'
  terms:
    somme:
      ok: 'S_k = X_1 + X_2 + \\cdots + X_k'
params:
  k: { type: number, label: "Nombre de dés k", min: 1, max: 30, step: 1, default: 10,
       sweep_values: [1, 2, 3, 5, 10, 20, 30] }
hypotheses:
  dependance:
    type: continuous
    range: [0, 0.95]
    step: 0.05
    healthy_value: 0.0
    label: "Dés lancés indépendamment"
    category: "independance"
    ok_label: "Indépendants"
    broken_label: "Liés (chaque dé copie en partie son voisin)"
    statement_tex: 'X_1, \\ldots, X_k \\ \\text{indépendants}'
    why: "Des dés indépendants se compensent : les sommes se resserrent au centre."
    when_broken: "Des dés qui se copient ne se compensent plus : la somme reste plate."
    affects: [somme]
counterexamples:
  - id: "un-seul-de"
    label: "Un seul dé"
    explain: "Les six faces sont également probables : l'histogramme est plat."
    state: { params: { k: 1 } }
generator:
  type: random
  n: p.k
  repeat: 1000
  variables:
    z: { expr: "ar1(normal(), h.dependance)" }
    face: { expr: "1 + (z > -0.9674) + (z > -0.4307) + (z > 0) + (z > 0.4307) + (z > 0.9674)" }
methods:
  - id: somme
    role: method
    call: statistic
    label: "Somme des faces"
    args: { x: face, kind: "sum", continuity: true }
measures:
  aplatissement:
    agg: "kurtosis(reps.stat)"
    label: "Aplatissement (0 pour une cloche)"
    decimals: 2
    primary: true
    target: 0
    direction: both
    ok_within: 0.30
    broken_beyond: 0.50
    texts:
      ok: "Forme en cloche : aplatissement de {value}."
      warning: "Presque une cloche : aplatissement de {value}."
      broken: "Pas encore une cloche : aplatissement de {value}."
challenges:
  - id: "peu-de-des"
    goal: "Trouvez le plus petit nombre de dés qui donne déjà une cloche."
    when: "p.k <= 5 and s.aplatissement == 'ok'"
    unlock: "La cloche apparaît très vite : quelques dés suffisent."
auto_sweep: [p.k]
views:
  - id: sommes
    type: distribution
    title: "1000 lancers : la somme des dés"
    bind: { stat: reps.stat }
  - id: sens-k
    type: sensitivity
    title: "Selon le nombre de dés"
    sweep: { axes: [p.k] }
questions:
  - id: "des-q1-lies"
    type: misconception
    prompt: "Les dés sont reliés par un fil. Avec {k} dés, obtient-on une cloche ?"
    hypothesis: "dependance"
    procedural_params:
      k: { min: 10, max: 15, step: 5 }
    choices:
      - id: "a"
        label: "Oui : avec assez de dés, on obtient toujours une cloche."
        correct: false
        reveal_state: { params: { k: "{k}" }, hypotheses: { dependance: 0.9 } }
        verify: "s.aplatissement == 'broken'"
        focus_view: "sommes"
        explain: "L'histogramme reste plat : des dés qui se copient ne se compensent plus."
      - id: "b"
        label: "Non : des dés qui se copient ne se compensent plus."
        correct: true
        reveal_state: { params: { k: "{k}" }, hypotheses: { dependance: 0.9 } }
        verify: "s.aplatissement == 'broken'"
        focus_view: "sommes"
        explain: "Exact : sans indépendance, ajouter des dés ne crée pas de cloche."

Le théorème que je veux : `

/** Le YAML d'exemple contenu dans le prompt (sert aussi de « Charger l'exemple »). */
export function promptExample(): string {
  const start = IMPORT_PROMPT.indexOf('schema_version: 1')
  const end = IMPORT_PROMPT.indexOf('\n\nLe théorème que je veux')
  return IMPORT_PROMPT.slice(start, end) + '\n'
}

/** Les deux appels utiles du client API (injectables pour les tests). */
export interface ImportApi {
  validate(req: { raw_content: string }): Promise<ValidateResponse>
  run(req: { experiment_id: null; raw_content: string; state: EngineState }): Promise<RunResult>
}

/** État par défaut envoyé pour la prévisualisation : le moteur complète paramètres et hypothèses. */
export const PREVIEW_STATE: EngineState = { params: {}, hypotheses: {}, extra_points: [], seed: 42 }

async function previewOf(client: ImportApi, text: string): Promise<RunResult> {
  return client.run({ experiment_id: null, raw_content: text, state: PREVIEW_STATE })
}

/**
 * Valide le YAML et prépare la prévisualisation. `/api/validate` d'abord ; si la route n'existe pas encore,
 * repli sur `/api/run` (erreurs du chargeur seulement). Les autres erreurs (moteur injoignable…) remontent.
 */
export async function checkYaml(client: ImportApi, text: string): Promise<ImportCheck> {
  try {
    const v = await client.validate({ raw_content: text })
    let preview: RunResult | null = null
    if (v.ok) preview = await previewOf(client, text).catch(() => null)
    return { mode: 'validate', ok: v.ok, errors: sortIssues(v.errors), warnings: sortIssues(v.warnings), tests: v.tests, preview }
  } catch (err) {
    if (!isMissingRoute(err)) throw err
  }
  try {
    const preview = await previewOf(client, text)
    return { mode: 'run', ok: true, errors: [], warnings: [], tests: [], preview }
  } catch (err) {
    const issues = issuesFromError(err)
    if (issues === null) throw err
    return { mode: 'run', ok: false, errors: sortIssues(issues), warnings: [], tests: [], preview: null }
  }
}
