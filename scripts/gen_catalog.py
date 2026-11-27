"""Catalogue du moteur (R1) : lit les registres (méthodes, lois, fonctions, agrégateurs, vues) et écrit

  - frontend/src/lib/catalog.gen.ts : données pour l'interface (prompt de l'écran Import, R3) ;
  - docs/catalogue.md : la même chose lisible par les humains.

    uv run python scripts/gen_catalog.py           écrit les deux fichiers
    uv run python scripts/gen_catalog.py --check   échoue s'ils ne sont plus à jour (tests)

À relancer et à commiter quand une méthode, une loi, une fonction, un agrégateur ou une vue change.
Les fichiers générés ne s'éditent jamais à la main.
"""

import inspect
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import backend.methods  # noqa: E402,F401  (remplit le registre des méthodes)
from backend.engine.aggregators import list_aggregators  # noqa: E402
from backend.engine.expr import ALLOWED_KEYWORDS, BASE_FUNCTIONS, CONSTANTS  # noqa: E402
from backend.engine.laws import list_laws  # noqa: E402
from backend.engine.method_contract import list_methods  # noqa: E402

TS_OUT = ROOT / "frontend" / "src" / "lib" / "catalog.gen.ts"
MD_OUT = ROOT / "docs" / "catalogue.md"

# Fonctions fournies par le générateur `random` (elles dépendent du flux aléatoire : pas dans BASE_FUNCTIONS).
GENERATOR_FUNCTIONS = {
    "law": "law('nom') : un tirage de la loi du registre (standardisée)",
    "normal": "normal() : un tirage de la loi normale standard",
    "uniform": "uniform() : un tirage de la loi uniforme standardisée",
    "bernoulli": "bernoulli(p) : un tirage de Bernoulli de paramètre p",
}
GENERATOR_NAMES = {"idx": "indice d'observation (0, 1, ..., n - 1)"}

# Pas de registre des vues côté moteur : les types sont dessinés par `frontend/src/lib/plot.ts`
# (`buildFigure`), et un type inconnu retombe sur `measures_table`. Cette liste est celle de `buildFigure`.
VIEWS = {
    "scatter": "nuage de points (données et droite ajustée)",
    "residuals": "résidus en fonction des valeurs ajustées",
    "curves": "courbes y(x) ou y(t) par méthode",
    "repetitions": "une grandeur sur les répétitions (mode `intervals`, ou `paths` pour des trajectoires)",
    "distribution": "distribution d'une grandeur sur les répétitions",
    "sensitivity": "mesure primaire en fonction d'un axe (hypothèse ou paramètre), calculée par /api/sweep",
    "validity_domain": "carte des verdicts sur deux axes, calculée par /api/sweep",
    "heatmap": "matrices en cartes de couleur (série `matrix`, `paths[i][j]` = coefficient (i + 1, j + 1))",
    "measures_table": "tableau des mesures (vue de secours)",
}


def _first_line(doc: str | None) -> str:
    """Premier paragraphe d'une docstring, sur une seule ligne."""
    if not doc or not doc.strip():
        return ""
    paragraph = doc.strip().split("\n\n")[0]
    return " ".join(line.strip() for line in paragraph.splitlines())


def build() -> dict[str, Any]:
    methods = []
    for name, spec in sorted(list_methods().items()):
        args = [p for p in inspect.signature(spec.fn).parameters if p != "rng"]
        methods.append(
            {
                "name": name,
                "args": args,
                "provides": {block: list(keys) for block, keys in spec.provides.items()},
                "cost": spec.cost,
                "doc": _first_line(spec.fn.__doc__),
            }
        )
    laws = [
        {"name": n, "has_mean": law.has_mean, "has_variance": law.has_variance}
        for n, law in sorted(list_laws().items())
    ]
    functions = [{"name": n, "doc": ""} for n in sorted(BASE_FUNCTIONS)]
    functions += [{"name": n, "doc": d} for n, d in GENERATOR_FUNCTIONS.items()]
    return {
        "methods": methods,
        "laws": laws,
        "functions": functions,
        "constants": sorted(CONSTANTS),
        "names": [{"name": n, "doc": d} for n, d in GENERATOR_NAMES.items()],
        "keywords": sorted(ALLOWED_KEYWORDS),
        "aggregators": sorted(list_aggregators()),
        "views": [{"type": t, "doc": d} for t, d in VIEWS.items()],
    }


