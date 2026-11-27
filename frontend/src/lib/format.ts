/**
 * format.ts : mise en forme française des nombres et des mesures (R3).
 * Virgule décimale, espace insécable avant « % ». La valeur reçue du moteur est brute : on applique
 * `scale` (100 pour un pourcentage) et `decimals` de la mesure.
 */

import type { MeasureResult } from './types.gen'

export type MeasureFmt = Pick<MeasureResult, 'unit' | 'scale' | 'decimals'>

const NBSP = ' '

/** Nombre en français, avec un nombre fixe de décimales. */
export function frNumber(value: number, decimals = 2): string {
  return value.toFixed(Math.max(0, decimals)).replace('-', '−').replace('.', ',')
}

/** Unité accolée à la valeur (« 79,6 % », « 0,004 », « 3,2 s »). */
function withUnit(text: string, unit: string): string {
  if (!unit) return text
  return `${text}${NBSP}${unit}`
}

/** Valeur d'une mesure (« 79,6 % »), « — » si la valeur manque (NaN ou Infinity côté moteur). */
export function formatMeasure(value: number | null | undefined, m: MeasureFmt): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return withUnit(frNumber(value * m.scale, m.decimals), m.unit)
}

/** Marge du hasard affichée : ± 2 erreurs Monte Carlo (« ± 3,6 »), null si l'erreur n'existe pas. */
export function formatMargin(mcSe: number | null | undefined, m: MeasureFmt): string | null {
  if (typeof mcSe !== 'number' || !Number.isFinite(mcSe) || mcSe <= 0) return null
  return `±${NBSP}${frNumber(2 * mcSe * m.scale, m.decimals)}`
}

/** Valeur d'un contrôle (curseur), sans unité : « 0,85 », « 150 ». */
export function formatControl(value: number, step: number | null | undefined): string {
  const decimals = step && step < 1 ? Math.min(6, Math.ceil(-Math.log10(step) - 1e-9)) : 0
  return frNumber(value, decimals)
}
