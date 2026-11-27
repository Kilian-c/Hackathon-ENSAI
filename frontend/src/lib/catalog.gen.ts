/**
 * FICHIER GÉNÉRÉ par scripts/gen_catalog.py depuis les registres du moteur (backend/).
 * Ne pas modifier à la main : modifiez le registre, puis relancez
 * « uv run python scripts/gen_catalog.py » et commitez le résultat.
 */

export interface CatalogMethod {
  name: string
  args: string[]
  provides: Record<string, string[]>
  cost: string
  doc: string
}

export interface Catalog {
  methods: CatalogMethod[]
  laws: { name: string; has_mean: boolean; has_variance: boolean }[]
  functions: { name: string; doc: string }[]
  constants: string[]
  names: { name: string; doc: string }[]
  keywords: string[]
  aggregators: string[]
  views: { type: string; doc: string }[]
}

export const CATALOG: Catalog = {
  "methods": [
    {
      "name": "classifier",
      "args": [
        "score",
        "label",
        "threshold",
        "kind"
      ],
      "provides": {
        "reps": [
          "error",
          "best_error",
          "excess",
          "sens",
          "spec",
          "accuracy",
          "auc"
        ],
        "example": [
          "score_neg",
          "score_pos"
        ],
        "curves": [
          "fpr",
          "tpr"
        ]
      },
      "cost": "repeat * n",
      "doc": "Classe positif si `score > threshold`. Par répétition : taux d'erreur, meilleur taux atteignable par un seuil sur ce même échantillon, excès d'erreur, sensibilité, spécificité, exactitude et AUC."
    },
    {
      "name": "clt_mean",
      "args": [
        "x",
        "sigma",
        "rho",
        "kind",
        "alpha"
      ],
      "provides": {
        "reps": [
          "z",
          "inside"
        ],
        "example": [
          "x"
        ],
        "curves": [
          "k",
          "paths"
        ]
      },
      "cost": "repeat * n",
      "doc": "Statistique z par répétition ; `inside` vaut 1 si |z| ne dépasse pas le quantile normal."
    },
    {
      "name": "formula_estimate",
      "args": [
        "est",
        "truth"
      ],
      "provides": {
        "reps": [
          "est",
          "error"
        ]
      },
      "cost": "repeat",
      "doc": "`est` : l'estimation de chaque répétition (formule) ; `error` : `est - truth` (NaN sans `truth`)."
    },
    {
      "name": "formula_interval",
      "args": [
        "est",
        "low",
        "high",
        "truth"
      ],
      "provides": {
        "reps": [
          "est",
          "low",
          "high",
          "hit",
          "width"
        ]
      },
      "cost": "repeat",
      "doc": "Un intervalle par formule : `hit` vaut vrai si `low <= truth <= high`, `width` = `high - low`."
    },
    {
      "name": "formula_test",
      "args": [
        "stat",
        "pvalue",
        "critical",
        "alpha"
      ],
      "provides": {
        "reps": [
          "stat",
          "pvalue",
          "reject"
        ]
      },
      "cost": "repeat",
      "doc": "Un test défini par formule. Donnez `pvalue` (rejet si `pvalue < alpha`) ou `stat` et `critical` (rejet si `|stat| > critical`). Sans `stat` (resp. `pvalue`), cette colonne vaut NaN."
    },
    {
      "name": "integrate",
      "args": [
        "system",
        "dt",
        "scheme"
      ],
      "provides": {
        "curves": [
          "t",
          "theta"
        ],
        "summary": [
          "max_rel_error"
        ]
      },
      "cost": "t_end / dt",
      "doc": "Intègre `system` avec le pas `dt` (arrondi pour tomber pile sur t_end)."
    },
    {
      "name": "ols_ci",
      "args": [
        "x",
        "y",
        "truth",
        "alpha",
        "se_type"
      ],
      "provides": {
        "reps": [
          "est",
          "low",
          "high",
          "hit",
          "width",
          "bp_pvalue"
        ],
        "example": [
          "x",
          "y",
          "y_hat",
          "y_mean",
          "resid",
          "leverage",
          "cooks_d"
        ]
      },
      "cost": "repeat * n",
      "doc": "MCO de y sur (1, x) et IC à (1 - alpha) de la pente, par répétition."
    },
    {
      "name": "ols_two",
      "args": [
        "x1",
        "x2",
        "y",
        "signal",
        "truth",
        "alpha",
        "kind"
      ],
      "provides": {
        "reps": [
          "est",
          "low",
          "high",
          "hit",
          "reject",
          "width",
          "vif",
          "pred_error"
        ],
        "example": [
          "x1",
          "x2",
          "y",
          "y_hat",
          "resid"
        ]
      },
      "cost": "repeat * n",
      "doc": "Estime le coefficient de x1 ; `reject` vaut 1 si le test de Student le déclare non nul."
    },
    {
      "name": "one_sample_test",
      "args": [
        "x0",
        "x1",
        "alpha",
        "kind"
      ],
      "provides": {
        "reps": [
          "reject",
          "reject_h1",
          "pvalue",
          "stat"
        ],
        "example": [
          "x0"
        ]
      },
      "cost": "repeat * n",
      "doc": "Teste H0 : centre = 0 sur x0 (sous H0) et sur x1 (sous H1)."
    },
    {
      "name": "pairwise_tests",
      "args": [
        "y",
        "groups",
        "alpha",
        "kind"
      ],
      "provides": {
        "reps": [
          "any_reject",
          "n_reject",
          "max_stat"
        ],
        "example": [
          "group",
          "y",
          "group_mean"
        ]
      },
      "cost": "repeat * n",
      "doc": "Teste l'égalité des moyennes pour chaque paire de groupes."
    },
    {
      "name": "regressor",
      "args": [
        "x",
        "y",
        "kind",
        "slope"
      ],
      "provides": {
        "reps": [
          "slope",
          "sse",
          "excess"
        ],
        "example": [
          "x",
          "y",
          "y_hat"
        ]
      },
      "cost": "repeat * n",
      "doc": "Par répétition : pente, somme des carrés des résidus (`sse`), et `excess` = sse / sse des MCO - 1 (0 pour la droite des MCO, positif pour toute autre droite)."
    },
    {
      "name": "statistic",
      "args": [
        "x",
        "kind",
        "continuity"
      ],
      "provides": {
        "reps": [
          "stat"
        ],
        "example": [
          "x"
        ]
      },
      "cost": "repeat * n",
      "doc": "`stat` : la statistique `kind` de chaque ligne de x, forme (repeat,)."
    }
  ],
  "laws": [
    {
      "name": "bimodal",
      "has_mean": true,
      "has_variance": true
    },
    {
      "name": "cauchy",
      "has_mean": false,
      "has_variance": false
    },
    {
      "name": "exponential",
      "has_mean": true,
      "has_variance": true
    },
    {
      "name": "normal",
      "has_mean": true,
      "has_variance": true
    },
    {
      "name": "student_2",
      "has_mean": true,
      "has_variance": false
    },
    {
      "name": "uniform",
      "has_mean": true,
      "has_variance": true
    }
  ],
  "functions": [
    {
      "name": "abs",
      "doc": ""
    },
    {
      "name": "ar1",
      "doc": ""
    },
    {
      "name": "arccos",
      "doc": ""
    },
    {
      "name": "arcsin",
      "doc": ""
    },
    {
      "name": "arctan",
      "doc": ""
    },
    {
      "name": "arctan2",
      "doc": ""
    },
    {
      "name": "ceil",
      "doc": ""
    },
    {
      "name": "clip",
      "doc": ""
    },
    {
      "name": "cos",
      "doc": ""
    },
    {
      "name": "cosh",
      "doc": ""
    },
    {
      "name": "cumprod",
      "doc": ""
    },
    {
      "name": "cumsum",
      "doc": ""
    },
    {
      "name": "exp",
      "doc": ""
    },
    {
      "name": "floor",
      "doc": ""
    },
    {
      "name": "isfinite",
      "doc": ""
    },
    {
      "name": "isnan",
      "doc": ""
    },
    {
      "name": "log",
      "doc": ""
    },
    {
      "name": "log10",
      "doc": ""
    },
    {
      "name": "log2",
      "doc": ""
    },
    {
      "name": "max",
      "doc": ""
    },
    {
      "name": "maximum",
      "doc": ""
    },
    {
      "name": "mean",
      "doc": ""
    },
    {
      "name": "median",
      "doc": ""
    },
    {
      "name": "min",
      "doc": ""
    },
    {
      "name": "minimum",
      "doc": ""
    },
    {
      "name": "ols_match",
      "doc": ""
    },
    {
      "name": "quantile",
      "doc": ""
    },
    {
      "name": "round",
      "doc": ""
    },
    {
      "name": "sign",
      "doc": ""
    },
    {
      "name": "sin",
      "doc": ""
    },
    {
      "name": "sinh",
      "doc": ""
    },
    {
      "name": "sort",
      "doc": ""
    },
    {
      "name": "sqrt",
      "doc": ""
    },
    {
      "name": "std",
      "doc": ""
    },
    {
      "name": "sum",
      "doc": ""
    },
    {
      "name": "tan",
      "doc": ""
    },
    {
      "name": "tanh",
      "doc": ""
    },
    {
      "name": "var",
      "doc": ""
    },
    {
      "name": "where",
      "doc": ""
    },
    {
      "name": "law",
      "doc": "law('nom') : un tirage de la loi du registre (standardisée)"
    },
    {
      "name": "normal",
      "doc": "normal() : un tirage de la loi normale standard"
    },
    {
      "name": "uniform",
      "doc": "uniform() : un tirage de la loi uniforme standardisée"
    },
    {
      "name": "bernoulli",
      "doc": "bernoulli(p) : un tirage de Bernoulli de paramètre p"
    }
  ],
  "constants": [
    "e",
    "pi"
  ],
  "names": [
    {
      "name": "idx",
      "doc": "indice d'observation (0, 1, ..., n - 1)"
    }
  ],
  "keywords": [
    "axis"
  ],
  "aggregators": [
    "bias",
    "first",
    "kurtosis",
    "mean",
    "median",
    "quantile",
    "rate",
    "rmse",
    "sd",
    "summary",
    "var"
  ],
  "views": [
    {
      "type": "scatter",
      "doc": "nuage de points (données et droite ajustée)"
    },
    {
      "type": "residuals",
      "doc": "résidus en fonction des valeurs ajustées"
    },
    {
      "type": "curves",
      "doc": "courbes y(x) ou y(t) par méthode"
    },
    {
      "type": "repetitions",
      "doc": "une grandeur sur les répétitions (mode `intervals`, ou `paths` pour des trajectoires)"
    },
    {
      "type": "distribution",
      "doc": "distribution d'une grandeur sur les répétitions"
    },
    {
      "type": "sensitivity",
      "doc": "mesure primaire en fonction d'un axe (hypothèse ou paramètre), calculée par /api/sweep"
    },
    {
      "type": "validity_domain",
      "doc": "carte des verdicts sur deux axes, calculée par /api/sweep"
    },
    {
      "type": "heatmap",
      "doc": "matrices en cartes de couleur (série `matrix`, `paths[i][j]` = coefficient (i + 1, j + 1))"
    },
    {
      "type": "measures_table",
      "doc": "tableau des mesures (vue de secours)"
    }
  ]
}
