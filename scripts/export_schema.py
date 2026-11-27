"""Exporte le JSON Schema des contrats (contracts.py) et du schéma YAML (ExperimentSpec), pour
scripts/gen_types.sh qui en tire frontend/src/lib/types.gen.ts (R3).

Mode « serialization » : le schéma décrit ce que le serveur ENVOIE. Pydantic envoie toujours tous les
champs, même ceux qui ont une valeur par défaut : on les marque donc tous comme requis, pour que
TypeScript n'oblige pas l'interface à tester `undefined` partout.
"""

import inspect
import json
import sys
from pathlib import Path

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import contracts  # noqa: E402
from backend.engine.schema import ExperimentSpec  # noqa: E402


def contract_models() -> list[type[BaseModel]]:
    """Tous les modèles Pydantic définis dans contracts.py, dans l'ordre du fichier."""
    models = [
        obj
        for _, obj in inspect.getmembers(contracts, inspect.isclass)
        if issubclass(obj, BaseModel)
        and obj.__module__ == contracts.__name__
        and obj is not contracts.Contract
    ]
    return sorted(models, key=lambda m: inspect.getsourcelines(m)[1])


def require_all(node: object) -> None:
    """Marque requises toutes les propriétés de chaque objet du schéma (voir la docstring)."""
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            node["required"] = sorted(node["properties"])
        for value in node.values():
            require_all(value)
    elif isinstance(node, list):
        for value in node:
            require_all(value)


def strip_titles(node: object) -> None:
    """Retire les titres des champs : sans cela, json2ts crée un alias par champ (Id14, Series1...)."""
    if isinstance(node, dict):
        # Ici `node` est un schéma : sa clé « title » est une annotation de Pydantic, on la retire.
        node.pop("title", None)
        # Tuple homogène (ex. range: [min, max]) : json2ts ne lit pas prefixItems, on le traduit en items.
        prefix = node.get("prefixItems")
        if prefix and all(p == prefix[0] for p in prefix):
            node["items"] = node.pop("prefixItems")[0]
        for key, value in node.items():
            if key in ("properties", "patternProperties", "$defs"):
                # Dictionnaire {nom: schéma} : les noms (dont un champ « title ») restent intacts.
                for sub in value.values():
                    strip_titles(sub)
            else:
                strip_titles(value)
    elif isinstance(node, list):
        for value in node:
            strip_titles(value)


def main() -> None:
    models = [*contract_models(), ExperimentSpec]
    _, schema = models_json_schema([(m, "serialization") for m in models])
    for name, definition in schema["$defs"].items():
        strip_titles(definition)
        definition["title"] = name  # seul le nom du modèle devient un type TypeScript
    require_all(schema)
    # Écrit en UTF-8 dans le fichier donné (la sortie standard n'est pas en UTF-8 sous Windows).
    text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    Path(sys.argv[1]).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
