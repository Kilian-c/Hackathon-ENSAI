"""Fichiers générés depuis le moteur (chantier modularité, R3) : ils doivent rester à jour.

- frontend/src/lib/catalog.gen.ts (scripts/gen_catalog.py) : lu par le prompt de l'écran Import ;
- experiments/schema.json (scripts/export_schema.py --yaml) : autocomplétion du YAML dans VS Code.

Si un de ces tests échoue après l'ajout d'une méthode, d'une loi, d'une fonction ou d'un champ du
schéma : relancez la commande indiquée et commitez le fichier régénéré.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalogue_a_jour():
    gen = _script("gen_catalog")
    current = gen.OUT.read_text(encoding="utf-8")
    message = "Lancez « uv run python scripts/gen_catalog.py » et commitez catalog.gen.ts."
    assert current == gen.render(), message


def test_catalogue_couvre_tout_le_registre():
    import backend.methods  # noqa: F401
    from backend.engine.aggregators import list_aggregators
    from backend.engine.laws import list_laws
    from backend.engine.method_contract import list_methods

    catalog = _script("gen_catalog").build_catalog()
    assert [m["name"] for m in catalog["methods"]] == sorted(list_methods())
    assert [law["name"] for law in catalog["laws"]] == sorted(list_laws())
    assert [a["name"] for a in catalog["aggregators"]] == sorted(list_aggregators())
    for m in catalog["methods"]:
        assert "rng" not in [a["name"] for a in m["args"]]
        assert m["provides"], f"{m['name']} : provides vide"


def test_kinds_lus_dans_le_module():
    catalog = _script("gen_catalog").build_catalog()
    kinds = {m["name"]: m["kinds"] for m in catalog["methods"]}
    assert set(kinds["statistic"]) >= {"sum", "mean", "median"}
    assert kinds["one_sample_test"] == ["student", "wilcoxon"]


def test_schema_yaml_a_jour():
    exp = _script("export_schema")
    assert exp.YAML_SCHEMA.read_text(encoding="utf-8") == exp.yaml_schema(), (
        "Lancez « bash scripts/gen_types.sh » et commitez experiments/schema.json."
    )


def test_schema_yaml_refuse_les_cles_inconnues():
    schema = json.loads(_script("export_schema").yaml_schema())
    assert schema["additionalProperties"] is False
    assert {"id", "title", "generator", "methods", "measures"} <= set(schema["required"])
