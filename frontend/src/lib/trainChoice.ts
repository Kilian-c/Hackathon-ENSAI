/**
 * trainChoice.ts : choix des thèmes d'une série d'Entraînement (plan de docs/notes/r1.md, étape 3).
 *
 * Les disciplines viennent des YAML (`GET /api/experiments`) : aucune liste écrite à la main. Le filtre envoyé
 * au moteur est `toutes`, `exp:<id>[,<id>...]` (théorèmes choisis) ou `discipline:<id>[,<id>...]`, où l'identifiant est le nom de la discipline sans
 * accent ni espace (« algèbre linéaire » devient « algebre-lineaire »), comme `discipline_slug` du moteur
 * (backend/engine/training.py) : les deux doivent rester d'accord.
 */

import { LINK_VERSION } from './state'

/** Libellés affichés des disciplines connues ; une discipline nouvelle (un YAML de plus) est mise en forme. */
const DISCIPLINE_LABELS: Record<string, string> = {
  statistique: 'Statistique',
  probabilites: 'Probabilités',
  apprentissage: 'Apprentissage',
  'algebre-lineaire': 'Algèbre linéaire',
}

/** Identifiant court d'une discipline, identique à `discipline_slug` du moteur. */
export function disciplineSlug(name: string): string {
  return name
    .normalize('NFKD')
    .replace(/[^\x00-\x7f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

/** Libellé affiché d'une discipline, à partir de son nom (YAML) ou de son identifiant court. */
export function disciplineLabel(nameOrSlug: string): string {
  const known = DISCIPLINE_LABELS[disciplineSlug(nameOrSlug)]
  if (known) return known
  const spaced = nameOrSlug.replace(/-/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export interface DisciplineChoice {
  slug: string
  label: string
  /** Nombre d'expériences de cette discipline. */
  count: number
}

/** Les disciplines des expériences, une fois chacune, triées par libellé. */
export function disciplineChoices(items: readonly { discipline: string }[]): DisciplineChoice[] {
  const byslug = new Map<string, DisciplineChoice>()
  for (const { discipline } of items) {
    const slug = disciplineSlug(discipline)
    const found = byslug.get(slug)
    if (found) found.count += 1
    else byslug.set(slug, { slug, label: disciplineLabel(discipline), count: 1 })
  }
  return [...byslug.values()].sort((a, b) => a.label.localeCompare(b.label, 'fr'))
}

/** « A », « A et B », « A, B et C ». */
export function joinLabels(labels: readonly string[]): string {
  if (labels.length <= 1) return labels.join('')
  return `${labels.slice(0, -1).join(', ')} et ${labels[labels.length - 1]}`
}

/**
 * Filtre à envoyer au moteur pour une sélection de disciplines. Aucune sélection, ou toutes les disciplines :
 * `toutes` (une seule écriture pour le même ensemble de questions, donc une seule série par graine).
 */
export function trainingFilter(selected: readonly string[], available: readonly string[]): string {
  const chosen = [...new Set(selected)].filter((s) => available.includes(s)).sort()
  if (chosen.length === 0 || chosen.length === new Set(available).size) return 'toutes'
  return `discipline:${chosen.join(',')}`
}

/** Disciplines d'un filtre `discipline:a,b` (identifiants courts, triés) ; [] pour tout autre filtre. */
export function selectedFromFilter(filter: string): string[] {
  if (!filter.startsWith('discipline:')) return []
  const slugs = filter
    .slice('discipline:'.length)
    .split(',')
    .map((part) => disciplineSlug(part))
    .filter(Boolean)
  return [...new Set(slugs)].sort()
}

/** Ajoute ou retire une discipline de la sélection ; toutes sélectionnées revient à « aucune » (= Tout). */
export function toggleDiscipline(selected: readonly string[], slug: string, available: readonly string[]): string[] {
  const next = selected.includes(slug) ? selected.filter((s) => s !== slug) : [...selected, slug]
  return next.length === new Set(available).size ? [] : next
}

/** Nombre de théorèmes au plus dans un filtre `exp:` (même plafond que le contrat du moteur). */
export const MAX_CHOSEN_EXPERIMENTS = 15

/** Filtre `exp:<id>,<id>...` pour des théorèmes choisis un à un ; `null` si aucun n'est choisi. */
export function experimentFilter(ids: readonly string[]): string | null {
  const chosen = [...new Set(ids)].sort().slice(0, MAX_CHOSEN_EXPERIMENTS)
  return chosen.length === 0 ? null : `exp:${chosen.join(',')}`
}

/** Théorèmes d'un filtre `exp:a,b` (triés, sans doublon) ; [] pour tout autre filtre. */
export function experimentsFromFilter(filter: string): string[] {
  if (!filter.startsWith('exp:')) return []
  const ids = filter.slice('exp:'.length).split(',').map((part) => part.trim()).filter(Boolean)
  return [...new Set(ids)].sort()
}

/** Coche ou décoche un théorème ; au plafond, une case de plus n'est pas ajoutée. */
export function toggleExperiment(selected: readonly string[], id: string): string[] {
  if (selected.includes(id)) return selected.filter((s) => s !== id)
  return selected.length >= MAX_CHOSEN_EXPERIMENTS ? [...selected] : [...selected, id]
}

/** Les expériences regroupées par discipline (ordre des libellés), chacune triée par titre. */
export function groupByDiscipline<T extends { discipline: string; title: string }>(
  items: readonly T[],
): { slug: string; label: string; items: T[] }[] {
  const groups = new Map<string, { slug: string; label: string; items: T[] }>()
  for (const item of items) {
    const slug = disciplineSlug(item.discipline)
    const group = groups.get(slug) ?? { slug, label: disciplineLabel(item.discipline), items: [] }
    group.items.push(item)
    groups.set(slug, group)
  }
  return [...groups.values()]
    .map((g) => ({ ...g, items: [...g.items].sort((a, b) => a.title.localeCompare(b.title, 'fr')) }))
    .sort((a, b) => a.label.localeCompare(b.label, 'fr'))
}

/** Lien de la série pour un filtre : ?train=<filtre>&v=1 (la graine est tirée par le moteur). */
export function trainHref(filter: string): string {
  return `?train=${encodeURIComponent(filter)}&v=${LINK_VERSION}`
}

/** Phrase sous les boutons : ce que contient la sélection. */
export function describeSelection(choices: readonly DisciplineChoice[], selected: readonly string[]): string {
  const chosen = selected.length === 0 ? choices : choices.filter((c) => selected.includes(c.slug))
  const experiments = chosen.reduce((sum, c) => sum + c.count, 0)
  const noun = experiments > 1 ? 'expériences' : 'expérience'
  if (selected.length === 0) return `Toutes les disciplines : ${experiments} ${noun}.`
  return `${joinLabels(chosen.map((c) => c.label))} : ${experiments} ${noun}.`
}
