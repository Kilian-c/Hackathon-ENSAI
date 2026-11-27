# Catalogue du moteur

Fichier généré par `scripts/gen_catalog.py` : ne pas l'éditer à la main.

## Méthodes (`call:` d'un YAML)

| Méthode | Arguments | Fournit | Coût | Rôle |
|---|---|---|---|---|
| `classifier` | score, label, threshold, kind | reps : error, best_error, excess, sens, spec, accuracy, auc ; example : score_neg, score_pos ; curves : fpr, tpr | `repeat * n` | Classe positif si `score > threshold`. Par répétition : taux d'erreur, meilleur taux atteignable par un seuil sur ce même échantillon, excès d'erreur, sensibilité, spécificité, exactitude et AUC. |
| `clt_mean` | x, sigma, rho, kind, alpha | reps : z, inside ; example : x ; curves : k, paths | `repeat * n` | Statistique z par répétition ; `inside` vaut 1 si |z| ne dépasse pas le quantile normal. |
| `integrate` | system, dt, scheme | curves : t, theta ; summary : max_rel_error | `t_end / dt` | Intègre `system` avec le pas `dt` (arrondi pour tomber pile sur t_end). |
| `ols_ci` | x, y, truth, alpha, se_type | reps : est, low, high, hit, width, bp_pvalue ; example : x, y, y_hat, y_mean, resid, leverage, cooks_d | `repeat * n` | MCO de y sur (1, x) et IC à (1 - alpha) de la pente, par répétition. |
| `ols_two` | x1, x2, y, signal, truth, alpha, kind | reps : est, low, high, hit, reject, width, vif, pred_error ; example : x1, x2, y, y_hat, resid | `repeat * n` | Estime le coefficient de x1 ; `reject` vaut 1 si le test de Student le déclare non nul. |
| `one_sample_test` | x0, x1, alpha, kind | reps : reject, reject_h1, pvalue, stat ; example : x0 | `repeat * n` | Teste H0 : centre = 0 sur x0 (sous H0) et sur x1 (sous H1). |
| `pairwise_tests` | y, groups, alpha, kind | reps : any_reject, n_reject, max_stat ; example : group, y, group_mean | `repeat * n` | Teste l'égalité des moyennes pour chaque paire de groupes. |
| `regressor` | x, y, kind, slope | reps : slope, sse, excess ; example : x, y, y_hat | `repeat * n` | Par répétition : pente, somme des carrés des résidus (`sse`), et `excess` = sse / sse des MCO - 1 (0 pour la droite des MCO, positif pour toute autre droite). |
| `statistic` | x, kind, continuity | reps : stat ; example : x | `repeat * n` | `stat` : la statistique `kind` de chaque ligne de x, forme (repeat,). |

## Lois (`law('nom')`)

| Loi | Moyenne | Variance |
|---|---|---|
| `bimodal` | oui | oui |
| `cauchy` | non | non |
| `exponential` | oui | oui |
| `normal` | oui | oui |
| `student_2` | oui | non |
| `uniform` | oui | oui |

## Fonctions des expressions

`abs`, `ar1`, `arccos`, `arcsin`, `arctan`, `arctan2`, `ceil`, `clip`, `cos`, `cosh`, `cumsum`, `exp`, `floor`, `isfinite`, `isnan`, `log`, `log10`, `log2`, `max`, `maximum`, `mean`, `median`, `min`, `minimum`, `ols_match`, `round`, `sign`, `sin`, `sinh`, `sqrt`, `std`, `sum`, `tan`, `tanh`, `var`, `where`, `law`, `normal`, `uniform`, `bernoulli`.

Constantes : `e`, `pi`. Mot-clé accepté : `axis`.
- `law` : law('nom') : un tirage de la loi du registre (standardisée)
- `normal` : normal() : un tirage de la loi normale standard
- `uniform` : uniform() : un tirage de la loi uniforme standardisée
- `bernoulli` : bernoulli(p) : un tirage de Bernoulli de paramètre p
- `idx` : indice d'observation (0, 1, ..., n - 1)

## Agrégateurs (`agg:` d'une mesure)

`bias`, `first`, `kurtosis`, `mean`, `median`, `quantile`, `rate`, `rmse`, `sd`, `summary`, `var`.

## Vues (`type:` d'une vue)

| Type | Rôle |
|---|---|
| `scatter` | nuage de points (données et droite ajustée) |
| `residuals` | résidus en fonction des valeurs ajustées |
| `curves` | courbes y(x) ou y(t) par méthode |
| `repetitions` | une grandeur sur les répétitions (mode `intervals`, ou `paths` pour des trajectoires) |
| `distribution` | distribution d'une grandeur sur les répétitions |
| `sensitivity` | mesure primaire en fonction d'un axe (hypothèse ou paramètre), calculée par /api/sweep |
| `validity_domain` | carte des verdicts sur deux axes, calculée par /api/sweep |
| `heatmap` | matrices en cartes de couleur (série `matrix`, `paths[i][j]` = coefficient (i + 1, j + 1)) |
| `measures_table` | tableau des mesures (vue de secours) |
