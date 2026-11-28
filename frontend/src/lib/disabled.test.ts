import { describe, expect, it } from 'vitest'
import { disabledNotice, isDisabled, type DisabledState } from './disabled'

const state: DisabledState = {
  hypotheses: { hetero: 0.8, loi: 'cauchy', independante: true },
  params: { n: 30 },
}

describe('disabled_when', () => {
  it('constantes : True grise toujours (hypothèse affichée mais non cassable)', () => {
    expect(isDisabled('True', state)).toBe(true)
    expect(isDisabled('true', state)).toBe(true)
    expect(isDisabled('False', state)).toBe(false)
  })
  it('lit l’état : hypothèses et paramètres', () => {
    expect(isDisabled("h.loi == 'cauchy'", state)).toBe(true)
    expect(isDisabled('h.loi != "cauchy"', state)).toBe(false)
    expect(isDisabled('p.n < 50', state)).toBe(true)
    expect(isDisabled('p.n >= 50', state)).toBe(false)
    expect(isDisabled('h.hetero > 0.5', state)).toBe(true)
    expect(isDisabled('h.independante', state)).toBe(true)
  })
  it('not, and, or, parenthèses, avec les priorités de Python', () => {
    expect(isDisabled('not h.independante', state)).toBe(false)
    expect(isDisabled('h.hetero > 0.5 and p.n < 10', state)).toBe(false)
    expect(isDisabled('h.hetero > 0.5 or p.n < 10', state)).toBe(true)
    expect(isDisabled('not (h.hetero > 0.5 and p.n < 10)', state)).toBe(true)
    expect(isDisabled('True or False and False', state)).toBe(true) // and avant or
  })
  it('une expression vide ou illisible n’interdit rien', () => {
    for (const bad of [undefined, null, '', '   ', 'h.', 'foo.bar', '1 +', '((True)', 'h.loi < 3', "__import__('os')", 'True; False']) {
      expect(isDisabled(bad, state)).toBeNull()
    }
  })
  it('nom d’état inconnu : valeur indéfinie, jamais d’erreur', () => {
    expect(isDisabled('h.absente', state)).toBe(false)
    expect(isDisabled('h.absente == True', state)).toBe(false)
  })
  it('phrase affichée : celle du YAML, ou une phrase par défaut, seulement si grisé', () => {
    const h = { disabled_when: 'True', disabled_text: ' Toujours vraie ici. ' }
    expect(disabledNotice(h, state)).toBe('Toujours vraie ici.')
    expect(disabledNotice({ disabled_when: 'True' }, state)).toMatch(/ne peut pas être modifiée/)
    expect(disabledNotice({ disabled_when: 'p.n > 100', disabled_text: 'x' }, state)).toBeNull()
    expect(disabledNotice({}, state)).toBeNull()
  })
})
