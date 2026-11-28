# Chantier « modularité » : fichiers réservés (R1 + R3)

Ce chantier ouvre Crash-Test à d'autres théorèmes, à commencer par l'algèbre linéaire. Il ne touche à **aucun fichier de contrat** (`contracts.py`, `schema.py`, `method_contract.py`).

**Règle** : jusqu'à la fin du chantier, personne d'autre ne modifie les fichiers listés ci-dessous. Si vous avez besoin d'y toucher (correctif urgent pour la démo, par exemple), prévenez d'abord la personne indiquée. Elle intègre votre changement ou vous laisse la main.

Quand une ligne est terminée et fusionnée sur `main`, rayez-la (`~~...~~`) : le fichier redevient libre.

## R1 (moteur)

| Fichier | Nouveau ? | Ce qui change | Relu par |
|---|---|---|---|
| ~~`backend/methods/formula.py`~~ | oui | ~~méthodes génériques `formula_estimate`, `formula_test`, `formula_interval`~~ **Fait** (arguments = expressions réduisant l'axe des observations, ex. `mean(x, axis=1)`) ; 3 exemples ajoutés dans `tests/test_method_contract.py` (R2) | R2 |
| ~~`backend/methods/linalg/__init__.py`~~ | oui | ~~paquet de l'algèbre linéaire~~ **Fait** | R2 |
| ~~`backend/methods/linalg/linsolve.py`~~ | oui | ~~`linsolve` (gauss, gauss_pivot, cholesky, jacobi, gauss_seidel, cg)~~ **Fait** + `experiments/systemes_lineaires.yaml` (Jacobi contre diagonale faible ; Gauss-Seidel en alternative, pivot de Gauss en correction) | R2 |
| ~~`backend/methods/linalg/eigen.py`~~ | oui | ~~`eigen` (power, qr, numpy)~~ **Fait** + `experiments/valeurs_propres.yaml` (puissance contre valeur propre dominante noyée dans le spectre ; QR en alternative, calcul direct en correction) | R2 |
| ~~`backend/methods/linalg/orthonormalize.py`~~ | oui | ~~`orthonormalize` (cgs, mgs, householder)~~ **Fait** + `experiments/orthonormalisation.yaml` (perte d'orthogonalité : epsilon fois cond² pour le classique, cond pour le modifié, epsilon pour Householder) | R2 |
| ~~`backend/methods/linalg/spectrum.py`~~ | oui | ~~`spectrum` (spectre de matrices aléatoires)~~ **Fait** (Wigner : `reps` lmax, lmin, radius ; `curves` matrix, eigenvalues ; `summary` semicircle_ks) | R2 |
| ~~`backend/methods/__init__.py`~~ | non | ~~découverte automatique (`pkgutil`)~~ **Fait** | R2 |
| ~~`backend/engine/expr.py`~~ | non | ~~liste blanche : `sort`, `quantile`, `cumprod`~~ **Fait** | R3 |
| ~~`backend/engine/validate.py`~~ | non | ~~seuils proposés~~ **Fait** : un avertissement par mesure, `path` = `measures.<id>`, message « Seuils proposés : ok_within = x ; broken_beyond = y (fichier : ...). » (s'affiche déjà dans l'Import) | R3 |
| ~~`backend/engine/runner.py`~~ | non | ~~`_build_view` : vue `heatmap`~~ **Fait** : série `slot: matrix` par méthode + Référence (`.ref`), `bind: { matrix: curves.<clé> }`, 64 × 64 au plus (coin supérieur gauche) | R3 |
| `scripts/new_experiment.py` | oui | crée un YAML à partir d'un modèle (statistique, régression, classifieur, algèbre) ; mettre en tête `# yaml-language-server: $schema=./schema.json` | R2 |
| ~~`experiments/matrices_wigner.yaml`~~ | oui | ~~expérience pilote de l'algèbre~~ **Fait** : universalité de Wigner (normale, uniforme, exponentielle : demi-cercle ; Student à 2 ddl, Cauchy : rompu), 40 graines sans verdict ambigu, test 6 à 50 tirages vert | R2 |
| ~~`tests/test_formula.py`~~ | oui | ~~tests des méthodes `formula_*`~~ **Fait** | |
| `tests/test_linalg.py` | oui | tests de `linalg/` (comparaison à `np.linalg`, vectorisation, temps de calcul) | |
| ~~`tests/test_api.py`~~ | non | ~~`/api/validate` : seuils proposés~~ **Fait** | |
| ~~`scripts/gen_catalog.py`~~ | | **fait par R3** pour débloquer le prompt de l'Import (voir la liste R3) | R1 |

À chaque méthode ajoutée : `uv run python scripts/gen_catalog.py`, puis commiter `frontend/src/lib/catalog.gen.ts` (sinon `tests/test_generated.py` échoue). Un module de méthode qui déclare une constante `_KINDS` (tuple ou dictionnaire) voit ses valeurs de `kind` listées dans le prompt.

## R3 (Kilian, interface) : terminé

| Fichier | Nouveau ? | Ce qui a changé | Relu par |
|---|---|---|---|
| ~~`frontend/src/lib/plot.ts`~~ | non | `ui.log_y`, `ui.log_x`, `ui.aspect: "equal"`, `ui.unit_circle` ; vue `heatmap` ; `VIEW_TYPES` et `VIEW_UI_KEYS` (lus par le prompt) | |
| ~~`frontend/src/lib/plot.test.ts`~~ | non | tests de ces réglages et de `heatmap` | |
| ~~`frontend/src/lib/views.ts`~~ | non | commentaire : forme des données de `heatmap` | |
| ~~`frontend/src/lib/importPrompt.ts`~~ | non | lit le catalogue généré au lieu de la liste écrite à la main ; `PENDING_VIEWS` tait `heatmap` tant que le moteur ne la sert pas | R4 |
| ~~`frontend/src/lib/importPrompt.test.ts`~~ | oui | tests du prompt | |
| ~~`frontend/src/lib/catalog.gen.ts`~~ | oui | **généré** par `scripts/gen_catalog.py` : ne jamais l'éditer à la main | |
| ~~`scripts/gen_catalog.py`~~ | oui | registres du moteur → `catalog.gen.ts` (`--check` pour vérifier) | R1 |
| ~~`scripts/export_schema.py`~~, ~~`scripts/gen_types.sh`~~ | non | écrivent aussi `experiments/schema.json` (`--check` le vérifie) | R1 |
| ~~`experiments/schema.json`~~ | oui | **généré** : schéma JSON d'un YAML, pour VS Code ; ne jamais l'éditer à la main | |
| ~~`frontend/src/lib/experimentSchema.test.ts`~~ | oui | les 13 YAML (dont les archives) passent le schéma ; clés inconnues, clé manquante et rôle inconnu refusés | |
| ~~`tests/test_generated.py`~~ | oui | `catalog.gen.ts` et `schema.json` à jour, catalogue complet | |
| ~~`frontend/package.json`~~ | non | `ajv` et `yaml` en dépendances de développement (tests du schéma seulement) | |
| ~~`CLAUDE.md`~~ | non | sections 6, 7 et 11 : commandes, schéma, réglages `ui` | |
| ~~`frontend/src/components/ImportView.svelte`~~ | non | **rien à faire** : les avertissements de `/api/validate` s'affichent déjà avec leur ligne (fichier rendu à R4) | |

Vérifié dans le navigateur (Chromium sans interface, vrai moteur, console sans erreur) : `log_y` sur une Sensibilité réelle, `aspect` et `unit_circle` sur une courbe ROC, la Sensibilité linéaire inchangée, l'écran Import. `heatmap` et `log_y` sur une courbe : vérifiés avec le vrai Plotly sur des données construites, car le moteur ne sert pas encore de matrice.

## Dépendances entre les deux listes

- `heatmap` : R1 sert la vue (`runner.py`) et R3 la dessine (`plot.ts`, **fait**). Forme proposée par R3, à confirmer par R1, sans changer le contrat :
  - **Données** : une `Series` par méthode (et une par Référence, `role: reference`). La matrice va dans `paths`, une liste par ligne (`paths[i][j]` = coefficient (i + 1, j + 1)). `NaN` et `inf` arrivent en `null`, ce qui donne une case vide. `slot` est libre (par exemple `matrix`), `id` = `<vue>.<emplacement>.<methode>`.
  - **Taille** : 3 cartes au plus côte à côte. Au-delà de 12 × 12, les valeurs ne sont plus écrites dans les cases, seulement au survol.
  - **`ui` facultatif** : `zmin`, `zmax` (bornes de couleur, communes à toutes les cartes), `decimals` (2 par défaut).
  - Exemple de `bind` : `{ matrix: "curves.A" }`, où la méthode renvoie la matrice de la répétition 0 dans `curves`, de forme (d, d).
  - **Quand `runner.py` la sert** : retirer `heatmap` de `PENDING_VIEWS` (`frontend/src/lib/importPrompt.ts`), pour que le prompt de l'Import la propose.
- `ui.log_y` et `ui.log_x` (**faits**) : à `true`, l'axe passe en échelle logarithmique pour les vues `scatter`, `residuals`, `curves` et `sensitivity`. Les bornes du moteur restent en unités de données : l'interface les convertit, et passe en automatique si une borne est ≤ 0. Les valeurs ≤ 0 sont retirées des courbes et comptées sous la vue. À savoir : avec Plotly 4, sur un axe log, les formes (`shapes`) se placent en unités de données et les annotations en log10. C'est vérifié dans le navigateur et géré dans `sensitivityFigure`.
- `ui.aspect: "equal"` et `ui.unit_circle` (**faits**) : repère orthonormé (bornes gardées, zone de tracé resserrée) et cercle centré en 0 (`true` ou un rayon), pour le plan complexe.
- Seuils proposés : R1 les ajoute à `/api/validate` comme **avertissements** (`ValidateIssue` avec `line`, `path: measures.<id>.ok_within` et un message en français qui donne la valeur proposée). L'écran Import les affiche déjà avec un lien vers la ligne : aucun changement d'interface ni de contrat.

## Hors chantier (horizon 2, après le pitch, `schema_version: 2`)

Rien n'est réservé pour l'instant : formes explicites des variables (`shape`), registre des générateurs (`grid` pour l'analyse), registre des vues des deux côtés, arguments de méthode typés.
