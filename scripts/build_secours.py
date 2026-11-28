"""Fabrique la branche de secours `secours-dist` : l'interface construite, pour une machine sans Node (R1).

    uv run python scripts/build_secours.py                # construit frontend/dist puis crée la branche
    uv run python scripts/build_secours.py --no-build     # réutilise le frontend/dist existant
    uv run python scripts/build_secours.py --force        # accepte un arbre de travail modifié

À lancer UNE FOIS, sur la version finale validée (après le gel du code) : un `dist` doit correspondre à la
version du moteur. Le script :

1. construit `frontend/dist` SANS `VITE_API_URL` (l'interface appelle alors `/api` sur le même serveur) ;
2. vérifie le résultat (page, scripts, aucune clé secrète dans le code envoyé au navigateur) ;
3. crée la branche **orpheline** `secours-dist` : un seul commit, qui ne contient que `frontend/dist/` et un
   `README.md`, sans aucun historique commun avec `main` (git refuse donc de la fusionner : pas de risque
   d'ajouter 6 Mo de binaire à `main`). Elle est recréée à chaque fois : l'historique reste à un commit.

Votre branche courante, votre arbre de travail et votre index ne sont pas touchés (le commit se fait dans un
répertoire de travail temporaire). Le script ne pousse JAMAIS : il affiche la commande à lancer.

Récupération, sur n'importe quelle machine qui a cloné le dépôt (sans Node) :

    git fetch origin secours-dist
    git restore --source=origin/secours-dist --worktree -- frontend/dist
    uv run uvicorn backend.main:app --port 8000        # puis http://127.0.0.1:8000/

(`git restore --worktree`, et non `git checkout origin/secours-dist -- frontend/dist`, qui mettrait les
fichiers dans l'index : on pourrait alors les commiter par erreur.)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANCH = "secours-dist"
# Ne doit jamais se retrouver dans le code envoyé au navigateur (clés d'administration Supabase).
FORBIDDEN = (re.compile(rb"service_role"), re.compile(rb"sb_secret_[A-Za-z0-9_-]+"))

README = """\
# Crash-Test : interface construite (branche de secours)

**Cette branche n'est PAS à fusionner dans `main`.** Elle ne contient que l'interface déjà construite
(`frontend/dist/`), pour faire tourner Crash-Test sur une machine sans Node.

- Code source : `{source}` (branche `{source_branch}`), construit le {date}.
- Taille : {size} dans {files} fichiers. Construit sans `VITE_API_URL` : l'interface appelle `/api` sur le
  même serveur que celui qui la sert.

## Utilisation

