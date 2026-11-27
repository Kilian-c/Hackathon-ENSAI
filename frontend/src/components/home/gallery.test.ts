import { describe, expect, it } from 'vitest'
import type { ExperimentSummary } from '../../lib/types.gen'
import {
  EMPTY_FILTER,
  conceptLabel,
  countLabel,
  disciplineLabel,
  disciplinesOf,
  experimentHref,
  filterAndSort,
  isFiltered,
  levelsOf,
  trainHref,
} from './gallery'

const items: ExperimentSummary[] = [
  { id: 'b', title: 'Régression', discipline: 'statistique', level: '3', concepts: ['intervalle de confiance'] },
  { id: 'a', title: 'Somme de dés', discipline: 'probabilites', level: '1', concepts: ['loi uniforme'] },
  { id: 'c', title: 'Théorème central limite', discipline: 'probabilites', level: '2', concepts: ['moyenne'] },
  { id: 'd', title: 'Moyenne ou médiane', discipline: 'statistique', level: '1', concepts: ['robustesse', 'valeur-aberrante'] },
]

const ids = (list: ExperimentSummary[]) => list.map((e) => e.id)

describe('galerie', () => {
  it('trie par niveau puis par titre', () => {
    expect(ids(filterAndSort(items, EMPTY_FILTER))).toEqual(['d', 'a', 'c', 'b'])
  })

  it('trie par titre seul', () => {
    expect(ids(filterAndSort(items, { ...EMPTY_FILTER, sort: 'title' }))).toEqual(['d', 'b', 'a', 'c'])
  })

  it('combine niveau et discipline', () => {
    expect(ids(filterAndSort(items, { ...EMPTY_FILTER, level: '1', discipline: 'statistique' }))).toEqual(['d'])
    expect(filterAndSort(items, { ...EMPTY_FILTER, level: '2', discipline: 'statistique' })).toEqual([])
  })

  it('cherche sans tenir compte des accents ni de la casse, dans les concepts et la discipline', () => {
    expect(ids(filterAndSort(items, { ...EMPTY_FILTER, search: 'THEOREME' }))).toEqual(['c'])
    expect(ids(filterAndSort(items, { ...EMPTY_FILTER, search: 'robust' }))).toEqual(['d'])
    expect(ids(filterAndSort(items, { ...EMPTY_FILTER, search: 'probabilités' }))).toEqual(['a', 'c'])
    expect(ids(filterAndSort(items, { ...EMPTY_FILTER, search: '  somme   dés ' }))).toEqual(['a'])
    expect(ids(filterAndSort(items, { ...EMPTY_FILTER, search: 'valeur aberrante' }))).toEqual(['d'])
  })

  it('ne modifie pas la liste reçue et accepte une liste vide', () => {
    const copy = [...items]
    filterAndSort(items, EMPTY_FILTER)
    expect(items).toEqual(copy)
    expect(filterAndSort([], EMPTY_FILTER)).toEqual([])
  })

  it('liste les disciplines et les niveaux présents', () => {
    expect(disciplinesOf(items)).toEqual(['probabilites', 'statistique'])
    expect(levelsOf(items)).toEqual(['1', '2', '3'])
  })

  it('met en forme les libellés et les liens', () => {
    expect(disciplineLabel('probabilites')).toBe('Probabilités')
    expect(disciplineLabel('physique')).toBe('Physique')
    expect(isFiltered(EMPTY_FILTER)).toBe(false)
    expect(isFiltered({ ...EMPTY_FILTER, search: ' x ' })).toBe(true)
    expect(experimentHref('somme-des')).toBe('?exp=somme-des&v=1')
    expect(trainHref('discipline:statistique')).toBe('?train=discipline%3Astatistique&v=1')
    expect(conceptLabel('moindres-carres')).toBe('moindres carres')
    expect(countLabel(1)).toBe('1 expérience')
    expect(countLabel(9)).toBe('9 expériences')
  })
})
