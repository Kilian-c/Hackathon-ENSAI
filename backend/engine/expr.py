"""Évaluateur d'expressions du YAML (R1) : le même pour le générateur, les arguments, les défis et `verify`.

Aucun `eval` ni `exec` : l'expression est lue par `ast.parse`, puis un évaluateur maison parcourt l'arbre
et n'accepte qu'une liste blanche de noeuds. Tout le reste (boucle, compréhension, lambda, indice,
attribut commençant par `_`, appel d'une fonction hors liste, exposant > 100) est refusé, à la
compilation quand c'est statique, sinon à l'exécution.

Espace de noms (CLAUDE.md, section 7) :
- `p.<id>`, `h.<id>`, `m.<mesure>[.<methode>]`, `s.<mesure>`, `base.<mesure>`, `reps.<k>` : des
  *espaces de noms* (dictionnaires imbriqués fournis par l'appelant) ; jamais d'accès à un attribut Python.
- nom nu (`x`, `eps`, `idx`) : variable fournie par l'appelant ;
- `@h.<id>` : la loi ou l'expression de l'option choisie (résolue par l'appelant) ;
- fonctions : `BASE_FUNCTIONS` (NumPy usuel, `ar1`, `ols_match`) plus celles que l'appelant ajoute (`law`,
  `normal`, `uniform`, `bernoulli` : elles dépendent du flux aléatoire du générateur).
"""

import ast
import operator
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.signal import lfilter

MAX_EXPR_LEN = 300
MAX_EXPONENT = 100
MAX_LITERAL_ITEMS = 50

# Racines d'espaces de noms : toujours suivies d'un point (`p.n`), jamais utilisées nues.
NAMESPACE_ROOTS = frozenset({"p", "h", "m", "s", "base", "reps", "example", "curves", "summary", "gen"})

_OPTION_RE = re.compile(r"@h\.([A-Za-z_][A-Za-z0-9_]*)")
_OPTION_TOKEN = re.compile(r"^__opt_([A-Za-z_][A-Za-z0-9_]*)__$")


class ExprError(ValueError):
    """Expression invalide ou impossible à évaluer. Le message est en français."""


class Layered(dict):
    """Valeurs d'une mesure par méthode : `m.coverage.hc3` lit une clé, `m.coverage` seul lit `default`."""

    def __init__(self, values: Mapping[str, Any] | None = None, default: Any = None):
        super().__init__(values or {})
        self.default = default


# --- Fonctions de la liste blanche ----------------------------------------------------------------


def ar1(base: Any, rho: float) -> np.ndarray:
    """Filtre AR(1) le long des observations (dernier axe) : z_t = rho z_{t-1} + sqrt(1 - rho^2) base_t.

    Le premier terme reste `base_0` : si `base` est de variance 1, `z` aussi (processus stationnaire).
    """
    rho = float(rho)
    if not -1.0 < rho < 1.0:
        raise ExprError("ar1 : rho doit être strictement compris entre -1 et 1.")
    base = np.asarray(base, dtype=float)
    b0 = float(np.sqrt(1.0 - rho**2))
    out, _ = lfilter([b0], [1.0, -rho], base, axis=-1, zi=(1.0 - b0) * base[..., :1])
    return out


