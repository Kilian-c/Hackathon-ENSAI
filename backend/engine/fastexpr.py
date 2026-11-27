"""Expressions rapides pour les boucles chaudes (second membre `rhs` du générateur `ode`).

Même langage et même liste blanche que `expr.py` : l'arbre est celui de `compile_expr` (déjà validé), jamais
`eval` ni `exec`. Différence : l'arbre est parcouru UNE fois pour produire des fermetures Python ; tout ce qui
ne dépend pas des variables d'état (`p.*`, `h.*`, constantes) est calculé à ce moment-là. Un appel ne coûte
plus qu'un petit nombre d'opérations NumPy au lieu d'un parcours d'arbre.

Seuls les noeuds utiles à une équation différentielle sont gérés ; `compile_fast` renvoie `None` pour les
autres (le runner retombe alors sur l'évaluateur général).
"""

import ast
from collections.abc import Callable, Mapping
from operator import itemgetter
from typing import Any

import numpy as np

from backend.engine.expr import (
    _BIN_OPS,
    _UNARY_OPS,
    BASE_FUNCTIONS,
    CONSTANTS,
    MAX_EXPONENT,
    ExprError,
    compile_expr,
)

Fast = Callable[[Any], Any]  # prend le tableau d'état `y`
_Built = tuple[bool, Any]  # (constant ?, valeur si constant sinon fonction de y)


class _Unsupported(Exception):
    pass


def _power(left: Any, right: Any) -> Any:
    exponent = np.asarray(right, dtype=float)
    if not np.all(np.abs(exponent) <= MAX_EXPONENT):
        raise ExprError(f"Exposant hors limite (|exposant| <= {MAX_EXPONENT}) dans une expression.")
    result = np.power(np.asarray(left, dtype=float), exponent)
    return result[()] if result.ndim == 0 else result


def _build(node: ast.AST, namespaces: Mapping[str, Mapping[str, Any]], index: Mapping[str, int]) -> _Built:
    if isinstance(node, ast.Constant):
        return True, node.value
    if isinstance(node, ast.Name):
        if node.id in index:
            return False, itemgetter(index[node.id])
        if node.id in CONSTANTS:
            return True, CONSTANTS[node.id]
        raise _Unsupported
    if isinstance(node, ast.Attribute):  # p.<id>, h.<id> : constantes pendant tout le calcul
        path: list[str] = []
        cur: ast.AST = node
        while isinstance(cur, ast.Attribute):
            path.append(cur.attr)
            cur = cur.value
        if not isinstance(cur, ast.Name):
            raise _Unsupported
        value: Any = namespaces.get(cur.id)
        for key in reversed(path):
            if not isinstance(value, Mapping) or key not in value:
                raise ExprError(f"Nom inconnu : « {cur.id}.{'.'.join(reversed(path))} ».")
            value = value[key]
        return True, value
    if isinstance(node, ast.BinOp):
        lc, lv = _build(node.left, namespaces, index)
        rc, rv = _build(node.right, namespaces, index)
        op: Callable[[Any, Any], Any] = _power if isinstance(node.op, ast.Pow) else _BIN_OPS[type(node.op)]
        if lc and rc:
            return True, op(lv, rv)
        if lc:
            return False, lambda y, a=lv, g=rv: op(a, g(y))
        if rc:
            return False, lambda y, f=lv, b=rv: op(f(y), b)
        return False, lambda y, f=lv, g=rv: op(f(y), g(y))
    if isinstance(node, ast.UnaryOp):
        oc, ov = _build(node.operand, namespaces, index)
        uop = _UNARY_OPS[type(node.op)]
        return (True, uop(ov)) if oc else (False, lambda y, f=ov: uop(f(y)))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        fn = BASE_FUNCTIONS.get(node.func.id)
        if fn is None:
            raise _Unsupported
        args = [_build(a, namespaces, index) for a in node.args]
        if all(c for c, _ in args):
            return True, fn(*[v for _, v in args])
        if len(args) == 1:
            return False, lambda y, f=args[0][1]: fn(f(y))
        getters = [(c, v) for c, v in args]
        return False, lambda y: fn(*[v if c else v(y) for c, v in getters])
    raise _Unsupported


def compile_fast(
    source: str, namespaces: Mapping[str, Mapping[str, Any]], index: Mapping[str, int]
) -> Fast | None:
    """Fonction `f(y)` équivalente à l'expression, `y[index[nom]]` donnant chaque variable d'état.

    `None` si l'expression utilise autre chose que des opérations, des constantes, `p.*`, `h.*` et des
    fonctions de la liste blanche.
    """
    tree = compile_expr(source).tree.body
    try:
        constant, value = _build(tree, namespaces, index)
    except _Unsupported:
        return None
    if constant:
        return lambda _y, v=value: v
    return value
