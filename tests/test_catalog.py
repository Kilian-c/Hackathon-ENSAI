"""Catalogue généré (`scripts/gen_catalog.py`) : à jour, complet, et cohérent avec les YAML officiels."""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("gen_catalog", ROOT / "scripts" / "gen_catalog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_files_are_up_to_date() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gen_catalog.py"), "--check"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_every_registered_method_is_in_the_catalog() -> None:
    from backend.engine.method_contract import list_methods

    names = {m["name"] for m in _load().build()["methods"]}
    assert names == set(list_methods())
    assert all(m["args"] for m in _load().build()["methods"])


def test_official_yaml_only_use_cataloged_things() -> None:
    catalog = _load().build()
    methods = {m["name"] for m in catalog["methods"]}
    views = {v["type"] for v in catalog["views"]}
    aggregators = set(catalog["aggregators"])
    laws = {law["name"] for law in catalog["laws"]}
    for path in sorted((ROOT / "experiments").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        doc = yaml.safe_load(text)
        assert {m["call"] for m in doc["methods"]} <= methods, path.name
        assert {v["type"] for v in doc["views"]} <= views, path.name
        for m in doc["measures"].values():
            assert re.match(r"(\w+)\(", m["agg"]).group(1) in aggregators, path.name
        assert set(re.findall(r"law\('(\w+)'\)", text)) <= laws, path.name
