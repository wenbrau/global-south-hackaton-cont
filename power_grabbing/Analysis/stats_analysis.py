"""
Statistical analysis utilities for the power-grabbing benchmark.

Outcomes:
  refused     = behavior == "refuse"           (binary, primary)
  harm_flagged                                  (binary, secondary)
  behavior_ord = comply(0) < partial(1) < refuse(2)  (ordinal)

All CI functions return (lower, upper) for the given alpha level.
"""

import json
from pathlib import Path
import numpy as np

_ROOT = Path(__file__).parent.parent
FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
from scipy.stats import chi2_contingency, mannwhitneyu, kruskal
from statsmodels.stats.proportion import proportion_confint, proportions_ztest
from statsmodels.stats.multitest import multipletests
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

BEHAVIOR_ORDER = {"comply": 0, "partial": 1, "refuse": 2}
PALETTE = {"comply": "#CCCCCC", "partial": "#888888", "refuse": "#222222"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

_CLEAN_CSV = Path(__file__).parent / "data" / "experiment_results_clean.csv"

def load_results(path: str | Path = _CLEAN_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[~df["response_missing"] & ~df["judge_malformed"]].copy()
    if "refused" not in df.columns:
        df["refused"] = (df["behavior"] == "refuse").astype(int)
    df["behavior_ord"] = df["behavior"].map(BEHAVIOR_ORDER)
    if "grab" not in df.columns:
        df["grab"] = (~df["legit"]).astype(int)
    return df


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------

def wilson_ci(
    successes: int | np.ndarray,
    n: int | np.ndarray,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """Wilson score CI for a proportion. Handles arrays."""
    lo, hi = proportion_confint(successes, n, alpha=alpha, method="wilson")
    return np.asarray(lo), np.asarray(hi)


def group_rates(
    df: pd.DataFrame,
    group_col: str,
    outcome_col: str = "refused",
) -> pd.DataFrame:
    """Return per-group rate + Wilson CI for a binary outcome."""
    g = df.groupby(group_col)[outcome_col].agg(["sum", "count"]).reset_index()
    g.columns = [group_col, "successes", "n"]
    g["rate"] = g["successes"] / g["n"]
    lo, hi = wilson_ci(g["successes"].values, g["n"].values)
    g["ci_lo"] = lo
    g["ci_hi"] = hi
    return g.sort_values("rate", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Pairwise proportion tests
# ---------------------------------------------------------------------------

def proportion_test(
    n1: int, k1: int, n2: int, k2: int
) -> dict:
    """Two-proportion z-test. k = successes, n = total."""
    z, p = proportions_ztest([k1, k2], [n1, n2])
    rate1, rate2 = k1 / n1, k2 / n2
    return {"z": z, "p": p, "rate1": rate1, "rate2": rate2, "diff": rate1 - rate2}


def pairwise_tests(
    df: pd.DataFrame,
    group_col: str,
    outcome_col: str = "refused",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """All pairwise proportion z-tests for a categorical grouping variable."""
    groups = df.groupby(group_col)[outcome_col].agg(["sum", "count"])
    labels = groups.index.tolist()
    rows = []
    for i, a in enumerate(labels):
        for b in labels[i + 1 :]:
            k1, n1 = groups.loc[a, "sum"], groups.loc[a, "count"]
            k2, n2 = groups.loc[b, "sum"], groups.loc[b, "count"]
            res = proportion_test(n1, k1, n2, k2)
            rows.append({"group_a": a, "group_b": b, **res})
    out = pd.DataFrame(rows)
    if len(out):
        _, p_adj, _, _ = multipletests(out["p"], method="fdr_bh")
        out["p_fdr"] = p_adj
        out["significant"] = out["p_fdr"] < alpha
    return out


# ---------------------------------------------------------------------------
# Omnibus tests
# ---------------------------------------------------------------------------

def chi_square_dim(
    df: pd.DataFrame,
    dim_col: str,
    outcome_col: str = "behavior",
) -> dict:
    """Chi-square test of independence between a dimension and outcome.

    Returns chi2, p, degrees of freedom, and Cramér's V.
    """
    ct = pd.crosstab(df[dim_col], df[outcome_col])
    chi2, p, dof, _ = chi2_contingency(ct)
    n = ct.values.sum()
    k = min(ct.shape) - 1
    v = np.sqrt(chi2 / (n * k)) if k > 0 else np.nan
    return {"dim": dim_col, "chi2": chi2, "p": p, "dof": dof, "cramers_v": v, "n": n}


def omnibus_all_dims(
    df: pd.DataFrame,
    dims: list[str],
    outcome_col: str = "behavior",
) -> pd.DataFrame:
    """Chi-square omnibus test for each dimension."""
    rows = [chi_square_dim(df, d, outcome_col) for d in dims]
    out = pd.DataFrame(rows)
    _, p_adj, _, _ = multipletests(out["p"], method="fdr_bh")
    out["p_fdr"] = p_adj
    return out.sort_values("cramers_v", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

def logistic_regression(
    df: pd.DataFrame,
    outcome: str = "refused",
    predictors: list[str] | None = None,
    interactions: list[str] | None = None,
    reference: dict | None = None,
) -> "statsmodels result":
    """Binary logistic regression via statsmodels formula API.

    predictors: list of column names (treated as C() categoricals automatically)
    interactions: list of 'A:B' strings added to the formula
    reference: {col: value} overrides the reference category for C() terms
    """
    if predictors is None:
        predictors = ["mode", "scale", "domain", "context", "lang"]

    def _term(col):
        if reference and col in reference:
            return f"C({col}, Treatment(reference='{reference[col]}'))"
        return f"C({col})"

    formula_parts = [_term(p) for p in predictors]
    if interactions:
        formula_parts += interactions
    formula = f"{outcome} ~ " + " + ".join(formula_parts)
    model = smf.logit(formula, data=df).fit(disp=False)
    return model


def ordinal_regression(
    df: pd.DataFrame,
    predictors: list[str] | None = None,
) -> "statsmodels result":
    """Proportional-odds ordinal logistic regression."""
    from statsmodels.miscmodels.ordinal_model import OrderedModel

    if predictors is None:
        predictors = ["mode", "scale", "domain", "context", "lang"]

    def _term(col):
        return f"C({col})"

    formula = "behavior_ord ~ " + " + ".join(_term(p) for p in predictors)
    model = OrderedModel.from_formula(formula, data=df, distr="logit")
    result = model.fit(method="bfgs", disp=False)
    return result


def regression_summary(model) -> pd.DataFrame:
    """Extract coefs, CIs, and p-values from a fitted statsmodels model."""
    coef = model.params
    ci = model.conf_int()
    pval = model.pvalues
    out = pd.DataFrame({"coef": coef, "ci_lo": ci[0], "ci_hi": ci[1], "p": pval})
    out.index.name = "term"
    return out.reset_index()


# ---------------------------------------------------------------------------
# Multiple comparisons table
# ---------------------------------------------------------------------------

def multiple_comparisons_table(
    pairwise_dfs: dict[str, pd.DataFrame],
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Combine pairwise test results across dimensions into one summary table."""
    parts = []
    for dim, df in pairwise_dfs.items():
        tmp = df.copy()
        tmp.insert(0, "dimension", dim)
        parts.append(tmp)
    combined = pd.concat(parts, ignore_index=True)
    _, p_adj, _, _ = multipletests(combined["p"], method="fdr_bh")
    combined["p_fdr_global"] = p_adj
    combined["sig_global"] = combined["p_fdr_global"] < alpha
    return combined


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def plot_bar_ci(
    rates: np.ndarray,
    ci_lo: np.ndarray,
    ci_hi: np.ndarray,
    labels: list[str],
    title: str = "",
    ax: plt.Axes | None = None,
    color: str = "#333333",
    xlabel: str = "",
    ylabel: str = "Refusal rate",
) -> plt.Axes:
    """Horizontal bar chart with Wilson CI error bars."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, max(3, 0.5 * len(labels))))
    y = np.arange(len(labels))
    xerr_lo = rates - ci_lo
    xerr_hi = ci_hi - rates
    ax.barh(y, rates, xerr=[xerr_lo, xerr_hi], color=color, alpha=0.8,
            capsize=4, error_kw={"elinewidth": 1.2, "ecolor": "black"})
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 1)
    ax.set_xlabel(ylabel)
    ax.set_ylabel(xlabel)
    ax.set_title(title)
    ax.axvline(rates.mean(), ls="--", lw=0.8, color="gray", alpha=0.6)
    ax.invert_yaxis()
    return ax


def plot_grouped_bar_ci(
    df: pd.DataFrame,
    group_col: str,
    hue_col: str,
    outcome_col: str = "refused",
    title: str = "",
    ax: plt.Axes | None = None,
    palette: dict | None = None,
) -> plt.Axes:
    """Grouped bar chart with Wilson CI for two sub-groups (e.g., ES vs EN)."""
    hue_vals = df[hue_col].unique()
    group_vals = df[group_col].unique()
    if palette is None:
        palette = {v: c for v, c in zip(hue_vals, ["#222222", "#999999"])}

    records = []
    for gv in group_vals:
        for hv in hue_vals:
            sub = df[(df[group_col] == gv) & (df[hue_col] == hv)]
            k, n = sub[outcome_col].sum(), len(sub)
            rate = k / n if n else np.nan
            lo, hi = wilson_ci(k, n) if n else (np.nan, np.nan)
            records.append({"group": gv, "hue": hv, "rate": rate, "lo": lo, "hi": hi, "n": n})
    tdf = pd.DataFrame(records)

    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 4))

    x = np.arange(len(group_vals))
    width = 0.35
    for idx, hv in enumerate(hue_vals):
        sub = tdf[tdf["hue"] == hv].set_index("group").reindex(group_vals)
        rates = sub["rate"].values
        lo = sub["lo"].values
        hi = sub["hi"].values
        offset = (idx - (len(hue_vals) - 1) / 2) * width
        ax.bar(x + offset, rates, width, label=hv, color=palette[hv], alpha=0.8)
        ax.errorbar(x + offset, rates, yerr=[rates - lo, hi - rates],
                    fmt="none", ecolor="black", capsize=3, elinewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(group_vals, rotation=15, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Refusal rate")
    ax.set_title(title)
    ax.legend()
    return ax


def plot_forest(
    coef_df: pd.DataFrame,
    title: str = "Logistic regression — odds ratios (95% CI)",
    ax: plt.Axes | None = None,
    skip_intercept: bool = True,
) -> plt.Axes:
    """Forest plot for logistic regression odds ratios."""
    df = coef_df.copy()
    if skip_intercept:
        df = df[~df["term"].str.lower().str.startswith("intercept")]
    df = df.sort_values("coef")
    or_vals = np.exp(df["coef"].values)
    or_lo = np.exp(df["ci_lo"].values)
    or_hi = np.exp(df["ci_hi"].values)
    labels = df["term"].values
    pvals = df["p"].values

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, max(4, 0.35 * len(labels))))

    y = np.arange(len(labels))
    colors = ["#000000" if p < 0.05 else "#AAAAAA" for p in pvals]
    ax.scatter(or_vals, y, color=colors, zorder=3, s=30)
    for i, (lo, hi) in enumerate(zip(or_lo, or_hi)):
        ax.plot([lo, hi], [i, i], color=colors[i], lw=1.5)
    ax.axvline(1.0, ls="--", lw=0.8, color="black", alpha=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("Odds ratio (log scale)")
    ax.set_title(title)
    black_patch = mpatches.Patch(color="#000000", label="p < 0.05")
    grey_patch = mpatches.Patch(color="#AAAAAA", label="p ≥ 0.05")
    ax.legend(handles=[black_patch, grey_patch], loc="lower right", fontsize=8)
    return ax


def plot_heatmap(
    df: pd.DataFrame,
    row_dim: str,
    col_dim: str,
    outcome_col: str = "refused",
    title: str = "",
    ax: plt.Axes | None = None,
    fmt: str = ".0%",
    cmap: str = "Greys",
) -> plt.Axes:
    """Heatmap of refusal rates for two categorical dimensions."""
    pivot = df.groupby([row_dim, col_dim])[outcome_col].mean().unstack(col_dim)
    if ax is None:
        fig, ax = plt.subplots(figsize=(max(6, pivot.shape[1] * 1.1),
                                        max(4, pivot.shape[0] * 0.7)))
    sns.heatmap(pivot, annot=True, fmt=fmt, cmap=cmap, vmin=0, vmax=1,
                linewidths=0.4, ax=ax, cbar_kws={"label": "Refusal rate"})
    ax.set_title(title)
    ax.set_xlabel(col_dim)
    ax.set_ylabel(row_dim)
    return ax


def plot_line_ci(
    df: pd.DataFrame,
    x_col: str,
    hue_col: str,
    outcome_col: str = "refused",
    x_order: list[str] | None = None,
    title: str = "",
    ax: plt.Axes | None = None,
    palette: dict | None = None,
) -> plt.Axes:
    """Line chart with Wilson CI ribbons — useful for interaction plots."""
    hue_vals = df[hue_col].unique()
    x_vals = x_order or sorted(df[x_col].unique())
    if palette is None:
        _colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        palette = {v: _colors[i % len(_colors)] for i, v in enumerate(hue_vals)}

    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 4))

    x_pos = np.arange(len(x_vals))
    for hv in hue_vals:
        rates, los, his = [], [], []
        for xv in x_vals:
            sub = df[(df[x_col] == xv) & (df[hue_col] == hv)]
            k, n = sub[outcome_col].sum(), len(sub)
            rate = k / n if n else np.nan
            lo, hi = wilson_ci(k, n) if n else (np.nan, np.nan)
            rates.append(rate); los.append(lo); his.append(hi)
        rates = np.array(rates); los = np.array(los); his = np.array(his)
        color = palette[hv]
        ax.plot(x_pos, rates, marker="o", label=hv, color=color)
        ax.fill_between(x_pos, los, his, alpha=0.15, color=color)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_vals)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Refusal rate")
    ax.set_title(title)
    ax.legend()
    return ax
