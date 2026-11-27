# Crash-Test

Des QCM de révision où la correction est une expérience : **casser une hypothèse d'un théorème, mesurer ce qui cède, appliquer la correction.** Projet du hackathon ENSAI.

- **Référence complète** : [docs/cahier_crash_test.pdf](docs/cahier_crash_test.pdf) (source `.tex` à côté).
- **Règles de travail et formats** : [CLAUDE.md](CLAUDE.md), à lire en entier (il fait foi sur les écarts avec le cahier).
- **Où en est-on** : [docs/passation.md](docs/passation.md) (note de relève la plus récente en haut) et [docs/notes/](docs/notes/) (une note par rôle).

---

## Installation (une fois)

Prérequis : **git**, **Node.js 20 ou plus**, **uv** (gestionnaire Python ; il installe lui-même Python 3.12).

```bash
# uv, s'il manque (Windows PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# uv (macOS, Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone https://github.com/Kilian-c/Hackathon-ENSAI.git
cd Hackathon-ENSAI
uv sync                          # moteur : crée .venv avec les versions fixées dans uv.lock
cd frontend && npm install       # interface
```

## Commandes

| But | Commande | Où |
|---|---|---|
| Lancer le moteur (port 8000) | `uv run uvicorn backend.main:app --reload --port 8000` | racine |
| Lancer l'interface (port 5173, relaie `/api` vers 8000) | `npm run dev` | `frontend/` |
| Tests du moteur | `uv run pytest -q` | racine |
| Style Python | `uv run ruff check .` | racine |
| Types de l'interface | `npm run check` | `frontend/` |
| Tests de l'interface | `npm test` | `frontend/` |
| Construire l'interface | `npm run build` | `frontend/` |
| Contexte pour un LLM de discussion | `node scripts/pack.mjs <r1\|r2\|r3\|r4> [--diff \| --full]` | racine |

**Rien n'entre dans `main` sans les quatre vérifications au vert** : `pytest`, `ruff check`, `npm run check`, `npm test`.

---

## Travailler avec un LLM de discussion (sans accès au dépôt)

Pour R2 et R4, qui codent avec un LLM en conversation. Le LLM doit **voir tout ce qui existe** (sinon il invente des noms et des formats incohérents), sans payer tout le code en entier. D'où un pack **hybride** :

- **Partie A, en entier** : `CLAUDE.md`, la dernière passation, vos notes et les fichiers de votre rôle (ceux que le LLM a le droit de modifier).
- **Partie B, compressée** : tout le reste du dépôt, front et back, réduit aux signatures, types et docstrings (les corps de fonctions sont omis). Le LLM voit les noms, les types et les formats des autres, et sait qu'il ne doit pas réécrire ces fichiers.
- Le cahier, les fichiers de verrouillage et les images sont exclus de tout export (`.repomixignore`).

