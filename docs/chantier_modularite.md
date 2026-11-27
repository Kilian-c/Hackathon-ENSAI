# Chantier « modularité » : fichiers réservés (R1 + R3)

Ce chantier ouvre Crash-Test à d'autres théorèmes, à commencer par l'algèbre linéaire. Il ne touche à **aucun fichier de contrat** (`contracts.py`, `schema.py`, `method_contract.py`).

**Règle** : jusqu'à la fin du chantier, personne d'autre ne modifie les fichiers listés ci-dessous. Si vous avez besoin d'y toucher (correctif urgent pour la démo, par exemple), prévenez d'abord la personne indiquée. Elle intègre votre changement ou vous laisse la main.

Quand une ligne est terminée et fusionnée sur `main`, rayez-la (`~~...~~`) : le fichier redevient libre.

## R1 (moteur)

| Fichier | Nouveau ? | Ce qui change | Relu par |
|---|---|---|---|
| `backend/methods/formula.py` | oui | méthodes génériques `formula_estimate`, `formula_test`, `formula_interval` : une méthode s'écrit dans le YAML, sans Python | R2 |
| `backend/methods/linalg/__init__.py` | oui | paquet de l'algèbre linéaire | R2 |
| `backend/methods/linalg/linsolve.py` | oui | `linsolve` (gauss, gauss_pivot, cholesky, jacobi, gauss_seidel, cg) | R2 |
| `backend/methods/linalg/eigen.py` | oui | `eigen` (power, qr, numpy) | R2 |
| `backend/methods/linalg/orthonormalize.py` | oui | `orthonormalize` (cgs, mgs, householder) | R2 |
| `backend/methods/linalg/spectrum.py` | oui | `spectrum` (spectre de matrices aléatoires) | R2 |
| `backend/methods/__init__.py` | non | les méthodes sont découvertes automatiquement (`pkgutil`), plus de liste à la main | R2 |
| `backend/engine/expr.py` | non | liste blanche : `sort`, `quantile`, `cumprod` | R3 |
| `backend/engine/validate.py` | non | `/api/validate` propose des seuils (`ok_within`, `broken_beyond`) d'après la simulation | R3 |
| `backend/engine/runner.py` | non | `_build_view` : vue `heatmap` (afficher une matrice) | R3 |
| ~~`scripts/gen_catalog.py`~~ | oui | ~~lit les registres (méthodes, lois, fonctions, vues), puis écrit `frontend/src/lib/catalog.gen.ts` et `docs/catalogue.md`~~ **Fait** (`--check` pour la fraîcheur, `tests/test_catalog.py`). Il reste à R3 : brancher `importPrompt.ts` sur `CATALOG` | R3 |
| `scripts/new_experiment.py` | oui | crée un YAML à partir d'un modèle (statistique, régression, classifieur, algèbre) | R2 |
| `experiments/matrices_wigner.yaml` | oui | expérience pilote de l'algèbre, simulée avant d'écrire les seuils | R2 |
| `tests/test_formula.py` | oui | tests des méthodes `formula_*` | |
| `tests/test_linalg.py` | oui | tests de `linalg/` (comparaison à `np.linalg`, vectorisation, temps de calcul) | |
| `tests/test_api.py` | non | `/api/validate` : seuils proposés | |

## R3 (Kilian, interface)

| Fichier | Nouveau ? | Ce qui change | Relu par |
|---|---|---|---|
| `frontend/src/lib/plot.ts` | non | `ui.log_y`, `ui.aspect: equal`, `ui.unit_circle` ; type de vue `heatmap` | |
| `frontend/src/lib/plot.test.ts` | non | tests de ces réglages et de `heatmap` | |
| `frontend/src/lib/views.ts` | non | lecture des données de `heatmap` | |
| `frontend/src/lib/importPrompt.ts` | non | lit le catalogue généré au lieu de la liste écrite à la main | R4 |
| `frontend/src/lib/catalog.gen.ts` | oui | **généré** par `scripts/gen_catalog.py` : ne jamais l'éditer à la main | |
| `frontend/src/components/ImportView.svelte` | non | affiche les seuils proposés par `/api/validate` | R4 |
| `scripts/export_schema.py` | non | écrit aussi `experiments/schema.json` (schéma JSON du YAML, pour l'autocomplétion dans VS Code) | R1 |
| `experiments/schema.json` | oui | **généré** : ne jamais l'éditer à la main | |
| `CLAUDE.md` | non | section 11 : nouveaux réglages `ui` et méthodes `formula_*` ; section 3 : renvoi vers ce fichier | |

## Dépendances entre les deux listes

- `heatmap` : R1 sert la vue (`runner.py`) et R3 la dessine (`plot.ts`, **fait**). Forme proposée par R3, à confirmer par R1, sans changer le contrat :
  - **Données** : une `Series` par méthode (et une par Référence, `role: reference`). La matrice va dans `paths`, une liste par ligne (`paths[i][j]` = coefficient (i + 1, j + 1)). `NaN` et `inf` arrivent en `null`, ce qui donne une case vide. `slot` est libre (par exemple `matrix`), `id` = `<vue>.<emplacement>.<methode>`.
  - **Taille** : 3 cartes au plus côte à côte. Au-delà de 12 × 12, les valeurs ne sont plus écrites dans les cases, seulement au survol.
  - **`ui` facultatif** : `zmin`, `zmax` (bornes de couleur, communes à toutes les cartes), `decimals` (2 par défaut).
  - Exemple de `bind` : `{ matrix: "curves.A" }`, où la méthode renvoie la matrice de la répétition 0 dans `curves`, de forme (d, d).
- `ui.log_y` et `ui.log_x` (**faits**, `plot.ts`) : à `true`, l'axe passe en échelle logarithmique pour les vues `scatter`, `residuals`, `curves` et `sensitivity`. Les bornes du moteur restent en unités de données : l'interface les convertit, et passe en automatique si une borne est ≤ 0. Les valeurs ≤ 0 sont comptées sous la vue.
- Catalogue : R1 écrit `gen_catalog.py`, puis R3 branche `importPrompt.ts` sur `catalog.gen.ts`.
- Seuils proposés : R1 les ajoute à `/api/validate` sans toucher au contrat (dans les avertissements ou les résultats de tests déjà renvoyés), puis R3 les affiche.

## Hors chantier (horizon 2, après le pitch, `schema_version: 2`)

Rien n'est réservé pour l'instant : formes explicites des variables (`shape`), registre des générateurs (`grid` pour l'analyse), registre des vues des deux côtés, arguments de méthode typés.
