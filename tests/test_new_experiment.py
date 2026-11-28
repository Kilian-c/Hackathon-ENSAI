"""`scripts/new_experiment.py` : un brouillon créé depuis chaque modèle est valide, le chargeur du moteur ne
lit jamais le dossier des brouillons, et les erreurs d'usage sont claires."""

import importlib.util
from pathlib import Path

import pytest

from backend.api import registry
from backend.engine.loader import load_experiment
from backend.engine.validate import validate

ROOT = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location("new_experiment", ROOT / "scripts" / "new_experiment.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _script()


@pytest.mark.parametrize("model", list(script.MODELS))
def test_each_model_gives_a_valid_draft_with_its_own_identity(model: str, tmp_path: Path) -> None:
    out = tmp_path / "essai.yaml"
    path = script.create(
        model, "essai-modele", title="Mon titre", discipline="ma discipline", level="2", out=out
    )
    text = path.read_text(encoding="utf-8")
    spec = load_experiment(text)
    identity = (spec.id, spec.title, spec.discipline, spec.level)
    assert identity == ("essai-modele", "Mon titre", "ma discipline", "2")
    report = validate(text)
    assert report.errors == [] and report.ok, [t for t in report.tests if not t.passed]


def test_draft_header_points_to_the_schema_and_lists_what_to_edit(tmp_path: Path) -> None:
    out = tmp_path / "sous" / "dossier" / "x.yaml"
    text = script.create("statistique", "x-essai", out=out).read_text(encoding="utf-8")
    first = text.splitlines()[0]
    assert first.startswith("# yaml-language-server: $schema=") and first.endswith("experiments/schema.json")
    assert text.count("yaml-language-server") == 1  # l'en-tête du modèle n'est pas dupliquée
    assert "scripts/new_experiment.py" in text and "au moins 3 questions" in text


def test_default_location_is_outside_what_the_engine_reads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(script, "DRAFTS", tmp_path / "brouillons")
    path = script.create("algebre", "algo-essai")
    assert path == tmp_path / "brouillons" / "algo_essai.yaml" and path.exists()
    assert "algo-essai" not in registry.official()  # le registre ne lit pas les sous-dossiers
    assert sorted(p.name for p in registry.EXPERIMENTS_DIR.glob("*.yaml")) == sorted(
        p.name for p in (ROOT / "experiments").glob("*.yaml")
    )


def test_usage_errors_are_french_and_say_what_to_do(tmp_path: Path) -> None:
    err = script.NewExperimentError
    with pytest.raises(err, match="Identifiant invalide"):
        script.create("statistique", "Mauvais Nom", out=tmp_path / "a.yaml")
    with pytest.raises(err, match="existe déjà"):
        script.create("statistique", "regression-lineaire", out=tmp_path / "b.yaml")  # identifiant officiel
    with pytest.raises(err, match="Modèle inconnu"):
        script.create("inconnu", "nouveau", out=tmp_path / "c.yaml")
    with pytest.raises(err, match="niveau"):
        script.create("statistique", "nouveau", level="9", out=tmp_path / "d.yaml")
    script.create("statistique", "nouveau", out=tmp_path / "e.yaml")
    with pytest.raises(err, match="--force"):
        script.create("statistique", "autre", out=tmp_path / "e.yaml")
    script.create("statistique", "autre", out=tmp_path / "e.yaml", force=True)  # --force écrase


def test_command_line_list_create_and_check(tmp_path: Path, capsys) -> None:
    assert script.main(["--list"]) == 0
    assert "algebre" in capsys.readouterr().out
    out = tmp_path / "cli.yaml"
    assert script.main(["statistique", "cli-essai", "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "Brouillon créé" in printed and "Validation : OK" in printed
    assert script.main(["--check", str(out)]) == 0
    broken = tmp_path / "casse.yaml"
    typo = out.read_text(encoding="utf-8").replace("healthy_value", "healty_value", 1)
    broken.write_text(typo, encoding="utf-8")
    assert script.main(["--check", str(broken)]) == 1
    assert "ERREUR" in capsys.readouterr().out
    assert script.main(["statistique", "Mauvais Nom"]) == 2  # erreur d'usage : code 2, message sur stderr