| Commande | Produit | Quand |
|---|---|---|
| `node scripts/pack.mjs r2` | `context/r2.md`, hybride (environ 35 000 tokens aujourd'hui) | début de conversation |
| `node scripts/pack.mjs r2 --diff` | `context/r2-diff.md`, seulement les fichiers modifiés depuis votre dernier pack, en entier | après un `git pull` ou vos changements |
| `node scripts/pack.mjs r2 --full` | `context/r2.md`, tout le dépôt en entier (environ 50 000 tokens aujourd'hui, davantage ensuite) | si votre LLM a une grande fenêtre |

1. **Début de conversation** : collez `context/r2.md` en premier message, avec : « Je suis R2. Lis ce contexte en suivant ses consignes, puis attends ma demande. »
2. **En cours de conversation** : collez `context/r2-diff.md` en disant « Voici les fichiers qui ont changé ».
3. **Si le LLM a besoin d'un fichier de la partie B en entier**, il doit le demander : collez-le simplement.
4. **Nouvelle conversation** quand le LLM commence à oublier ou à se contredire : refaites un pack complet. C'est moins cher que de traîner un long historique.

Le code renvoyé par le LLM : collez-le dans le bon fichier, lancez les tests, puis commitez sur une branche (`r2/methodes-ols`). Le dossier `context/` n'est jamais commité.

---

## Arborescence

Propriétaires : **R1** moteur et API · **R2** maths et contenu · **R3** (Kilian) interface · **R4** écrans secondaires et qualité. Chacun ne modifie que ses fichiers (détail : [CLAUDE.md](CLAUDE.md), section 3). **[Contrat]** : figé après le tag `contracts-v1` (H4). *(à venir)* : prévu, pas encore créé.

```text
Hackathon-ENSAI/
├── CLAUDE.md                       Règles pour les assistants IA et l'équipe                 R3
├── README.md                       Ce fichier                                               R3
├── pyproject.toml, uv.lock         Dépendances Python (versions fixées)                      R1
├── Dockerfile                      Image du moteur (à venir)                                 R1
├── docs/
│   ├── cahier_crash_test.{tex,pdf} Cahier de cadrage (référence)
│   ├── passation.md                Notes de relève (H9, H17, H23), la plus récente en haut  tous
│   └── notes/r1.md … r4.md         Notes personnelles, une par rôle                         chacun
├── experiments/                    Une expérience = un fichier YAML                          R2
│   ├── regression_lineaire.yaml    P0, modèle du générateur random
│   ├── test_student.yaml           P0, cible relative (puissance)
│   └── pendule_euler.yaml          P0, modèle du générateur ode
├── backend/
│   ├── main.py                     Point d'entrée FastAPI                                    R1
│   ├── contracts.py                [Contrat] Requêtes et réponses de l'API                   R1
│   ├── api/                        Routes /api/run, /api/sweep, /api/training/session        R1
│   ├── engine/
│   │   ├── schema.py               [Contrat] Schéma YAML v1                                  R1
│   │   ├── loader.py               Lecture du YAML, erreurs avec numéro de ligne             R1
│   │   ├── expr.py, rng.py, state.py  Expressions, aléatoire, état canonique                 R1
│   │   ├── method_contract.py      [Contrat] Décorateur et MethodResult                      R2
│   │   ├── laws.py, aggregators.py Lois et agrégateurs                                       R2
│   │   ├── sanitize, runner, training .py  (à venir)                                         R1
│   │   └── generators/             random (ode à venir)                                      R1
│   └── methods/                    ols_ci, one_sample_test, integrate                        R2
├── tests/                          test_engine, test_experiments, tests des méthodes ;
│                                   test_api (R1) et test_loader (R4) à venir
├── scripts/
│   ├── pack.mjs                    Contexte pour LLM de discussion                           R3
│   ├── gen_types.sh                contracts.py + schema.py vers types.gen.ts (--check)     R3
│   ├── export_schema.py            JSON Schema des contrats, lu par gen_types.sh             R3
│   └── make_fixtures.py            Fixtures de l'interface (simulation provisoire)           R1
└── frontend/                       Vite + Svelte 5 + TypeScript                              R3
    ├── scripts/test.mjs            Lanceur de Vitest (corrige c: en C: sous Windows)
    └── src/
        ├── main.ts, App.svelte     Point d'entrée, navigation
        ├── styles/tokens.css       Seule source des couleurs et espacements
        ├── lib/
        │   ├── roles.ts            Style de chaque rôle et verdict (trait, marqueur)
        │   ├── equation.ts         Règle de couleur des termes de l'équation
        │   ├── views.ts            Format des vues attendu du moteur
        │   ├── plot.ts             Construction des graphiques Plotly
        │   ├── types.gen.ts        Généré depuis contracts.py et schema.py, jamais à la main
        │   ├── executor.ts, state.ts  Client API, état et lien de partage
        │   ├── lab.ts, labSource.ts, format.ts  Règles du Laboratoire, source des données, nombres
        │   └── calibration.ts      Crans de confiance, score de Brier (à venir)            R4
        ├── components/
        │   ├── PlotlyChart.svelte  Le composant graphique unique
        │   ├── DynamicEquation.svelte, Tex.svelte  Équation dynamique (KaTeX)
        │   ├── lab/                Laboratoire
        │   ├── training/           Entraînement (à venir)
        │   └── home/, summary/, ImportView.svelte  Accueil, Bilan, Import (à venir)         R4
        ├── fixtures/               Faux résultats JSON, puis vrais (make_fixtures)          R1
        └── dev/                    Banc d'essai et specs de repli (à supprimer plus tard)
```

---

## Git en bref

- Petites branches nommées par rôle (`r1/runner-cache`, `r4/galerie`), petits commits fréquents.
- Avant de pousser : `git pull --rebase`, puis les quatre vérifications.
- La nuit, l'interface avance sur des branches relues par Kilian ; R1 fusionne le moteur sur `main` dès que les tests passent.
- Ne commitez jamais `context/`, `repomix-output.*`, `.env`.
