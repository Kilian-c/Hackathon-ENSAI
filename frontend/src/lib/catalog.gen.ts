/**
 * FICHIER GÉNÉRÉ par scripts/gen_catalog.py depuis les registres du moteur (méthodes, lois,
 * agrégateurs, fonctions des expressions). Ne pas modifier à la main : relancez
 * « uv run python scripts/gen_catalog.py » après avoir ajouté une méthode, une loi ou une fonction.
 */

export interface CatalogArg {
  name: string
  /** Valeur par défaut (texte), null si l'argument est obligatoire. */
  default: string | null
}

export interface CatalogMethod {
  name: string
  args: CatalogArg[]
  /** Valeurs possibles de l'argument `kind` ; vide si la méthode n'en a pas (ou ne les déclare pas). */
  kinds: string[]
  provides: Record<string, string[]>
  cost: string
  doc: string
}

export interface CatalogLaw {
  name: string
  has_mean: boolean
  has_variance: boolean
}

export interface CatalogFunction {
  name: string
  signature: string
  doc: string
}

export interface Catalog {
  methods: CatalogMethod[]
  laws: CatalogLaw[]
  aggregators: CatalogFunction[]
  functions: string[]
  generator_functions: CatalogFunction[]
  constants: string[]
}

export const CATALOG: Catalog = {
  "methods": [
    {
      "name": "classifier",
      "args": [
        {
          "name": "score",
          "default": null
        },
        {
          "name": "label",
          "default": null
        },
        {
          "name": "threshold",
          "default": null
        },
        {
          "name": "kind",
          "default": "'seuil'"
        }
      ],
      "kinds": [
        "seuil"
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
        {
          "name": "x",
          "default": null
        },
        {
          "name": "sigma",
          "default": null
        },
        {
          "name": "rho",
          "default": null
        },
        {
          "name": "kind",
          "default": null
        },
        {
          "name": "alpha",
          "default": "0.05"
        }
      ],
      "kinds": [
        "independance",
        "dependance"
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
      "name": "eigen",
      "args": [
        {
          "name": "a",
          "default": null
        },
        {
          "name": "d",
          "default": null
        },
        {
          "name": "spike",
          "default": "3.0"
        },
        {
          "name": "kind",
          "default": "'numpy'"
        },
        {
          "name": "iters",
          "default": "60"
        }
      ],
      "kinds": [
        "power",
        "qr",
        "numpy"
      ],
      "provides": {
        "reps": [
          "log_error",
          "estimate",
          "failed"
        ],
        "curves": [
          "matrix",
          "k",
          "history"
        ]
      },
      "cost": "repeat * iters * d**3",
      "doc": "Estime la valeur propre de plus grand module de A = Wigner + spike v vᵀ."
    },
    {
      "name": "formula_estimate",
      "args": [
        {
          "name": "est",
          "default": null
        },
        {
          "name": "truth",
          "default": "None"
        }
      ],
      "kinds": [],
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
        {
          "name": "est",
          "default": null
        },
        {
          "name": "low",
          "default": null
        },
        {
          "name": "high",
          "default": null
        },
        {
          "name": "truth",
          "default": null
        }
      ],
      "kinds": [],
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
        {
          "name": "stat",
          "default": "None"
        },
        {
          "name": "pvalue",
          "default": "None"
        },
        {
          "name": "critical",
          "default": "None"
        },
        {
          "name": "alpha",
          "default": "0.05"
        }
      ],
      "kinds": [],
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
        {
          "name": "system",
          "default": null
        },
        {
          "name": "dt",
          "default": null
        },
        {
          "name": "scheme",
          "default": null
        }
      ],
      "kinds": [],
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
      "name": "iterated_integral",
      "args": [
        {
          "name": "x",
          "default": null
        },
        {
          "name": "y",
          "default": null
        },
        {
          "name": "f",
          "default": null
        },
        {
          "name": "truth",
          "default": "None"
        }
      ],
      "kinds": [
        "rectangles",
        "trapezes",
        "simpson",
        "monte_carlo"
      ],
      "provides": {
        "reps": [
          "est",
          "error"
        ],
        "curves": [
          "matrix"
        ]
      },
      "cost": "repeat * n",
      "doc": "Intégrale double de f sur [0, 1]², sommée sur une grille rectangulaire A × B de milieux de cellules."
    },
    {
      "name": "iterated_integrals",
      "args": [
        {
          "name": "x",
          "default": null
        },
        {
          "name": "y",
          "default": null
        },
        {
          "name": "f",
          "default": null
        },
        {
          "name": "x0",
          "default": "0.5"
        }
      ],
      "kinds": [
        "rectangles",
        "trapezes",
        "simpson",
        "monte_carlo"
      ],
      "provides": {
        "reps": [
          "dy_dx",
          "dx_dy",
          "gap",
          "abs_int",
          "slice_int"
        ],
        "curves": [
          "t",
          "dy",
          "dx",
          "slice_y",
          "slice_f"
        ]
      },
      "cost": "repeat * n",
      "doc": "Les deux intégrales itérées de f sur [lo, 1]², chacune sur une grille adaptée à son ordre."
    },
    {
      "name": "linsolve",
      "args": [
        {
          "name": "a",
          "default": null
        },
        {
          "name": "d",
          "default": null
        },
        {
          "name": "shift",
          "default": "3.0"
        },
        {
          "name": "kind",
          "default": "'gauss_pivot'"
        },
        {
          "name": "iters",
          "default": "60"
        }
      ],
      "kinds": [
        "gauss",
        "gauss_pivot",
        "cholesky",
        "jacobi",
        "gauss_seidel",
        "cg"
      ],
      "provides": {
        "reps": [
          "log_error",
          "failed"
        ],
        "curves": [
          "matrix",
          "k",
          "history"
        ]
      },
      "cost": "repeat * d**3",
      "doc": "Résout A x = b pour A = (G + Gᵀ) / sqrt(2 d) + shift I et b = A 1 (solution exacte : le vecteur de 1)."
    },
    {
      "name": "ols_ci",
      "args": [
        {
          "name": "x",
          "default": null
        },
        {
          "name": "y",
          "default": null
        },
        {
          "name": "truth",
          "default": null
        },
        {
          "name": "alpha",
          "default": null
        },
        {
          "name": "se_type",
          "default": null
        }
      ],
      "kinds": [],
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
        {
          "name": "x1",
          "default": null
        },
        {
          "name": "x2",
          "default": null
        },
        {
          "name": "y",
          "default": null
        },
        {
          "name": "signal",
          "default": null
        },
        {
          "name": "truth",
          "default": null
        },
        {
          "name": "alpha",
          "default": null
        },
        {
          "name": "kind",
          "default": null
        }
      ],
      "kinds": [
        "complet",
        "reduit"
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
        {
          "name": "x0",
          "default": null
        },
        {
          "name": "x1",
          "default": null
        },
        {
          "name": "alpha",
          "default": null
        },
        {
          "name": "kind",
          "default": null
        }
      ],
      "kinds": [
        "student",
        "wilcoxon"
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
      "name": "orthonormalize",
      "args": [
        {
          "name": "a",
          "default": null
        },
        {
          "name": "d",
          "default": null
        },
        {
          "name": "decades",
          "default": "1.0"
        },
        {
          "name": "kind",
          "default": "'householder'"
        }
      ],
      "kinds": [
        "cgs",
        "mgs",
        "householder"
      ],
      "provides": {
        "reps": [
          "log_ortho",
          "log_resid",
          "failed"
        ],
        "curves": [
          "matrix"
        ]
      },
      "cost": "repeat * d**3",
      "doc": "Factorise A = Q R et mesure ce que vaut Q."
    },
    {
      "name": "pairwise_tests",
      "args": [
        {
          "name": "y",
          "default": null
        },
        {
          "name": "groups",
          "default": null
        },
        {
          "name": "alpha",
          "default": null
        },
        {
          "name": "kind",
          "default": null
        }
      ],
      "kinds": [
        "aucune",
        "bonferroni",
        "tukey"
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
      "name": "quadrature",
      "args": [
        {
          "name": "x",
          "default": null
        },
        {
          "name": "f",
          "default": null
        },
        {
          "name": "a",
          "default": null
        },
        {
          "name": "b",
          "default": null
        },
        {
          "name": "kind",
          "default": "'rectangles'"
        },
        {
          "name": "truth",
          "default": "None"
        },
        {
          "name": "samples",
          "default": "200"
        }
      ],
      "kinds": [
        "rectangles",
        "trapezes",
        "simpson",
        "monte_carlo"
      ],
      "provides": {
        "reps": [
          "est",
          "error"
        ],
        "example": [
          "x",
          "f"
        ]
      },
      "cost": "repeat * n",
      "doc": "`est` : l'intégrale de f sur [a, b] ; `error` : `est - truth` (NaN sans `truth`)."
    },
    {
      "name": "regressor",
      "args": [
        {
          "name": "x",
          "default": null
        },
        {
          "name": "y",
          "default": null
        },
        {
          "name": "kind",
          "default": null
        },
        {
          "name": "slope",
          "default": "None"
        }
      ],
      "kinds": [
        "ols",
        "manuelle"
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
      "name": "spectrum",
      "args": [
        {
          "name": "x",
          "default": null
        },
        {
          "name": "d",
          "default": null
        }
      ],
      "kinds": [],
      "provides": {
        "reps": [
          "lmax",
          "lmin",
          "radius"
        ],
        "curves": [
          "matrix",
          "eigenvalues"
        ],
        "summary": [
          "semicircle_ks"
        ]
      },
      "cost": "repeat * d**3",
      "doc": "`lmax`, `lmin`, `radius` : plus grande, plus petite valeur propre et rayon spectral par répétition."
    },
    {
      "name": "statistic",
      "args": [
        {
          "name": "x",
          "default": null
        },
        {
          "name": "kind",
          "default": null
        },
        {
          "name": "continuity",
          "default": "False"
        }
      ],
      "kinds": [
        "sum",
        "mean",
        "max",
        "min",
        "median"
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
  "aggregators": [
    {
      "name": "bias",
      "signature": "bias(f, truth)",
      "doc": "Biais : moyenne de `values` moins la vraie valeur `truth`. Erreur MC : sd / sqrt(n)."
    },
    {
      "name": "first",
      "signature": "first(f)",
      "doc": "Valeur sur la répétition 0 (l'échantillon affiché dans les vues)."
    },
    {
      "name": "kurtosis",
      "signature": "kurtosis(f)",
      "doc": "Aplatissement (kurtosis en excès) des répétitions valides : 0 pour une loi normale, -1,2 pour une loi uniforme. Pas d'erreur MC (CLAUDE.md, section 8 : seulement pour rate, mean et bias)."
    },
    {
      "name": "mean",
      "signature": "mean(f)",
      "doc": "Moyenne des répétitions valides. Erreur MC : écart type / sqrt(n)."
    },
    {
      "name": "median",
      "signature": "median(f)",
      "doc": "Médiane des répétitions valides."
    },
    {
      "name": "quantile",
      "signature": "quantile(f, q)",
      "doc": "Quantile d'ordre `q` (dans [0, 1]) des répétitions valides."
    },
    {
      "name": "rate",
      "signature": "rate(f)",
      "doc": "Part des répétitions où `values` est vrai (non nul). Erreur MC : sqrt(p(1-p)/n)."
    },
    {
      "name": "rmse",
      "signature": "rmse(f, truth)",
      "doc": "Racine de l'erreur quadratique moyenne par rapport à `truth`."
    },
    {
      "name": "sd",
      "signature": "sd(f)",
      "doc": "Écart type empirique corrigé (ddof=1) des répétitions valides."
    },
    {
      "name": "summary",
      "signature": "summary(k)",
      "doc": "Lit une grandeur globale renvoyée dans `MethodResult.summary`."
    },
    {
      "name": "var",
      "signature": "var(f)",
      "doc": "Variance empirique corrigée (ddof=1) des répétitions valides."
    }
  ],
  "functions": [
    "abs",
    "ar1",
    "arccos",
    "arcsin",
    "arctan",
    "arctan2",
    "ceil",
    "clip",
    "cos",
    "cosh",
    "cumprod",
    "cumsum",
    "exp",
    "floor",
    "isfinite",
    "isnan",
    "log",
    "log10",
    "log2",
    "max",
    "maximum",
    "mean",
    "median",
    "min",
    "minimum",
    "ols_match",
    "quantile",
    "round",
    "sign",
    "sin",
    "sinh",
    "sort",
    "sqrt",
    "std",
    "sum",
    "tan",
    "tanh",
    "var",
    "where"
  ],
  "generator_functions": [
    {
      "name": "law",
      "signature": "law('<loi>')",
      "doc": "tirage dans une loi du registre (voir laws)"
    },
    {
      "name": "normal",
      "signature": "normal()",
      "doc": "loi normale centrée réduite"
    },
    {
      "name": "uniform",
      "signature": "uniform()",
      "doc": "loi uniforme standardisée (moyenne 0, variance 1)"
    },
    {
      "name": "bernoulli",
      "signature": "bernoulli(p)",
      "doc": "booléen vrai avec la probabilité p"
    },
    {
      "name": "idx",
      "signature": "idx",
      "doc": "indice de l'observation, de 0 à n - 1"
    },
    {
      "name": "@h.<id>",
      "signature": "@h.<id>",
      "doc": "loi ou expression de l'option choisie"
    }
  ],
  "constants": [
    "e",
    "pi"
  ]
}
