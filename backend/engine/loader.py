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
from pydantic_core import ErrorDetails

from backend.engine.expr import BASE_FUNCTIONS, Compiled, ExprError, compile_expr
from backend.engine.laws import list_laws
from backend.engine.schema import (
    MAX_YAML_BYTES,
    SCHEMA_VERSION,
    ExperimentSpec,
    OdeGenerator,
    RandomGenerator,
    SpecIssues,
)


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
        spec = ExperimentSpec.model_validate(data)
    except ValidationError as exc:
        raise ExperimentError(_issues_from(exc, root)) from exc
    problems = check_expressions(spec)
    if problems:
        raise ExperimentError([Issue(_line(root, loc), _path(loc), message) for loc, message in problems])
    return spec


def load_experiment_file(path: str | Path) -> ExperimentSpec:
    return load_experiment(Path(path).read_text(encoding="utf-8"))


# --- Traduction des erreurs Pydantic --------------------------------------------------------------


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


def _message(err: ErrorDetails) -> str:
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


# --- Vérification des expressions (noms, fonctions, cycles) ---------------------------------------

DRAW_FUNCTIONS = frozenset({"law", "normal", "uniform", "bernoulli"})
Loc = tuple[str | int, ...]


def check_expressions(spec: ExperimentSpec) -> list[tuple[Loc, str]]:
    """Ce que `schema.py` ne voit pas : chaque expression se lit, n'utilise que des noms et des fonctions
    connus, et les variables du générateur ne forment pas de cycle."""
    issues: list[tuple[Loc, str]] = []
    laws = set(list_laws())
    method_ids = {m.id for m in spec.methods}
    with_verdict = {k for k, m in spec.measures.items() if m.target is not None}
    generator = spec.generator
    if isinstance(generator, RandomGenerator):
        scope_names = set(generator.variables)
    elif isinstance(generator, OdeGenerator):
        scope_names = set(generator.state) | set(generator.derived or {}) | {"system"}
    else:
        scope_names = set()

    def add(loc: Loc, message: str) -> None:
        issues.append((loc, message))

    def comp(loc: Loc, source: str) -> Compiled | None:
        try:
            return compile_expr(source)
        except ExprError as exc:
            add(loc, str(exc))
            return None

    def check_ref(loc: Loc, ref: tuple[str, ...], roots: frozenset[str]) -> None:
        root, rest = ref[0], ref[1:]
        shown = ".".join(ref)
        if root not in roots:
            add(loc, f"« {root}. » n'est pas disponible dans cette expression ({shown}).")
        elif root == "p":
            if len(rest) != 1 or rest[0] not in spec.params:
                add(loc, f"Paramètre inconnu : « {shown} ».")
        elif root == "h":
            if len(rest) != 1 or rest[0] not in spec.hypotheses:
                add(loc, f"Hypothèse inconnue : « {shown} ».")
        else:  # m, s, base : <mesure>[.<méthode>]
            measure = rest[0].removesuffix("_se") if root == "m" else rest[0]
            known = with_verdict if root == "s" else set(spec.measures)
            if measure not in known or len(rest) > 2 or (len(rest) == 2 and rest[1] not in method_ids):
                add(loc, f"Mesure ou méthode inconnue : « {shown} ».")

    def check(
        loc: Loc, source: str, roots: frozenset[str], names: set[str], draw: bool = False
    ) -> Compiled | None:
        c = comp(loc, source)
        if c is None:
            return None
        for ref in sorted(c.refs):
            check_ref(loc, ref, roots)
        for hid in sorted(c.options):
            hyp = spec.hypotheses.get(hid)
            if hyp is None or hyp.type != "choice":
                add(loc, f"@h.{hid} : « {hid} » n'est pas une hypothèse de type choice.")
        allowed = set(BASE_FUNCTIONS) | (DRAW_FUNCTIONS if draw else set())
        for fn in sorted(c.calls - allowed):
            add(loc, f"Fonction non autorisée ou inconnue : « {fn} ».")
        for fn, arg in c.strings:
            if fn == "law" and arg not in laws:
                add(loc, f"Loi inconnue : « {arg} ». Lois du registre : {sorted(laws)}.")
        for name in sorted(c.names - names):
            add(loc, f"Nom inconnu : « {name} ».")
        return c

    pc = frozenset({"p"})
    ph = frozenset({"p", "h"})
    verdict_roots = frozenset({"p", "h", "m", "s", "base"})

    # Options d'hypothèses : loi du registre ou expression sur les variables du générateur.
    option_names: dict[str, set[str]] = {}
    for hid, hyp in spec.hypotheses.items():
        option_names[hid] = set()
        for oid, option in (hyp.options or {}).items():
            where = ("hypotheses", hid, "options", oid)
            if option.law is not None and option.law not in laws:
                add((*where, "law"), f"Loi inconnue : « {option.law} ». Lois du registre : {sorted(laws)}.")
            if option.expr is not None:
                c = check((*where, "expr"), option.expr, ph, scope_names)
                if c is not None:
                    option_names[hid] |= c.names
        if hyp.disabled_when:
            check(("hypotheses", hid, "disabled_when"), hyp.disabled_when, ph, set())

    # Générateur.
    if isinstance(generator, RandomGenerator):
        if isinstance(generator.n, str):
            check(("generator", "n"), generator.n, pc, set())
        deps: dict[str, set[str]] = {}
        for name, var in generator.variables.items():
            c = check(("generator", "variables", name, "expr"), var.expr, ph, scope_names, draw=True)
            if c is not None:
                from_options = {n for h in c.options for n in option_names.get(h, set())}
                deps[name] = (c.names & scope_names) | from_options
        _find_cycle(
            deps,
            lambda cycle: add(
                ("generator", "variables", cycle[0]), "Cycle entre variables : " + " -> ".join(cycle) + "."
            ),
        )
    elif isinstance(generator, OdeGenerator):
        if isinstance(generator.t_end, str):
            check(("generator", "t_end"), generator.t_end, ph, set())
        for name, value in generator.state.items():
            if isinstance(value, str):
                check(("generator", "state", name), value, ph, set())
        for name, source in generator.rhs.items():
            check(("generator", "rhs", name), source, ph, set(generator.state) | {"t"})
        for name, source in (generator.derived or {}).items():
            check(("generator", "derived", name), source, ph, set(generator.derived or {}) - {name})

    # Arguments des méthodes : une chaîne qui se lit comme expression et dont les noms existent est une
    # expression ; sinon c'est un texte littéral ("classic", "euler"). Seules les fautes de frappe sur
    # p.<id> et h.<id> sont signalées.
    for i, method in enumerate(spec.methods):
        for key, value in method.args.items():
            if not isinstance(value, str):
                continue
            try:
                c = compile_expr(value)
            except ExprError:
                continue
            for ref in sorted(c.refs):
                if ref[0] in ("p", "h"):
                    check_ref(("methods", i, "args", key), ref, ph)

    # Mesures (syntaxe seulement : les agrégateurs sont ceux de R2), défis et `verify`.
    for mid, measure in spec.measures.items():
        comp(("measures", mid, "agg"), measure.agg)
    for i, challenge in enumerate(spec.challenges):
        check(("challenges", i, "when"), challenge.when, verdict_roots, set())
    for i, question in enumerate(spec.questions):
        for j, choice in enumerate(getattr(question, "choices", [])):
            check(("questions", i, "choices", j, "verify"), choice.verify, verdict_roots, set())

    # Ajout de points : la vue exige `inject` dans le générateur.
    if not (isinstance(generator, RandomGenerator) and generator.inject):
        for i, view in enumerate(spec.views):
            if view.allow_point_injection:
                add(("views", i, "allow_point_injection"), "L'ajout de points exige `inject` (générateur).")
    return issues


def _find_cycle(deps: dict[str, set[str]], report) -> None:
    """Signale un cycle de dépendances (un seul, le premier trouvé)."""
    state: dict[str, int] = {}  # 1 = en cours, 2 = terminé

    def visit(node: str, path: list[str]) -> bool:
        state[node] = 1
        for nxt in sorted(deps.get(node, ())):
            if state.get(nxt) == 1:
                report([*path[path.index(nxt) :], nxt] if nxt in path else [node, nxt])
                return True
            if nxt not in state and nxt in deps and visit(nxt, [*path, nxt]):
                return True
        state[node] = 2
        return False

    for start in sorted(deps):
        if start not in state and visit(start, [start]):
            return
