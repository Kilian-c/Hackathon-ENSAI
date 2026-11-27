"""Test du chargeur (R4) : les YAML de référence sont acceptés, trois YAML volontairement faux sont
refusés avec le bon numéro de ligne.

Les YAML faux sont fabriqués à partir de `regression_lineaire.yaml` : on altère une seule ligne et on attend
du chargeur qu'il désigne exactement cette ligne. Le numéro attendu est retrouvé dans le texte d'origine,
donc le test reste juste si R2 réécrit le fichier (tant que les lignes visées existent).
"""

from pathlib import Path

import pytest

from backend.engine.loader import ExperimentError, Issue, load_experiment, load_experiment_file

ROOT = Path(__file__).parent.parent / "experiments"
PLAYABLE = sorted(ROOT.glob("*.yaml"))
ARCHIVED = sorted((ROOT / "archives").glob("*.yaml"))
REGRESSION = (ROOT / "regression_lineaire.yaml").read_text(encoding="utf-8")


def _line_of(text: str, line: str) -> int:
    """Numéro (à partir de 1) de la première ligne exactement égale à `line`."""
    lines = text.splitlines()
    assert lines.count(line) >= 1, f"ligne introuvable dans le YAML de référence : {line!r}"
    return lines.index(line) + 1


def _issues(text: str) -> list[Issue]:
    with pytest.raises(ExperimentError) as info:
        load_experiment(text)
    return info.value.issues


def _broken(old: str, new: str) -> tuple[str, int]:
    """YAML de la régression dont la ligne `old` (la première) devient `new`, et le numéro de cette ligne."""
    line = _line_of(REGRESSION, old)
    lines = REGRESSION.splitlines(keepends=True)
    lines[line - 1] = new + "\n"
    return "".join(lines), line


# --- YAML de référence acceptés ---------------------------------------------------------------------


def test_there_are_reference_yamls():
    assert len(PLAYABLE) >= 7, "les expériences jouables doivent être dans experiments/"
    assert len(ARCHIVED) >= 2, "Student et le pendule doivent rester dans experiments/archives/"


@pytest.mark.parametrize("path", PLAYABLE + ARCHIVED, ids=lambda p: p.name)
def test_reference_yaml_is_accepted(path: Path):
    spec = load_experiment_file(path)
    assert spec.schema_version == 1
    assert spec.id and spec.title
    assert spec.level in {"1", "2", "3"}, f"niveau attendu « 1 », « 2 » ou « 3 », reçu {spec.level!r}"
    assert sum(m.primary for m in spec.measures.values()) == 1
    assert sum(m.role == "method" for m in spec.methods) == 1


@pytest.mark.parametrize("path", PLAYABLE + ARCHIVED, ids=lambda p: p.name)
def test_reference_yaml_text_is_clean(path: Path):
    """Garde-fou contre une copie depuis le PDF (CLAUDE.md, section 7) : accents cassés, espaces insérés."""
    text = path.read_text(encoding="utf-8")
    for damage in (" é ", "p . ", "law ( ", "’"):
        assert damage not in text, f"{path.name} contient « {damage} » : copie depuis le PDF ?"


# --- Trois YAML volontairement faux, refusés avec le bon numéro de ligne -----------------------------


def test_syntax_error_tab_reports_line():
    """Faux n° 1, erreur de syntaxe : une tabulation en début de ligne (interdite en YAML)."""
    text, line = _broken("    step: 0.05", "\tstep: 0.05")
    issues = _issues(text)
    assert len(issues) == 1
    assert issues[0].line == line
    assert issues[0].message.startswith("YAML invalide")


def test_unknown_field_typo_reports_line():
    """Faux n° 2, faute de frappe dans un champ d'hypothèse : `healty_value` au lieu de `healthy_value`."""
    text, line = _broken("    healthy_value: 0.0", "    healty_value: 0.0")
    issues = _issues(text)
    unknown = [i for i in issues if i.path.endswith("healty_value")]
    assert len(unknown) == 1
    assert unknown[0].line == line
    assert unknown[0].message == "Champ inconnu."
    # Le champ obligatoire manquant est signalé aussi, sur l'hypothèse qui le réclame.
    missing = [i for i in issues if i.path.endswith("healthy_value")]
    assert [i.message for i in missing] == ["Champ obligatoire manquant."]


def test_wrong_type_reports_line():
    """Faux n° 3, mauvais type : un pas de curseur écrit en texte."""
    text, line = _broken("    step: 0.05", '    step: "beaucoup"')
    issues = _issues(text)
    assert len(issues) == 1
    assert issues[0].line == line
    assert issues[0].path.endswith(".step")
    assert issues[0].message == "Type de valeur incorrect."


def test_error_messages_are_in_french():
    text, _ = _broken("    step: 0.05", '    step: "beaucoup"')
    assert "ligne" in str(_issues(text)[0])
