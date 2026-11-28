import { describe, expect, it } from 'vitest'
import { parsePreference, resolveTheme, THEME_CHOICES } from './theme.svelte'

describe('thème', () => {
  it('lit le choix gardé ; une valeur inconnue ou absente vaut « auto »', () => {
    expect(parsePreference('light')).toBe('light')
    expect(parsePreference('dark')).toBe('dark')
    expect(parsePreference('auto')).toBe('auto')
    expect(parsePreference(null)).toBe('auto')
    expect(parsePreference('violet')).toBe('auto')
  })

  it('« auto » suit le système ; un choix explicite l’emporte', () => {
    expect(resolveTheme('auto', true)).toBe('light')
    expect(resolveTheme('auto', false)).toBe('dark')
    expect(resolveTheme('dark', true)).toBe('dark')
    expect(resolveTheme('light', false)).toBe('light')
  })

  it('propose les trois choix, en français', () => {
    expect(THEME_CHOICES.map((c) => c.label)).toEqual(['Auto', 'Clair', 'Sombre'])
  })
})
