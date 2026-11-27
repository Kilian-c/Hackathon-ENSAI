import { afterEach, describe, expect, it, vi } from 'vitest'
import { listExperiments, openExperiment, openSession } from './labSource'

describe('labSource : pas de repli automatique sur les fixtures', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('moteur injoignable : l’erreur remonte', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    await expect(listExperiments()).rejects.toMatchObject({ status: 0 })
    await expect(openExperiment('regression-lineaire')).rejects.toMatchObject({ status: 0 })
    await expect(openSession('toutes', 1)).rejects.toMatchObject({ status: 0 })
  })

  it('?source=fixtures : données de démonstration, sans appel au moteur', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    vi.stubGlobal('location', { search: '?source=fixtures' })
    await expect(listExperiments()).resolves.toMatchObject({ kind: 'fixtures' })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
