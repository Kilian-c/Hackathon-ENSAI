"""Exporte le JSON Schema des contrats (contracts.py) et du schéma YAML (ExperimentSpec), pour
scripts/gen_types.sh qui en tire frontend/src/lib/types.gen.ts (R3). Avec `--yaml`, écrit aussi
experiments/schema.json, le schéma d'un fichier d'expérience pour l'éditeur (voir yaml_schema).

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


YAML_SCHEMA = Path(__file__).resolve().parent.parent / "experiments" / "schema.json"


def yaml_schema() -> str:
    """Schéma JSON d'un fichier d'expérience, pour l'éditeur (autocomplétion et erreurs dans VS Code).

    Mode « validation » : il décrit ce qu'un auteur peut ÉCRIRE (champs facultatifs non requis, clés
    inconnues refusées comme par le chargeur). Les règles croisées (une seule mesure primaire, une
    seule méthode principale, chemins des `bind`...) restent vérifiées par le chargeur et
    `/api/validate`, pas par ce schéma.
    """
    schema = ExperimentSpec.model_json_schema(mode="validation")
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Expérience Crash-Test",
        "description": (
            "Fichier de experiments/ (schema_version 1). Généré par scripts/export_schema.py --yaml."
        ),
        **{k: v for k, v in schema.items() if k != "title"},
    }
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> None:
    # `--yaml` : écrit experiments/schema.json ; `--yaml --check` : échoue s'il n'est plus à jour.
    if sys.argv[1:2] == ["--yaml"]:
        text = yaml_schema()
        if "--check" in sys.argv[2:]:
            if not YAML_SCHEMA.exists() or YAML_SCHEMA.read_text(encoding="utf-8") != text:
                command = "bash scripts/gen_types.sh"
                message = f"experiments/schema.json n'est plus à jour : lancez « {command} ».\n"
                sys.stderr.buffer.write(message.encode())
                sys.exit(1)
            return
        YAML_SCHEMA.write_text(text, encoding="utf-8", newline="\n")
        return
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