Depuis un clone du dépôt, sur `main` à jour (le moteur vient de `main`, pas d'ici) :

```bash
git fetch origin secours-dist
git restore --source=origin/secours-dist --worktree -- frontend/dist
uv run uvicorn backend.main:app --port 8000
```

Puis ouvrez <http://127.0.0.1:8000/>. Le moteur charge les expériences au démarrage (environ 3 s) et sert
l'interface sur `/`. `frontend/dist` est ignoré par git : rien n'est ajouté à `main`.

- N'utilisez pas `git checkout origin/secours-dist -- frontend/dist` : il mettrait les fichiers dans
  l'index, et on pourrait les commiter par erreur.
- Ce `dist` correspond au commit `{short}` : si `main` a changé depuis, reconstruisez
  (`cd frontend && npm ci && npm run build`, sans `VITE_API_URL`) ou régénérez cette branche avec
  `uv run python scripts/build_secours.py`.
"""


class SecoursError(Exception):
    """Erreur d'usage ou de vérification : le message dit quoi faire."""


def git(*args: str, cwd: Path, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and result.returncode != 0:
        raise SecoursError(f"git {' '.join(args)} a échoué : {(result.stderr or result.stdout).strip()}")
    return result.stdout.strip()


def build_frontend(root: Path = ROOT) -> None:
    """`npm run build` sans VITE_API_URL (la variable du shell l'emporte sur frontend/.env)."""
    npm = shutil.which("npm")
    if npm is None:
        raise SecoursError(
            "npm est introuvable : installez Node, ou utilisez --no-build avec un dist déjà construit."
        )
    frontend = root / "frontend"
    if not (frontend / "node_modules").is_dir():
        print("Installation des dépendances (npm ci)...")
        subprocess.run([npm, "ci"], cwd=frontend, check=True)
    env = {**os.environ, "VITE_API_URL": ""}
    print("Construction de l'interface sans VITE_API_URL...")
    result = subprocess.run([npm, "run", "build"], cwd=frontend, env=env)
    if result.returncode != 0:
        raise SecoursError("La construction de l'interface a échoué (voir ci-dessus).")


def verify_dist(dist: Path) -> tuple[int, int]:
    """Contrôle `dist` ; renvoie (nombre de fichiers, taille en octets)."""
    if not (dist / "index.html").is_file():
        raise SecoursError(f"{dist}/index.html est absent : construisez l'interface (retirez --no-build).")
    if not any((dist / "assets").glob("*.js")):
        raise SecoursError(f"{dist}/assets ne contient aucun script : le build est incomplet.")
    files = [p for p in dist.rglob("*") if p.is_file()]
    for path in files:
        if path.suffix in {".js", ".html", ".css", ".json", ".map"}:
            data = path.read_bytes()
            for pattern in FORBIDDEN:
                if pattern.search(data):
                    raise SecoursError(
                        f"{path.relative_to(dist)} contient « {pattern.pattern.decode()} » : une clé "
                        "d'administration ne doit jamais être dans le code envoyé au navigateur. "
                        "Retirez-la de frontend/.env."
                    )
    return len(files), sum(p.stat().st_size for p in files)


def human(size: int) -> str:
    return f"{size / 1_048_576:.1f}".replace(".", ",") + " Mo"


def make_branch(repo: Path, dist: Path, branch: str = BRANCH, *, force: bool = False) -> str:
    """Crée (ou remplace) la branche orpheline `branch` avec `dist` ; renvoie le commit créé."""
    if not (repo / ".git").exists():
        raise SecoursError(f"{repo} n'est pas un dépôt git.")
    dirty = git("status", "--porcelain", "--untracked-files=no", cwd=repo)
    if dirty and not force:
        raise SecoursError(
            "L'arbre de travail contient des modifications non commitées : le dist ne correspondrait pas à "
            "un commit précis. Commitez-les, ou ajoutez --force.\n" + dirty
        )
    source = git("rev-parse", "HEAD", cwd=repo)
    short = git("rev-parse", "--short", "HEAD", cwd=repo)
    source_branch = git("branch", "--show-current", cwd=repo) or "(HEAD détachée)"
    count, size = verify_dist(dist)

    work = Path(tempfile.mkdtemp(prefix="secours-"))
    temp_branch = f"{branch}-tmp"
    try:
        git("worktree", "add", "--detach", str(work), "HEAD", cwd=repo)
        git("checkout", "-q", "--orphan", temp_branch, cwd=work)
        git("rm", "-rf", "-q", "--ignore-unmatch", ".", cwd=work)
        for leftover in work.iterdir():  # dossiers vides ou ignorés restés après `git rm`
            if leftover.name != ".git":
                shutil.rmtree(leftover) if leftover.is_dir() else leftover.unlink()
        shutil.copytree(dist, work / "frontend" / "dist")
        (work / "README.md").write_text(
            README.format(
                source=source,
                short=short,
                source_branch=source_branch,
                date=dt.datetime.now().strftime("%d/%m/%Y à %H:%M"),
                size=human(size),
                files=count,
            ),
            encoding="utf-8",
        )
        git("add", "-f", "-A", cwd=work)
        git(
            "-c", "commit.gpgsign=false", "commit", "-q", "-m",
            f"Interface construite pour la version locale de secours (source : {short})",
            cwd=work,
        )
        commit = git("rev-parse", "HEAD", cwd=work)
        git("branch", "-f", branch, commit, cwd=repo)
    finally:
        git("worktree", "remove", "--force", str(work), cwd=repo, check=False)
        git("branch", "-D", temp_branch, cwd=repo, check=False)
        git("worktree", "prune", cwd=repo, check=False)
        shutil.rmtree(work, ignore_errors=True)
    return commit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Crée la branche de secours `secours-dist` (interface construite)."
    )
    parser.add_argument(
        "--no-build", action="store_true", help="réutiliser frontend/dist sans le reconstruire"
    )
    parser.add_argument("--force", action="store_true", help="accepter un arbre de travail modifié")
    parser.add_argument("--branch", default=BRANCH, help=f"nom de la branche (défaut : {BRANCH})")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        if not args.no_build:
            build_frontend()
        commit = make_branch(ROOT, ROOT / "frontend" / "dist", args.branch, force=args.force)
    except SecoursError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
    count, size = verify_dist(ROOT / "frontend" / "dist")
    print(f"\nBranche « {args.branch} » créée : {commit[:7]} ({count} fichiers, {human(size)}),")
    print("sans historique commun avec main (git refusera de la fusionner).")
    print("Votre branche courante et votre arbre de travail n'ont pas été modifiés. Rien n'est poussé.")
    print("\nPour la partager (c'est à vous de pousser ; --force-with-lease car la branche est recréée) :")
    print(f"    git push --force-with-lease origin {args.branch}")
    print("\nPour l'installer ailleurs (sans Node) :")
    print(f"    git fetch origin {args.branch}")
    print(f"    git restore --source=origin/{args.branch} --worktree -- frontend/dist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
