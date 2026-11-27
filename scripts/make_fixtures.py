"""Fixtures de l'interface (R1) : des réponses d'API au format de `backend/contracts.py`.

    uv run python scripts/make_fixtures.py        # écrit frontend/src/fixtures/*.json

ÉTAT ACTUEL (H3 à H4) : le moteur `run()` n'existe pas encore. Ces fixtures viennent d'une mini-simulation
écrite ici (mêmes lois que `engine/laws.py`, mêmes flux que `engine/rng.py`, formules fermées en NumPy),
puis validées par les modèles de `contracts.py` : tout champ hors contrat fait échouer le script.
Quand `run()` marche, remplacer `build_*` par des appels à `run()` : les noms de fichiers ne changent pas.

Aucune fixture ne dépend d'un théorème dans l'interface : l'interface lit seulement le contrat.
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.contracts import RunResult, SweepResult, TrainingSessionResponse
from backend.engine.laws import sample_law
from backend.engine.loader import content_hash
from backend.engine.rng import rng_for

OUT = ROOT / "frontend" / "src" / "fixtures"
SEED = 42
SHOWN_INTERVALS = 100


# --- Utilitaires -------------------------------------------------------------------------------------------


def clean(value):
    """JSON propre : NaN et Infinity -> null, flottants arrondis, tableaux NumPy -> listes."""
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float):
        return None if not math.isfinite(value) else round(value, 6)
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [clean(v) for v in value]
    return value


def stable_range(values: np.ndarray) -> list[float]:
    """Bornes stables : quantiles 0,5 % et 99,5 % de la Référence, plus 10 % de marge."""
    lo, hi = np.quantile(values, [0.005, 0.995])
    pad = (hi - lo) * 0.1
    return [float(lo - pad), float(hi + pad)]


def verdict(value, target, direction, ok_within, broken_beyond):
    """Règle unique du CLAUDE.md, section 8."""
    if value is None or not math.isfinite(value):
        return "broken"
    gap = {"below": target - value, "above": value - target, "both": abs(value - target)}[direction]
    gap = max(gap, 0.0) if direction != "both" else gap
    return "ok" if gap <= ok_within else "broken" if gap > broken_beyond else "warning"


def fr(value: float, scale: float, decimals: int, unit: str) -> str:
    text = f"{value * scale:.{decimals}f}".replace(".", ",")
    return f"{text} {unit}".strip() if unit else text


def series(view, slot, method, role, label, **data):
    suffix = ".ref" if role == "reference" else ""
    return {"id": f"{view}.{slot}.{method or 'gen'}{suffix}", "slot": slot, "method": method,
            "role": role, "label": label, **data}


def measure_block(spec, values, mc_se, baseline, method_ids):
    """Un `MeasureResult` complet : verdicts et textes par méthode, selon la règle du CLAUDE.md."""
    block = {
        "label": spec["label"], "unit": spec.get("unit", ""), "scale": spec.get("scale", 1.0),
        "decimals": spec.get("decimals", 2), "primary": spec.get("primary", False),
        "values": values, "mc_se": mc_se, "baseline": baseline,
    }
    if "target" in spec:
        block.update(target=spec["target"], direction=spec["direction"],
                     ok_within=spec["ok_within"], broken_beyond=spec["broken_beyond"])
        states, texts = {}, {}
        for m in method_ids:
            target = baseline[m] if spec["target"] == "base" else spec["target"]
            states[m] = verdict(values[m], target, spec["direction"], spec["ok_within"], spec["broken_beyond"])
            if "texts" in spec:
                texts[m] = spec["texts"][states[m]].replace(
                    "{value}", fr(values[m], block["scale"], block["decimals"], block["unit"])
                )
        block.update(states=states, texts=texts)
    return block


# --- Régression linéaire (MCO classique, HC3) ---------------------------------------------------------------

REG_METHODS = [
    {"id": "ols", "role": "method", "label": "MCO classique (IC à 95 %)"},
    {
        "id": "hc3", "role": "correction", "label": "Écarts-types robustes de White (HC3)",
        "explain": "L'estimateur sandwich HC3 estime la variance de chaque résidu séparément.",
    },
]
REG_MEASURES = {
    "coverage": {"label": "Taux de couverture réel", "unit": "%", "scale": 100, "decimals": 1, "primary": True,
                 "target": 0.95, "direction": "below", "ok_within": 0.03, "broken_beyond": 0.10,
                 "texts": {"ok": "Intervalle fiable : {value} de couverture.",
                           "warning": "Couverture en baisse ({value}) : la variance commence à être sous-estimée.",
                           "broken": "Intervalle non fiable ({value}) : la variance est sous-estimée."}},
    "bias": {"label": "Biais de la pente", "decimals": 3, "target": 0.0, "direction": "both",
             "ok_within": 0.05, "broken_beyond": 0.15,
             "texts": {"ok": "Pente sans biais ({value}).", "warning": "Pente légèrement biaisée ({value}).",
                       "broken": "Pente biaisée ({value})."}},
    "width": {"label": "Largeur moyenne des IC", "decimals": 3},
}


def reg_world(n: int, repeat: int, hetero: float, beta1: float, seed: int):
    """Mêmes tirages quelle que soit `hetero` : seul le facteur d'échelle de l'erreur change."""
    x = sample_law("normal", rng_for(seed, "x_raw"), (repeat, n))
    base_eps = sample_law("normal", rng_for(seed, "base_eps"), (repeat, n))
    return x, 1.0 + beta1 * x + base_eps * np.exp(0.9 * hetero * x)


def ols_ci(x, y, truth, se_type):
    n = x.shape[1]
    dx = x - x.mean(axis=1, keepdims=True)
    sxx = (dx**2).sum(axis=1)
    b1 = (dx * (y - y.mean(axis=1, keepdims=True))).sum(axis=1) / sxx
    b0 = y.mean(axis=1) - b1 * x.mean(axis=1)
    y_hat = b0[:, None] + b1[:, None] * x
    resid = y - y_hat
    if se_type == "classic":
        se = np.sqrt((resid**2).sum(axis=1) / (n - 2) / sxx)
    else:  # HC3
        lev = 1.0 / n + dx**2 / sxx[:, None]
        se = np.sqrt((dx**2 * resid**2 / (1.0 - lev) ** 2).sum(axis=1)) / sxx
    q = stats.t.ppf(0.975, n - 2)
    low, high = b1 - q * se, b1 + q * se
    return {"est": b1, "low": low, "high": high, "hit": (low <= truth) & (truth <= high),
            "width": high - low, "y_hat": y_hat, "resid": resid}


def reg_run(hetero: float, n: int = 150, repeat: int = 500, beta1: float = 1.5, seed: int = SEED):
    x, y = reg_world(n, repeat, hetero, beta1, seed)
    xr, yr = reg_world(n, repeat, 0.0, beta1, seed)
    cur = {m: ols_ci(x, y, beta1, t) for m, t in (("ols", "classic"), ("hc3", "HC3"))}
    ref = {m: ols_ci(xr, yr, beta1, t) for m, t in (("ols", "classic"), ("hc3", "HC3"))}
    ids = ["ols", "hc3"]

    def agg(res):
        cov = {m: float(res[m]["hit"].mean()) for m in ids}
        return {
            "coverage": (cov, {m: math.sqrt(cov[m] * (1 - cov[m]) / repeat) for m in ids}),
            "bias": ({m: float(res[m]["est"].mean() - beta1) for m in ids},
                     {m: float(res[m]["est"].std(ddof=1) / math.sqrt(repeat)) for m in ids}),
            "width": ({m: float(res[m]["width"].mean()) for m in ids},
                      {m: float(res[m]["width"].std(ddof=1) / math.sqrt(repeat)) for m in ids}),
        }

    now, base = agg(cur), agg(ref)
    measures = {k: measure_block(spec, now[k][0], now[k][1], base[k][0], ids) for k, spec in REG_MEASURES.items()}

    xs, xs_ref = x[0], xr[0]
    axes_xy = {"x": stable_range(xr), "y": stable_range(yr)}
    shown = slice(0, SHOWN_INTERVALS)
    ic_series = [
        series("ic", "est", m, role, label, x=cur[m]["est"][shown], low=cur[m]["low"][shown],
               high=cur[m]["high"][shown], hit=cur[m]["hit"][shown])
        for m, role, label in (("ols", "method", REG_METHODS[0]["label"]), ("hc3", "correction", REG_METHODS[1]["label"]))
    ] + [series("ic", "truth", None, "truth", "Vraie pente", value=beta1)]
    views = [
        {"id": "nuage", "type": "scatter", "title": "Nuage et droite ajustée", "axes": axes_xy,
         "shown": n, "total": n, "clipped": 0, "series": [
             series("nuage", "xy", None, "data", "Observations", x=xs, y=y[0]),
             series("nuage", "fit", "ols", "reference", "Référence (état sain)", x=xs_ref, y=ref["ols"]["y_hat"][0]),
             series("nuage", "fit", "ols", "method", REG_METHODS[0]["label"], x=xs, y=cur["ols"]["y_hat"][0]),
         ]},
        {"id": "residus", "type": "residuals", "title": "Résidus",
         "axes": {"x": axes_xy["x"], "y": stable_range(ref["ols"]["resid"])}, "shown": n, "total": n,
         "clipped": 0, "ui": {"x_title": "x", "y_title": "Résidu"}, "series": [
             series("residus", "resid", "ols", "reference", "Référence (état sain)", x=xs_ref, y=ref["ols"]["resid"][0]),
             series("residus", "resid", "ols", "method", "Résidus MCO", x=xs, y=cur["ols"]["resid"][0]),
         ]},
        {"id": "ic", "type": "repetitions", "mode": "intervals", "title": "100 intervalles de confiance empilés",
         "axes": {"x": stable_range(np.concatenate([ref["ols"]["low"][shown], ref["ols"]["high"][shown]]))},
         "shown": SHOWN_INTERVALS, "total": repeat, "clipped": 0, "series": ic_series},
        {"id": "sens", "type": "sensitivity", "title": "Étude de sensibilité", "series": []},
    ]
    return {
        "schema_version": 1, "state_hash": f"reg{int(hetero * 100):03d}n{n}s{seed}".ljust(16, "0")[:16],
        "methods": REG_METHODS, "measures": measures,
        "equation": {"terms": {"var": {"violated_by": ["hetero"] if hetero > 0 else []}}},
        "challenges": [{"id": "trap-bp-test", "passed": False}, {"id": "big-n-limit", "passed": False}],
        "views": views, "draw_log": None, "invalid_rate": {"ols": 0.0, "hc3": 0.0}, "warnings": [],
        "repeat_used": repeat, "compute_ms": 0.0,
    }


def reg_sweep(repeat: int = 500, seed: int = SEED, beta1: float = 1.5):
    grid = [round(i / 10, 1) for i in range(11)]
    values = {"ols": [], "hc3": []}
    for h in grid:
        x, y = reg_world(150, repeat, h, beta1, seed)
        for m, t in (("ols", "classic"), ("hc3", "HC3")):
            values[m].append(float(ols_ci(x, y, beta1, t)["hit"].mean()))
    target, ok, broken = 0.95, 0.03, 0.10

    def crossing(vals, limit):
        for i in range(1, len(vals)):
            if vals[i - 1] >= limit > vals[i]:
                return grid[i - 1] + (vals[i - 1] - limit) / (vals[i - 1] - vals[i]) * (grid[i] - grid[i - 1])
        return None

    critical = {}
    for m, vals in values.items():
        w, b = crossing(vals, target - ok), crossing(vals, target - broken)
        critical[m] = {"warning_at": w, "broken_at": b} if (w is not None or b is not None) else None
    return {
        "axes": [{"target": "h.hetero", "values": grid, "labels": [f"{v:.1f}".replace(".", ",") for v in grid]}],
        "measure": "coverage", "values": values,
        "mc_se": {m: [math.sqrt(v * (1 - v) / repeat) for v in vals] for m, vals in values.items()},
        "states": {m: [verdict(v, target, "below", ok, broken) for v in vals] for m, vals in values.items()},
        "critical": critical, "target": target, "ok_within": ok, "broken_beyond": broken, "direction": "below",
        "current": {"h.hetero": 0.8}, "repeat_used": repeat, "reduced": False, "compute_ms": 0.0,
    }


# --- Test de Student et Wilcoxon ------------------------------------------------------------------------------

STU_METHODS = [
    {"id": "student", "role": "method", "label": "Test de Student"},
    {"id": "wilcoxon", "role": "correction", "label": "Test de Wilcoxon (rangs signés)",
     "explain": "Les rangs ne voient pas la taille des valeurs extrêmes : sous une loi symétrique, "
                "le niveau reste exact et la puissance tient."},
]
STU_MEASURES = {
    "power": {"label": "Puissance sous H1", "unit": "%", "scale": 100, "decimals": 1, "primary": True,
              "target": "base", "direction": "below", "ok_within": 0.10, "broken_beyond": 0.25,
              "texts": {"ok": "Puissance préservée : {value}.", "warning": "Puissance entamée : {value}.",
                        "broken": "Puissance effondrée : {value}."}},
    "alpha": {"label": "Risque de première espèce réel", "unit": "%", "scale": 100, "decimals": 1,
              "target": 0.05, "direction": "both", "ok_within": 0.025, "broken_beyond": 0.04},
}


def student_tests(x0, x1):
    out = {}
    for m, fn in (("student", lambda a: stats.ttest_1samp(a, 0.0, axis=1)),
                  ("wilcoxon", lambda a: stats.wilcoxon(a, axis=1))):
        p0, p1 = fn(x0).pvalue, fn(x1).pvalue
        out[m] = {"pvalue": p0, "reject": p0 < 0.05, "reject_h1": p1 < 0.05}
    return out


def student_run(law: str, n: int = 25, delta: float = 0.5, repeat: int = 500, seed: int = SEED):
    def world(name):
        x0 = sample_law(name, rng_for(seed, "x0"), (repeat, n))
        return x0, x0 + delta

    (x0, x1), (r0, r1) = world(law), world("normal")
    cur, ref = student_tests(x0, x1), student_tests(r0, r1)
    ids = ["student", "wilcoxon"]

    def agg(res):
        power = {m: float(res[m]["reject_h1"].mean()) for m in ids}
        alpha = {m: float(res[m]["reject"].mean()) for m in ids}
        se = lambda d: {m: math.sqrt(d[m] * (1 - d[m]) / repeat) for m in ids}  # noqa: E731
        return {"power": (power, se(power)), "alpha": (alpha, se(alpha))}

    now, base = agg(cur), agg(ref)
    measures = {k: measure_block(spec, now[k][0], now[k][1], base[k][0], ids) for k, spec in STU_MEASURES.items()}
    states = {m: measures["power"]["states"][m] for m in ids}
    lo_all = np.concatenate([x0[0], r0[0]])
    views = [
        {"id": "pvalues", "type": "distribution", "title": "Distribution des p-values sous H0",
         "axes": {"x": [0.0, 1.0]}, "shown": repeat, "total": repeat, "clipped": 0,
         "ui": {"x_range": [0, 1], "uniform_reference": True},
         "series": [series("pvalues", "stat", m, role, label, x=cur[m]["pvalue"])
                    for m, role, label in (("student", "method", "Test de Student"),
                                           ("wilcoxon", "correction", "Test de Wilcoxon"))]},
        {"id": "echantillon", "type": "distribution", "title": "Un échantillon",
         "axes": {"x": stable_range(lo_all)}, "shown": n, "total": n, "clipped": 0,
         "series": [series("echantillon", "stat", "student", "reference", "Référence (loi normale)", x=r0[0]),
                    series("echantillon", "stat", "student", "method", "Échantillon affiché", x=x0[0])]},
        {"id": "sens", "type": "sensitivity", "title": "Puissance selon la loi", "series": []},
    ]
    return {
        "schema_version": 1, "state_hash": f"stu-{law}-n{n}".ljust(16, "0")[:16],
        "methods": STU_METHODS, "measures": measures,
        "equation": {"terms": {"stat": {"violated_by": ["loi"] if law != "normal" else []}}},
        "challenges": [
            {"id": "moitie-puissance", "passed": now["power"][0]["student"] < 0.5 * base["power"][0]["student"]},
            {"id": "grand-n-cauchy", "passed": law == "cauchy" and n >= 100 and states["student"] == "broken"},
        ],
        "views": views, "draw_log": {"reject": bool(cur["student"]["reject"][0]),
                                      "pvalue": float(cur["student"]["pvalue"][0])},
        "invalid_rate": {"student": 0.0, "wilcoxon": 0.0}, "warnings": [],
        "repeat_used": repeat, "compute_ms": 0.0,
    }


# --- Pendule : Euler explicite et RK4 ---------------------------------------------------------------------------

PEN_METHODS = [
    {"id": "euler", "role": "method", "label": "Euler explicite"},
    {"id": "rk4", "role": "correction", "label": "Runge-Kutta d'ordre 4",
     "explain": "RK4 évalue la pente quatre fois par pas : l'erreur devient proportionnelle à la puissance 4 du pas."},
]
PEN_MEASURES = {
    "err_angle": {"label": "Erreur maximale sur l'angle", "unit": "%", "scale": 100, "decimals": 1, "primary": True,
                  "target": 0.0, "direction": "above", "ok_within": 0.05, "broken_beyond": 0.20,
                  "texts": {"ok": "Trajectoire fidèle : erreur de {value}.",
                            "warning": "La trajectoire dérive : erreur de {value}.",
                            "broken": "Trajectoire fausse : erreur de {value}."}},
    "energy_drift": {"label": "Dérive de l'énergie", "unit": "%", "scale": 100, "decimals": 1},
    "full_turn": {"label": "Le pendule fait le tour", "decimals": 0},
}


def rhs(_t, s):
    return [s[1], -9.81 * math.sin(s[0])]


def integrate(theta0: float, t_end: float, dt: float, scheme: str):
    steps = max(1, round(t_end / dt))
    dt = t_end / steps
    s = np.array([theta0, 0.0])
    out = [s.copy()]
    for _ in range(steps):
        if scheme == "euler":
            s = s + dt * np.array(rhs(0, s))
        else:
            k1 = np.array(rhs(0, s))
            k2 = np.array(rhs(0, s + dt / 2 * k1))
            k3 = np.array(rhs(0, s + dt / 2 * k2))
            k4 = np.array(rhs(0, s + dt * k3))
            s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        out.append(s.copy())
    return np.linspace(0.0, t_end, steps + 1), np.array(out)


def pendulum_run(pas: float, theta0: float = 1.2, t_end: float = 5.0):
    t = np.linspace(0.0, t_end, 400)
    truth = solve_ivp(rhs, (0.0, t_end), [theta0, 0.0], t_eval=t, rtol=1e-10, atol=1e-10).y[0]
    ids = ["euler", "rk4"]
    sol, vals, base = {}, {"err": {}, "drift": {}, "turn": {}}, {"err": {}, "drift": {}, "turn": {}}
    for target_state, p in ((vals, pas), (base, 0.0)):
        for m in ids:
            tt, s = integrate(theta0, t_end, 10 ** (-3.5 + 2.5 * p), m)
            theta = np.interp(t, tt, s[:, 0])
            energy = 0.5 * s[:, 1] ** 2 - 9.81 * np.cos(s[:, 0])
            scale = 9.81 * (1 - math.cos(theta0))
            target_state["err"][m] = float(np.max(np.abs(theta - truth)) / theta0)
            target_state["drift"][m] = float(abs(energy[-1] - energy[0]) / scale)
            target_state["turn"][m] = float(np.max(np.abs(s[:, 0])) > math.pi)
            if p == pas:
                sol[m] = theta
    none = {m: None for m in ids}
    measures = {
        "err_angle": measure_block(PEN_MEASURES["err_angle"], vals["err"], none, base["err"], ids),
        "energy_drift": measure_block(PEN_MEASURES["energy_drift"], vals["drift"], none, base["drift"], ids),
        "full_turn": measure_block(PEN_MEASURES["full_turn"], vals["turn"], none, base["turn"], ids),
    }
    views = [
        {"id": "trajectoire", "type": "curves", "title": "Angle au cours du temps",
         "axes": {"x": [0.0, t_end], "y": [-theta0 * 1.6, theta0 * 1.6]}, "shown": 400, "total": 400, "clipped": 0,
         "ui": {"x_title": "Temps (s)", "y_title": "Angle (rad)"}, "series": [
             series("trajectoire", "truth", None, "truth", "Solution de référence", x=t, y=truth),
             series("trajectoire", "series", "euler", "method", "Euler explicite", x=t, y=sol["euler"]),
             series("trajectoire", "series", "rk4", "correction", "Runge-Kutta d'ordre 4", x=t, y=sol["rk4"]),
         ]},
        {"id": "sens", "type": "sensitivity", "title": "Erreur selon le pas", "series": []},
    ]
    euler_state = measures["err_angle"]["states"]["euler"]
    return {
        "schema_version": 1, "state_hash": f"pen-pas{int(pas * 100):03d}".ljust(16, "0")[:16],
        "methods": PEN_METHODS, "measures": measures,
        "equation": {"terms": {"err": {"violated_by": ["pas"] if pas > 0 else []}}},
        "challenges": [
            {"id": "plus-grand-pas", "passed": pas >= 0.2 and euler_state == "ok"},
            {"id": "rk4-gros-pas", "passed": vals["turn"]["euler"] == 1.0 and vals["err"]["rk4"] < 0.05},
        ],
        "views": views, "draw_log": None, "invalid_rate": {"euler": 0.0, "rk4": 0.0}, "warnings": [],
        "repeat_used": 1, "compute_ms": 0.0,
    }


# --- Série d'Entraînement -------------------------------------------------------------------------------------------


def full_state(params: dict, hypotheses: dict, defaults: dict):
    return {"params": {**defaults["params"], **params}, "hypotheses": {**defaults["hypotheses"], **hypotheses},
            "extra_points": [], "seed": SEED}


REG_DEFAULTS = {"params": {"n": 150, "beta1": 1.5},
                "hypotheses": {"hetero": 0.0, "autocorr": False, "error_law": "normal",
                               "relation": "linear", "add_leverage": False}}
STU_DEFAULTS = {"params": {"n": 25, "delta": 0.5}, "hypotheses": {"loi": "normal"}}


def confidence(k: int) -> dict:
    return {"guess": 1 / k, "fair": (1 / k + 0.95) / 2, "sure": 0.95}


def training_session():
    reg_state = full_state({"n": 300}, {"hetero": 0.9}, REG_DEFAULTS)
    stu_state = full_state({"n": 25}, {"loi": "cauchy"}, STU_DEFAULTS)
    diag_view = reg_run(0.9)["views"][1]  # les résidus, avec la pathologie cachée
    order = np.random.default_rng(7)  # mélange fixe des choix, pour des fixtures stables
    pathologies = [
        ("Hétéroscédasticité", "hetero", {"hetero": 0.9}, True,
         "Les résidus s'ouvrent en entonnoir : la variance dépend de x."),
        ("Point levier influent", "add_leverage", {"add_leverage": True}, False,
         "Un levier montrerait un point isolé loin des autres, pas une dispersion croissante."),
        ("Relation quadratique", "relation", {"relation": "quadratic"}, False,
         "Une relation courbe dessinerait un arc dans les résidus."),
        ("Hypothèses respectées", None, {}, False,
         "Des hypothèses respectées donneraient un nuage de résidus homogène autour de zéro."),
    ]
    diag_choices = []
    for i, k in enumerate(order.permutation(len(pathologies))):
        label, _, hyp, correct, explain = pathologies[k]
        diag_choices.append({"id": f"c{i + 1}", "label": label, "correct": correct, "explain": explain,
                             "reveal": {"state": full_state({}, hyp, REG_DEFAULTS), "focus_view": "residus"}})
    questions = [
        {"qid": "regression-lineaire/reg-q1-biais/0", "experiment_id": "regression-lineaire", "type": "misconception",
         "prompt": "Sous forte hétéroscédasticité (n = 300), que devient l'estimateur MCO de la pente ?",
         "hypothesis": "hetero", "k": 2, "confidence": confidence(2), "choices": [
             {"id": "a", "label": "Il reste sans biais, mais les intervalles de confiance sont invalides.",
              "correct": True, "explain": "Exact : l'estimation reste juste en moyenne tandis que la couverture chute.",
              "reveal": {"state": reg_state, "focus_view": "ic"}},
             {"id": "b", "label": "Il devient biaisé, même pour un grand échantillon.", "correct": False,
              "explain": "Observez les centres des 100 intervalles : ils restent centrés sur la vraie pente. "
                         "Seule la largeur est fausse.",
              "reveal": {"state": reg_state, "focus_view": "ic"}}]},
        {"qid": "regression-lineaire/reg-q2-diag/0", "experiment_id": "regression-lineaire",
         "type": "diagnostic_auto",
         "prompt": "Analysez le graphique des résidus ci-dessous. Quelle situation observez-vous ?",
         "initial_view": diag_view, "hypothesis": "hetero", "k": 4, "confidence": confidence(4),
         "choices": diag_choices},
        {"qid": "test-student/stu-q1-cauchy/0", "experiment_id": "test-student", "type": "misconception",
         "prompt": "Sous une loi de Cauchy (n = 25), le test de Student rejette-t-il H0 à tort plus souvent que 5 % ?",
         "hypothesis": "loi", "k": 2, "confidence": confidence(2), "choices": [
             {"id": "a", "label": "Non : il devient trop prudent, et c'est sa puissance qui s'effondre.",
              "correct": True, "explain": "Exact : un point extrême gonfle S, donc T reste petit, sous H0 comme sous H1.",
              "reveal": {"state": stu_state, "focus_view": "pvalues"}},
             {"id": "b", "label": "Oui, beaucoup plus souvent.", "correct": False,
              "explain": "Les p-values s'entassent près de 1 : le test devient trop prudent, "
                         "et c'est sa puissance qui s'effondre.",
              "reveal": {"state": stu_state, "focus_view": "pvalues"}}]},
    ]
    digest = content_hash("".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "experiments").glob("*.yaml"))))
    return {"id": f"toutes~{SEED}", "filter": "toutes", "seed": SEED, "content_hash": digest[:6],
            "stale_link": False, "questions": questions, "dropped": []}


# --- Écriture -----------------------------------------------------------------------------------------------------------

FIXTURES = {
    "regression_sain.run": (RunResult, lambda: reg_run(0.0)),
    "regression_hetero.run": (RunResult, lambda: reg_run(0.8)),
    "regression_hetero.sweep": (SweepResult, reg_sweep),
    "student_normal.run": (RunResult, lambda: student_run("normal")),
    "student_cauchy.run": (RunResult, lambda: student_run("cauchy")),
    "pendule_sain.run": (RunResult, lambda: pendulum_run(0.0)),
    "pendule_gros_pas.run": (RunResult, lambda: pendulum_run(0.8)),
    "training_session": (TrainingSessionResponse, training_session),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (model, build) in FIXTURES.items():
        payload = model.model_validate(clean(build())).model_dump(mode="json")  # échoue si hors contrat
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(clean(payload), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:.0f} Ko")


if __name__ == "__main__":
    main()
