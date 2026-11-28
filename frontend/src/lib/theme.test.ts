import { describe, expect, it, vi } from 'vitest'
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

describe('thème : un seul état par page', () => {
  it('deux chargements du module partagent le même état (serveur de développement)', async () => {
    const first = await import('./theme.svelte')
    vi.resetModules() // le module est évalué une seconde fois, comme avec une copie « ?t=… »
    const second = await import('./theme.svelte')
    expect(second.setTheme).not.toBe(first.setTheme) // bien deux copies
    first.setTheme('light')
    expect(second.theme.resolved).toBe('light')
    second.setTheme('dark')
    expect(first.theme.resolved).toBe('dark')
  })
})