def to_ts(catalog: dict[str, Any]) -> str:
    body = json.dumps(catalog, ensure_ascii=False, indent=2)
    return (
        "/**\n"
        " * FICHIER GÉNÉRÉ par scripts/gen_catalog.py depuis les registres du moteur (backend/).\n"
        " * Ne pas modifier à la main : modifiez le registre, puis relancez\n"
        " * « uv run python scripts/gen_catalog.py » et commitez le résultat.\n"
        " */\n\n"
        "export interface CatalogMethod {\n"
        "  name: string\n"
        "  args: string[]\n"
        "  provides: Record<string, string[]>\n"
        "  cost: string\n"
        "  doc: string\n"
        "}\n\n"
        "export interface Catalog {\n"
        "  methods: CatalogMethod[]\n"
        "  laws: { name: string; has_mean: boolean; has_variance: boolean }[]\n"
        "  functions: { name: string; doc: string }[]\n"
        "  constants: string[]\n"
        "  names: { name: string; doc: string }[]\n"
        "  keywords: string[]\n"
        "  aggregators: string[]\n"
        "  views: { type: string; doc: string }[]\n"
        "}\n\n"
        f"export const CATALOG: Catalog = {body}\n"
    )


def to_md(catalog: dict[str, Any]) -> str:
    out = [
        "# Catalogue du moteur\n",
        "Fichier généré par `scripts/gen_catalog.py` : ne pas l'éditer à la main.\n",
        "## Méthodes (`call:` d'un YAML)\n",
        "| Méthode | Arguments | Fournit | Coût | Rôle |",
        "|---|---|---|---|---|",
    ]
    for m in catalog["methods"]:
        provides = " ; ".join(f"{b} : {', '.join(k)}" for b, k in m["provides"].items())
        out.append(f"| `{m['name']}` | {', '.join(m['args'])} | {provides} | `{m['cost']}` | {m['doc']} |")
    out += ["", "## Lois (`law('nom')`)\n", "| Loi | Moyenne | Variance |", "|---|---|---|"]
    for law in catalog["laws"]:
        mean, var = ("oui" if law[k] else "non" for k in ("has_mean", "has_variance"))
        out.append(f"| `{law['name']}` | {mean} | {var} |")
    out += ["", "## Fonctions des expressions\n"]
    out.append(", ".join(f"`{f['name']}`" for f in catalog["functions"]) + ".")
    constants = ", ".join(f"`{c}`" for c in catalog["constants"])
    keywords = ", ".join(f"`{k}`" for k in catalog["keywords"])
    out.append(f"\nConstantes : {constants}. Mot-clé accepté : {keywords}.")
    for item in [*(f for f in catalog["functions"] if f["doc"]), *catalog["names"]]:
        out.append(f"- `{item['name']}` : {item['doc']}")
    aggregators = ", ".join(f"`{a}`" for a in catalog["aggregators"])
    out += ["", "## Agrégateurs (`agg:` d'une mesure)\n", aggregators + ".", ""]
    out += ["## Vues (`type:` d'une vue)\n", "| Type | Rôle |", "|---|---|"]
    out += [f"| `{v['type']}` | {v['doc']} |" for v in catalog["views"]]
    return "\n".join(out) + "\n"


def main() -> int:
    catalog = build()
    outputs = {TS_OUT: to_ts(catalog), MD_OUT: to_md(catalog)}
    if "--check" in sys.argv:
        stale = [p for p, text in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            names = ", ".join(str(p.relative_to(ROOT)) for p in stale)
            print(f"Catalogue périmé ({names}) : lancez scripts/gen_catalog.py.", file=sys.stderr)
            return 1
        print("Le catalogue est à jour.")
        return 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(f"Généré : {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