def ols_match(x: Any, y: Any, a: float, b: float, r2: float) -> np.ndarray:
    """Recale chaque répétition de `y` pour que la régression de `y` sur `x` donne exactement
    l'ordonnée `a`, la pente `b` et le R^2 `r2` (contre-exemples d'Anscombe).

    `y` est remplacé par a + b x + c e, où e est le résidu de y sur x, centré, réduit et orthogonal à x ;
    c = |b| sd(x) sqrt((1 - r2) / r2) fixe le R^2. Si b = 0, le R^2 vaut 0 par nécessité : c = 1.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if not 0.0 < float(r2) <= 1.0:
        raise ExprError("ols_match : r2 doit être compris entre 0 (exclu) et 1.")
    dx = x - x.mean(axis=-1, keepdims=True)
    dy = y - y.mean(axis=-1, keepdims=True)
    sxx = (dx**2).sum(axis=-1, keepdims=True)
    resid = dy - dx * (dx * dy).sum(axis=-1, keepdims=True) / sxx
    sd_resid = np.sqrt((resid**2).mean(axis=-1, keepdims=True))
    e = resid / np.where(sd_resid == 0.0, np.nan, sd_resid)
    sd_x = np.sqrt(sxx / x.shape[-1])
    c = np.abs(b) * sd_x * np.sqrt((1.0 - r2) / r2) if b != 0 else 1.0
    return a + b * x + c * e


def _unary_np(fn: Callable) -> Callable:
    def call(x: Any) -> Any:
        with np.errstate(all="ignore"):
            return fn(np.asarray(x, dtype=float))

    return call


BASE_FUNCTIONS: dict[str, Callable[..., Any]] = {
    **{
        name: _unary_np(getattr(np, name))
        for name in (
            "sqrt", "exp", "log", "log10", "log2", "sin", "cos", "tan", "arcsin", "arccos", "arctan",
            "sinh", "cosh", "tanh", "abs", "sign", "floor", "ceil", "round", "isnan", "isfinite",
        )
    },
    "arctan2": np.arctan2,
    "minimum": np.minimum,
    "maximum": np.maximum,
    "where": np.where,
    "clip": np.clip,
    "mean": np.mean,
    "sum": np.sum,
    "std": np.std,
    "var": np.var,
    "median": np.median,
    "min": np.min,
    "max": np.max,
    "cumsum": np.cumsum,
    "cumprod": np.cumprod,
    "sort": np.sort,
    "quantile": np.quantile,
    "ar1": ar1,
    "ols_match": ols_match,
}
CONSTANTS: dict[str, float] = {"pi": float(np.pi), "e": float(np.e)}
ALLOWED_KEYWORDS = frozenset({"axis"})


# --- Compilation (vérifications statiques) --------------------------------------------------------

_BIN_OPS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.BitAnd: operator.and_, ast.BitOr: operator.or_, ast.BitXor: operator.xor,
}
_UNARY_OPS: dict[type, Callable[[Any], Any]] = {
    ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_, ast.Invert: operator.invert,
}
_CMP_OPS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
}


@dataclass
class Compiled:
    """Une expression validée, avec ce qu'elle utilise (pour les vérifications au chargement)."""

    source: str
    tree: ast.Expression
    names: set[str] = field(default_factory=set)  # variables nues (hors fonctions, constantes, idx exclu)
    refs: set[tuple[str, ...]] = field(default_factory=set)  # chemins pointés : ("p", "n"), ("m", "c", "ols")
    options: set[str] = field(default_factory=set)  # hypothèses citées par `@h.<id>`
    calls: set[str] = field(default_factory=set)  # fonctions appelées
    strings: list[tuple[str, str]] = field(default_factory=list)  # (fonction, texte), ex. law('normal')

    def evaluate(self, env: "Env") -> Any:
        try:
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                return _Evaluator(env).visit(self.tree.body)
        except ExprError:
            raise
        except ZeroDivisionError as exc:
            raise ExprError(f"Division par zéro dans « {self.source} ».") from exc
        except (TypeError, ValueError, KeyError, IndexError, OverflowError) as exc:
            raise ExprError(f"Évaluation impossible de « {self.source} » : {exc}") from exc


def compile_expr(source: str) -> Compiled:
    """Lit et valide une expression. Lève `ExprError` (message en français) au moindre problème."""
    if not isinstance(source, str) or not source.strip():
        raise ExprError("Expression vide.")
    if len(source) > MAX_EXPR_LEN:
        raise ExprError(f"Expression trop longue ({MAX_EXPR_LEN} caractères au plus).")
    rewritten = _OPTION_RE.sub(lambda m: f"__opt_{m.group(1)}__", source.strip())
    if "@" in rewritten:
        raise ExprError("Le caractère « @ » n'est admis que sous la forme @h.<hypothèse>.")
    try:
        tree = ast.parse(rewritten, mode="eval")
    except SyntaxError as exc:
        raise ExprError(f"Syntaxe invalide dans « {source} ».") from exc
    compiled = Compiled(source=source, tree=tree)
    _Checker(compiled).visit(tree.body)
    return compiled


