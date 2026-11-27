"""gen_catalog.py : registres du moteur -> frontend/src/lib/catalog.gen.ts (chantier modularité).

Une seule source de vérité pour ce qu'un YAML peut appeler : méthodes (signature, `kind` possibles,
`provides`, coût, première phrase de la docstring), lois, agrégateurs, fonctions des expressions.
Le prompt de l'écran Import (`importPrompt.ts`) lit ce fichier : une méthode ajoutée avec
`@register_method` y apparaît sans rien recopier à la main.

    uv run python scripts/gen_catalog.py           régénère catalog.gen.ts
    uv run python scripts/gen_catalog.py --check   échoue si catalog.gen.ts n'est plus à jour

`kind` : lu dans la constante `_KINDS` du module de la méthode (tuple ou dictionnaire), quand elle
existe ; sinon la liste reste vide et la docstring dit quoi passer.
"""

from __future__ import annotations

import inspect
import io
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import backend.methods  # noqa: E402, F401  (remplit le registre des méthodes)
from backend.engine.aggregators import list_aggregators  # noqa: E402
from backend.engine.expr import BASE_FUNCTIONS, CONSTANTS  # noqa: E402
from backend.engine.laws import list_laws  # noqa: E402
from backend.engine.method_contract import list_methods  # noqa: E402

OUT = ROOT / "frontend" / "src" / "lib" / "catalog.gen.ts"

# Fonctions propres au générateur `random` (définies dans generators/random_world.generate, pas dans
# la liste blanche commune) : à tenir à jour si le générateur en ajoute.
GENERATOR_FUNCTIONS = [
    {"name": "law", "signature": "law('<loi>')", "doc": "tirage dans une loi du registre (voir laws)"},
    {"name": "normal", "signature": "normal()", "doc": "loi normale centrée réduite"},
    {"name": "uniform", "signature": "uniform()", "doc": "loi uniforme standardisée (moyenne 0, variance 1)"},
    {"name": "bernoulli", "signature": "bernoulli(p)", "doc": "booléen vrai avec la probabilité p"},
    {"name": "idx", "signature": "idx", "doc": "indice de l'observation, de 0 à n - 1"},
    {"name": "@h.<id>", "signature": "@h.<id>", "doc": "loi ou expression de l'option choisie"},
]

AGG_ARG_NAMES = {"values": "f", "key_or_value": "k"}

BANNER = """/**
 * FICHIER GÉNÉRÉ par scripts/gen_catalog.py depuis les registres du moteur (méthodes, lois,
 * agrégateurs, fonctions des expressions). Ne pas modifier à la main : relancez
 * « uv run python scripts/gen_catalog.py » après avoir ajouté une méthode, une loi ou une fonction.
 */"""

TYPES = """export interface CatalogArg {
  name: string
  /** Valeur par défaut (texte), null si l'argument est obligatoire. */
  default: string | null
}

export interface CatalogMethod {
  name: string
  args: CatalogArg[]
  /** Valeurs possibles de l'argument `kind` ; vide si la méthode n'en a pas (ou ne les déclare pas). */
  kinds: string[]
  provides: Record<string, string[]>
  cost: string
  doc: string
}

export interface CatalogLaw {
  name: string
  has_mean: boolean
  has_variance: boolean
}

export interface CatalogFunction {
  name: string
  signature: string
  doc: string
}

export interface Catalog {
  methods: CatalogMethod[]
  laws: CatalogLaw[]
  aggregators: CatalogFunction[]
  functions: string[]
  generator_functions: CatalogFunction[]
  constants: string[]
}"""


def first_sentence(doc: str | None) -> str:
    """Premier paragraphe d'une docstring, sur une ligne."""
    if not doc:
        return ""
    paragraph = inspect.cleandoc(doc).split("\n\n", 1)[0]
    return " ".join(line.strip() for line in paragraph.splitlines())


def method_kinds(fn: Any) -> list[str]:
    kinds = getattr(inspect.getmodule(fn), "_KINDS", None)
    if isinstance(kinds, dict):
        return [str(k) for k in kinds]
    if isinstance(kinds, (tuple, list, set, frozenset)):
        return [str(k) for k in kinds]
    return []


def method_args(fn: Any) -> list[dict[str, str | None]]:
    out = []
    for name, param in inspect.signature(fn).parameters.items():
        if name == "rng":  # fourni par le moteur, jamais écrit dans le YAML
            continue
        default = None if param.default is inspect.Parameter.empty else repr(param.default)
        out.append({"name": name, "default": default})
    return out


def build_catalog() -> dict[str, Any]:
    methods = [
        {
            "name": name,
            "args": method_args(spec.fn),
            "kinds": method_kinds(spec.fn),
            "provides": {block: list(keys) for block, keys in spec.provides.items()},
            "cost": spec.cost,
            "doc": first_sentence(spec.fn.__doc__),
        }
        for name, spec in sorted(list_methods().items())
    ]
    laws = [
        {"name": name, "has_mean": law.has_mean, "has_variance": law.has_variance}
        for name, law in sorted(list_laws().items())
    ]
    aggregators = []
    for name, fn in sorted(list_aggregators().items()):
        # Seuls les arguments obligatoires s'écrivent dans un YAML (summary_dict est fourni par le
        # moteur) ; noms courts de CLAUDE.md, section 8 : rate(f), quantile(f, q), summary(k).
        params = [
            AGG_ARG_NAMES.get(p.name, p.name)
            for p in inspect.signature(fn).parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        signature = f"{name}({', '.join(params)})"
        aggregators.append({"name": name, "signature": signature, "doc": first_sentence(fn.__doc__)})
    return {
        "methods": methods,
        "laws": laws,
        "aggregators": aggregators,
        "functions": sorted(BASE_FUNCTIONS),
        "generator_functions": GENERATOR_FUNCTIONS,
        "constants": sorted(CONSTANTS),
    }


def render() -> str:
    body = json.dumps(build_catalog(), ensure_ascii=False, indent=2)
    return f"{BANNER}\n\n{TYPES}\n\nexport const CATALOG: Catalog = {body}\n"


def main() -> int:
    # Sous Windows, la sortie standard n'est pas en UTF-8 par défaut : les accents seraient illisibles.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    text = render()
    if "--check" in sys.argv[1:]:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            command = "uv run python scripts/gen_catalog.py"
            print(f"catalog.gen.ts n'est plus à jour : lancez « {command} » et commitez-le.", file=sys.stderr)
            return 1
        print("catalog.gen.ts est à jour.")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print("Généré : frontend/src/lib/catalog.gen.ts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
