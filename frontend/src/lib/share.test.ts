import { describe, expect, it } from 'vitest'
import { isShareId, newShareId, supabaseBaseUrl } from './share'

describe('partage : adresse Supabase', () => {
  it("garde l'adresse du projet telle quelle", () => {
    expect(supabaseBaseUrl('https://abc.supabase.co')).toBe('https://abc.supabase.co')
  })

  it('retire la barre finale et le suffixe /rest/v1 copié du tableau de bord', () => {
    expect(supabaseBaseUrl('https://abc.supabase.co/')).toBe('https://abc.supabase.co')
    expect(supabaseBaseUrl('https://abc.supabase.co/rest/v1')).toBe('https://abc.supabase.co')
    expect(supabaseBaseUrl('https://abc.supabase.co/rest/v1/')).toBe('https://abc.supabase.co')
    expect(supabaseBaseUrl('  https://abc.supabase.co/rest/v1//  ')).toBe('https://abc.supabase.co')
  })

  it('laisse vide une adresse absente (partage désactivé)', () => {
    expect(supabaseBaseUrl('')).toBe('')
  })
})

describe('partage : identifiants', () => {
  it('fabrique des identifiants acceptés par la table', () => {
    for (let i = 0; i < 50; i++) expect(isShareId(newShareId())).toBe(true)
    expect(isShareId('court')).toBe(false)
    expect(isShareId('abc/def?ghi=1')).toBe(false)
  })
})
