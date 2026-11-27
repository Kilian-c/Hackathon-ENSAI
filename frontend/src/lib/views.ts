/**
 * views.ts : lecture des vues du moteur (R3).
 *
 * Les TYPES viennent de types.gen.ts (générés depuis backend/contracts.py) : ViewResult, Series,
 * SweepResult... Ce fichier ajoute seulement ce que le contrat laisse libre, à savoir le contenu de
 * `Series.data` selon le type de vue (annexe E du cahier), et des accès typés à ce contenu.
 *
 * Contenu de `Series.data` attendu par l'interface (à garder aligné avec les fixtures de R1) :
 * - points ou ligne (nuage, résidus, courbes) : { x: number[], y: number[] }
 * - intervalles (Répétitions)                 : { est, low, high: number[], hit: boolean[] }
 * - distribution                             : { x: number[] }  (valeurs à mettre en histogramme)
 * - valeur scalaire (vraie valeur, seuil)    : { value: number }
 * Les NaN arrivent en null : toutes les lectures les tolèrent.
 */

import type { MeasureResult, Series, SweepResult, ViewResult } from './types.gen'

export type { Series, SweepResult, ViewResult }

export type Num = number | null
export type Range = [number, number]

/** Mise en forme d'une mesure (sous-ensemble de RunResult.measures.<id>). */
export type MeasureFormat = Pick<MeasureResult, 'label'> & Partial<Pick<MeasureResult, 'unit' | 'scale' | 'decimals'>>

/** Emplacement d'une série, lu dans son identifiant stable `<vue>.<emplacement>.<methode>`. */
export function slotOf(s: Series): string {
  return s.id.split('.')[1] ?? ''
}

/** Tableau numérique d'une série (null pour les valeurs absentes ou non numériques). */
export function nums(s: Series, key: string): Num[] {
  const v = s.data[key]
  return Array.isArray(v) ? v.map((x) => (typeof x === 'number' && Number.isFinite(x) ? x : null)) : []
}

/** Tableau booléen d'une série. */
export function bools(s: Series, key: string): boolean[] {
  const v = s.data[key]
  return Array.isArray(v) ? v.map((x) => x === true) : []
}

/** Valeur scalaire d'une série, ou null. */
export function scalar(s: Series, key = 'value'): Num {
  const v = s.data[key]
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

/** Bornes [min, max] d'un axe de la vue, ou null (automatique). */
export function axisRange(view: ViewResult, axis: 'x' | 'y'): Range | null {
  const r = view.axes?.[axis]
  return r && r.length === 2 ? [r[0], r[1]] : null
}

/**
 * Série de données du générateur (nuage d'observations), commune à toutes les méthodes :
 * pas de méthode d'origine, et ni vraie valeur, ni Référence, ni point ajouté.
 */
export function isGeneratorData(s: Series): boolean {
  return s.method === null && (s.role === 'method' || s.role === 'correction')
}
