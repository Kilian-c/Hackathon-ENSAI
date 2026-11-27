import { describe, expect, it } from 'vitest'
import { frThreshold, parseProposal, splitWarnings } from './proposals'

// Messages copiés de réponses réelles de POST /api/validate (régression linéaire, tests multiples).
const coverage = {
  line: 142,
  path: 'measures.coverage',
  message:
    'Seuils proposés : ok_within = 0.035 ; broken_beyond = 0.086 (fichier : ok_within = 0.03 ; broken_beyond = 0.1).',
}
const lonely = {
  line: 80,
  path: 'measures.false_alarm',
  message:
    'Seuils proposés : ok_within = 0.028 (aucune perturbation du fichier ne la dépasse : pas de broken_beyond proposé) (fichier : ok_within = 0.025 ; broken_beyond = 0.1).',
}
const realWarning = { line: null, path: 'questions', message: 'Moins de 3 questions : en ajouter.' }

describe('Import : seuils proposés', () => {
  it('lit une proposition complète', () => {
    expect(parseProposal(coverage)).toEqual({
      measure: 'coverage',
      line: 142,
      ok: 0.035,
      broken: 0.086,
      fileOk: 0.03,
      fileBroken: 0.1,
    })
  })

  it('lit une proposition sans broken_beyond (la valeur du fichier ne compte pas comme proposée)', () => {
    expect(parseProposal(lonely)).toMatchObject({ measure: 'false_alarm', ok: 0.028, broken: null, fileOk: 0.025, fileBroken: 0.1 })
  })

  it('accepte la notation scientifique de Python (format :g)', () => {
    const tiny = { line: 3, path: 'measures.m', message: 'Seuils proposés : ok_within = 1.2e-05 ; broken_beyond = 3e-05 (fichier : ok_within = 0.001 ; broken_beyond = 0.01).' }
    expect(parseProposal(tiny)).toMatchObject({ ok: 1.2e-5, broken: 3e-5 })
  })

  it('sépare les propositions des vrais avertissements ; un message illisible reste un avertissement', () => {
    const broken = { line: 1, path: 'measures.x', message: 'Seuils proposés : format inattendu' }
    const { proposals, others } = splitWarnings([coverage, realWarning, lonely, broken])
    expect(proposals.map((p) => p.measure)).toEqual(['coverage', 'false_alarm'])
    expect(others).toEqual([realWarning, broken])
  })

  it('écrit les seuils à la française', () => {
    expect(frThreshold(0.035)).toBe('0,035')
    expect(frThreshold(null)).toBe('—')
  })
})
