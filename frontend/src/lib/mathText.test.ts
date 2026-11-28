import { describe, expect, it } from 'vitest'
import { exponentTex, splitPowers, splitRich } from './mathText'

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

const kinds = (text: string) => splitRich(text).map((p) => (p.kind === 'text' ? p.value : `[${p.display ? 'D:' : ''}${p.tex}]`))

describe('formules entre dollars dans les textes de contenu', () => {
  it('en ligne, avec le texte autour inchangé', () => {
    expect(kinds('Si $f_n \\to f$ presque partout, alors $\\int f_n$ converge.')).toEqual([
      'Si ', '[f_n \\to f]', ' presque partout, alors ', '[\\int f_n]', ' converge.',
    ])
  })
  it('centrée avec $$…$$', () => {
    expect(kinds('Énoncé : $$\\lim_n \\int f_n = \\int f$$ pour tout n.')).toEqual([
      'Énoncé : ', '[D:\\lim_n \\int f_n = \\int f]', ' pour tout n.',
    ])
  })
  it('un dollar échappé ou un prix n’est pas une formule', () => {
    expect(kinds('Coûte 5 \\$ et 6 \\$ en tout.')).toEqual(['Coûte 5 $ et 6 $ en tout.'])
    expect(kinds('De 5 $ à 6 $ seulement.')).toEqual(['De 5 $ à 6 $ seulement.'])
    expect(kinds('Un seul $ dans ce texte.')).toEqual(['Un seul $ dans ce texte.'])
    expect(kinds('Prix : $5 et $6.')).toEqual(['Prix : $5 et $6.'])
  })
  it('les puissances de dix hors formule sont rendues aussi', () => {
    const parts = splitRich('erreur de 10^−4 pour $x^2$')
    expect(parts.filter((p) => p.kind === 'tex').map((p) => (p as { tex: string }).tex)).toEqual(['10^{-4}', 'x^2'])
  })
  it('plusieurs lignes : une formule en ligne ne s’étend pas sur un saut de ligne', () => {
    expect(kinds('a $b\nc$ d')).toEqual(['a $b\nc$ d'])
  })
  it('un texte sans dollar reste tel quel, une chaîne vide ne donne rien', () => {
    expect(kinds('Aucune formule ici.')).toEqual(['Aucune formule ici.'])
    expect(splitRich('')).toEqual([])
  })
  it('le texte hostile reste une chaîne LaTeX confiée à KaTeX en mode sûr, jamais du HTML', () => {
    const parts = splitRich('$\\href{javascript:alert(1)}{clic}$ <img src=x onerror=alert(1)>')
    expect(parts[0]).toMatchObject({ kind: 'tex' })
    expect(parts[1]).toMatchObject({ kind: 'text', value: ' <img src=x onerror=alert(1)>' }) // texte : Svelte l'échappe
  })
})
