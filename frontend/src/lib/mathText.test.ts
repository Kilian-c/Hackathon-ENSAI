import { describe, expect, it } from 'vitest'
import { exponentTex, splitPowers } from './mathText'

describe('puissances de dix dans les textes de mesure', () => {
  it('rend 10^exposant en formule, avec le signe moins typographique et la virgule décimale', () => {
    expect(splitPowers('Solution précise : erreur relative de 10^−13,8.')).toEqual([
      { kind: 'text', value: 'Solution précise : erreur relative de ' },
      { kind: 'tex', tex: '10^{-13{,}8}' },
      { kind: 'text', value: '.' },
    ])
  })
  it('accepte le tiret ASCII, les entiers et les exposants positifs', () => {
    expect(splitPowers('10^-4')).toEqual([{ kind: 'tex', tex: '10^{-4}' }])
    expect(splitPowers('10^16')).toEqual([{ kind: 'tex', tex: '10^{16}' }])
    expect(splitPowers('10^16,0 (échec)')).toEqual([
      { kind: 'tex', tex: '10^{16{,}0}' },
      { kind: 'text', value: ' (échec)' },
    ])
  })
  it('plusieurs puissances dans un même texte', () => {
    const parts = splitPowers('de 10^−9 à 10^−3,5 : ok')
    expect(parts.filter((p) => p.kind === 'tex')).toHaveLength(2)
    expect(parts.map((p) => (p.kind === 'text' ? p.value : p.tex)).join('|')).toBe('de |10^{-9}| à |10^{-3{,}5}| : ok')
  })
  it('un texte sans puissance reste un seul morceau, tel quel', () => {
    expect(splitPowers('Comportement gaussien : 95,0 % entre -1,96 et 1,96.')).toEqual([
      { kind: 'text', value: 'Comportement gaussien : 95,0 % entre -1,96 et 1,96.' },
    ])
    expect(splitPowers('')).toEqual([])
  })
  it('ne touche pas à ce qui ne ressemble pas à une puissance de dix', () => {
    for (const text of ['t^2', '10 puissance 3', '210^3', '0,10^3', 'x^−1', '1 / (1 - rho^2)']) {
      expect(splitPowers(text)).toEqual([{ kind: 'text', value: text }])
    }
  })
  it('seuls des chiffres, un signe et une virgule arrivent jusqu’à KaTeX (aucune injection possible)', () => {
    const hostile = '10^\\href{javascript:alert(1)}{x} et 10^{-1}\\input'
    for (const part of splitPowers(hostile)) {
      if (part.kind === 'tex') expect(part.tex).toMatch(/^10\^\{-?\d+(\{,\}\d+)?\}$/)
    }
  })
  it('exponentTex', () => {
    expect(exponentTex('−13,8')).toBe('-13{,}8')
    expect(exponentTex('4')).toBe('4')
  })
})
