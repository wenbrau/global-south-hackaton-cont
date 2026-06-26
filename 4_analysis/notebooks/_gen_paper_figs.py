"""Generate the three paper-marked figures (ESTE GRAFICO SI VA) from 06_figures.ipynb:
fig2b_by_mode, fig8_behavior_spectrum, fig_dyad_nationality. Run from Analysis/."""
import matplotlib
matplotlib.use("Agg")
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch

plt.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 150, "savefig.bbox": "tight",
    "font.family": "serif", "mathtext.fontset": "cm",
    "font.size": 11, "axes.titlesize": 12, "axes.labelsize": 12,
    "axes.grid": False, "axes.spines.top": True, "axes.spines.right": True,
    "axes.edgecolor": "black", "axes.linewidth": 1.0,
})
ERR = "0.35"
BRAND = {"gemini": "#4285F4", "qwen": "#9333EA", "deepseek": "#0D9488", "minimax": "#E11D48",
         "claude": "#EA8A4B", "haiku": "#EA8A4B"}
def brand_color(name, default="0.45"):
    n = name.lower()
    for k, c in BRAND.items():
        if k in n: return c
    return default

DATA = Path("data"); FIGS = Path("figures"); FIGS.mkdir(exist_ok=True)

def wilson_ci(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z**2 / n
    c = (p + z**2 / (2*n)) / d
    h = (z * np.sqrt(p*(1-p)/n + z**2 / (4*n**2))) / d
    return (c - h, c + h)

panel = pd.read_csv(DATA / "clean" / "dataset2_5models_4langs.csv")
def short(t): return t.split("/")[-1]
P = panel.copy(); P["m"] = P["target"].map(short)
SEEK = P[P["mode"] == "positive"]; DIS = P[P["mode"] == "negative"]; GRAB = P[P["mode"] == "positive+negative"]
MODEL_ORDER = ["gemini-2.5-flash-lite", "qwen3.7-plus", "deepseek-v4-pro", "minimax-m3", "claude-3-haiku"]

def refusal_stats(df, by):
    by = [by] if isinstance(by, str) else list(by)
    g = df.dropna(subset=["refused"]).groupby(by, observed=True)["refused"].agg(["sum", "count"]).reset_index()
    g.columns = by + ["k", "n"]; g["rate"] = g["k"] / g["n"]
    ci = g.apply(lambda r: wilson_ci(r["k"], r["n"]), axis=1)
    g["lo"] = ci.apply(lambda x: x[0]); g["hi"] = ci.apply(lambda x: x[1])
    return g

# ---- Fig 2b: refusal by mode, per model
modes3 = [("positive", "harmless empowerment", "#7DCFB6"),
          ("positive+negative", "power-grabbing", "#D1495B"),
          ("negative", "disempowerment", "#F6AE2D")]
x = np.arange(len(MODEL_ORDER)); w = 0.26
fig, ax = plt.subplots(figsize=(9, 4.5))
for j, (mode, label, c) in enumerate(modes3):
    s = refusal_stats(P[P["mode"] == mode], "m").set_index("m").reindex(MODEL_ORDER)
    off = x + (j - 1)*w
    ax.bar(off, s["rate"], w, color=c, edgecolor="black", linewidth=0.6, label=label)
    ax.errorbar(off, s["rate"], yerr=[s["rate"] - s["lo"], s["hi"] - s["rate"]],
                fmt="none", ecolor="0.3", capsize=2, lw=0.7)
    for xi, rv, hv in zip(off, s["rate"], s["hi"]):
        if np.isfinite(rv):
            ax.text(xi, hv + 0.015, f"{rv*100:.0f}", ha="center", va="bottom", fontsize=6.5)
ax.set_xticks(x); ax.set_xticklabels(MODEL_ORDER, rotation=20, ha="right")
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1)); ax.set_ylim(0, 1)
ax.set_ylabel("refusal rate")
ax.set_title("Refusal by mode", loc="left")
ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=9)
fig.tight_layout(); fig.savefig(FIGS / "fig2b_by_mode.png"); plt.close(fig)
print("fig2b_by_mode.png OK")

# ---- Fig 8: behavior spectrum (comply/partial/refuse) on power-grabbing, by model
def _s(x): return x.strip().strip("'") if isinstance(x, str) else x
GRAB2 = GRAB.copy(); GRAB2["behavior"] = GRAB2["behavior"].apply(_s)
def spec(m):
    return (GRAB2[GRAB2.m == m]["behavior"].dropna().value_counts(normalize=True)
            .reindex(["comply", "partial", "refuse"]).fillna(0))
S = pd.DataFrame({m: spec(m) for m in MODEL_ORDER}).T
fig, ax = plt.subplots(figsize=(10, 4.2))
xb = np.arange(len(MODEL_ORDER)); wb = 0.26
for j, (beh, c) in enumerate(zip(["comply", "partial", "refuse"], ["#D1495B", "#EDAE49", "#00798C"])):
    ax.bar(xb + (j - 1)*wb, S[beh], wb, color=c, edgecolor="black", linewidth=0.6, label=beh)
