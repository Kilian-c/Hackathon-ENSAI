import { describe, expect, it } from 'vitest'
import { CATALOG, type Catalog } from './catalog.gen'
import { catalogSection, importPrompt, methodLine, PENDING_VIEWS } from './importPrompt'
import { VIEW_TYPES, VIEW_UI_KEYS } from './plot'

describe('catalogue généré (catalog.gen.ts)', () => {
  it('contient les méthodes, lois et agrégateurs du moteur', () => {
    const names = CATALOG.methods.map((m) => m.name)
    for (const m of ['ols_ci', 'statistic', 'classifier', 'clt_mean']) expect(names).toContain(m)
    expect(CATALOG.laws.map((l) => l.name)).toEqual(expect.arrayContaining(['normal', 'cauchy']))
    expect(CATALOG.aggregators.map((a) => a.name)).toEqual(expect.arrayContaining(['rate', 'mean', 'summary']))
  })
  it('rng est fourni par le moteur : jamais listé comme argument', () => {
    for (const m of CATALOG.methods) expect(m.args.map((a) => a.name)).not.toContain('rng')
  })
})

describe('prompt de l’écran Import', () => {
  const prompt = importPrompt('Loi des grands nombres')

  it('cite le sujet, ou un emplacement à remplir', () => {
    expect(prompt).toContain('Sujet : Loi des grands nombres')
    expect(importPrompt('  ')).toContain('<décrivez ici le théorème')
  })
  it('liste chaque méthode du catalogue, avec ses valeurs de kind', () => {
    for (const m of CATALOG.methods) expect(prompt).toContain(`- ${m.name}(`)
    const stat = CATALOG.methods.find((m) => m.name === 'statistic')!
    expect(methodLine(stat)).toMatch(/\[kind : (\w+ \| )+\w+\]/)
    expect(methodLine(stat)).toContain('reps: stat')
  })
  it('liste chaque loi, agrégateur, type de vue et réglage ui', () => {
    for (const l of CATALOG.laws) expect(prompt).toContain(`law('${l.name}')`)
    for (const a of CATALOG.aggregators) expect(prompt).toContain(`${a.name}(`)
    for (const t of Object.keys(VIEW_TYPES)) {
      if (!PENDING_VIEWS.has(t)) expect(prompt).toContain(`- ${t} : `)
    }
    for (const k of ['log_y', 'aspect', 'unit_circle', 'x_title']) expect(prompt).toContain(`${k} (`)
  })
  it('agrégateurs écrits comme dans un YAML : summary(k), rate(f)', () => {
    expect(prompt).toContain('summary(k)')
    expect(prompt).toContain('rate(f)')
    expect(prompt).not.toContain('summary_dict')
  })
  it('la vue heatmap, servie par le moteur depuis matrices_wigner, est proposée avec ses réglages', () => {
    expect(PENDING_VIEWS.has('heatmap')).toBe(false)
    expect(prompt).toContain('- heatmap : ')
    expect(prompt).toContain('zmin (')
  })
  it('une méthode ajoutée au catalogue apparaît sans rien recopier', () => {
    const extra: Catalog = {
      ...CATALOG,
      methods: [
        ...CATALOG.methods,
        { name: 'linsolve', args: [{ name: 'A', default: null }, { name: 'kind', default: "'gauss'" }], kinds: ['gauss', 'gauss_pivot'], provides: { reps: ['err'] }, cost: 'repeat * n', doc: 'Résout Ax = b.' },
      ],
    }
    expect(catalogSection(extra)).toContain("- linsolve(A, kind='gauss') [kind : gauss | gauss_pivot] -> reps: err — Résout Ax = b.")
  })
  it('garde les deux vrais exemples de experiments/', () => {
    expect(prompt).toContain('id: "somme-de-des"')
    expect(prompt).toContain('id: "regression-lineaire"')
  })
})
