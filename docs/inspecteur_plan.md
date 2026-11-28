# Inspecteur d'observation (P2) : plan d'implémentation

Écrit par R4 (avec l'assistant), le 28/11 vers 4 h 30. Référence : cahier, fiche F.6 (« Inspecteur d'observation ») et fiche F.4 (partage du clic avec l'ajout de points).
**Statut :** non commencé. À faire sur une branche `r4/inspecteur`, un commit par propriétaire, fusion seulement après essai au navigateur et relecture de R1. C'est du P2 : seulement si le P1 est vert, et bien avant le gel de H25 ; sinon après le pitch.

---

## 1. Ce que fait l'inspecteur

Dans la régression, un clic sur un point du nuage (ou des résidus) **entoure le point** et ouvre **sa fiche** :

| Champ | Formule | Ce que l'étudiant apprend |
|---|---|---|
| Observation | (xᵢ, yᵢ) | quel point il regarde |
| Prédiction | ŷᵢ | ce que la droite prévoit à cet endroit |
| Résidu | ε̂ᵢ = yᵢ − ŷᵢ | l'écart entre le point et la droite |
| Levier | hᵢᵢ | le poids du point dans la position de la droite (élevé si x est loin de la moyenne) |
| Distance de Cook | Dᵢ | de combien la droite bougerait sans ce point |
| Part dans la SCR | ε̂ᵢ² / Σ ε̂ⱼ² | la part de l'erreur totale due à ce point |

Seuils signalés (couleur **et** texte) : levier élevé si hᵢᵢ > 2p/n, point influent si Dᵢ > 4/n (p = nombre de coefficients, 2 ici ; n = nombre de points, points posés compris).

**Intérêt pédagogique** : avec l'ajout de points par clic, l'étudiant pose un point loin à droite, l'inspecte et lit « levier élevé, point influent » : il comprend pourquoi la pente a bougé (lien avec l'hypothèse « point levier »).

**Règles du cahier** : la fiche se met à jour quand l'état change et se ferme si le point disparaît ; un point posé à la main s'inspecte comme les autres.

---

## 2. Ce qui existe déjà (vérifié sur `main`, `820080f`)

| Élément | État |
|---|---|
| Champ YAML `inspect: true` sur une vue | accepté par `schema.py` et le contrat (`ViewSpec.inspect`, dans `types.gen.ts`) |
| Régression, vue `nuage` | `inspect: true` **déjà déclaré** |
| `ols_ci` : `example.leverage`, `example.cooks_d` | **déjà calculés** (`backend/methods/ols_ci.py`) |
| Envoi de ces valeurs à l'interface | **absent** : la vue n'envoie que `x`, `y`, `fit` |
| `Inspector.svelte` | **absent** |
| Clic sur un point de l'échantillon | aujourd'hui, il **ajoute** un point (conflit à régler) |

---

## 3. Implémentation (aucun contrat modifié)

### Moteur (R1)
1. **`backend/engine/runner.py`, `_build_view`** : si `view.inspect` est vrai, ajouter deux séries pour la méthode principale, avec les champs existants de `Series` :
   - `slot: "inspect.leverage"` : `x` = abscisses de l'échantillon, `y` = leviers ;
   - `slot: "inspect.cooks_d"` : `x` = abscisses, `y` = distances de Cook.
   Même ordre et même longueur que `x` (points posés compris, déjà dans `example`). Environ 20 lignes.
2. **`backend/engine/loader.py`** : si une vue déclare `inspect`, vérifier que la méthode principale déclare `example.leverage` et `example.cooks_d` dans `provides` ; sinon erreur en français avec le numéro de ligne. Environ 10 lignes.

### Interface (R3, Kilian ; repris par R1 la nuit)
3. **`frontend/src/lib/inspect.ts`** (nouveau, fonctions pures) :
   - `inspectionFor(view, i)` : fiche du point `i` à partir des séries de la vue (`x`, `y`, `fit`, `inspect.leverage`, `inspect.cooks_d`) ;
   - résidu, part dans la SCR, seuils 2p/n et 4/n ;
   - **générique** : n'affiche que ce que la vue fournit (sans `fit`, pas de résidu ; sans levier, pas de ligne levier). Aucun `if experiment.id`.
4. **`frontend/src/lib/plot.ts`** :
   - ne jamais dessiner les séries dont le `slot` commence par `inspect.` ;
   - trace « anneau » autour du point sélectionné (identifiant stable `<vue>.inspect.selection`) ;
   - indice de l'observation dans `customdata` des points de l'échantillon.
5. **`frontend/src/components/PlotlyChart.svelte`** : `plotly_click` sur un point de l'échantillon appelle `oninspect(i)` et **bloque l'ajout de point** pour ce clic (même mécanisme que `removedJustNow` pour le retrait). Clic dans le vide : ajout, comme aujourd'hui.
6. **`frontend/src/components/lab/Inspector.svelte`** (nouveau) : panneau sous le graphique avec la fiche, les seuils (couleur et texte : « levier élevé », « influent »), « Fermer », et pour un point posé « Retirer ce point ». Vouvoiement, nombres à la française (`lib/format.ts`).
7. **`frontend/src/components/lab/LabView.svelte`** : indice sélectionné ; transmis au graphique ; fiche fermée si l'indice dépasse le nombre de points, ou si `n` ou la graine changent ; mise à jour si une hypothèse change.

### Contenu (R2, facultatif)
8. `inspect: true` sur la vue `residus` de la régression (prévu par le cahier), même indice d'observation.

---

## 4. Décisions à prendre avant de commencer

| Question | Proposition |
|---|---|
| Clic sur un **point posé** : le retirer (comme aujourd'hui) ou l'inspecter ? | L'inspecter, avec « Retirer ce point » dans la fiche (fidèle au « s'inspecte comme les autres »). Change un geste existant : à confirmer. |
| `n` ou la graine changent | Fermer la fiche (le point `i` n'est plus le même). |
| Calculer levier et Cook dans l'interface pour éviter le moteur ? | **Non** : formules propres à la régression simple (code propre à un théorème, interdit par `CLAUDE.md`), alors que le moteur les calcule déjà. |

---

## 5. Tests

- **Moteur** (`tests/test_runner.py`, `tests/test_engine.py`) : séries `inspect.*` présentes si et seulement si `inspect: true` ; même longueur que `x` ; points posés inclus ; erreur du chargeur si la méthode ne fournit pas le levier.
- **Interface** (`lib/inspect.test.ts`, `lib/plot.test.ts`) : fiche d'un point, seuils, somme des parts dans la SCR égale à 1, fermeture hors limites, séries `inspect.*` jamais dessinées, anneau présent seulement avec une sélection.
- **Navigateur** : clic sur un point (fiche et anneau) ; clic dans le vide (ajout, pas d'inspecteur) ; point posé loin à droite (« levier élevé, influent ») ; fiche mise à jour en bougeant l'hétéroscédasticité ; fermée quand `n` change ; thèmes clair et sombre ; console sans erreur.

---

## 6. Coût et risques

- Environ 2 h 30 à 3 h, tests et vérification compris.
- Touche le nuage de la régression (écran de la démo) et le geste du clic, déjà partagé avec l'ajout de points : vérifier l'ajout et le retrait de points après coup.
- Propriétaires à prévenir : R1 (moteur), Kilian ou R1 (interface), R2 (YAML).
