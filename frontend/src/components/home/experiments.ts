// Mise en forme commune à l'accueil et à la galerie du Laboratoire.
import { LINK_VERSION } from '../../lib/state'

// Libellés des disciplines : lib/trainChoice.ts (partagés avec le choix des thèmes de l'Entraînement).
export { disciplineLabel } from '../../lib/trainChoice'

/** « Thème : sous-titre » en deux morceaux ; titre entier s'il n'y a pas de deux-points. */
export function splitTitle(t: string): { head: string; sub: string | null } {
  const i = t.indexOf(' : ')
  return i < 0 ? { head: t, sub: null } : { head: t.slice(0, i), sub: t.slice(i + 3) }
}

export const LAB_GALLERY_HREF = '?labo'
export const TRAIN_ALL_HREF = `?train=toutes&v=${LINK_VERSION}`
export const labHref = (id: string): string => `?exp=${encodeURIComponent(id)}&v=${LINK_VERSION}`
export const trainOneHref = (id: string): string => `?train=${encodeURIComponent(id)}&v=${LINK_VERSION}`
