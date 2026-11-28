import { describe, expect, it } from 'vitest'
import { parseLink } from './state'
import { filterLabel, shortSeriesNotice, SERIES_SIZE } from './training'
import {
  describeSelection,
  experimentFilter,
  experimentsFromFilter,
  groupByDiscipline,
  MAX_CHOSEN_EXPERIMENTS,
  toggleExperiment,
  disciplineChoices,
  disciplineLabel,
  disciplineSlug,
  joinLabels,
  selectedFromFilter,
  toggleDiscipline,
  trainHref,
  trainingFilter,
} from './trainChoice'

const experiments = [
  ...Array.from({ length: 6 }, () => ({ discipline: 'statistique' })),
  ...Array.from({ length: 3 }, () => ({ discipline: 'probabilités' })),
  ...Array.from({ length: 4 }, () => ({ discipline: 'algèbre linéaire' })),
  ...Array.from({ length: 2 }, () => ({ discipline: 'apprentissage' })),
]
const choices = disciplineChoices(experiments)
const all = choices.map((c) => c.slug)

describe('identifiant court d’une discipline (le même que discipline_slug du moteur)', () => {
  it('retire accents, espaces et majuscules', () => {
    expect(disciplineSlug('algèbre linéaire')).toBe('algebre-lineaire')
    expect(disciplineSlug('probabilités')).toBe('probabilites')
    expect(disciplineSlug('Algèbre  Linéaire')).toBe('algebre-lineaire')
    expect(disciplineSlug('statistique')).toBe('statistique')
  })
  it('un libellé se retrouve depuis le nom ou depuis l’identifiant', () => {
    expect(disciplineLabel('algèbre linéaire')).toBe('Algèbre linéaire')
    expect(disciplineLabel('algebre-lineaire')).toBe('Algèbre linéaire')
    expect(disciplineLabel('probabilités')).toBe('Probabilités')
    expect(disciplineLabel('chimie organique')).toBe('Chimie organique') // discipline nouvelle : mise en forme
    expect(disciplineLabel('chimie-organique')).toBe('Chimie organique')
  })
})

describe('disciplines proposées', () => {
  it('une par discipline, triées, avec leur nombre d’expériences', () => {
    expect(choices.map((c) => [c.slug, c.label, c.count])).toEqual([
      ['algebre-lineaire', 'Algèbre linéaire', 4],
      ['apprentissage', 'Apprentissage', 2],
      ['probabilites', 'Probabilités', 3],
      ['statistique', 'Statistique', 6],
    ])
  })
  it('aucune expérience : aucune discipline', () => {
    expect(disciplineChoices([])).toEqual([])
  })
})

describe('filtre envoyé au moteur', () => {
  it('aucune sélection ou toutes les disciplines : « toutes » (une seule écriture)', () => {
    expect(trainingFilter([], all)).toBe('toutes')
    expect(trainingFilter(all, all)).toBe('toutes')
  })
  it('une ou plusieurs disciplines : identifiants courts triés, sans doublon', () => {
    expect(trainingFilter(['statistique'], all)).toBe('discipline:statistique')
    expect(trainingFilter(['statistique', 'algebre-lineaire', 'statistique'], all)).toBe('discipline:algebre-lineaire,statistique')
  })
  it('ignore ce qui n’existe pas', () => {
    expect(trainingFilter(['chimie'], all)).toBe('toutes')
  })
  it('la sélection bascule, et « toutes cochées » revient à « aucune »', () => {
    let selected: string[] = []
    selected = toggleDiscipline(selected, 'statistique', all)
    expect(selected).toEqual(['statistique'])
    selected = toggleDiscipline(selected, 'statistique', all)
    expect(selected).toEqual([])
    for (const slug of all) selected = toggleDiscipline(selected, slug, all)
    expect(selected).toEqual([])
  })
})

describe('lien de la série', () => {
  it('survit à l’aller-retour de l’URL (virgule et deux-points encodés)', () => {
    const filter = trainingFilter(['probabilites', 'algebre-lineaire'], all)
    const link = parseLink(trainHref(filter))
    expect(link).toMatchObject({ kind: 'training', filter: 'discipline:algebre-lineaire,probabilites' })
    expect(selectedFromFilter((link as { filter: string }).filter)).toEqual(['algebre-lineaire', 'probabilites'])
  })
  it('« toutes » et un identifiant d’expérience ne sont pas des disciplines', () => {
    expect(selectedFromFilter('toutes')).toEqual([])
    expect(selectedFromFilter('regression-lineaire')).toEqual([])
  })
  it('un ancien lien avec le nom de la discipline est compris', () => {
    expect(selectedFromFilter('discipline:probabilités,statistique')).toEqual(['probabilites', 'statistique'])
  })
})

