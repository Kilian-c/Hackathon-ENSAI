# CLAUDE.md : Crash-Test (hackathon ENSAI, code jusqu'à H25, pitch à H29)

Ce fichier est écrit pour toi, l'assistant IA. Lis-le en entier au début de chaque session, avant toute action.
La référence complète est le cahier de cadrage : `docs/cahier_crash_test.pdf` (source : `docs/cahier_crash_test.tex`).
Ce fichier en résume tout ce dont tu as besoin pour coder. En cas de doute, le cahier fait foi, **sauf pour les écarts assumés ci-dessous** ; les numéros de section ci-dessous y renvoient.

### Écarts assumés avec le cahier (ce fichier fait foi)

- **Expériences P0 (décision de H4, remplace partout ailleurs « les 3 expériences P0 »)** : uniquement des théorèmes vus en cours. Les quatre sont `regression_lineaire.yaml` (intervalle de confiance d'une pente ; Newey-West et Anscombe retirés), `theoreme_central_limite.yaml`, `multicolinearite.yaml` et `tests_multiples.yaml`. `test_student.yaml` et `pendule_euler.yaml` sont **abandonnées** : n'y consacrez plus de temps, et le générateur `ode` n'est plus nécessaire en P0. Les deux fichiers restent dans le dépôt tant que les tests et les fixtures s'en servent. Les passages ci-dessous qui les décrivent (sections 1, 7, 9, 12, 13) ne valent plus que pour ces anciens fichiers.
- **Avance à H6,5 (18 h 30, décision de Kilian)** : R2 et R3 ont déjà écrit l'essentiel du moteur (`run()`, `/api/run`, `/api/sweep` à 1 ou 2 axes, `/api/training/session`), et Laboratoire, Entraînement et Bilan tournent. Donc : **jalon P0 avancé à H9 (21 h)** ; chaque rôle passe au P1 dès que son reste de P0 est fait, sans attendre le jalon ; priorités P1 : **mécaniques visuelles** puis **Import + Supabase** ; la liste de coupes s'applique au P1 à H17 (section 13). Nouveau planning et tâches par rôle : section 2.
- **Expériences jouables** : les 4 du cours (ci-dessus) et 3 du catalogue de R2, de niveau 1 : `somme_des.yaml`, `seuil_roc.yaml`, `carres_residus.yaml`. `level` vaut « 1 » (Découverte), « 2 » (Intermédiaire) ou « 3 » (Avancé). Student et le pendule partent dans `experiments/archives/` : le registre ne lit que `experiments/*.yaml`, sans sous-dossiers, donc ils sortent de l'accueil et des séries ; les tests qui s'en servent pointent vers le nouveau chemin.
- **Planning** : le cahier suppose 30 h à partir de 9 h. Ici, le départ est à **12 h**, le code s'arrête le lendemain à **13 h (H25)** et le pitch a lieu à **17 h (H29)**. Les créneaux de la section 2 sont recalculés.
- **Entraînement** : une seule route `POST /api/training/session`, `seed` facultative, pas de réserve de séries en P0, `count = min(10, questions disponibles)`. Le cahier (tableau des routes, annexe C.5 et arborescence) décrit encore deux routes `GET /api/training/next` et `GET /api/training/session` avec une réserve : **ignore-les**, voir section 8.
- **Les 3 YAML de référence sont déjà dans `experiments/`**, extraits du `.tex` (annexe B.1 à B.3). Ne les recopie pas une seconde fois : pars de ces fichiers. Seul changement par rapport au cahier : le `explain` du contre-exemple `cauchy-petit-n` ne contient plus de chiffre écrit en dur.
- **Nombre de questions** : le cahier n'en donne que 3 (régression), 2 (Student) et 1 (pendule). R2 a complété pour atteindre 3 par expérience (section 9).
- **Seuil de Student** : la puissance de `test_student.yaml` a `broken_beyond: 0.30` (0,25 dans le cahier), après simulation (section 9).

### Rôles et entraide

- **R3 = Kilian** (interface), qui pourra aussi aider R1 sur le moteur. **R4** pourra reprendre une partie des tâches d'interface de R3. Dans ces cas, la règle de la section 3 s'applique au **fichier**, pas à la personne : on prévient le propriétaire du fichier et il relit avant fusion.

---

## 0. Au début de chaque session (obligatoire)

1. **Identifie la personne et son rôle.** Si elle ne l'a pas dit, demande : « Quel est votre rôle : R1 (moteur), R2 (maths et contenu), R3 (interface, Kilian) ou R4 (écrans secondaires) ? »
2. **Situe-toi dans le planning (section 2 de ce fichier).** Le départ (H0) est à 12 h : demande seulement l'heure actuelle et déduis le créneau en cours. Le gel du code est à H25 (13 h le lendemain).
3. **Lis la dernière note de passation** dans `docs/passation.md` (la plus récente en haut), puis `docs/notes/<rôle>.md` de la personne, et lance `git status` et `git log --oneline -10`.
4. **Annonce en 3 lignes au plus** : le créneau en cours, la prochaine tâche du rôle selon le planning, et ce qui bloque d'après la passation. Puis attends la confirmation ou commence si la demande est claire.

Si la demande de la personne sort de son rôle ou de son créneau, dis-le en une phrase, puis fais ce qu'elle demande si elle confirme.

---

## 1. Le projet en 10 lignes

- Crash-Test : des QCM de révision où la correction est une simulation. Pour chaque théorème : **casser une hypothèse, mesurer ce qui cède, appliquer la correction**.
- Deux modes sur les mêmes fichiers : **Laboratoire** (manipuler) et **Entraînement** (QCM, crans de confiance, score de Brier, écran Bilan).
- Une expérience = **un fichier YAML** dans `experiments/`, lu par **une seule fonction** `run(experiment, state) -> RunResult`.
- **Jamais de code propre à un théorème** : aucun `if experiment.id == "..."`, ni en Python ni en Svelte. Si tu en as besoin, c'est que la solution passe par le YAML.
- Calcul **déterministe** : même état + même graine = même résultat, octet pour octet.
- Stack : Python (FastAPI, NumPy, SciPy ; statsmodels seulement dans les tests), Svelte 5 + Plotly.js + KaTeX, Supabase seulement pour le partage d'expériences importées (P1).
- Déploiement : interface sur Cloudflare, moteur dans une image Docker sur un hébergeur Python gratuit, version locale de secours sur un seul port.
- Équipe : R1 + R4 la nuit, R3 (Kilian) + R2 le jour.
- Expériences jouables (écarts assumés ci-dessus) : régression, TCL, multicolinéarité, tests multiples (cours) ; somme de dés, seuil et ROC, carrés des résidus (catalogue, niveau 1). Student et pendule : abandonnés, dans `experiments/archives/`.
- Interface **en français, vouvoiement partout** (boutons, énoncés, erreurs, explications).

---

## 2. Le planning (départ à 12 h ; code figé le lendemain à 13 h ; pitch à 17 h)

**Planning revu à H6,5 (18 h 30)** : le P0 est presque vert, donc le jalon P0 passe à H9 et le temps gagné va au P1 (mécaniques visuelles, puis Import + Supabase). Les relèves (H9, H17, H23), le gel à H25 et le pitch à H29 ne changent pas. Ce fichier fait foi sur les heures et sur les tâches ; le cahier fait foi sur le contenu des fonctionnalités (fiches de l'annexe F).

| Créneau | Heures | Qui | Objectif |
|---|---|---|---|
| H0 à H6,5 | 12 h à 18 h 30 | Tous | **Fait** : contrats, moteur, API P0, 7 expériences, Laboratoire, Entraînement, Bilan |
| H6,5 à H9 | 18 h 30 à 21 h | R3 + R2 | Fermer le P0 restant, puis premières mécaniques P1 |
| H9 à H10 | 21 h à 22 h | Tous | Relève, **jalon P0 avancé** (critère ci-dessous), relecture par R1, première mise en ligne |
| H10 à H17 | 22 h à 5 h | R1 + R4 | Import + `/api/validate` + Supabase, galerie, P1 côté moteur, tests P1 |
| H17 à H19 | 5 h à 7 h | Tous | **Jalon P1** : ce qui n'est pas vert est coupé dans l'ordre de la section 13 |
| H19 à H23 | 7 h à 11 h | R3 + R2 | Prédictions, Domaine de validité, contenus définitifs, démo et pitch |
| H23 à H25 | 11 h à 13 h | Tous | Démo de bout en bout, intégration P1 terminée ; **H25 (13 h) : plus aucune fonctionnalité** |
| H25 à H29 | 13 h à 17 h | Tous | Corrections de bugs seulement, audit, vidéo de secours, répétitions ; **pitch à 17 h** |

### H6,5 à H9 (18 h 30 à 21 h), R3 + R2, dans l'ordre
**R3 (Kilian, interface)**
1. Reste de P0 : niveau affiché en mots (« Découverte », « Intermédiaire », « Avancé ») dans `App.svelte` et `LabView.svelte` ; `segments` dessinés par `plot.ts` (séries sans `y` : seuil et ROC, carrés des résidus) ; vérifier à l'œil `h1` (rôle `truth`, orange) dans les vues `distribution`.
2. **Banc de méthodes** (annexe F, fiche « Banc de méthodes ») : afficher ou masquer chaque alternative sans aucun appel (tout est dans `RunResult`), `on=` dans l'URL (`lib/state.ts`).
3. **Trajectoires** du TCL (`Series.paths`, TODO dans `plot.ts`), dès que R2 les sert.
4. **Ajout de points par clic** (fiche F) : `extra_points` existe déjà dans `EngineState` (20 au plus), activé par `allow_point_injection` de la vue.

**R2 (contenu, et moteur à la place de R1 : prévenir R1, qui relit à H9)**
1. Student et pendule vers `experiments/archives/` ; mettre à jour les chemins dans `tests/test_api.py`, `tests/test_runner.py`, `tests/test_integrate.py` ; régénérer avec R3 les specs de repli (`frontend/src/dev/specs/`).
2. `Dockerfile` du moteur (`OMP_NUM_THREADS=1`, port de l'hébergeur choisi) pour la mise en ligne de H9.
3. Pour R3 : `paths` servis dans la vue du TCL (`runner.py`) ; `auto_sweep` rempli dans les YAML qui s'y prêtent (régression, TCL, tests multiples).
4. Si tout est vert : une expérience de plus du catalogue (simulée avant d'écrire les seuils, 3 questions, tests de contenu verts).

### H9 à H10 (21 h à 22 h), tous
- R1 relit ce qui a été fusionné sans lui : `runner.py`, `training.py`, `fastexpr.py`, `sweep.py`, `api/registry.py`, `api/routes.py`, `Dockerfile`.
- Jalon P0 vérifié (critère ci-dessous) ; note de relève dans `docs/passation.md`.
- Première mise en ligne : interface sur Cloudflare (`frontend/DEPLOIEMENT.md`), moteur sur l'hébergeur.

### H10 à H17 (22 h à 5 h), R1 + R4
**R1 (moteur et API)**
1. `POST /api/validate` (P1, annexe C du cahier) : erreurs par ligne (le chargeur les donne déjà) et tests 1, 3, 4, 10 lancés sur le YAML reçu. `/api/run` accepte déjà `raw_content`.
2. Journal des tirages : `draw_log` servi pour les expériences qui le déclarent, vérifié par un test.
3. Tests P1 : 2, 5, 6, 7, 9 et `tests/test_properties.py`.
4. Seulement si tout est vert : budget (réduction automatique de `repeat`), réserve de séries, lenteur de Tukey au premier appel.

**R4 (écrans secondaires)**
1. Galerie (`components/home/`) à la place de l'accueil provisoire de `App.svelte` : filtres et tri par niveau et discipline, accès à l'Entraînement et au Bilan (`?bilan`).
2. Lien vers le Bilan sur l'écran de fin de l'Entraînement ; relecture du Bilan écrit par R3 (`lib/calibration.ts`, `components/summary/CalibrationSummary.svelte`).
3. **Écran Import** (`ImportView.svelte`) : coller ou déposer un YAML, erreurs par ligne via `/api/validate`, ouverture dans le Laboratoire avec `raw_content`.
4. **Partage Supabase** : table dans `supabase/schema.sql` (fichier de R3 : Kilian relit au matin), enregistrer une expérience importée et l'ouvrir par lien.

### H17 à H19 (5 h à 7 h), tous
Jalon P1 : chaque mécanique commencée est terminée ou coupée (section 13). Note de relève H17.

### H19 à H23 (7 h à 11 h), R3 + R2
- R3 : questions de prédiction dans l'Entraînement ; balayage automatique (pause sur la mesure primaire, fiche F) s'il n'est pas fait ; Domaine de validité si le temps le permet.
- R2 : questions `prediction` dans les YAML et servies par `training.py` ; vue `validity_domain` côté moteur si R3 la fait ; contenus définitifs (textes et seuils revérifiés sur le vrai moteur).
- Les deux : **démo** (graine fixée, lien direct vers la question de démonstration de la régression, cahier section 7) et **nouveau déroulé du pitch** : le passage « pendule, 2:45 à 3:30 » est remplacé par une autre expérience du cours (TCL sous Cauchy, que rien ne répare, ou tests multiples et Bonferroni) ; l'Import est montré à 3:30 s'il est prêt.

### Historique : H0 à H4, dans l'ordre (fait)
- **H0 à H1 (les 4)** : dépôt (fait : arborescence, `docs/`, `docs/passation.md`, les 3 YAML de référence dans `experiments/`), puis **lecture commune** de `experiments/regression_lineaire.yaml` : c'est le modèle des autres.
- **H1 à H2** : `backend/engine/schema.py` qui charge **les 3 YAML de référence** (R1) ; `method_contract.py`, `aggregators.py`, `laws.py` avec leur test de conformité (R2) ; R2 relit `test_student.yaml` et signale à R1 tout besoin du schéma avant le gel.
- **H2 à H3** : `backend/contracts.py` (requêtes et réponses de `/api/run`, `/api/sweep`, `/api/training/session`) (R1) ; `roles.ts`, `tokens.css`, règle de couleur dans `equation.ts` (R3).
- **H3 à H4** : `scripts/gen_types.sh` et premier `types.gen.ts` (R3) ; faux JSON des vues P0 et d'une série d'Entraînement, validés par `contracts.py` (R1) ; `tests/test_loader.py` (R4) ; FastAPI + Vite/Svelte 5 + proxy `/api`, projet Cloudflare, `Dockerfile` pour l'hébergeur choisi avant le hackathon (Hugging Face Spaces ou Render).
- **Jalon tranche verticale (H4, 16 h)** : `POST /api/run` (générateur `random` + MCO) renvoie une vraie courbe affichée par `PlotlyChart.svelte`. Tag git `contracts-v1`.

### Critère du jalon P0 (avancé à H9, 21 h)
Sur les 7 expériences jouables : Laboratoire (casser, Correction, Référence, verdicts) et Entraînement minimal (question générée et vérifiée, crans, validation par simulation) tournent sur la vraie API, et les tests P0 (1, 3, 4, 8, 10) passent.

---

## 3. Qui possède quoi (ne modifie que les fichiers du rôle de la personne)

| Rôle | Fichiers |
|---|---|
| **R1, moteur et API** | `backend/main.py`, `backend/contracts.py`, `backend/api/*`, `backend/engine/{schema,expr,rng,sanitize,runner,loader,training}.py`, `backend/engine/generators/`, `scripts/make_fixtures.py`, `frontend/src/fixtures/`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `tests/{test_engine,test_api,test_properties}.py` |
| **R2, maths et contenu** | `backend/methods/*`, `backend/engine/{method_contract,laws,aggregators}.py`, `experiments/*.yaml`, `tests/{test_experiments,test_method_contract}.py` |
| **R3, Kilian, interface** | `frontend/` (sauf `fixtures/`, `lib/calibration.ts`, `components/{home,summary}/`, `ImportView.svelte`), `scripts/gen_types.sh`, `supabase/schema.sql`, `CLAUDE.md` |
| **R4, écrans secondaires** | `frontend/src/components/{home,summary}/`, `frontend/src/components/ImportView.svelte`, `frontend/src/lib/calibration.ts`, `tests/test_loader.py` |

**Chantier « modularité » en cours (R1 + R3)** : les fichiers listés dans `docs/chantier_modularite.md` sont réservés. Ne les modifie pas pour une autre personne sans prévenir celle que le fichier indique, même s'ils appartiennent à son rôle dans le tableau ci-dessus.

**Fichiers de contrat** : `backend/contracts.py`, `backend/engine/schema.py`, `backend/engine/method_contract.py`. Après le tag `contracts-v1`, **ils ne changent plus pendant le hackathon**. `frontend/src/lib/types.gen.ts` est **généré**, ne l'édite jamais à la main.

---

## 4. Ce que tu ne dois jamais faire

- Écrire du code propre à un théorème (`if experiment.id == ...`, un composant `RegressionView.svelte`, etc.).
- Modifier un fichier de contrat après H4, ou éditer `types.gen.ts` à la main.
- Inventer un format, un champ YAML, une route ou une clé JSON qui n'est pas dans ce fichier ou dans le cahier. Utilise d'abord les **sorties prévues** (section 11).
- Utiliser `eval`, `exec`, ou une autre source d'aléatoire que le `rng` reçu (pas de `np.random.seed`, pas de `random`).
- Boucler en Python sur les répétitions, ou appeler `statsmodels` dans une méthode (seulement dans les tests, comme référence).
- Écrire du Svelte 4 : pas de `export let`, pas de `$:`, pas de `on:click` (utilise `onclick`).
- Tutoyer l'utilisateur dans l'interface, ou écrire un texte d'interface en anglais.
- Commencer une fonctionnalité P1 avant que le jalon P0 soit vert, sans le signaler.
- Fusionner sur `main` sans `uv run pytest -q`, `uv run ruff check`, `npm run check` et `npm test` au vert.
- Ajouter une fonctionnalité après H25 (13 h).

---

## 5. Si tu es perdu ou bloqué

1. La réponse est-elle dans ce fichier ? Applique-la.
2. Sinon, dans le cahier (annexes B à F pour les formats) ? Applique-la et cite la section dans ton message.
3. Sinon, une **sortie prévue** (section 11) couvre-t-elle le besoin ? Utilise-la.
4. Sinon : **ne change aucun contrat**. Fais la version la plus simple qui respecte les contrats, ajoute un `TODO(passation)` dans le code, une ligne dans `docs/passation.md`, et préviens la personne en une phrase.
5. Si une tâche te prend plus de 45 minutes sans progrès visible, arrête-toi et propose de simplifier ou de couper (section 13).

---

## 6. Commandes

```bash
# Moteur
uv sync
uv run uvicorn backend.main:app --reload --reload-include "*.yaml" --port 8000   # recharge aussi quand un YAML change
uv run pytest -q
uv run ruff check .

# Interface
cd frontend && npm install && npm run dev        # proxy /api vers le port 8000
cd frontend && npm run check
cd frontend && npm test                         # tests unitaires (Vitest) des règles de lib/
cd frontend && npm run build                   # sans VITE_API_URL : puis uvicorn sert l'interface sur / (secours, un seul port : frontend/DEPLOIEMENT.md)

# Contrats et fixtures
bash scripts/gen_types.sh                        # contracts.py -> types.gen.ts, schema.py -> experiments/schema.json
uv run python scripts/gen_catalog.py             # registres (méthodes, lois, agrégateurs, fonctions) -> lib/catalog.gen.ts
uv run python scripts/make_fixtures.py           # vrais résultats -> frontend/src/fixtures/
```

Variables : `VITE_API_URL` (adresse du moteur pour l'interface en ligne), `OMP_NUM_THREADS=1` (déterminisme).

---

## 7. Le format YAML (annexe B du cahier : 3 fichiers complets, déjà dans `experiments/`)

**Ne recopie jamais un YAML depuis le PDF** : l'extraction altère les accents (`R é gression`), insère des espaces (`p . n`, `law ( ’ normal ’)`) et perd l'indentation. Les fichiers de `experiments/` ont été extraits du `.tex` par script : pars d'eux, puis vérifie avec `tests/test_loader.py`.

**Après avoir ajouté une méthode, une loi, un agrégateur ou une fonction**, lance `uv run python scripts/gen_catalog.py` et commite `catalog.gen.ts` : le prompt de l'écran Import le lit, et `tests/test_generated.py` échoue tant qu'il n'est pas à jour. **Après un changement de `schema.py`**, `bash scripts/gen_types.sh` régénère aussi `experiments/schema.json`. Ce fichier donne l'autocomplétion et les erreurs du YAML dans VS Code, avec l'extension YAML et le réglage `"yaml.schemas": { "./experiments/schema.json": ["experiments/*.yaml"] }` dans `.vscode/settings.json`, qui n'est pas suivi par git.

Clés de premier niveau d'une expérience :
`schema_version: 1`, `id`, `title`, `discipline`, `level`, `concepts`, `theorem`, `equation`, `params`, `hypotheses`, `counterexamples`, `generator`, `methods`, `measures`, `challenges`, `auto_sweep`, `draw_log` (P1), `views`, `opening_question` (P1), `questions`.

Règles :
- Chaînes de texte **toujours entre guillemets**. Lecture par `yaml.safe_load`, validation Pydantic stricte (`extra="forbid"`), erreurs avec numéro de ligne.
- Une hypothèse ou un paramètre absent d'un état prend sa valeur saine (`healthy_value`) ou sa valeur par défaut.
- **Hypothèses** : `type: continuous | choice | boolean`, `healthy_value` obligatoire, `label`, `category`, `affects: [termes]`, `why`, `when_broken`, `statement_tex`, facultatifs `range` (défaut `[0, 1]` pour un continu : le pendule ne le précise pas), `step`, `ok_label`, `broken_label`, `options`, `robust_expected`, `disabled_when`, `disabled_text`. Une option de choix porte `label` et `law:` (registre) **ou** `expr:` (expression libre).
- **`robust_expected` existe à deux niveaux** : sur l'hypothèse entière (`error_law` dans la régression) ou sur une option (`uniform`, `bimodal` dans Student). Le schéma (R1) accepte les deux ; le test 2 lit l'option d'abord, puis l'hypothèse.
- **Paramètres** : `type: number | boolean`, `label`, `default`, et pour un nombre `min`, `max`, `step`, facultatif `sweep_values`.
- **Mesures sans cible** (`width`, `bp_pvalue`, `energy_drift`, `full_turn`) : informatives, pas de verdict. `target`, `direction`, `ok_within`, `broken_beyond` et `texts` sont donc facultatifs ensemble.
- **Dépendances P1 dans un YAML P0** : la régression contient des entrées qui reposent sur des hypothèses P1 (`autocorr`, `relation`, `ols_match`) : contre-exemples `erreurs-autocorrelees`, `anscombe-courbe`, `anscombe-levier`, et `relation` dans `hc3.repairs`. Les tests P0 (3 et 4) les exécutent. Donc : soit `ar1` et `ols_match` existent dès le P0 (R1 pour la liste blanche, peu de code), soit on **retire ces entrées** du YAML en cas de coupe. Ne laisse jamais une entrée qui fait échouer les tests P0.
- **Méthodes** : liste ; exactement 1 `role: method`, au plus 1 `role: correction`, au plus 2 `role: alternative`, 4 au plus. Champs `id`, `call`, `label`, `args`, `explain` (obligatoire hors méthode principale), `repairs: [hypothèses]`.
- **Mesures** : `agg`, `label`, `unit`, `scale`, `decimals`, `primary` (une seule), `target` (nombre ou `base`), `direction: below | above | both`, `ok_within`, `broken_beyond`, `texts: {ok, warning, broken}` avec `{value}`.
- **Contre-exemples** : `id`, `label`, `explain`, `state`, facultatif `expect: same_summary` (Anscombe).
- **Vues** : `id`, `type`, `title`, `bind` (chemins), facultatifs `sweep`, `axes`, `layers`, `inspect`, `allow_point_injection`, `mode`, `ui`.
- **Questions** : `misconception` (choix avec `reveal_state`, `verify`, `focus_view`, `explain`), `diagnostic_auto` (`view`, `state`, `pathologies: {from: [...]}`), `prediction` (P1).

**Espace de noms des expressions** (le même partout) :

| Nom | Valeur | Où |
|---|---|---|
| `p.<id>` | paramètre | partout |
| `h.<id>` | hypothèse (nombre, booléen, clé d'option) | partout |
| nom nu (`x`, `eps`) | variable du générateur | générateur, `args` |
| `m.<mesure>`, `m.<mesure>.<methode>`, `m.<mesure>_se` | valeur (méthode principale ou donnée), erreur Monte Carlo | défis, `verify` |
| `s.<mesure>` | verdict de la méthode principale : `"ok"`, `"warning"`, `"broken"` | défis, `verify` |
| `base.<mesure>` | valeur de la Référence | défis, `verify` |

Liste blanche des fonctions : fonctions NumPy usuelles (`sqrt`, `exp`, `sin`, `log`, `abs`, `where`...), `law(nom)`, `normal`, `uniform`, `bernoulli`, `ar1(base, rho)`, `ols_match(x, y, a, b, r2)`, l'indice d'observation `idx`, et `@h.<id>` (loi ou expression de l'option choisie). Pas de boucle, pas de compréhension, pas d'attribut commençant par `_`, exposants bornés à 100.

---

## 8. Le moteur (R1, section 4 et annexes C, D du cahier)

**Pipeline de `run()`** : générer le monde, appliquer **toutes** les méthodes, agréger les mesures, calculer verdicts, défis et vues. La Référence = mêmes méthodes sur l'état sain (hypothèses à `healthy_value`, sans points ajoutés, mêmes `params` et `seed`), en cache par jeu de paramètres.

**État** :
- `EngineState` (envoyé au moteur, entre dans le cache) : `params`, `hypotheses`, `extra_points` (20 au plus), `seed`.
- `UiState` (jamais envoyé) : `methods_on`, onglet, calques.
- Forme canonique : valeurs par défaut complétées, continus arrondis au `step`, clés triées, JSON compact ; `state_hash` = 16 premiers caractères du SHA-256. Clé de cache = SHA-256 de `schema_version` + hash du contenu YAML + `state_hash`.

**Aléatoire** (`engine/rng.py`, `engine/laws.py`) :
```python
def rng_for(seed: int, name: str) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(
        np.random.SeedSequence([seed, zlib.crc32(name.encode())])))
```
Un flux par variable, et `method:<id>` pour une méthode. Toute loi est tirée depuis des uniformes par sa fonction quantile, puis standardisée : moyenne 0 et variance 1 quand elles existent, sinon médiane 0 et écart interquartile de la normale (`student_2`, `cauchy`). Lois du registre : `normal`, `uniform`, `exponential`, `student_2`, `cauchy`, `bimodal`.

**Générateurs** :
- `random` : variables triées par dépendances (cycle = erreur au chargement), formes `(repeat, n)` par défaut (`dims: sample` pour `(repeat,)`, `obs_p` pour `(repeat, n, p)`). Les fonctions de tirage ne prennent jamais de taille. `inject` désigne les variables qui reçoivent les points posés au clic, ajoutés à toutes les répétitions après le calcul, jamais à la Référence.
- `ode` : `t_end`, `state` (conditions initiales), `rhs`, `derived` ; fournit `t` (400 points), la solution de référence par variable d'état (`solve_ivp`, tolérance 1e-10) et `system` pour les méthodes. Pas de répétitions.
- `function` : P2, format seulement (`grid`, `variables`).

**Agrégateurs** (`engine/aggregators.py`, R2) : `rate(f)`, `mean(f)`, `bias(f, t)`, `rmse(f, t)`, `sd(f)`, `var(f)`, `median(f)`, `quantile(f, q)`, `first(f)` (répétition 0 = échantillon affiché), `summary(k)`. `f` peut être une expression sur `reps` (`rate(reps.pvalue < 0.05)`). Erreur Monte Carlo : `sqrt(p(1-p)/n)` pour `rate`, `sd/sqrt(n)` pour `mean` et `bias`, `null` sinon. `n` = répétitions valides.

**Verdict** (une seule règle, dans `runner.py`) :
```text
écart = target - value  si direction = below
        value - target  si direction = above
        |value - target| si direction = both
écart = max(écart, 0)    (pour below et above)
ok si écart <= ok_within ; broken si écart > broken_beyond ; warning sinon
target: base  =>  target = valeur de la même méthode à l'état sain
```
La mesure `primary` pilote le badge, l'équation, la sensibilité, le seuil critique et la pause du balayage automatique.

**Répétitions invalides** : `NaN` dans `reps` = répétition exclue et comptée (`invalid_rate`), avertissement au-delà de 5 %. NaN et Infinity sortent en `null` avec un avertissement en français à code stable.

**Routes** (toutes en `def`, pas `async def`) :

| Verbe | Route | Prio. | Rôle |
|---|---|---|---|
| GET | `/api/experiments` | P0 | liste filtrable |
| GET | `/api/experiments/{id}` | P0 | `ExperimentSpec` (le YAML validé) |
| POST | `/api/run` | P0 | `{experiment_id | raw_content, state}` vers `RunResult` |
| POST | `/api/sweep` | P0 (1 axe), P1 (2 axes) | `SweepResult` |
| POST | `/api/training/session` | P0 | `{filter, count, seed?}` vers `TrainingSessionResponse` (série vérifiée) |
| POST | `/api/validate` | P1 | erreurs par ligne et tests |

**`RunResult`** (annexe C) : `schema_version`, `state_hash`, `methods[] {id, role, label, explain}`, `measures.<id> {label, unit, scale, decimals, primary, target, direction, ok_within, broken_beyond, values{methode}, mc_se{methode}, states{methode}, texts{methode}, baseline{methode}}`, `equation.terms.<terme>.violated_by[]`, `challenges[] {id, passed}`, `views[]`, `draw_log` (ou `null`), `invalid_rate{methode}`, `warnings[] {code, text}`, `repeat_used`, `compute_ms`.

**Balayage** : un axe = `h.<id>` ou `p.<id>`. Par défaut : 11 points de 0 à 1 (continu), toutes les options (choix), les deux valeurs (booléen), `sweep_values` (paramètre ; sans ce champ, pas balayable). Même graine dans toutes les cases. Réponse : `axes`, `measure`, `values`, `mc_se`, `states` (2D pour 2 axes, indexés `[axe 2][axe 1]`), `critical{methode: {warning_at, broken_at} | null}` (un seul axe continu, interpolé), `target`, `ok_within`, `broken_beyond`, `direction`, `current`, `repeat_used`, `reduced`, `compute_ms`.

**Entraînement** (`engine/training.py`) : une seule route, `POST /api/training/session` avec `{filter, count, seed}`. `seed` est facultative : absente, le serveur en tire une et la renvoie (écart assumé avec l'annexe C.5 du cahier, sans effet sur le reste du contrat ; dans `contracts.py` : `seed: int | None = None`). Une série est déterminée par `(filtre, graine, hash du contenu des YAML)` et compte `count = min(10, questions disponibles)`.
- Une question `misconception` apparaît **une seule fois** par série.
- Une question `diagnostic_auto` peut revenir : la pathologie cachée change à chaque tirage, et le `qid` se termine par un indice (`.../0`, `.../1`).
- Fabrication : tirer les questions et leurs paramètres, remplir les énoncés, lancer chaque `reveal_state` et contrôler `verify` (5 tirages au plus, sinon question retirée et listée dans `dropped`), fabriquer les pathologies, mélanger les choix.
- **Pas de réserve de séries en P0.** La fabrication à la demande (15 s au plus) suffit. Une réserve en arrière-plan reste une optimisation, à ne faire qu'après le jalon P0.
- L'interface affiche « Série de N questions », jamais un « 10 » en dur.

**Plafonds** (identiques pour tout YAML) : `repeat` <= 1000, `n` <= 5000, 4 méthodes, 30 variables, expressions <= 300 caractères, YAML <= 64 Ko, 20 points ajoutés, balayage <= 21 points ou 144 cases, délais 2 s (`/api/run`), 15 s (`/api/sweep` et série à la demande). Budget avec réduction automatique de `repeat` : P1.

---

## 9. Les méthodes (R2, annexe D du cahier)

```python
@register_method(
    "ols_ci",
    provides={
        "reps": ["est", "low", "high", "hit", "width", "bp_pvalue"],
        "example": ["x", "y", "y_hat", "y_mean", "resid", "leverage", "cooks_d"],
    },
    cost="repeat * n",
)
def ols_ci(*, x, y, truth, alpha, se_type, rng) -> MethodResult:
    # x, y : (repeat, n). se_type : "classic", "HC3" ou "HAC".
    ...
```
- Retour : `MethodResult(reps, example, curves, summary)` ; `reps` en `(repeat,)`, `example` en `(n,)` (répétition 0), `curves` et `summary` facultatifs. Exactement les clés déclarées.
- **Formules fermées en NumPy**, vectorisées sur l'axe 0 ; moins de 200 ms pour `repeat = 500`, `n = 1000`. `scipy.stats.ttest_1samp` et `scipy.stats.wilcoxon` acceptent `axis`.
- Une méthode ne calcule **jamais** une couverture ou un taux de rejet (c'est l'agrégateur), et ne construit jamais un JSON de vue.
- Méthodes P0 : `ols_ci` (classic, HC3, HAC, Breusch-Pagan), `one_sample_test` (student, wilcoxon ; `provides` : `reps: [reject, reject_h1, pvalue, stat]`, `example: [x0]`), `integrate` (euler, rk4 ; `provides` : `curves: [t, theta]`, `summary: [max_rel_error, energy_drift, full_turn]`, `cost: "t_end / dt"`).
- **Règle de R2** : toute paire méthode/correction est **simulée avant d'être écrite** dans un YAML. Rappel : Wilcoxon teste le centre de symétrie, pas la moyenne ; il ne corrige pas l'asymétrie (15 % de rejets à tort sous loi exponentielle à n = 25).

**Chiffres de référence vérifiés par simulation** (graine 42, 500 répétitions ; ce sont des ordres de grandeur, pas des tests exacts) :
- Régression, n = 150 : couverture classique 95 % à l'état sain, environ 80 % à `hetero = 0.8` (HC3 vers 97 %) ; loi des erreurs sans effet (robust_expected) ; x et erreurs en AR(1) : classique et HC3 vers 75 %, Newey-West vers 87 % ; défi Breusch-Pagan : à n = 30 et `hetero = 0.7`, environ 1 échantillon sur 5 a une p-value > 0,05.
- Student, n = 25, implémentation réelle : puissance de 67 % (normale) contre 11 % (Cauchy) ; Wilcoxon 66 % contre 39 %. À n = 200, Student reste bas sous Cauchy (environ 14 %), Wilcoxon monte à 100 %. Les textes de mesures utilisent `{value}`, jamais un chiffre écrit en dur.
- Pendule, θ0 = 1,2 rad, 5 s, `dt = 10 ** (-3.5 + 2.5 * h.pas)` : erreur d'Euler 1,2 % à h = 0, 45 % à h = 0,6, tour complet à partir de h = 0,9 ; RK4 exact partout.

**`test_student.yaml`** (dans `experiments/`, version de l'annexe B.2 du cahier, qui fait foi sauf pour `broken_beyond` et la troisième question) :
- Noms : hypothèse `h.loi` (5 lois symétriques), paramètres `p.n` et `p.delta` ; générateur `x0 = @h.loi`, `x1 = x0 + p.delta`.
- Méthodes : `student` (principale) et `wilcoxon` (correction, `repairs: [loi]`), appel `one_sample_test`.
- Mesure primaire : puissance `rate(reps.reject_h1)`, `target: base`, `direction: below`, `ok_within: 0.10`, `broken_beyond: 0.30`.
- **Point de vigilance** (graine 42) : sous Cauchy à n = 25, Wilcoxon perd 0,27 de puissance et reste Fragile (test 3 accepté). Sous Student à 2 ddl, Student perd 0,32 et reste Rompu, avec seulement 0,02 de marge : sur 100 graines, il est Fragile 13 fois. Ne changez ni ce seuil ni la graine par défaut sans rejouer la simulation.
- Chaque expérience contient au moins 3 questions.

---

## 10. L'interface (R3 et R4, sections 2, 3 et annexes E, F du cahier)

- **Svelte 5 uniquement** : `$props()`, `$state()`, `$derived()`, `$effect()`, événements `onclick`. Pars de `frontend/src/components/_Modele.svelte`.
- **Types** : importe depuis `lib/types.gen.ts`. Données de développement : `frontend/src/fixtures/`.
- **Un seul client API** (`lib/executor.ts`) : requêtes regroupées (100 ms) et anciennes requêtes annulées pendant un glissement ; adresse dans `VITE_API_URL`.
- **Un seul composant graphique** (`PlotlyChart.svelte`) : `Plotly.react()` avec `uirevision: 'keep'`, identifiants de séries stables (`<vue>.<emplacement>.<methode>`), bornes d'axes reçues du moteur et conservées tant que `params` et `seed` ne changent pas, points hors cadre au bord avec un triangle.
- **La graine ne change jamais quand on bouge un curseur** ; seul « Nouveau tirage » l'incrémente.
- **Afficher ou masquer une méthode ne fait aucun appel** : toutes les méthodes sont déjà dans `RunResult`.
- **URL** (`lib/state.ts`) : `?exp=regression-lineaire&v=1&p.n=300&h.hetero=0.85&seed=42&on=hc3&tab=repetitions&pts=4.2,-2.0;5.1,3.3`. Entraînement : `?train=<filtre>&seed=<graine>&v=1`. L'interface rappelle `POST /api/training/session` avec cette graine ; aucune route GET. (Un `h=<hash6>` de contenu pourra s'ajouter en P1.)
- **Rôles et styles** (`lib/roles.ts`, `styles/tokens.css`), jamais la couleur seule :

| Rôle | Couleur (thème sombre) | Trait | Marqueur |
|---|---|---|---|
| `method` | `#4ea1ff` | plein, 2 px | rond |
| `correction` | `#3fb950` | plein, 3 px | losange |
| `alternative_1` | `#d2a8ff` | tirets et points | triangle |
| `alternative_2` | `#56d4dd` | points | carré |
| `reference` | `#6e7681` | tirets, 1,5 px | rond creux |
| `truth` | `#f0883e` | plein, 1 px | aucun |
| `rupture` | `#f85149` | plein | croix |
| `injected` | `#e6edf3` | aucun | étoile |

- **Couleur d'un terme de l'équation** (`lib/equation.ts`) :

| Situation | Affichage |
|---|---|
| aucune hypothèse de `violated_by` | version saine, neutre |
| hypothèse cassée, méthode principale Fiable | version saine, neutre |
| hypothèse cassée, méthode principale Fragile ou Rompue | version saine, rouge `#f85149` |
| idem, Correction affichée et Fiable | version corrigée, vert `#3fb950` |
| idem, Correction affichée mais pas Fiable | version corrigée, rouge |

- **Verdicts affichés** : Fiable / Fragile / Rompu (`ok` / `warning` / `broken`), avec la valeur et `± 2 mc_se` quand `mc_se` existe.
- **Validation d'une question** : appeler `/api/run` avec `reveal.state` du choix (ou du bon choix si la réponse est fausse), afficher `focus_view`, `explain` et le `when_broken` de l'hypothèse ; « Ouvrir dans le Laboratoire » ouvre l'URL de cet état. Bilan dans `localStorage`, rangé par identifiant de série.
- **Taille d'une série** : afficher « Série de N questions » avec le `N` reçu, jamais un « 10 » en dur.
- **Crans de confiance** : Je devine = 1/k, Plutôt sûr = (1/k + 0,95)/2, Certain = 0,95. Courbe de calibration à partir d'environ 20 réponses.
- Les 7 mécaniques visuelles ont chacune une fiche dans l'annexe F du cahier (ce que voit l'étudiant, champ YAML, données du moteur, interface, cas limites). Lis la fiche avant de coder une mécanique.

---

## 11. Les sorties prévues (au lieu de modifier un contrat)

| Besoin imprévu | Sortie |
|---|---|
| Une grandeur qu'aucun agrégateur ne calcule | la méthode la renvoie dans `summary`, lue par `summary(k)` |
| Un agrégateur manquant | une fonction de plus dans `engine/aggregators.py` |
| Une loi absente du registre | option avec `expr:` au lieu de `law:` |
| Une nouvelle méthode | une fonction de plus avec `@register_method` |
| Un réglage d'affichage propre à une vue | champ libre `ui: {}` de la vue. Réglages lus par l'interface, avec leur sens dans `VIEW_UI_KEYS` (`lib/plot.ts`) : `x_title`, `y_title`, `log_x`, `log_y`, `aspect: "equal"`, `unit_circle`, `marker_size`, `point_labels`, et pour `heatmap` `zmin`, `zmax`, `decimals` |
| Une série de plus dans une vue | une seconde vue du même type |
| Une vue qui ne se construit pas | la vue de secours `measures_table` s'affiche |

---

## 12. Tests et définition de « terminé »

Un changement est terminé quand :
1. `uv run pytest -q`, `uv run ruff check .`, `npm run check` et `npm test` sont au vert ;
2. aucune erreur dans la console du navigateur ;
3. les textes d'interface sont en français et vouvoient ;
4. aucun code propre à un théorème n'a été ajouté ;
5. le commit est petit et son message dit ce qui marche maintenant.

Tests de `tests/test_experiments.py` (section 4.10 du cahier). **P0 : 1, 3, 4, 8, 10.** P1 : 2, 5, 6, 7, 9 et `test_properties.py`.
1. État sain : la mesure primaire de la méthode principale est `ok`.
2. Chaque hypothèse cassée seule rompt au moins une mesure, sauf `robust_expected`.
3. Chaque méthode ramène à `ok` ou `warning` les hypothèses de son `repairs`.
4. Chaque contre-exemple rompt au moins une mesure, sauf `expect: same_summary` (pente et R² identiques à 1e-9).
5. Chaque défi est atteignable par un balayage.
6. `verify` passe sur au moins 90 % de 50 tirages.
7. Les pathologies d'une question diffèrent d'au moins 3 `mc_se` sur une mesure.
8. Deux exécutions du même état donnent exactement le même résultat.
9. L'état par défaut répond en moins de 500 ms en local.
10. Chaque hypothèse a `why` et `when_broken`, chaque correction et alternative a `explain`.

**Test d'API de l'Entraînement** (`tests/test_api.py`, R1, P0) : `POST /api/training/session` renvoie `min(10, questions disponibles)` questions ; une même `misconception` n'apparaît jamais deux fois dans une série ; sans `seed`, la réponse en contient une ; deux appels avec la même `seed` donnent la même série.

---

## 13. Priorités et coupes (section 6.5 du cahier)

- **P0** (presque fait à H6,5 ; jalon à H9) : les expériences jouables (section 1) ; `run()`, générateur `random`, méthodes en liste, agrégateurs, verdicts, Référence, balayage à 1 axe, cache, plafonds ; Laboratoire (Comprendre, 3 types de contrôles, bouton Correction, Référence, verdicts, équation dynamique, Répétitions, Sensibilité, contre-exemples, 2 défis) ; Entraînement (idées fausses, diagnostics, `verify`, crans, validation par simulation, pont vers le Laboratoire, Bilan) ; partage par URL ; tests P0 ; types générés ; fixtures.
- **P1** (ouvert dès qu'un rôle a fini son P0 ; répartition à la section 2) : banc de méthodes, trajectoires du TCL, ajout de points, balayage automatique, Import + `/api/validate` + Supabase, journal des tirages, prédictions, Domaine de validité, tests P1 ; en dernier, budget et réserve de séries. Les hypothèses P1 de la régression (indépendance, forme de la relation, Anscombe) restent retirées (décision de H4).
- **P2** : inspecteur, calques, régression 3D, TFA, petits angles, générateur `function`.

Au jalon P1 (H17, 5 h), toute mécanique qui n'est pas verte est coupée **dans cet ordre, sans débat** (même règle si, par surprise, le P0 n'est pas vert à H9) :
1. journal des tirages et ajout de points ;
2. écran Import et partage Supabase ;
3. questions de prédiction ;
4. hypothèses P1 de la régression (indépendance, forme de la relation, Anscombe) ;
5. balayage automatique ;
6. Domaine de validité ;
7. expérience LGN et TCL ;
8. banc de méthodes (le bouton Correction seul reste).

**Ne se coupe jamais** : Laboratoire avec Correction, Référence et verdicts ; Entraînement avec questions vérifiées et validation par simulation ; explications ; vues Répétitions et Sensibilité ; Bilan ; lien de partage ; les 4 expériences du cours.

---

## 14. Git et passation

- Branches courtes : `r1/runner-cache`, `r4/galerie`. Petits commits fréquents.
- La nuit, l'interface avance sur des branches, relues par Kilian et fusionnées au jalon ; R1 fusionne le moteur sur `main` dès que les tests sont au vert.
- **Un seul fichier de passation**, `docs/passation.md` : une note par relève (H9, H17, H23), ajoutée **en haut**, rédigée ensemble par le binôme qui part, avec **une ligne par rôle présent** :

```markdown
## H9 (21 h) : R3 + R2 -> R1 + R4
- R3 (interface) : tourne : ... / en cours (branche) : ... / bloque : ...
- R2 (contenu) : tourne : ... / en cours (branche) : ... / bloque : ...
- Priorité du binôme suivant : ...
- TODO(passation) ajoutés : ...
```

- La première note (H0, décisions de départ) est déjà dans `docs/passation.md`.
- **Notes personnelles** : `docs/notes/r1.md` à `r4.md`, une par rôle, où chacun note où il en est pendant son créneau (tâche en cours, pistes, choix faits). Chacun n'édite que la sienne, donc pas de conflit git. Elles ne remplacent jamais la note de relève : ce qui doit être su par le binôme suivant va dans `docs/passation.md`.

Au début d'une session, lis la note de relève la plus récente **et** `docs/notes/<rôle>.md` de la personne. Quand la personne te demande « où en est-on ? », réponds à partir de `docs/passation.md`, de `git log` et du planning de la section 2, en 5 lignes au plus.
