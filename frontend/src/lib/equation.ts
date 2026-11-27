/**
 * equation.ts : règle de couleur des termes de l'équation dynamique (R3).
 * Cahier, section 3.2 (tableau « La règle de couleur d'un terme ») ; CLAUDE.md, section 10.
 *
 * | Situation                                                  | Affichage                 |
 * |------------------------------------------------------------|---------------------------|
 * | aucune hypothèse dans violated_by                          | version saine, neutre     |
 * | hypothèse cassée, méthode principale Fiable                | version saine, neutre     |
 * | hypothèse cassée, méthode principale Fragile ou Rompue     | version saine, rouge      |
 * | idem, Correction affichée et Fiable                        | version corrigée, vert    |
 * | idem, Correction affichée mais pas Fiable                  | version corrigée, rouge   |
 *
 * Le rouge commence au verdict Fragile, donc exactement au seuil critique.
 * Aucun appel au serveur : tout vient de RunResult et de l'état d'affichage (methods_on).
 */

import { cssVar, type MethodRole, type Verdict } from './roles'

// TODO(passation) : remplacer ces types par ceux de types.gen.ts quand il existera (H3 à H4).

/** Bloc `equation` du YAML (ExperimentSpec). */
export interface EquationSpec {
  tex: string
  terms: Record<string, { ok: string; corrected?: string }>
}

/** Bloc `equation` de RunResult. */
export interface EquationResult {
  terms: Record<string, { violated_by: string[] }>
}

/** Ce dont la règle a besoin dans RunResult. */
export interface EquationContext {
  methods: ReadonlyArray<{ id: string; role: MethodRole }>
  /** Verdicts de la mesure primaire, par identifiant de méthode. */
  primaryStates: Readonly<Record<string, Verdict | null | undefined>>
  /** Méthodes affichées (état d'affichage, methods_on). */
  methodsOn: ReadonlySet<string> | ReadonlyArray<string>
}

/**
 * neutral  : version saine, couleur neutre
 * broken   : rouge (version saine, ou version corrigée si la Correction ne suffit pas)
 * repaired : version corrigée, vert
 */
export type TermTone = 'neutral' | 'broken' | 'repaired'

export interface TermDisplay {
  name: string
  tone: TermTone
  /** true : afficher la version corrigée du terme. */
  corrected: boolean
  /** Hypothèses cassées qui mettent ce terme en cause (pour la légende). */
  violatedBy: string[]
}

function isShown(methodsOn: EquationContext['methodsOn'], id: string): boolean {
  return methodsOn instanceof Set ? methodsOn.has(id) : (methodsOn as ReadonlyArray<string>).includes(id)
}

/** Applique la règle de couleur à un terme. Fonction pure. */
export function termDisplay(name: string, violatedBy: readonly string[], ctx: EquationContext): TermDisplay {
  const base = { name, violatedBy: [...violatedBy] }
  if (violatedBy.length === 0) return { ...base, tone: 'neutral', corrected: false }

  const principal = ctx.methods.find((m) => m.role === 'method')
  const principalState = principal ? ctx.primaryStates[principal.id] : undefined
  // Verdict absent (mesure non calculable) : on ne conclut pas, le terme reste neutre.
  if (principalState === 'ok' || principalState == null) return { ...base, tone: 'neutral', corrected: false }

  const correction = ctx.methods.find((m) => m.role === 'correction')
  if (!correction || !isShown(ctx.methodsOn, correction.id)) return { ...base, tone: 'broken', corrected: false }

  const repaired = ctx.primaryStates[correction.id] === 'ok'
  return { ...base, tone: repaired ? 'repaired' : 'broken', corrected: true }
}

/** Applique la règle à tous les termes du gabarit. */
export function equationTerms(spec: EquationSpec, result: EquationResult, ctx: EquationContext): TermDisplay[] {
  return Object.keys(spec.terms).map((name) => termDisplay(name, result.terms[name]?.violated_by ?? [], ctx))
}

export interface ToneColors {
  broken: string
  repaired: string
}

/** Couleurs lues dans tokens.css (rupture, correction). */
export function defaultToneColors(): ToneColors {
  return { broken: cssVar('--ct-role-rupture'), repaired: cssVar('--ct-role-correction') }
}

const PLACEHOLDER = /\{\{\s*([A-Za-z0-9_]+)\s*\}\}/g

/**
 * Fabrique le LaTeX final pour KaTeX : remplace chaque {{terme}} par sa version (saine ou
 * corrigée), colorée selon sa tonalité. Un terme rouge est aussi souligné : la couleur
 * n'est jamais le seul indice.
 */
export function buildEquationTex(
  spec: EquationSpec,
  displays: readonly TermDisplay[],
  colors: ToneColors = defaultToneColors(),
): string {
  const byName = new Map(displays.map((d) => [d.name, d]))
  return spec.tex.replace(PLACEHOLDER, (whole, name: string) => {
    const term = spec.terms[name]
    if (!term) {
      if (import.meta.env.DEV) console.error(`Terme d'équation inconnu dans le gabarit : ${name}`)
      return whole
    }
    const d = byName.get(name)
    const body = d?.corrected && term.corrected ? term.corrected : term.ok
    switch (d?.tone) {
      case 'broken':
        return `{\\textcolor{${colors.broken}}{\\underline{${body}}}}`
      case 'repaired':
        return `{\\textcolor{${colors.repaired}}{${body}}}`
      default:
        return `{${body}}`
    }
  })
}