class _Checker(ast.NodeVisitor):
    def __init__(self, out: Compiled):
        self.out = out

    def generic_visit(self, node: ast.AST) -> None:
        raise ExprError(f"Construction non autorisée dans une expression : {type(node).__name__}.")

    # Noeuds feuilles et composés autorisés.
    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, bool) or isinstance(node.value, int | float | str):
            return
        raise ExprError("Seuls les nombres, booléens et textes sont admis comme constantes.")

    def visit_Name(self, node: ast.Name) -> None:
        name = node.id
        match = _OPTION_TOKEN.match(name)
        if match:
            self.out.options.add(match.group(1))
        elif name.startswith("_"):
            raise ExprError("Un nom ne peut pas commencer par « _ ».")
        elif name in NAMESPACE_ROOTS:
            raise ExprError(f"« {name} » s'utilise avec un point, par exemple {name}.nom.")
        elif name == "idx" or name in CONSTANTS or name in ("True", "False"):
            pass
        else:
            self.out.names.add(name)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        path = []
        cur: ast.AST = node
        while isinstance(cur, ast.Attribute):
            if cur.attr.startswith("_"):
                raise ExprError("Un attribut ne peut pas commencer par « _ ».")
            path.append(cur.attr)
            cur = cur.value
        if not isinstance(cur, ast.Name) or cur.id not in NAMESPACE_ROOTS:
            raise ExprError("Les points ne servent qu'aux espaces de noms : p., h., m., s., base., reps.")
        self.out.refs.add((cur.id, *reversed(path)))

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if not isinstance(node.op, ast.Pow) and type(node.op) not in _BIN_OPS:
            raise ExprError(f"Opérateur non autorisé : {type(node.op).__name__}.")
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        if type(node.op) not in _UNARY_OPS:
            raise ExprError(f"Opérateur non autorisé : {type(node.op).__name__}.")
        self.visit(node.operand)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        for value in node.values:
            self.visit(value)

    def visit_Compare(self, node: ast.Compare) -> None:
        if any(type(op) not in _CMP_OPS for op in node.ops):
            raise ExprError("Comparaison non autorisée (admis : < <= > >= == !=).")
        self.visit(node.left)
        for comparator in node.comparators:
            self.visit(comparator)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.visit(node.test)
        self.visit(node.body)
        self.visit(node.orelse)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        self._sequence(node)

    def visit_List(self, node: ast.List) -> None:
        self._sequence(node)

    def _sequence(self, node: ast.Tuple | ast.List) -> None:
        if len(node.elts) > MAX_LITERAL_ITEMS:
            raise ExprError(f"Une liste littérale compte {MAX_LITERAL_ITEMS} éléments au plus.")
        for elt in node.elts:
            self.visit(elt)

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name) or node.func.id.startswith("_"):
            raise ExprError("Seules les fonctions de la liste blanche peuvent être appelées.")
        if any(isinstance(a, ast.Starred) for a in node.args):
            raise ExprError("Les arguments étoilés ne sont pas autorisés.")
        for kw in node.keywords:
            if kw.arg not in ALLOWED_KEYWORDS:
                raise ExprError(f"Argument nommé non autorisé : {kw.arg}.")
        name = node.func.id
        self.out.calls.add(name)
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                self.out.strings.append((name, arg.value))
            self.visit(arg)
        for kw in node.keywords:
            self.visit(kw.value)


# --- Évaluation -----------------------------------------------------------------------------------


