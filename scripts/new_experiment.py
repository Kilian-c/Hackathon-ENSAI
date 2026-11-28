"""Crée le brouillon d'une nouvelle expérience à partir d'un modèle (R1, chantier modularité).

    uv run python scripts/new_experiment.py --list
    uv run python scripts/new_experiment.py statistique mon-theoreme --title "Mon théorème" \\
        --discipline probabilités
    uv run python scripts/new_experiment.py algebre mon-algo --level 3 --official

Le brouillon est une COPIE FONCTIONNELLE d'une expérience de référence de `experiments/` : il passe la
validation tel quel (états sain et cassé, contre-exemples, questions), et il sert de point de départ. On le
modifie par petites touches, en relançant la validation (`--check` ci-dessous, ou l'écran Import) après
chaque changement, plutôt que d'écrire un YAML de zéro.

Par défaut, le brouillon va dans `experiments/brouillons/<id>.yaml` : le moteur ne lit que
`experiments/*.yaml`, sans sous-dossier, donc un brouillon à moitié modifié ne casse jamais le démarrage.
`--official` l'écrit directement dans `experiments/` (l'expérience apparaît alors à l'accueil).

    uv run python scripts/new_experiment.py --check experiments/brouillons/mon-theoreme.yaml

valide un fichier (erreurs avec numéro de ligne, tests 1, 3, 4 et 10, seuils proposés).

L'en-tête `# yaml-language-server: $schema=...` active l'autocomplétion et la vérification dans VS Code
(`experiments/schema.json`, généré par `scripts/gen_types.sh`).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXPERIMENTS = ROOT / "experiments"
DRAFTS = EXPERIMENTS / "brouillons"
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# modèle -> (fichier de référence, ce que l'on y trouve)
MODELS: dict[str, tuple[str, str]] = {
    "statistique": (
        "moyenne_mediane.yaml",
        "statistique d'un échantillon (méthode `statistic` : somme, moyenne, médiane, maximum...)",
    ),
    "regression": (
        "carres_residus.yaml",
        "droite et moindres carrés (méthode `regressor`) ; pour un intervalle de confiance, voir `ols_ci`",
    ),
    "classifieur": (
        "seuil_roc.yaml",
        "seuil de décision, erreurs, courbe ROC (méthode `classifier`)",
    ),
    "algebre": (
        "systemes_lineaires.yaml",
        "algèbre linéaire (méthode `linsolve` ; voir aussi `eigen`, `spectrum`, `orthonormalize`)",
    ),
}

CHECKLIST = """\
# Brouillon créé par scripts/new_experiment.py à partir du modèle « {model} » (experiments/{source}).
# C'est une copie fonctionnelle : elle passe la validation telle quelle. Modifiez par petites touches et
# revalidez à chaque fois (uv run python scripts/new_experiment.py --check <ce fichier>).
# À remplacer, dans l'ordre : 1. concepts, theorem et equation ; 2. hypotheses (why et when_broken
# obligatoires) ; 3. generator et methods (méthodes disponibles : frontend/src/lib/catalog.gen.ts, ou le
# prompt de l'écran Import) ; 4. measures (seuils : voir les « Seuils proposés » de la validation) ;
# 5. counterexamples, challenges, views ; 6. au moins 3 questions.
# Un chiffre écrit dans un texte doit venir de {{value}}, jamais être recopié à la main.
"""


class NewExperimentError(Exception):
    """Erreur d'usage : le message est en français et dit quoi faire."""


def existing_ids() -> set[str]:
    """Identifiants déjà pris : expériences officielles, archives et brouillons."""
    found: set[str] = set()
    for folder in (EXPERIMENTS, EXPERIMENTS / "archives", DRAFTS):
        for path in folder.glob("*.yaml"):
            match = re.search(r'^id:\s*"?([^"\s#]+)"?', path.read_text(encoding="utf-8"), re.M)
            if match:
                found.add(match.group(1))
    return found


