import { describe, expect, it } from 'vitest'
import { buildEquationTex, termDisplay, type EquationContext, type EquationSpec } from './equation'
import type { MethodRole, Verdict } from './roles'

// Équation de experiments/regression_lineaire.yaml.
const spec: EquationSpec = {
  tex: '\\widehat{\\mathrm{Var}}(\\hat{\\beta}) = {{var}}',
  terms: {
    var: {
      ok: '\\hat{\\sigma}^2 (X^\\top X)^{-1}',
      corrected: '(X^\\top X)^{-1} X^\\top \\hat{\\Omega}_{\\mathrm{HC3}} X (X^\\top X)^{-1}',
    },
  },
}

const methods: { id: string; role: MethodRole }[] = [
  { id: 'ols', role: 'method' },
  { id: 'hc3', role: 'correction' },
  { id: 'nw', role: 'alternative' },
]

function ctx(states: Record<string, Verdict>, on: string[] = ['ols']): EquationContext {
  return { methods, primaryStates: states, methodsOn: on }
}

const colors = { broken: '#f85149', repaired: '#3fb950' }

describe('termDisplay : les 5 lignes du tableau du cahier', () => {
  it('aucune hypothèse en cause : version saine, neutre', () => {
    const d = termDisplay('var', [], ctx({ ols: 'broken', hc3: 'ok' }, ['ols', 'hc3']))
    expect(d).toMatchObject({ tone: 'neutral', corrected: false })
  })

  it('hypothèse cassée mais méthode principale Fiable : neutre', () => {
    expect(termDisplay('var', ['hetero'], ctx({ ols: 'ok' }))).toMatchObject({ tone: 'neutral', corrected: false })
  })

  it('méthode principale Fragile ou Rompue : version saine, rouge', () => {
    for (const v of ['warning', 'broken'] as const) {
      expect(termDisplay('var', ['hetero'], ctx({ ols: v, hc3: 'ok' }))).toMatchObject({ tone: 'broken', corrected: false })
    }
  })

  it('Correction affichée et Fiable : version corrigée, vert', () => {
    const d = termDisplay('var', ['hetero'], ctx({ ols: 'broken', hc3: 'ok' }, ['ols', 'hc3']))
    expect(d).toMatchObject({ tone: 'repaired', corrected: true, violatedBy: ['hetero'] })
  })

  it('Correction affichée mais pas Fiable : version corrigée, rouge', () => {
    const d = termDisplay('var', ['autocorr'], ctx({ ols: 'broken', hc3: 'warning' }, ['ols', 'hc3']))
    expect(d).toMatchObject({ tone: 'broken', corrected: true })
  })
})

describe('termDisplay : cas limites', () => {
  it('une alternative affichée ne compte pas comme la Correction', () => {
    const d = termDisplay('var', ['hetero'], ctx({ ols: 'broken', hc3: 'ok', nw: 'ok' }, ['ols', 'nw']))
    expect(d).toMatchObject({ tone: 'broken', corrected: false })
  })

  it('pas de correction déclarée : rouge', () => {
    const d = termDisplay('var', ['hetero'], {
      methods: [{ id: 'ols', role: 'method' }],
      primaryStates: { ols: 'broken' },
      methodsOn: new Set(['ols']),
    })
    expect(d.tone).toBe('broken')
  })

  it('verdict absent (mesure non calculable) : neutre', () => {
    expect(termDisplay('var', ['hetero'], ctx({})).tone).toBe('neutral')
  })

  it('methodsOn accepte un Set', () => {
    const d = termDisplay('var', ['hetero'], { ...ctx({ ols: 'broken', hc3: 'ok' }), methodsOn: new Set(['hc3']) })
    expect(d.tone).toBe('repaired')
  })
})

describe('buildEquationTex', () => {
  it('neutre : version saine sans couleur', () => {
    const tex = buildEquationTex(spec, [termDisplay('var', [], ctx({ ols: 'ok' }))], colors)
    expect(tex).toBe('\\widehat{\\mathrm{Var}}(\\hat{\\beta}) = {\\hat{\\sigma}^2 (X^\\top X)^{-1}}')
  })

  it('rouge : couleur de rupture et soulignement', () => {
    const tex = buildEquationTex(spec, [termDisplay('var', ['hetero'], ctx({ ols: 'broken' }))], colors)
    expect(tex).toContain('\\textcolor{#f85149}{\\underline{\\hat{\\sigma}^2')
  })

  it('vert : version corrigée en couleur de correction', () => {
    const d = termDisplay('var', ['hetero'], ctx({ ols: 'broken', hc3: 'ok' }, ['ols', 'hc3']))
    const tex = buildEquationTex(spec, [d], colors)
    expect(tex).toContain('\\textcolor{#3fb950}{(X^\\top X)^{-1} X^\\top \\hat{\\Omega}_{\\mathrm{HC3}}')
  })

  it('terme sans version corrigée : la version saine sert de repli', () => {
    const s: EquationSpec = { tex: '{{err}}', terms: { err: { ok: 'O(\\Delta t)' } } }
    const d = termDisplay('err', ['pas'], ctx({ ols: 'broken', hc3: 'ok' }, ['hc3']))
    expect(buildEquationTex(s, [d], colors)).toBe('{\\textcolor{#3fb950}{O(\\Delta t)}}')
  })

  it('accepte les espaces dans le gabarit ({{ var }})', () => {
    const s: EquationSpec = { tex: 'a = {{ var }}', terms: spec.terms }
    expect(buildEquationTex(s, [], colors)).toBe('a = {\\hat{\\sigma}^2 (X^\\top X)^{-1}}')
  })
})