ax.set_xticks(xb); ax.set_xticklabels(MODEL_ORDER, rotation=20, ha="right")
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1)); ax.set_ylim(0, 1)
ax.set_ylabel("% of power-grabbing prompts")
ax.set_title("Behavior by model", loc="left")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIGS / "fig8_behavior_spectrum.png"); plt.close(fig)
print("fig8_behavior_spectrum.png OK")

# ---- Fig dyad: who the power-grab harms
from statsmodels.stats.contingency_tables import mcnemar
dyad = pd.read_csv(DATA / "clean" / "dataset4_dyads.csv")
dg = dyad[dyad["mode"] == "positive+negative"].copy()
dg["complied"] = 1 - dg["refused"]
PAIRS = ["american__chinese", "american__french", "chinese__north-korean", "argentine__british"]
PAIR_LBL = {"american__chinese": "US-CN", "american__french": "US-FR",
            "chinese__north-korean": "CN-KP", "argentine__british": "AR-GB"}
RIVAL = {"american__chinese", "argentine__british"}
ANCHOR = {"american__chinese": "US", "american__french": "US",
          "chinese__north-korean": "CN", "argentine__british": "AR"}
PARTNER = {"american__chinese": "CN", "american__french": "FR",
           "chinese__north-korean": "KP", "argentine__british": "GB"}
RED_D, RED_L = "#DC2626", "#FCA5A5"
BLU_D, BLU_L = "#2563EB", "#93C5FD"
def shades(pr): return (RED_D, RED_L) if pr in RIVAL else (BLU_D, BLU_L)
DMODELS = ["minimax/minimax-m3", "google/gemini-2.5-flash-lite"]
def comp(sub):
    s = sub["complied"].dropna(); k, n = s.sum(), len(s); lo, hi = wilson_ci(k, n); return k/n, lo, hi
def mcn_p(sub):
    p = (sub.dropna(subset=["refused"]).pivot_table(index=["domain", "context", "power"],
         columns="direction", values="refused", aggfunc="mean"))
    if not {"A->B", "B->A"}.issubset(p.columns): return np.nan
    p = p.dropna(subset=["A->B", "B->A"]); a = (p["A->B"] >= .5).astype(int); b = (p["B->A"] >= .5).astype(int)
    t = [[int(((a==1)&(b==1)).sum()), int(((a==1)&(b==0)).sum())],
         [int(((a==0)&(b==1)).sum()), int(((a==0)&(b==0)).sum())]]
    return float(mcnemar(t, exact=True).pvalue)

fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
for ax, mdl in zip(axes, DMODELS):
    sub = dg[dg.target == mdl]; x = np.arange(len(PAIRS)); w = 0.38
    tick_pos, tick_lab = [], []
    for k, pr in enumerate(PAIRS):
        cd, cl = shades(pr)
        specs = [(x[k] - w/2, "B->A", ANCHOR[pr], cd), (x[k] + w/2, "A->B", PARTNER[pr], cl)]
        his = []
        for xb, dirc, vic, col in specs:
            r, lo, hi = comp(sub[(sub.pair == pr) & (sub.direction == dirc)])
            ax.bar(xb, r, w, color=col, edgecolor="black", linewidth=0.5)
            ax.errorbar(xb, r, yerr=[[r - lo], [hi - r]], fmt="none", ecolor="0.3", capsize=2)
            tick_pos.append(xb); tick_lab.append(vic); his.append(hi)
        if mcn_p(sub[sub.pair == pr]) < 0.05:
            ax.text(x[k], max(his) + 0.012, "*", ha="center", va="bottom", fontsize=16)
        ax.text(x[k], -0.11, PAIR_LBL[pr], ha="center", va="top", fontsize=9,
                transform=ax.get_xaxis_transform())
    ax.set_xticks(tick_pos); ax.set_xticklabels(tick_lab, fontsize=8)
    ax.set_title(mdl.split("/")[-1], loc="left")
axes[0].yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1)); axes[0].set_ylim(0, 0.25)
axes[0].set_ylabel("compliance (power-grabbing)")
axes[1].legend(handles=[Patch(fc=RED_D, ec="black", label="rival pair"),
                        Patch(fc=BLU_D, ec="black", label="allied pair")],
               fontsize=8, frameon=False, loc="upper right")
fig.text(0.5, 0.005, "each bar = country harmed by the grab     * p<0.05 uncorrected (n.s. after Holm)",
         ha="center", fontsize=8, color="0.4")
fig.suptitle("Compliance is higher when the power-grab targets the US", fontsize=12)
fig.tight_layout(rect=[0, 0.03, 1, 1]); fig.savefig(FIGS / "fig_dyad_nationality.png"); plt.close(fig)
print("fig_dyad_nationality.png OK")
