"""Tests du moteur (R1). Pour l'instant : schéma YAML et chargeur."""

from pathlib import Path

import pytest

from backend.engine.loader import ExperimentError, load_experiment, load_experiment_file

EXPERIMENTS = sorted((Path(__file__).parent.parent / "experiments").glob("*.yaml"))
REGRESSION = (Path(__file__).parent.parent / "experiments" / "regression_lineaire.yaml").read_text(
    encoding="utf-8"
)


@pytest.mark.parametrize("path", EXPERIMENTS, ids=lambda p: p.name)
def test_reference_yamls_load(path):
    spec = load_experiment_file(path)
    assert spec.schema_version == 1
    assert sum(m.primary for m in spec.measures.values()) == 1


def _first_issue(text: str):
    with pytest.raises(ExperimentError) as info:
        load_experiment(text)
    return info.value.issues[0]


def test_unknown_field_reports_line():
    issue = _first_issue(REGRESSION.replace('level: "1A/2A"', 'level: "1A/2A"\nbidule: 3'))
    assert (issue.line, issue.path) == (6, "bidule")


def test_unknown_schema_version():
    issue = _first_issue(REGRESSION.replace("schema_version: 1", "schema_version: 2"))
    assert issue.line == 1


def test_unknown_repair_reports_line():
    issue = _first_issue(REGRESSION.replace("repairs: [hetero, relation]", "repairs: [hetero, fantome]"))
    assert issue.path == "methods[1].repairs[1]"
    assert issue.line == 147


def test_repeat_cap():
    issue = _first_issue(REGRESSION.replace("repeat: 500", "repeat: 5000"))
    assert issue.path.endswith("repeat")


def test_oversized_file():
    issue = _first_issue(REGRESSION + "#" * 70_000)
    assert issue.line is None