@dataclass
class Env:
    """Ce que l'appelant fournit à l'évaluateur."""

    variables: Mapping[str, Any] = field(default_factory=dict)  # noms nus : variables du générateur, idx
    namespaces: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)  # p, h, m, s, base, reps...
    functions: Mapping[str, Callable[..., Any]] = field(default_factory=dict)  # en plus de BASE_FUNCTIONS
    option: Callable[[str], Any] | None = None  # @h.<id> : valeur de l'option choisie


class _Evaluator:
    def __init__(self, env: Env):
        self.env = env

    def visit(self, node: ast.AST) -> Any:
        return getattr(self, f"visit_{type(node).__name__}")(node)

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        name = node.id
        match = _OPTION_TOKEN.match(name)
        if match:
            if self.env.option is None:
                raise ExprError(f"@h.{match.group(1)} n'est pas utilisable ici.")
            return self.env.option(match.group(1))
        if name in self.env.variables:
            return self.env.variables[name]
        if name in CONSTANTS:
            return CONSTANTS[name]
        raise ExprError(f"Nom inconnu : « {name} ».")

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        path: list[str] = []
        cur: ast.AST = node
        while isinstance(cur, ast.Attribute):
            path.append(cur.attr)
            cur = cur.value
        root = cur.id  # type: ignore[attr-defined]  # garanti par la compilation
        value: Any = self.env.namespaces.get(root)
        if value is None:
            raise ExprError(f"Espace de noms inconnu ou indisponible ici : « {root} ».")
        for key in reversed(path):
            if not isinstance(value, Mapping) or key not in value:
                raise ExprError(f"Nom inconnu : « {root}.{'.'.join(reversed(path))} ».")
            value = value[key]
        if isinstance(value, Layered):
            if value.default is None:
                raise ExprError(f"Précisez la méthode : « {root}.{'.'.join(reversed(path))}.<méthode> ».")
            value = value.default
        return value

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left, right = self.visit(node.left), self.visit(node.right)
        if isinstance(node.op, ast.Pow):
            exponent = np.asarray(right, dtype=float)
            if not np.all(np.abs(exponent) <= MAX_EXPONENT):
                raise ExprError(f"Exposant hors limite (|exposant| <= {MAX_EXPONENT}) dans une expression.")
            result = np.power(np.asarray(left, dtype=float), exponent)
            return result[()] if result.ndim == 0 else result
        return _BIN_OPS[type(node.op)](left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        return _UNARY_OPS[type(node.op)](self.visit(node.operand))

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        is_and = isinstance(node.op, ast.And)
        result = self.visit(node.values[0])
        for value_node in node.values[1:]:
            if isinstance(result, np.ndarray) and result.ndim > 0:
                other = self.visit(value_node)
                result = np.logical_and(result, other) if is_and else np.logical_or(result, other)
            elif bool(result) != is_and:
                return result  # court-circuit : False and ... / True or ...
            else:
                result = self.visit(value_node)
        return result

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        result: Any = True
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = self.visit(comparator)
            outcome = _CMP_OPS[type(op)](left, right)
            result = outcome if result is True else np.logical_and(result, outcome)
            left = right
        return result

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        test = self.visit(node.test)
        if isinstance(test, np.ndarray) and test.ndim > 0:
            return np.where(test, self.visit(node.body), self.visit(node.orelse))
        return self.visit(node.body) if test else self.visit(node.orelse)

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        return tuple(self.visit(e) for e in node.elts)

    def visit_List(self, node: ast.List) -> Any:
        return [self.visit(e) for e in node.elts]

    def visit_Call(self, node: ast.Call) -> Any:
        name = node.func.id  # type: ignore[attr-defined]  # garanti par la compilation
        fn = self.env.functions.get(name) or BASE_FUNCTIONS.get(name)
        if fn is None:
            raise ExprError(f"Fonction non autorisée ou inconnue : « {name} ».")
        args = [self.visit(a) for a in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords if kw.arg is not None}
        return fn(*args, **kwargs)


def evaluate(source: str, env: Env) -> Any:
    """Raccourci : compile puis évalue."""
    return compile_expr(source).evaluate(env)