describe('libellés lisibles', () => {
  it('énumération française', () => {
    expect(joinLabels([])).toBe('')
    expect(joinLabels(['A'])).toBe('A')
    expect(joinLabels(['A', 'B'])).toBe('A et B')
    expect(joinLabels(['A', 'B', 'C'])).toBe('A, B et C')
  })
  it('titre de la série selon le filtre', () => {
    expect(filterLabel('toutes')).toBe('Toutes les expériences')
    expect(filterLabel('discipline:algebre-lineaire')).toBe('Algèbre linéaire')
    expect(filterLabel('discipline:probabilites,statistique')).toBe('Probabilités et Statistique')
    expect(filterLabel('regression-lineaire')).toBe('Une seule expérience')
  })
  it('phrase sous les boutons', () => {
    expect(describeSelection(choices, [])).toBe('Toutes les disciplines : 15 expériences.')
    expect(describeSelection(choices, ['apprentissage'])).toBe('Apprentissage : 2 expériences.')
    expect(describeSelection(choices, ['statistique', 'probabilites'])).toBe('Probabilités et Statistique : 9 expériences.')
  })
})

describe('série plus courte que demandée', () => {
  it('prévient quand il y a moins de questions que demandé, et propose d’ajouter une discipline', () => {
    const note = shortSeriesNotice(6, 'discipline:apprentissage')
    expect(note).toContain('6 questions')
    expect(note).toContain('Apprentissage')
    expect(note).toContain(`${SERIES_SIZE} habituelles`)
    expect(note).toContain('Ajoutez une autre discipline')
  })
  it('au singulier, sans conseil pour « toutes »', () => {
    expect(shortSeriesNotice(1, 'toutes')).toContain('1 question ')
    expect(shortSeriesNotice(1, 'toutes')).not.toContain('Ajoutez')
  })
  it('aucun message pour une série complète ou vide', () => {
    expect(shortSeriesNotice(SERIES_SIZE, 'toutes')).toBeNull()
    expect(shortSeriesNotice(0, 'discipline:apprentissage')).toBeNull()
  })
})

describe('théorèmes choisis un à un', () => {
  it('filtre exp: trié, sans doublon, plafonné ; null si rien', () => {
    expect(experimentFilter([])).toBeNull()
    expect(experimentFilter(['b', 'a', 'b'])).toBe('exp:a,b')
    const many = Array.from({ length: 20 }, (_, i) => `e${String(i).padStart(2, '0')}`)
    expect(experimentsFromFilter(experimentFilter(many) as string)).toHaveLength(MAX_CHOSEN_EXPERIMENTS)
  })
  it('lit un filtre exp: et ignore les autres', () => {
    expect(experimentsFromFilter('exp:regression-lineaire,multicolinearite')).toEqual([
      'multicolinearite',
      'regression-lineaire',
    ])
    expect(experimentsFromFilter('toutes')).toEqual([])
    expect(experimentsFromFilter('discipline:statistique')).toEqual([])
  })
  it('coche, décoche, et refuse une case au-delà du plafond', () => {
    expect(toggleExperiment(['a'], 'b')).toEqual(['a', 'b'])
    expect(toggleExperiment(['a', 'b'], 'a')).toEqual(['b'])
    const full = Array.from({ length: MAX_CHOSEN_EXPERIMENTS }, (_, i) => `e${i}`)
    expect(toggleExperiment(full, 'nouveau')).toEqual(full)
  })
  it('regroupe par discipline, titres triés', () => {
    const groups = groupByDiscipline([
      { discipline: 'statistique', title: 'Zéta' },
      { discipline: 'algèbre linéaire', title: 'B' },
      { discipline: 'statistique', title: 'Alpha' },
    ])
    expect(groups.map((g) => g.label)).toEqual(['Algèbre linéaire', 'Statistique'])
    expect(groups[1].items.map((i) => i.title)).toEqual(['Alpha', 'Zéta'])
  })
  it('libellé et message de série courte', () => {
    expect(filterLabel('exp:a,b,c')).toBe('3 théorèmes choisis')
    expect(filterLabel('exp:a')).toBe('Un théorème choisi')
    expect(shortSeriesNotice(4, 'exp:a,b')).toContain('Ajoutez un autre théorème')
  })
  it('lien partageable : la virgule et les deux-points survivent', () => {
    const link = parseLink('?train=exp%3Aa%2Cb&seed=3&v=1')
    expect(link).toMatchObject({ kind: 'training', filter: 'exp:a,b', seed: 3 })
  })
})
