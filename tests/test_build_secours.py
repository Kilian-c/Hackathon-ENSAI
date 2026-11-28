"""`scripts/build_secours.py` : la branche orpheline `secours-dist`, essayée sur un dépôt git jetable."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location("build_secours", ROOT / "scripts" / "build_secours.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _script()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Un dépôt comme le vrai : `main`, un `.gitignore` qui ignore frontend/dist, et un dist construit."""
    folder = tmp_path / "repo"
    folder.mkdir()
    git(folder, "init", "-q", "-b", "main")
    git(folder, "config", "user.name", "Test")
    git(folder, "config", "user.email", "test@example.org")
    git(folder, "config", "commit.gpgsign", "false")
    write(folder / ".gitignore", "dist/\nfrontend/dist/\n")
    write(folder / "backend" / "main.py", "app = 1\n")
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "source")
    write(folder / "frontend" / "dist" / "index.html", "<title>Crash-Test</title>")
    write(folder / "frontend" / "dist" / "assets" / "app.js", "console.log('ok')")
    return folder


def dist(repo: Path) -> Path:
    return repo / "frontend" / "dist"


def test_branch_is_orphan_with_only_the_dist_and_a_readme(repo: Path) -> None:
    source = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    commit = script.make_branch(repo, dist(repo))
    files = git(repo, "ls-tree", "-r", "--name-only", "secours-dist").stdout.split()
    assert sorted(files) == ["README.md", "frontend/dist/assets/app.js", "frontend/dist/index.html"]
    assert git(repo, "rev-list", "--count", "secours-dist").stdout.strip() == "1"
    assert git(repo, "rev-parse", "secours-dist").stdout.strip() == commit
    assert git(repo, "merge-base", "main", "secours-dist", check=False).returncode != 0  # aucun ancêtre
    readme = git(repo, "show", "secours-dist:README.md").stdout
    assert "PAS à fusionner" in readme and source in readme
    assert "git restore --source=origin/secours-dist" in readme


def test_git_refuses_to_merge_it_into_main(repo: Path) -> None:
    script.make_branch(repo, dist(repo))
    merge = git(repo, "merge", "secours-dist", check=False)
    assert merge.returncode != 0  # « refusing to merge unrelated histories » (texte selon la langue de git)
    assert not (repo / "README.md").exists()  # main n'a rien reçu
    assert git(repo, "rev-list", "--count", "main").stdout.strip() == "1"


def test_current_branch_working_tree_index_and_worktrees_are_untouched(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD").stdout
    script.make_branch(repo, dist(repo))
    assert git(repo, "branch", "--show-current").stdout.strip() == "main"
    assert git(repo, "rev-parse", "HEAD").stdout == head
    assert git(repo, "status", "--porcelain").stdout == ""  # dist reste ignoré, rien d'indexé
    assert (dist(repo) / "index.html").exists() and (repo / "backend" / "main.py").exists()
    assert len(git(repo, "worktree", "list").stdout.strip().splitlines()) == 1  # temporaire retiré
    assert git(repo, "branch", "--list", "secours-dist-tmp").stdout.strip() == ""


def test_running_again_replaces_the_branch_with_a_single_commit(repo: Path) -> None:
    first = script.make_branch(repo, dist(repo))
    write(dist(repo) / "index.html", "<title>Nouvelle version</title>")
    second = script.make_branch(repo, dist(repo))
    assert first != second
    assert git(repo, "rev-list", "--count", "secours-dist").stdout.strip() == "1"  # historique stable
    assert "Nouvelle version" in git(repo, "show", "secours-dist:frontend/dist/index.html").stdout


def test_dirty_tree_is_refused_unless_forced(repo: Path) -> None:
    write(repo / "backend" / "main.py", "app = 2\n")  # fichier suivi modifié, non commité
    with pytest.raises(script.SecoursError, match="non commitées"):
        script.make_branch(repo, dist(repo))
    script.make_branch(repo, dist(repo), force=True)
    assert git(repo, "rev-parse", "--verify", "secours-dist").returncode == 0


def test_incomplete_or_dangerous_dist_is_refused(repo: Path) -> None:
    (dist(repo) / "index.html").unlink()
    with pytest.raises(script.SecoursError, match="index.html"):
        script.make_branch(repo, dist(repo))
    write(dist(repo) / "index.html", "<title>x</title>")
    write(dist(repo) / "assets" / "app.js", "const k = 'sb_secret_abcDEF123'")
    with pytest.raises(script.SecoursError, match="clé d'administration"):
        script.make_branch(repo, dist(repo))
    write(dist(repo) / "assets" / "app.js", "const role = 'service_role'")
    with pytest.raises(script.SecoursError, match="service_role"):
        script.make_branch(repo, dist(repo))
    assert git(repo, "rev-parse", "--verify", "secours-dist", check=False).returncode != 0  # rien créé


def test_restore_installs_the_dist_elsewhere_without_staging_it(repo: Path, tmp_path: Path) -> None:
    script.make_branch(repo, dist(repo))
    clone = tmp_path / "collaborateur"
    git(tmp_path, "clone", "-q", str(repo), str(clone))
    assert not dist(clone).exists()  # un clone ne reçoit pas le dist ignoré
    git(clone, "fetch", "-q", "origin", "secours-dist")
    git(clone, "restore", "--source=origin/secours-dist", "--worktree", "--", "frontend/dist")
    assert (dist(clone) / "index.html").read_text(encoding="utf-8") == "<title>Crash-Test</title>"
    assert git(clone, "status", "--porcelain").stdout == ""  # ignoré
    assert git(clone, "diff", "--cached", "--name-only").stdout == ""  # et surtout pas indexé
