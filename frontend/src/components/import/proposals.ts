/**
 * proposals.ts : seuils proposés par POST /api/validate (R4, écran Import).
 *
 * Le contrat de ValidateResponse est figé : le moteur (backend/engine/validate.py, `_proposals`) range ses
 * propositions dans `warnings`, avec un format stable : chemin `measures.<id>` et message
 * « Seuils proposés : ok_within = <x> ; broken_beyond = <y> (fichier : ok_within = <a> ; broken_beyond = <b>). »
 * (la partie broken_beyond proposée peut manquer). On les sépare des vrais avertissements pour les afficher
 * comme une aide, pas comme un problème.
 */

import type { ValidateIssue } from '../../lib/types.gen'

export interface ThresholdProposal {
  /** Identifiant de la mesure (`measures.<id>`). */
  measure: string
  line: number | null
  ok: number
  /** null : pas de broken_beyond proposé (voir `reason`). */
  broken: number | null
  /** Pourquoi il manque un broken_beyond (texte du moteur), null s'il est proposé. */
  reason: string | null
  /** Valeurs actuelles du fichier (null si le message ne les donne pas). */
  fileOk: number | null
  fileBroken: number | null
}

const PREFIX = 'Seuils proposés :'
const NUMBER = '(-?[0-9.]+(?:e[-+]?[0-9]+)?)'

export function isProposal(issue: ValidateIssue): boolean {
  return issue.message.startsWith(PREFIX)
}

function num(text: string | undefined): number | null {
  if (text === undefined) return null
  const v = Number(text)
  return Number.isFinite(v) ? v : null
}

/** Lit une proposition ; null si le message n'a pas le format attendu (il reste alors un avertissement). */
export function parseProposal(issue: ValidateIssue): ThresholdProposal | null {
  if (!isProposal(issue)) return null
  const [proposed, file = ''] = issue.message.slice(PREFIX.length).split('(fichier :')
  const ok = num(proposed.match(new RegExp(`ok_within = ${NUMBER}`))?.[1])
  if (ok === null) return null
  return {
    measure: issue.path.replace(/^measures\./, '') || '?',
    line: issue.line,
    ok,
    broken: num(proposed.match(new RegExp(`broken_beyond = ${NUMBER}`))?.[1]),
    reason: proposed.match(/\(pas de broken_beyond proposé : ([^)]*)\)/)?.[1] ?? null,
    fileOk: num(file.match(new RegExp(`ok_within = ${NUMBER}`))?.[1]),
    fileBroken: num(file.match(new RegExp(`broken_beyond = ${NUMBER}`))?.[1]),
  }
}

/** Sépare les propositions lisibles des vrais avertissements (une proposition illisible reste un avertissement). */
export function splitWarnings(warnings: readonly ValidateIssue[]): {
  proposals: ThresholdProposal[]
  others: ValidateIssue[]
} {
  const proposals: ThresholdProposal[] = []
  const others: ValidateIssue[] = []
  for (const w of warnings) {
    const p = parseProposal(w)
    if (p) proposals.push(p)
    else others.push(w)
  }
  return { proposals, others }
}

/** Nombre à la française (« 0,035 »), « — » s'il manque. */
export function frThreshold(value: number | null): string {
  if (value === null) return '—'
  return String(value).replace('.', ',').replace('-', '−')
}
