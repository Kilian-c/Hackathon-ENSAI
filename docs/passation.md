# Notes de passation (la plus récente en haut)

## Nuit : seuils suggérés masqués dans l'Import, et ce qui attend R1 et Kilian (R4, pas une relève)
- **R1, FAIT** (corrigé après la revue de R4 : `ok_within` = écart sain + 3 erreurs Monte Carlo, `broken_beyond` seulement si la plus petite perturbation dépasse `ok_within` de plus de 2,25 fois, avec la raison sinon ; `tests/test_proposals.py`) ; texte d'origine : (`backend/engine/validate.py`, `_proposals`, trouvé par une revue de code, essais non revérifiés par R4) : `ok_within` = 3 erreurs Monte Carlo, sans l'écart **déjà présent à l'état sain**. Recopiés tels quels, les seuils suggérés font échouer le test 1 sur 3 YAML officiels : `seuil_roc` (Rompu, suggestion 0,0011 / 0,0089 sur `exces`), `maximum_uniformes` (Rompu, 0,0028 / 0,02), `carres_residus` (Fragile, 0,014 / 0,07). Piste : `ok_within` au moins égal à l'écart sain plus son bruit (`broken_beyond` calculé à partir de lui), sinon aucune suggestion. Parfois aussi une zone Fragile quasi vide (`bias` de la régression : 0,011 / 0,012).
- **R4, fait** : le tableau « Seuils suggérés » de l'Import est masqué (`SHOW_THRESHOLD_PROPOSALS = false` dans `ImportView.svelte`) ; les suggestions ne reviennent pas dans les avertissements en jaune. TODO(passation) : à la réactivation, dire pourquoi il manque un `broken_beyond` (et signaler un `ok_within` suggéré supérieur au `broken_beyond` du fichier), n'écrire « votre fichier reste valable » que si `report.ok`, et « vos contre-exemples (ou, à défaut, vos hypothèses cassées) ».
- **R1, mineur, FAIT** (`UNAVAILABLE_METHODS` dans `importPrompt.ts`) : le prompt de l'Import (`catalog.gen.ts`) propose `integrate`, qui exige le générateur `ode`, non décrit dans le prompt : un YAML qui l'utilise est refusé.
- **R1 reprend les tâches de Kilian pendant qu'il dort** : la liste à jour est en tête de `docs/notes/r3.md`.
- **Kilian, à valider au réveil** (**déjà sur `main`, sans votre relecture** : la note « à relire avant fusion » ci-dessous est dépassée ; le commit de fusion `28cf0be` dit « relue par R1 », or R1 n'a relu avec certitude que `make_fixtures.py` : ne vous y fiez pas pour le reste) :
  1. `frontend/vite.config.ts` et `.env.example` : relais `/api` vers `127.0.0.1:8000`, variable `API_PROXY_TARGET`, messages au démarrage et si le moteur ne répond pas.
  2. `frontend/src/lib/share.ts` (`supabaseBaseUrl`) et `share.test.ts`.
  3. `frontend/src/components/PlotlyChart.svelte` : `showSendToCloud: false`.
  4. `frontend/src/dev/specs/*.spec.json` et `fixtures/training_session.json`, `pendule_gros_pas.run.json` : régénérés depuis les YAML.
  5. `frontend/src/components/ImportView.svelte` (fichier de R4 que vous avez écrit) : erreur de syntaxe « vers la ligne N », fichier non YAML refusé, suggestions mises à part puis masquées.
  6. Nouveau dossier `frontend/src/components/import/` (`proposals.ts` et son test), créé par R4 : hors de la liste des dossiers de R4 dans `CLAUDE.md` (section 3), donc à vous par défaut. Dire s'il passe à R4 ou ce qu'il faut déplacer.
- **Kilian, à décider** : la branche `r2/lab-lisible` (refonte de l'étape Expérimenter et vue `decomposition` de la régression), **non fusionnée**, à relire. R1 a repris les rôles R2 et R3 cette nuit (`docs/notes/r1.md`). Elle touche l'écran et l'expérience de la démo : à trancher avant le gel de H25.
- `importPrompt.ts` relu par R4 comme demandé : correct, hormis `integrate` ci-dessus.

## H9,5 (21 h 30) : corrections pour R1 et R3 faites par R4, branche `r4/corrections-autres-roles` (pas une relève)
- Branche partie de `origin/main` (après l'Import de Kilian), **à relire par chaque propriétaire avant fusion** (un commit par rôle). pytest, ruff, `npm run check` et `npm test` verts.
- ~~**R1** : `make_fixtures.py`, calculs inutiles retirés et défi `rk4-gros-pas` aligné~~ : fait et fusionné par R1 (`6cf283c`). Il ne reste sur cette branche que la partie de Kilian.
- **R3** : `src/dev/specs/*.spec.json` régénérées depuis les YAML au format de `GET /api/experiments/{id}` (`model_dump(mode="json", by_alias=True)`, Student et pendule depuis `archives/`) : niveaux « 3 » et « 2 », pendule sans les deux mesures, défi réécrit, `ui` des vues, notions accentuées. `lab.test.ts` vert sans changement.
- **R3** : `lib/share.ts`, nouvelle fonction `supabaseBaseUrl` : retire la barre finale et un suffixe `/rest/v1` de `VITE_SUPABASE_URL`. Copiée telle quelle depuis le tableau de bord Supabase, l'adresse se terminait par `/rest/v1/` et le partage échouait (404 `PGRST125`, chemin `/rest/v1/rest/v1/...`). Tests dans `lib/share.test.ts` ; `.env.example` précise l'adresse et la clé publique. Partage testé de bout en bout au navigateur (création, réouverture, Sensibilité).
- **R3, tout le monde concerné** : `vite.config.ts`, le relais `/api` vise `http://127.0.0.1:8000` au lieu de `localhost:8000`. Sous Windows, `localhost` était d'abord essayé en IPv6, où uvicorn n'écoute pas : **2 s perdues à chaque requête** (0,24 s après). Rien à faire pour personne ; si votre moteur tourne ailleurs (autre port, autre machine, IPv6 seul), mettez `API_PROXY_TARGET=...` dans `frontend/.env`. `npm run dev` affiche la cible au démarrage, et un message en français si le moteur ne répond pas. Sans effet en ligne (`VITE_API_URL`).
- **R3** : `PlotlyChart.svelte`, `showSendToCloud: false` : Plotly 4 affichait au survol un bouton « Share chart… » (en anglais) qui envoie le graphique vers Plotly Cloud. Vérifié au navigateur : il ne reste que des boutons en français.
- Côté R4 (branche `r4/relecture`, à relire par Kilian pour `ImportView.svelte`) : test du chargeur, Bilan relu et corrigé, Import relu (erreur de syntaxe « vers la ligne N », fichier non YAML refusé), tests utilisateurs. Ma galerie et mon Import (`r4/galerie`) sont abandonnés au profit de ceux de Kilian.

## Chantier « modularité » ouvert par R3 + R1 (pas une relève)
- Objectif : ouvrir l'appli à d'autres théorèmes (algèbre linéaire d'abord), sans toucher aux contrats. Méthodes `formula_*` (méthode écrite dans le YAML), paquet `backend/methods/linalg/`, vue `heatmap`, catalogue généré, seuils proposés par `/api/validate`.
- **Partie R3 terminée** (détail dans `docs/chantier_modularite.md`) :
  - `plot.ts` : `ui.log_y`, `ui.log_x`, `ui.aspect` et `ui.unit_circle`, plus la vue `heatmap` ;
  - catalogue généré (`scripts/gen_catalog.py` → `lib/catalog.gen.ts`), lu par le prompt de l'Import ;
  - schéma JSON du YAML (`experiments/schema.json`) pour VS Code.
  - **R1** : `gen_catalog.py` est fait (à relire) ; la forme des données de `heatmap` est à confirmer avant de coder `runner.py`. Après chaque méthode ajoutée, relancer `gen_catalog.py`, sinon `tests/test_generated.py` échoue.
  - **R4** : `ImportView.svelte` est libéré (rien à changer) ; `importPrompt.ts` est modifié (à relire).
- **Fichiers réservés** : la liste et le partage R1 / R3 sont dans `docs/chantier_modularite.md`. **R2** : `backend/methods/__init__.py`, `expr.py`, `validate.py` et `runner.py` restent réservés (partie de R1). Prévenez R1 avant d'y toucher. Les fichiers d'interface sont libérés.


## Questions de prédiction et Domaine de validité du TCL, faits par R3 (pas une relève)
- **R1, à relire** : `backend/engine/training.py` sert les questions `prediction` (une fois par série). Le moteur lance l'état de départ et l'état d'arrivée (même graine) et compare la mesure de la méthode principale : « reste stable » sous 2 mc_se d'écart, « augmente » ou « diminue » au-delà de 4 ; entre les deux, nouveau tirage (5 au plus), sinon question retirée (`dropped`). Choix fixes `up`, `down`, `stable` ; `reveal.state` = état d'arrivée. Tests dans `tests/test_training.py` (deux anciens tests adaptés : ils supposaient des séries sans prédiction).
- **R2, à relire** : une question `prediction` ajoutée au TCL (Cauchy, n au quadruple : la part dans ±1,96 **diminue**, 26 % puis 9 %), aux tests multiples (2 groupes puis 5 à 10 : fausses alarmes en hausse) et à la multicolinéarité (rho de 0 à 0,9-0,98 : puissance en baisse) ; celle de la régression (cahier) est désormais servie, énoncé retouché (« au double »). Simulées sur 30 graines : réponse nette à chaque fois. Vue `validite` (`validity_domain`, axes `[h.loi, p.n]`) ajoutée au TCL : Student à 2 ddl et Cauchy Rompus à tous les n, 0,1 s.
- Interface : « Ouvrir dans le Laboratoire » ouvre Comprendre sur l'hypothèse de la question (`stage=`, `hyp=`) ; bouton « Voir mon bilan » en fin de série.

## Laboratoire plus lisible, fait par R2 sur l'interface (pas une relève), branche `r2/lab-lisible`
- **Kilian, à relire avant fusion** (fichiers de R3) : étape Expérimenter refaite « l'essentiel d'abord ». Nouveau `ResultPanel.svelte` (remplace `MeasureStrip` et `MethodBench`, supprimés) : jauge Fiable / Fragile / Rompu par méthode affichée (`MeasureGauge.svelte`, cible et Référence), phrase « Que se passe-t-il ? » (verdict, `when_broken` des hypothèses relâchées, étape suivante), bouton Correction mis en avant quand il sert, alternatives en plus petit. Règles pures dans `lib/guide.ts` (15 tests, aucun code propre à un théorème). Contrôles : curseurs sans boutons min/max, interrupteur pour les booléens ; cas limites et animation repliés ; équation dynamique repliée sous le graphique (résumé « 1 terme en cause ») ; verdict retiré de l'en-tête (doublon) ; `PlotlyChart` : option `bare`. Comprendre et Défis inchangés. `npm run check` et `npm test` (128) verts ; vérifié à l'œil sur 7 expériences.
- **Régression** (`experiments/regression_lineaire.yaml`, commit séparé, à retirer si on n'en veut pas) : le nuage ne garde que points, droite et Référence ; les segments SCT/SCE/SCR et les calques passent dans une vue `decomposition`. pytest et ruff verts. **Le moteur doit être relancé** (ou lancé avec `--reload-include "*.yaml"`) pour voir la nouvelle vue.
- TODO(passation) : les specs de repli `frontend/src/dev/specs/regression_lineaire.spec.json` n'ont pas la vue `decomposition` (sans effet tant que le moteur répond).

## Import, `/api/validate` et partage Supabase, fait par R3 (pas une relève)
- **R1, à relire** : `backend/engine/validate.py` (nouveau : erreurs du chargeur, puis tests 1, 3, 4, 10 à 200 répétitions ; avertissement si `ok_within` < 2 mc_se au `repeat` du fichier, ou moins de 3 questions), `POST /api/validate` dans `routes.py`, `registry.register_import` / `imported` (un YAML au schéma valide est retenu en mémoire sous `import-<16 car. du SHA-256>` : `GET /api/experiments/{clé}` et `/api/sweep` l'acceptent, **aucun contrat changé**). `/api/run` et `/api/sweep` renvoient 422 au lieu de 500 sur une `ValueError` de méthode. Tests dans `tests/test_api.py`. Les 11 YAML officiels passent la validation (4 s au plus).
- **R4, à relire** : `components/ImportView.svelte` (`?import`) : prompt à copier (`lib/importPrompt.ts`, deux vrais YAML d'exemple + catalogue des méthodes, à compléter si une méthode est ajoutée), éditeur avec numéros de ligne, dépôt de fichier, erreurs cliquables, tests, « Ouvrir dans le Laboratoire » (`?brouillon`, brouillon dans `localStorage`), « Créer un lien de partage » (`?share=<id>`).
- **Supabase, à faire une fois** : coller `supabase/schema.sql` dans l'éditeur SQL du projet, puis renseigner `VITE_SUPABASE_URL` et `VITE_SUPABASE_ANON_KEY` (`frontend/.env.example`, et dans Cloudflare). Sans elles, le bouton de partage est grisé, le reste marche. Lecture par la fonction `get_shared_experiment` seulement : la table n'est pas listable.
- TODO(passation) : test 4 `expect: same_summary` non vérifié par `/api/validate` (seulement par `tests/test_experiments.py`) ; registre des imports en mémoire (64 au plus) : après un redémarrage du moteur, l'interface revalide toute seule sur un 404.

## Format du pitch (info donnée par R2, pas une relève)
- **Pitch : 3 minutes, puis 2 minutes de questions** (17 h, H29). Le déroulé de `CLAUDE.md` (« pendule 2:45 à 3:30 », « Import montré à 3:30 ») suppose plus de 3:30 : **à raccourcir**. Proposition : une seule expérience en démo (régression, graine fixée), un second exemple très court (TCL sous Cauchy ou tests multiples) ; l'Import seulement s'il tient dans les 3 minutes, sinon en réponse aux questions.
- Priorités avant d'ajouter des expériences (déjà 11 jouables) : démo de bout en bout sans erreur, vérification à l'œil du jalon P0, vidéo de secours, réponses préparées aux 2 minutes de questions.

## RÉSOLU par Kilian (`2bce65e`), sans changer le contrat : l'écran Import n'avait pas la description de l'expérience
- Solution retenue : `/api/validate` retient un YAML valide sous la clé `import-<hash16>`, que `GET /api/experiments/{id}` et `/api/sweep` acceptent ; le Laboratoire s'ouvre avec `?brouillon`. Le reste de cette note (option `spec` dans `ValidateResponse`) est **sans objet**. Le TODO « ValueError d'une méthode -> 500 » de la relecture du moteur est aussi traité (422).
- Note d'origine, gardée pour l'historique :
- **Problème** : le Laboratoire a besoin de l'`ExperimentSpec` complète (hypothèses, paramètres, vues, textes) pour dessiner ses contrôles. Pour un YAML collé, **aucune route ne la renvoie** : `POST /api/validate` n'existe pas encore (`routes.py`, P1 de R1) et sa réponse `ValidateResponse` (`contracts.py`) ne porte que `ok`, `errors`, `warnings`, `tests` ; `POST /api/run` avec `raw_content` renvoie un `RunResult` sans les définitions de curseurs ; `GET /api/experiments/{id}` ne lit que le registre officiel. Le contrat est figé depuis `contracts-v1`.
- **Option recommandée par R2** : ajouter à `ValidateResponse` un champ **facultatif** `spec: ExperimentSpec | None = None`, rempli par `/api/validate` quand le YAML est valide (`registry.from_raw` renvoie déjà la description). Changement additif : l'existant ne casse pas. Il faut ensuite `bash scripts/gen_types.sh` et commiter `types.gen.ts` avec. Propriétaire du fichier : R1 ; le gel relève de Kilian. Précédent : le contrat a déjà bougé une fois, sans changer le format (`454265f`, types seulement) ; ici le format change, donc **décision explicite requise**.
- Autres options, moins bonnes : une route dédiée (même gel, plus de code) ; faire lire le YAML par l'interface (duplique la validation du schéma côté client).
- **En attendant** : l'écran Import s'arrête à l'aperçu des mesures (`/api/run` avec `raw_content`), sans ouvrir le Laboratoire. Rien n'est cassé pour le reste. L'Import est en 2e position dans la liste de coupes de H17 (`CLAUDE.md`, section 13) et le pitch dure 3 minutes : si la décision n'est pas prise vite, couper l'Import sans débat.
- TODO(passation) R1 / Kilian : trancher, puis R1 implémente `/api/validate`, R4 branche l'ouverture dans le Laboratoire.

## Relecture du moteur par un agent, faite par R2 (pas une relève)
- Relecture en lecture seule de `runner.py`, `training.py`, `sweep.py`, `fastexpr.py`, `api/`, `methods/` : rien de grave (déterminisme, plafonds, verdicts, une seule `misconception` par série : conformes). Constats **non vérifiés par R2, non corrigés** (fichiers de R1) :
- TODO(passation) R1, **à faire avant la démo** : `runner.py:153-160`, `_CACHE` sans verrou alors que les routes `def` tournent dans un pool de threads ; un `/api/sweep` (144 cases) peut évincer une entrée pendant qu'un `/api/run` la relit (`move_to_end` puis `_CACHE[...]` : `KeyError`, 500 intermittent). Piste : `threading.Lock` autour de la lecture et de l'écriture.
- TODO(passation) R1 : `runner.py:62` (`verdict`), valeur NaN ou ±inf : l'interface affiche « Rompu » (`_measure_results`, ligne 277) mais `s.<mesure>`, les défis et `verify` appliquent la règle sans garde (NaN donne `warning`, +inf avec `below` donne `ok`). Piste : garde `isfinite` dans `verdict`.
- TODO(passation) R1, si l'Import est montré : `runner.py:182-183`, une `ValueError` levée par une méthode (kind inconnu, `dt <= 0`...) n'est pas transformée en `RunError` : 500 au lieu d'un 422 en français (`routes.py:86`). Idem `ExprError` hors `generate`. `runner.py:146-149`, `_eval_arg` renvoie le texte quand l'évaluation échoue : un `p.nn` mal écrit part comme chaîne vers la méthode. Les YAML officiels ne sont pas touchés.
- TODO(passation) R1, faible priorité : plafonds `repeat` et `n` non cumulés (1000 × 5000 × 30 variables, environ 1,2 Go) et délai de 2 s de `/api/run` non appliqué (budget P1) ; `sweep.py:51-53`, un point de balayage peut sortir de `range` si `range[1]` n'est pas un multiple de `step` (YAML actuels sains).

## H9 (21 h) : R3 + R2 -> R1 + R4
- **Brouillon préparé par R2 : R3 (Kilian) complète et corrige sa ligne avant de valider.** Vérifié sur `main` (`3b2ffea`) : pytest, ruff, `npm run check` (0 erreur) et `npm test` (111 tests) verts.
- R3 (interface) : tourne : niveaux en mots, `segments` et `h1` dessinés, banc de méthodes, ajout de points par clic (correctif du double comptage dans `runner.py`), trajectoires (`mode: paths`), balayage automatique, Domaine de validité, écran Bilan, vue de secours `measures_table`, Entraînement, partage par URL (d'après `docs/notes/r3.md` et `git log`) ; **refonte de l'accueil et du Laboratoire** (H9) : accueil sur un écran (Entraînement et Laboratoire), galerie `?labo` (recherche, filtres discipline et niveau), Laboratoire en trois étapes (Comprendre, Expérimenter, Défis) / en cours : relecture à l'œil / bloque : rien. **À vérifier à l'œil dans le navigateur** : la vue `trajectoires` du TCL (sous Cauchy), le tableau des mesures de repli, les specs de repli du pendule et de Student (`lab.test.ts` les importe encore).
- R2 (contenu) : tourne : 9 expériences officielles dans `experiments/` (4 du cours : régression, TCL, multicolinéarité, tests multiples ; 5 du catalogue de niveau « 1 » : somme de dés, seuil et ROC, carrés des résidus, déséquilibre, moyenne ou médiane), chacune simulée avant les seuils, 3 questions, tests de contenu verts ; Student et pendule dans `experiments/archives/` ; `integrate` générique ; trajectoires du TCL (`runner.py`, `clt_mean`) ; `docs/theoremes_restants.md` ; `auto_sweep` rempli partout / en cours : rien / **bloque : rien** ; le déploiement est **en pause** (décision de R2 à H8 : ce n'est pas la priorité, on avance sur le contenu et les écrans). Le `Dockerfile` n'existe pas dans le dépôt et n'est pas à faire pour l'instant.
- R1 (moteur, relecture H9 et suite, branche `r1/relecture-h9`, non fusionnée) : tourne : relecture de `runner.py`, `training.py`, `fastexpr.py`, `sweep.py`, `api/` faite ; correctifs (verrou du cache, verdict non fini = `broken`, erreur de méthode en 422) ; `scripts/make_fixtures.py` sans `energy_drift` ni `full_turn` ; `POST /api/validate` (tests 1, 3, 4, 10) ; `draw_log` testé ; tests P1 5, 7, 9, plafonds, `test_properties.py` ; `asteval` retiré. Fumée à la main avec `uvicorn` : les 5 routes répondent (200), série de 10 questions sans abandon, `/api/run` sous 100 ms sauf `tests-multiples` (850 ms au premier appel : Tukey). pytest, ruff, `npm run check`, `npm test` verts / en cours : budget non fait (inutile : tout sous 1 s) / bloque : rien. **Jalon P0 validé par Kilian (R3), d'après R1** (vérification à l'oeil sur la vraie API) ; tests P0 verts.
- Priorité du binôme suivant (R1 + R4) :
  1. **R1 relit ce qui a été fusionné sans lui** : `runner.py` (R2 : moteur complet, emplacements de l'annexe E, `paths` ; R3 : double comptage des points posés), `training.py`, `fastexpr.py`, `sweep.py`, `api/registry.py`, `api/routes.py`, et les tests adaptés par R2 (`test_runner.py`, `test_api.py`, `test_sweep.py`, `test_integrate.py`).
  2. **R1 : `scripts/make_fixtures.py`** : retirer `energy_drift` et `full_turn`, régénérer les fixtures `pendule_*` et `student_*` (ou les supprimer avec les specs de repli si les tests ne s'en servent plus).
  3. R1 : `POST /api/validate`, Import et Supabase (P1) ; R4 : **la galerie est faite par R3** (`components/home/LabGallery.svelte`, route `?labo` ; accueil dans `HomeView.svelte`) : relire et compléter au besoin (tri), puis lien vers le Bilan en fin de série, écran Import. La galerie lit la liste du moteur : les niveaux sont « 1 », « 2 », « 3 ».
- Jalon P0 (critère de `CLAUDE.md`, section 2) : tests P0 verts ; Laboratoire et Entraînement sur la vraie API : **à confirmer à l'œil** par R3 et R1 avant de dire « vert ».
- À savoir : toute nouvelle expérience se fait avec `docs/theoremes_restants.md` (cas YAML seul / méthode / vue, marche à suivre, pièges). Marges fines à ne pas toucher sans rejouer la simulation : `desequilibre` (« un malade sur 5 » Rompu à 0,03 de marge), `moyenne_mediane` (médiane Fragile à n = 10).
- **Déploiement en pause** : ni `Dockerfile` ni mise en ligne avant nouvel ordre. Si un projet Cloudflare Pages est relié au dépôt, il redéploie à chaque `git push` sur `main` : pour l'arrêter, désactivez les déploiements automatiques dans ses réglages (Settings, Builds & deployments).
- TODO(passation) ajoutés : fixtures du pendule et de Student ; pas de ligne `truth` sur la vue `trajectoires` du TCL ; pas de ligne de seuil dans `desequilibre` (`bind.threshold` n'accepte qu'un `p.<id>`).

## H7 (21 h 30) : expérience « Moyenne ou médiane », branche `r2/levier` (pas une relève)
- Nouvelle expérience niveau « 1 » : `experiments/moyenne_mediane.yaml` (méthode `statistic`, kinds `mean` et `median`, aucun code ajouté), 3 questions, 2 défis, tous les tests de contenu verts (dont le test 6 à 50 tirages).
- Simulation (graine 42, 500 échantillons) : une valeur extrême de 40 sur n = 20 décale la moyenne de 2,0 (Rompu), la médiane de 0,066 (Fiable) ; sans valeur extrême, la médiane est environ 25 % plus étalée que la moyenne (0,27 contre 0,22). Même n = 200 : moyenne décalée de 0,20 (Fragile). Seuils 0,12 / 0,30 ; médiane Fragile à n = 10 (0,139).
- Pas de point posé au clic (P1) : la valeur extrême est une hypothèse du générateur (`idx == p.n - 1`).

## H7 (21 h) : trajectoires du TCL, branche `r2/paths-auto-sweep` (pas une relève)
- `runner.py` (fichier de R1, modifié par R2, **R1 relit à H9**) sert l'emplacement `paths` : tableau 2D `(trajectoires, k)` lu sur la méthode, une série par méthode (`slot: paths`, `paths` = une liste par trajectoire, `x` = grille commune), plus une série `reference` (état sain) ; les méthodes aux trajectoires identiques ne donnent qu'une série ; bornes `axes` calculées sur la Référence ; `shown` = 30, `total` = nombre de répétitions. Constante `SHOWN_PATHS = 30`.
- `clt_mean` fournit `curves.k` et `curves.paths` (moyennes cumulées des 30 premières répétitions). `theoreme_central_limite.yaml` : nouvelle vue `trajectoires` (`type: repetitions`, `mode: paths`, `bind: { x: curves.k, paths: curves.paths }`). Test ajouté : `tests/test_runner.py`. Rien à changer côté R3 : le contrat est celui de `plot.test.ts`.
- `auto_sweep` était déjà rempli dans les 8 YAML (régression : `h.hetero` et `p.n` ; TCL : `p.n` ; tests multiples : `h.groupes`).
- Pas de ligne `truth` (valeur vraie 0) dans cette vue : `truth` ne lit qu'un `p.<id>`, et le TCL n'a pas de paramètre de moyenne.

## H7 (20 h 30) : suite des théorèmes, `docs/theoremes_restants.md` (pas une relève)
- Pour la personne qui continue les expériences : `docs/theoremes_restants.md` (ce qui est fait, ce qu'il reste, cas YAML seul / méthode / vue, marche à suivre, pièges) et `docs/catalogue_experiences.md` (copie du catalogue de Kilian).

## H7 (20 h) : Student et pendule archivés, branche `r2/archives` (pas une relève)
- `experiments/test_student.yaml` et `experiments/pendule_euler.yaml` sont dans `experiments/archives/` (`git mv`) : le registre ne lit pas les sous-dossiers, donc ils ont quitté l'accueil et les séries « toutes ». `README.md` mis à jour.
- Tests (fichiers de R1, adaptés par R2, à relire) : `test_runner.py` lit Student et le pendule dans `ARCHIVES` (ils testent toujours `draw_log`, le générateur `ode` et l'axe du temps) ; `test_api.py` : liste, lecture et erreurs sur `multicolinearite`, le YAML brut vient de `archives/` ; `test_sweep.py` : axe de choix sur le TCL, cible `base` sur la multicolinéarité (`h.rho` et `p.n`), grille 2D sur le TCL. pytest et ruff verts.
- **R3, à faire** : `frontend/src/dev/specs/test_student.spec.json` et `pendule_euler.spec.json` sont toujours importés par `lib/lab.test.ts` ; le second contient encore `energy_drift` et `full_turn`. Les régénérer depuis `archives/` ou retirer ces tests.
- **R1, à faire** : `scripts/make_fixtures.py` et les fixtures `pendule_*` / `student_*` (note précédente).

## H7 (19 h 30) : `integrate` générique, branche `r2/integrate-generique` (pas une relève)
- Fusionné dans `main` à la demande de R2. `backend/methods/integrate.py` ne calcule plus l'énergie du pendule ni `full_turn` : `summary` = `max_rel_error` seulement. `pendule_euler.yaml` : mesures `energy_drift` et `full_turn` retirées, défi `rk4-gros-pas` réécrit (`s.err_angle == 'broken'`). `test_integrate.py` adapté. pytest et ruff verts.
- **R1, à faire** : `scripts/make_fixtures.py` (lignes 323 à 370) fabrique encore `energy_drift` et `full_turn` : les retirer, puis régénérer `frontend/src/fixtures/pendule_*.run.json` (`uv run python scripts/make_fixtures.py`).
- **R3, à faire** : régénérer `frontend/src/dev/specs/pendule_euler.spec.json` (contient encore les deux mesures et l'ancien défi). Sans effet tant que le moteur répond.
- Reste propre au pendule : la courbe de sortie s'appelle `theta` (le YAML lit `curves.theta`).

## H7 (19 h) : expérience « Déséquilibre », branche `r2/desequilibre` (pas une relève)
- Fusionné dans `main` à la demande de R2. Aucun fichier de R1 ni de R3 touché : seulement `experiments/desequilibre.yaml` (niveau « 1 », méthode `classifier`, 3 questions, 2 défis). Vérifications vertes (pytest, test 6 à 50 tirages, ruff, npm check, npm test).
- Chiffres (graine 42, 300 études de 600 patients) : sensibilité du seuil « qui se trompe le moins » 77 % (50 % de malades), 44 % (1 sur 5), 1,2 % (1 sur 100) ; exactitude 77 %, 85 %, 99 %. Seuils 0,10 / 0,30 ; « un malade sur 5 » est Rompu avec 0,03 de marge : ne pas les changer sans rejouer la simulation.
- **R3** : pas de ligne de seuil dans la vue `distribution` (le seuil dépend de `h.rarete` et `p.ecart`, et `bind.threshold` n'accepte qu'un `p.<id>`) ; pas de courbe ROC (indépendante du seuil).

## H6,5 (18 h 30) : correctif moteur fait par R3, branche `r3/p1` (pas une relève)
- **R1, à relire** (`backend/engine/runner.py`, ligne 168) : `_compute_uncached` rappelait `with_extra_points` alors que `generate()` ajoute déjà les points posés : chaque point comptait deux fois. Le runner prend maintenant `world.variables` tel quel. Test : `tests/test_runner.py::test_extra_points_added_once` (échoue sans le correctif : 152 points au lieu de 151).
- Sur la même branche (interface) : niveaux en mots, `segments`, `h1` et seuil dans `distribution`, banc de méthodes, ajout de points par clic, faisceau de trajectoires (attend les `paths` du TCL, R2).

## H6,5 (18 h 30) : planning revu, on a de l'avance (pas une relève)
- Décision de Kilian : le P0 est presque vert, donc **jalon P0 avancé à H9 (21 h)**, P1 ouvert tout de suite, priorités P1 : mécaniques visuelles puis Import + Supabase. Coupes appliquées au P1 à H17. Détail et tâches dans l'ordre : **CLAUDE.md, section 2**.
- R3 (jusqu'à 21 h) : niveaux en mots, `segments` dans `plot.ts`, puis banc de méthodes, trajectoires du TCL, ajout de points par clic.
- R2 (jusqu'à 21 h) : Student et pendule vers `experiments/archives/` (tests mis à jour), `Dockerfile`, `paths` du TCL et `auto_sweep` dans les YAML, puis une expérience de plus du catalogue.
- R1 (21 h) : relire tout ce qui a été fusionné sans vous (liste en section 2), puis `POST /api/validate`, `draw_log`, tests P1.
- R4 (22 h) : galerie, lien vers le Bilan en fin de série, relecture du Bilan, écran Import, partage Supabase (`supabase/schema.sql` : prévenir Kilian).
- Pitch : le pendule est abandonné, donc le passage de 2:45 à 3:30 est à refaire (TCL sous Cauchy ou tests multiples) : R3 + R2, entre H19 et H23.

## H6 (18 h 30) : décision, `level` = difficulté 1, 2, 3 (pas une relève)
- Décision de R2 : `level` vaut « 1 » (Découverte), « 2 » (Intermédiaire) ou « 3 » (Avancé), comme le propose le catalogue ; l'année (« 1A », « 2A ») disparaît. Niveaux repris des tableaux du catalogue : 1 = somme de dés, seuil et ROC, carrés des résidus ; 2 = TCL, tests multiples, pendule ; 3 = régression, Student, multicolinéarité (absente du catalogue : rangée comme « Variable omise »).
- `tests/test_engine.py` (R1) : la chaîne repérée dans la régression passe de `level: "1A/2A"` à `level: "3"`.
- **R3 / R4** : l'accueil (`App.svelte`) et le Laboratoire (`LabView.svelte`) affichent le chiffre brut (« probabilites · 1 ») : afficher « Découverte », « Intermédiaire », « Avancé » ; la galerie peut trier par niveau. Specs de repli (`src/dev/specs/`) à régénérer.

## H6 (18 h) : 3 premières expériences du catalogue, branche `r2/catalogue` (pas une relève)
- Fusionné dans `main` à la demande de R2, **sans relecture de R1 : R1, relisez `runner.py` après coup** (les 4 vérifications de la section 4 étaient vertes : 274 tests pytest, ruff, npm run check, 80 tests npm).
- Nouvelles expériences niveau « 1 » (section 15 du catalogue) : `somme_des.yaml`, `seuil_roc.yaml`, `carres_residus.yaml`, chacune simulée avant d'écrire les seuils, 3 questions chacune, tous les tests de contenu verts (dont le test 6).
- Méthodes génériques du catalogue (R2) : `statistic` (sum, mean, max, min, median), `classifier` (kind « seuil » pour l'instant), `regressor` (ols, manuelle) ; agrégateur `kurtosis` (aplatissement, sans erreur MC).
- **R1, à relire** (`runner.py`) : emplacements de l'annexe E servis : `threshold` (scalaire, rôle `rupture`), `h1` et `observed` (méthode principale, rôle `truth`), `segments` (série `x`, `low` = from, `high` = to, `layer`) ; libellés des séries lus dans `ui.labels` (champ libre) et dans les `label` de `series`. Le runner importe tout `backend.methods`.
- **R3, interface (non fait, fichiers de Kilian)** : (1) `plot.ts` ne dessine pas encore les `segments` (séries sans `y` : ignorées sans erreur) ; (2) dans `distribution`, `h1` (rôle `truth`) sort en orange : à vérifier à l'œil ; (3) `theory` (courbe sur un histogramme) n'est pas servi : il serait dessiné comme un histogramme.
- Convention de `level` : tranchée à 18 h 30 (note ci-dessus).

## H5 (17 h) : écran Bilan fait par R3 (pas une relève)
- **R4 : n'écrivez pas le Bilan, il est fait** et fusionné dans `main` à la demande de R3, **sans votre relecture : relisez après coup**, ce sont vos fichiers : `lib/calibration.ts`, `lib/calibration.test.ts`, `components/summary/CalibrationSummary.svelte`. Ouverture : `?bilan`. Votre galerie devra garder ce lien.

## H5 (17 h) : Entraînement côté moteur, branche `r2/training` (pas une relève)
- Fusionné dans `main` à la demande de R2, **sans relecture de R1 : R1, relisez après coup** (les 4 vérifications de la section 4 étaient vertes). Fait par R2, dans des fichiers de R1 : `backend/engine/training.py` et `POST /api/training/session` (`backend/api/routes.py`), empreinte des YAML dans `backend/api/registry.py` (`content_digest`). Tests : `tests/test_training.py`, tests d'API de la section 12 ajoutés à `tests/test_api.py`. 227 tests verts.
- Règles : `misconception` une fois par série, chaque choix vérifié (`reveal_state` lancé, `verify`, 5 tirages au plus, sinon `dropped`) ; `diagnostic_auto` 2 fois au plus, pathologie cachée différente, libellés tirés des hypothèses (« <hypothèse> : <option ou broken_label> », plus « Hypothèses respectées ») ; `prediction` (P1) non servie.
- Temps : série « toutes » 5,8 s (avec le pendule), une expérience 0,1 à 1,4 s.
- **À décider (équipe)** : Student et le pendule sont toujours dans `experiments/`, donc dans la liste d'accueil et dans les séries « toutes ». Les exclure sans code propre à un théorème = sortir leurs fichiers de `experiments/` quand les tests ne s'en servent plus.
- Pas fait : test 7 (pathologies distinguables, P1).

## H4 (16 h 15) : `r2/runner` fusionnée dans `r3/entrainement-et-cours` (pas une relève)
Cette branche réunit le vrai moteur de R2, l'écran d'Entraînement et les nouvelles expériences : c'est elle qu'il faut fusionner dans `main`. Les 4 expériences ont été rejouées sur le vrai `run()` : mêmes valeurs de la mesure primaire qu'au mini-pipeline.

**Correctifs faits à la fusion, à relire par R1 et R2**
- `backend/methods/__init__.py` importe toutes les méthodes : sans cela, les 3 nouvelles expériences renvoyaient une erreur 500, sans qu'aucun test le signale (d'autres fichiers de test les importaient).
- `backend/engine/sweep.py` : une hypothèse continue est balayée sur la grille de son `step`, sans doublon.
- `tests/test_runner.py` : la vue des intervalles n'attend plus que MCO et HC3 (Newey-West retiré). `tests/_mini_run.py` supprimé, comme sur `r2/runner`.
- `match_summary` retiré de `training_session.json` et de `scripts/make_fixtures.py` (le moteur refusait la correction).
- **R2** : le pendule et Newey-West sont abandonnés (note ci-dessous), n'y passez plus de temps.

## H4 (16 h) : changement des expériences (pas une relève)
Décision de Kilian : ne montrer que des théorèmes vus en cours. P0 : régression (IC d'une pente), TCL, multicolinéarité, tests multiples. Student/Wilcoxon et pendule sont abandonnés. Aucun fichier de contrat modifié. Vérifié sur le mini-pipeline `tests/_mini_run.py` (graine 42, 500 répétitions), pas sur le moteur.

**R2 (à relire avant fusion, ce sont vos fichiers)**
- Nouveaux : `experiments/{theoreme_central_limite,multicolinearite,tests_multiples}.yaml`, `backend/methods/{clt_mean,ols_two,pairwise_tests}.py`, `tests/test_course_methods.py` ; `_mini_run.py` et `test_method_contract.py` complétés.
- `regression_lineaire.yaml` : textes repris avec le vocabulaire du cours ; retirés : `nw`, les 2 contre-exemples d'Anscombe, `match_summary`.
- Chiffres : TCL à n = 50, part dans ±1,96 : 95 % (sain), 67 % (Student 2 ddl), 30 % (Cauchy), 60 % (rho = 0,7 ; corrigé : 96 %). Colinéarité, n = 100 : X1 détecté 81 % (rho = 0), 38 % (0,8), 12 % (0,95) ; sans X2 : détecté, mais biais 0,28 à 0,95. Tests multiples, n = 120 : faux positif 4 % (2 groupes), 38 % (6), 62 % (10) ; Bonferroni 3 à 4 %.
- TCL : une correction par la médiane a été essayée et retirée (fausse sous loi exponentielle). Rien ne répare la variance infinie : c'est voulu.

**R1**
- Import des méthodes et grille du balayage : faits à la fusion (note ci-dessus).
- Plus besoin du générateur `ode` en P0.
- Tukey : `studentized_range.ppf` prend près de 0,7 s au premier appel d'un couple (groupes, ddl), puis reste en cache ; à surveiller pour la limite de 2 s et le balayage.
- Fixtures à refaire pour les 3 nouvelles ; numéro de ligne ajusté dans `tests/test_engine.py` (`test_unknown_repair_reports_line`).

**R3**
- Les 3 nouvelles expériences n'apparaissent pas encore dans l'interface : il faut le moteur, ou des specs et fixtures de repli. Spec de repli de la régression régénérée.

**R4** : rien à changer, la galerie lit la liste du moteur.

## H3 (15 h) : vérification croisée du travail de R1, R2 et R3 (pas une relève)
Vérifié au commit `82e7663` : YAML, générateur `random` et méthodes concordent (arguments, `bind`, formes). `run()` n'existant pas, les simulations ont été branchées à la main, à la graine 42.

**R1 (moteur)**
- `tests/_mini_run.py` (R2, `bdaa785`, non vérifié ici) reproduit une partie de `run()` pour les tests : à remplacer par le vrai dès qu'il existe.
- `runner.py` n'est plus bloqué : les 3 méthodes sont là. `backend/methods/__init__.py` n'importe rien, donc le registre est vide : importer les 3 modules (dans le runner, ou demander à R2 de le faire dans `__init__.py`), sinon `get_method` échoue.
- `make_fixtures.py` réécrit les méthodes, les seuils et la règle de verdict, et a divergé : `broken_beyond: 0.25` (YAML : 0.30), Wilcoxon sous Cauchy y est Rompu au lieu de Fragile ; `nw`, `bp_pvalue` et les nouvelles questions manquent. À brancher sur les vraies méthodes dès que `run()` existe.
- Pendule : avec un `rhs` passant par `expr.py`, `integrate` prend environ 0,75 s (Euler + RK4) à l'état par défaut et 2,2 s à `t_end = 10`, Référence non comprise (limite : 2 s). Fournir un `rhs` rapide et `ref` (angle seul, sur `t`).
- Une seule entrée par code dans `RunResult.warnings` de préférence (l'interface tolère désormais les doublons).
- Mineur : `state.py` arrondit au pas à partir de 0, `state.ts` à partir du minimum (sans effet avec les YAML actuels) ; `asteval` est inutilisé.

**R2 (maths et contenu)**
- `pend-q2-duree` : l'énoncé dit « un pas pour lequel Euler reste fiable sur 5 s », mais à `pas: 0.4` Euler est Fragile sur 5 s (12,2 %). Proposition : `pas: 0.2` (Fiable à 5 s : 3,7 % ; Fragile de 8 à 10 s : 8,4 à 12,3 %) et `verify: "s.err_angle != 'ok' and m.err_angle.rk4 < 0.05"`.
- Student à n = 5 : Wilcoxon ne peut jamais rejeter (p minimale 0,0625). Il s'affiche Fiable avec 0 % de puissance, et son risque alpha est Rompu même sous loi normale. Proposition : `n` minimum à 10, `sweep_values` à partir de 10.
- Défi `trap-bp-test` : réussi aussi sans hétéroscédasticité, avec `autocorr: true`, n = 30, graine 42. Ajouter `h.hetero > 0` à `when` si ce n'est pas voulu.
- Pendule : à `theta0 = 2.5` et `t_end = 10`, l'état sain est Fragile (16,8 %).
- `relation: break` ne rompt aucune mesure (couverture 87,8 %) : risque sur le test 2 (P1).
- Texte : `when_broken` de `relation` dit « vers 73 % » (réel : 76 %). Le commentaire de `alpha` est déjà corrigé (`0ae458a`).
- `integrate` calcule l'énergie du pendule et suppose 2 variables d'état : une autre équation différentielle donnerait un résultat faux ou une erreur.

**R3 (interface)**
- Corrigé : défis réussis retenus d'un onglet à l'autre, clés des avertissements, specs de repli régénérées, `CLAUDE.md` (section 9) et arborescence du README.
- Reste : zoom qui pourrait passer d'une vue à l'autre (à vérifier au navigateur) ; repli sur les fixtures à désactiver avant la démo.
- 15 h 30 : Entraînement minimal fait (`components/training/`), testé dans un navigateur sur la série de démonstration ; il passera sur le vrai moteur dès que `POST /api/training/session` et `/api/run` répondent.
- TODO(passation), R4 : le Bilan lit l'historique avec `loadHistory(browserStore())` (`lib/training.ts` : par série, chaque réponse a `correct`, `level`, `p`, `at`) ; ajouter le lien vers le Bilan sur l'écran de fin (`TrainingView.svelte`).

## H0 (12 h) : décisions de départ
- Rôles : R3 = Kilian (interface), qui pourra aider R1 ; R4 pourra reprendre une partie de l'interface de R3.
- Une seule route d'Entraînement (`POST /api/training/session`, `seed` facultative), pas de réserve en P0, `count = min(10, disponibles)`. Le cahier décrit encore deux routes GET : le CLAUDE.md fait foi.
- Les 3 YAML de référence sont dans `experiments/`, extraits du `.tex` par script (pas depuis le PDF). Seul changement : `explain` de `cauchy-petit-n` sans chiffre écrit en dur.
- `test_student.yaml` : version du cahier (`h.loi`, `p.delta`, `broken_beyond: 0.25`). R2 vérifie par simulation la marge de Wilcoxon sous Cauchy (passer à 0,30 si la perte dépasse 0,22).
- Questions à ajouter par R2 : au moins 3 par expérience (Student : +1, pendule : +2).
- Dépendances P1 dans la régression (`autocorr`, `relation`, `ols_match`) : à implémenter tôt, ou à retirer du YAML en cas de coupe, pour ne pas faire échouer les tests P0 3 et 4.
- Planning : code figé à H25 (13 h le lendemain), pitch à 17 h.
- Dépôt en place : `uv sync`, `uv run pytest` (2 tests de démarrage), `uv run ruff check .`, `npm run check` et `npm run build` au vert.
