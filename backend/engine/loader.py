"""Lecture d'un YAML d'expérience et erreurs par numéro de ligne (R1).

`load_experiment(text)` renvoie un `ExperimentSpec` ou lève `ExperimentError`, dont `.issues` liste
les problèmes (ligne, chemin, message en français). Lecture par `yaml.safe_load` uniquement.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from backend.engine.schema import MAX_YAML_BYTES, SCHEMA_VERSION, ExperimentSpec, SpecIssues


@dataclass(frozen=True)
class Issue:
    line: int | None  # 1 = première ligne ; None si inconnue
    path: str  # ex. « methods[1].repairs[0] »
    message: str

    def __str__(self) -> str:
        where = f"ligne {self.line}" if self.line else "fichier"
        return f"{where}, {self.path or 'racine'} : {self.message}"


class ExperimentError(Exception):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__("\n".join(str(i) for i in issues))


def content_hash(text: str) -> str:
    """Empreinte du contenu YAML (entre dans la clé de cache et la graine des séries)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_experiment(text: str) -> ExperimentSpec:
    if len(text.encode("utf-8")) > MAX_YAML_BYTES:
        raise ExperimentError([Issue(None, "", f"Fichier trop gros ({MAX_YAML_BYTES // 1024} Ko au plus).")])
    try:
        root = yaml.compose(text, Loader=yaml.SafeLoader)
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        problem = getattr(exc, "problem", None) or str(exc)
        line = mark.line + 1 if mark else None
        raise ExperimentError([Issue(line, "", f"YAML invalide : {problem}")]) from exc
    if not isinstance(data, dict) or root is None:
        raise ExperimentError([Issue(1, "", "Le fichier doit contenir un dictionnaire de clés YAML.")])

    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        message = f"Version de schéma inconnue ({version!r}) : seule la version {SCHEMA_VERSION} existe."
        raise ExperimentError([Issue(_line(root, ("schema_version",)), "schema_version", message)])

    try:
        return ExperimentSpec.model_validate(data)
    except ValidationError as exc:
        raise ExperimentError(_issues_from(exc, root)) from exc


def load_experiment_file(path: str | Path) -> ExperimentSpec:
    return load_experiment(Path(path).read_text(encoding="utf-8"))


# --- Traduction des erreurs Pydantic ----------------------------------------------------------------------


def _issues_from(exc: ValidationError, root: yaml.Node) -> list[Issue]:
    issues: list[Issue] = []
    for err in exc.errors():
        loc = tuple(err["loc"])
        original = (err.get("ctx") or {}).get("error")
        if isinstance(original, SpecIssues):
            for sub_loc, message in original.issues:
                issues.append(Issue(_line(root, sub_loc), _path(sub_loc), message))
        else:
            issues.append(Issue(_line(root, loc), _path(loc), _message(err)))
    return issues


def _message(err: dict[str, Any]) -> str:
    ctx = err.get("ctx") or {}
    kind = err["type"]
    if kind == "extra_forbidden":
        return "Champ inconnu."
    if kind == "missing":
        return "Champ obligatoire manquant."
    if kind == "value_error":
        return str(ctx.get("error", err["msg"]))
    if kind == "string_pattern_mismatch":
        return "Format invalide (lettres, chiffres et _ ; identifiant : minuscules, chiffres, - et _)."
    if kind == "string_too_long":
        return f"Texte trop long ({ctx.get('max_length')} caractères au plus)."
    if kind == "too_long":
        return f"Trop d'éléments ({ctx.get('max_length')} au plus)."
    if kind == "too_short":
        return f"Pas assez d'éléments ({ctx.get('min_length')} au moins)."
    if kind in ("greater_than_equal", "greater_than"):
        return f"Valeur trop petite (minimum : {ctx.get('ge', ctx.get('gt'))})."
    if kind in ("less_than_equal", "less_than"):
        return f"Valeur trop grande (maximum : {ctx.get('le', ctx.get('lt'))})."
    if kind == "literal_error":
        return f"Valeur non admise ; attendu : {ctx.get('expected')}."
    if kind == "union_tag_invalid":
        return f"Type inconnu ; attendu : {ctx.get('expected_tags')}."
    if kind == "union_tag_not_found":
        return "Champ `type` manquant."
    if kind.endswith("_type") or kind.endswith("_parsing"):
        return "Type de valeur incorrect."
    return err["msg"]


def _path(loc: tuple[Any, ...]) -> str:
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out


def _line(root: yaml.Node, loc: tuple[Any, ...]) -> int | None:
    """Ligne du nœud désigné par `loc` ; un élément introuvable (étiquette d'union...) est ignoré."""
    node = root
    key_node: yaml.Node | None = None
    for part in loc:
        if isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                if k.value == part:
                    key_node, node = k, v
                    break
        elif isinstance(node, yaml.SequenceNode) and isinstance(part, int) and part < len(node.value):
            key_node, node = None, node.value[part]
    target = key_node if key_node is not None and loc and loc[-1] == key_node.value else node
    return target.start_mark.line + 1