def render(
    model: str, exp_id: str, *, title: str | None, discipline: str | None, level: str | None, out: Path
) -> str:
    """Texte du brouillon : le modèle, avec son identité remplacée et l'en-tête du brouillon."""
    if model not in MODELS:
        raise NewExperimentError(f"Modèle inconnu : « {model} ». Modèles : {', '.join(MODELS)}.")
    source, _ = MODELS[model]
    text = (EXPERIMENTS / source).read_text(encoding="utf-8")
    text = re.sub(r"^# yaml-language-server:.*\n", "", text, flags=re.M)

    def put(key: str, value: str, body: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return re.sub(rf"^{key}:.*$", lambda _m: f'{key}: "{escaped}"', body, count=1, flags=re.M)

    text = put("id", exp_id, text)
    text = put("title", title or f"Nouvelle expérience : {exp_id}", text)
    if discipline:
        text = put("discipline", discipline, text)
    if level:
        text = re.sub(r'^level:\s*"[123]"', lambda _m: f'level: "{level}"', text, count=1, flags=re.M)
    schema = Path(os.path.relpath(EXPERIMENTS / "schema.json", out.parent)).as_posix()
    header = f"# yaml-language-server: $schema={schema}\n" + CHECKLIST.format(model=model, source=source)
    return header + text


def create(
    model: str,
    exp_id: str,
    *,
    title: str | None = None,
    discipline: str | None = None,
    level: str | None = None,
    out: Path | None = None,
    official: bool = False,
    force: bool = False,
) -> Path:
    """Écrit le brouillon et renvoie son chemin. `NewExperimentError` si les arguments sont invalides."""
    if not SLUG.match(exp_id):
        raise NewExperimentError(
            f"Identifiant invalide : « {exp_id} ». Lettres minuscules, chiffres, tirets et soulignés "
            "seulement, en commençant par une lettre ou un chiffre (par exemple « mon-theoreme »)."
        )
    if level is not None and level not in ("1", "2", "3"):
        raise NewExperimentError('Le niveau vaut "1" (Découverte), "2" (Intermédiaire) ou "3" (Avancé).')
    if exp_id in existing_ids() and not force:
        raise NewExperimentError(
            f"L'identifiant « {exp_id} » existe déjà (expériences, archives ou brouillons) : "
            "choisissez-en un autre."
        )
    if out is None:
        out = (EXPERIMENTS if official else DRAFTS) / f"{exp_id.replace('-', '_')}.yaml"
    if out.exists() and not force:
        raise NewExperimentError(f"{out} existe déjà : ajoutez --force pour l'écraser.")
    text = render(model, exp_id, title=title, discipline=discipline, level=level, out=out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


def check(path: Path) -> bool:
    """Valide un fichier comme `POST /api/validate` et l'affiche. Renvoie vrai s'il n'y a aucun échec."""
    from backend.engine.validate import validate

    report = validate(path.read_text(encoding="utf-8"))
    for error in report.errors:
        where = f"ligne {error.line}" if error.line else "fichier"
        print(f"  ERREUR  {where}, {error.path or 'racine'} : {error.message}")
    for test in report.tests:
        status = "ok    " if test.passed else "ÉCHEC "
        detail = f" : {test.detail}" if test.detail else ""
        print(f"  {status} test {test.id:>2} {test.name}{detail}")
    for warning in report.warnings:
        where = f"ligne {warning.line}, " if warning.line else ""
        print(f"  conseil {where}{warning.path} : {warning.message}")
    print("Validation : OK" if report.ok else "Validation : à corriger")
    return report.ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Crée le brouillon d'une expérience à partir d'un modèle, ou valide un fichier.",
        epilog="Modèles : " + ", ".join(MODELS),
    )
    parser.add_argument("model", nargs="?", help="modèle de départ (voir --list)")
    parser.add_argument("id", nargs="?", help="identifiant de la nouvelle expérience (ex. mon-theoreme)")
    parser.add_argument("--title", help="titre affiché")
    parser.add_argument("--discipline", help="discipline (ex. probabilités)")
    parser.add_argument("--level", choices=["1", "2", "3"], help="1 Découverte, 2 Intermédiaire, 3 Avancé")
    parser.add_argument("--out", type=Path, help="chemin du fichier à écrire")
    parser.add_argument(
        "--official", action="store_true", help="écrire dans experiments/ (visible à l'accueil)"
    )
    parser.add_argument("--force", action="store_true", help="écraser un fichier existant")
    parser.add_argument("--no-check", action="store_true", help="ne pas valider le brouillon créé")
    parser.add_argument("--list", action="store_true", help="liste les modèles")
    parser.add_argument("--check", type=Path, metavar="FICHIER", help="valide un fichier YAML et quitte")
    args = parser.parse_args(argv)

    if args.list:
        for name, (source, what) in MODELS.items():
            print(f"{name:12s} {what}  [experiments/{source}]")
        return 0
    if args.check:
        return 0 if check(args.check) else 1
    if not args.model or not args.id:
        parser.error("indiquez un modèle et un identifiant (ou --list, ou --check FICHIER).")
    try:
        path = create(
            args.model,
            args.id,
            title=args.title,
            discipline=args.discipline,
            level=args.level,
            out=args.out,
            official=args.official,
            force=args.force,
        )
    except NewExperimentError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"Brouillon créé : {shown} (modèle « {args.model} »)")
    ok = True if args.no_check else check(path)
    if path.parent == DRAFTS:
        print("Pour le rendre visible à l'accueil : déplacez-le dans experiments/")
        print("(et remplacez le chemin du schéma de l'en-tête par ./schema.json).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
