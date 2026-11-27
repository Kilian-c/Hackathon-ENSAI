import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, clearCache, createLatest, type CallOptions } from './executor'
import type { RunRequest } from './types.gen'

const req = (n: number): RunRequest => ({
  experiment_id: 'regression-lineaire',
  raw_content: null,
  state: { params: { n }, hypotheses: {}, extra_points: [], seed: 42 },
})

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('api : erreurs en français', () => {
  beforeEach(() => clearCache())
  afterEach(() => vi.unstubAllGlobals())

  it('message du moteur repris tel quel', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(400, { detail: 'Indiquez soit experiment_id, soit raw_content.' })))
    await expect(api.run(req(1))).rejects.toMatchObject({ status: 400, message: 'Indiquez soit experiment_id, soit raw_content.' })
  })

  it('erreur de validation (422) : le champ fautif est cité', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(422, { detail: [{ loc: ['body', 'state', 'seed'], msg: 'x' }] })))
    const err = await api.run(req(2)).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).message).toContain('state.seed')
  })

  it('moteur injoignable', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    await expect(api.run(req(3))).rejects.toMatchObject({ status: 0, message: expect.stringContaining('Impossible de joindre') })
  })

  it('cache : la même requête ne repart pas au moteur', async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, { ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    await api.run(req(4))
    await api.run(req(4))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

describe('createLatest : glissement de curseur', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  /** Faux appel au moteur : répond après `ms` millisecondes, sauf annulation. */
  function fakeEngine(ms: number) {
    const calls: number[] = []
    const aborted: number[] = []
    const fn = (n: number, opts: CallOptions) =>
      new Promise<string>((resolve, reject) => {
        calls.push(n)
        const t = setTimeout(() => resolve(`résultat ${n}`), ms)
        opts.signal?.addEventListener('abort', () => {
          clearTimeout(t)
          aborted.push(n)
          reject(new DOMException('annulé', 'AbortError'))
        })
      })
    return { fn, calls, aborted }
  }

  it('regroupe les appels rapprochés : seul le dernier part', async () => {
    const engine = fakeEngine(50)
    const latest = createLatest(engine.fn, 100)
    const p1 = latest.call(1)
    const p2 = latest.call(2)
    const p3 = latest.call(3)
    await vi.advanceTimersByTimeAsync(200)
    expect(await p1).toBeNull()
    expect(await p2).toBeNull()
    expect(await p3).toBe('résultat 3')
    expect(engine.calls).toEqual([3])
  })

  it('annule la requête en cours quand une plus récente part', async () => {
    const engine = fakeEngine(500)
    const latest = createLatest(engine.fn, 100)
    const p1 = latest.call(1)
    await vi.advanceTimersByTimeAsync(150) // la requête 1 est partie
    const p2 = latest.call(2)
    await vi.advanceTimersByTimeAsync(150) // la requête 2 part et annule la 1
    expect(engine.aborted).toEqual([1])
    await vi.advanceTimersByTimeAsync(600)
    expect(await p1).toBeNull()
    expect(await p2).toBe('résultat 2')
  })

  it('une vraie erreur est remontée', async () => {
    const latest = createLatest(async () => { throw new ApiError('panne', 500) }, 10)
    const p = latest.call(1)
    const check = expect(p).rejects.toThrow('panne')
    await vi.advanceTimersByTimeAsync(20)
    await check
  })

  it('cancel() : rien ne part, la promesse rend null', async () => {
    const engine = fakeEngine(50)
    const latest = createLatest(engine.fn, 100)
    const p = latest.call(1)
    latest.cancel()
    await vi.advanceTimersByTimeAsync(200)
    expect(await p).toBeNull()
    expect(engine.calls).toEqual([])
  })
})
