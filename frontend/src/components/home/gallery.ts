/**
 * gallery.ts : règles de la galerie d'accueil (R4). Logique pure, testée dans gallery.test.ts.
 * Filtres et tri sur la liste du moteur (`ExperimentSummary`), sans aucun cas propre à une expérience.
 */

import { LINK_VERSION } from '../../lib/state'
import type { ExperimentSummary } from '../../lib/types.gen'

export type GallerySort = 'level' | 'title'

export interface GalleryFilter {
  /** Niveau « 1 », « 2 », « 3 », ou null pour tous. */
  level: string | null
  /** Discipline telle que servie par le moteur, ou null pour toutes. */
  discipline: string | null
  /** Recherche libre dans le titre, la discipline et les concepts. */
  search: string
  sort: GallerySort
}

export const EMPTY_FILTER: GalleryFilter = { level: null, discipline: null, search: '', sort: 'level' }

/** Minuscules, sans accents, tirets et espaces réduits à une espace : « Probabilités » et « probabilites » se rejoignent. */
export function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[-_\s]+/g, ' ')
    .trim()
}

const compareFr = (a: string, b: string): number => a.localeCompare(b, 'fr', { sensitivity: 'base' })

/** Disciplines présentes, sans doublon, dans l'ordre alphabétique. */
export function disciplinesOf(items: readonly ExperimentSummary[]): string[] {
  return [...new Set(items.map((e) => e.discipline))].sort(compareFr)
}

/** Niveaux présents, sans doublon, du plus facile au plus difficile. */
export function levelsOf(items: readonly ExperimentSummary[]): string[] {
  return [...new Set(items.map((e) => String(e.level).trim()))].sort(compareLevel)
}

function compareLevel(a: string, b: string): number {
  const na = Number(a)
  const nb = Number(b)
  if (Number.isFinite(na) && Number.isFinite(nb) && na !== nb) return na - nb
  return compareFr(a, b)
}

/** Libellé d'une discipline : quelques accents rétablis, sinon première lettre en majuscule. */
const DISCIPLINES: Record<string, string> = {
  probabilites: 'Probabilités',
  statistique: 'Statistique',
  apprentissage: 'Apprentissage',
}

export function disciplineLabel(discipline: string): string {
  const known = DISCIPLINES[normalize(discipline)]
  if (known) return known
  const text = discipline.trim()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function matches(e: ExperimentSummary, f: GalleryFilter): boolean {
  if (f.level !== null && String(e.level).trim() !== f.level) return false
  if (f.discipline !== null && e.discipline !== f.discipline) return false
  const words = normalize(f.search).split(' ').filter(Boolean)
  if (words.length === 0) return true
  const haystack = normalize([e.title, e.discipline, disciplineLabel(e.discipline), ...e.concepts].join(' '))
  return words.every((w) => haystack.includes(w))
}

/** Expériences retenues par le filtre, triées par niveau puis titre (ou par titre seul). */
export function filterAndSort(items: readonly ExperimentSummary[], f: GalleryFilter): ExperimentSummary[] {
  const kept = items.filter((e) => matches(e, f))
  return kept.sort((a, b) => {
    if (f.sort === 'level') {
      const byLevel = compareLevel(String(a.level).trim(), String(b.level).trim())
      if (byLevel !== 0) return byLevel
    }
    return compareFr(a.title, b.title)
  })
}

/** Le filtre est-il différent du filtre vide (tri mis à part) ? */
export function isFiltered(f: GalleryFilter): boolean {
  return f.level !== null || f.discipline !== null || normalize(f.search) !== ''
}

/** Lien vers le Laboratoire d'une expérience. */
export function experimentHref(id: string): string {
  return `?exp=${encodeURIComponent(id)}&v=${LINK_VERSION}`
}

/** Lien vers une série d'Entraînement : `toutes`, un identifiant ou `discipline:<nom>` (filtre du moteur). */
export function trainHref(filter: string): string {
  return `?train=${encodeURIComponent(filter)}&v=${LINK_VERSION}`
}

/** Notion lisible : le moteur sert un identifiant (« moindres-carres ») ; on remplace les tirets. */
export function conceptLabel(concept: string): string {
  return concept.replace(/[-_]+/g, ' ').trim()
}

/** « 1 expérience », « 9 expériences ». */
export function countLabel(n: number): string {
  return n <= 1 ? `${n} expérience` : `${n} expériences`
}
