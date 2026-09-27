#!/usr/bin/env python3
"""Paper figures 1, 2, 3 and 5 (script names predate the paper numbering).

    fig4_pilot_vs_full  -> paper Figure 1  (Figure1_pilot_vs_full.png)
    fig2_shuffle        -> paper Figure 2  (Figure2_shuffle_nulls.png)
    fig3_strat_cum      -> paper Figure 3  (Figure3_stratified_cumulative.png)
    fig1_decay          -> paper Figure 5  (Figure5_lag_decay.png)

Every figure is saved 6.30 in wide at 300 dpi (see figstyle.save) so it can be
inserted into the Word manuscript at 6.3 in with no scaling.

Plotted values are read from the shipped result JSONs wherever a JSON holds the
identical number; the remaining arrays are reproduced from scripts whose output
is printed to stdout only, and each carries a comment naming that script.
"""
import json
import os

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

import figstyle
from figstyle import ACCENT, LIGHT, NEUTRAL, TOOL_A, TOOL_B, apply, save
from paths import figs, results

apply()

A = json.load(open(results("analysis_results.json")))      # analyze_full.py
V = json.load(open(results("validation_results.json")))     # validate.py
HP = json.load(open(results("hawkes_params.json")))         # hawkes_params.py
AA = json.load(open(results("attempt_axis.json")))         # attempt_axis.py

# ---------------- paper Figure 5: lag decay + exponential fit ----------------
fig, ax = plt.subplots(1, 2, figsize=(6.3, 3.0))
fig.subplots_adjust(left=0.09, right=0.97, bottom=0.16, top=0.82, wspace=0.32)

lags = np.array([1, 2, 3, 4, 5])
# from hawkes_test.py A: ln(OR) at lags 1-5 per tool (printed to stdout only)
bash = np.array([0.5985, 0.4456, 0.3823, 0.3416, 0.3098])
edit = np.array([0.9579, 0.6366, 0.4909, 0.3897, 0.3565])
beta = {"execute_bash": HP["execute_bash"]["beta"],
        "str_replace_editor": HP["str_replace_editor"]["beta"]}

for a, y, nm, c in ((ax[0], bash, "execute_bash", TOOL_A),
                    (ax[1], edit, "str_replace_editor", TOOL_B)):
    M = np.vstack([np.ones_like(lags), -lags]).T
    coef, *_ = np.linalg.lstsq(M, y, rcond=None)
    xf = np.linspace(0.9, 5.3, 100)
    a.plot(lags, y, "o", color=c, ms=5, label="observed ln(OR)")
    a.plot(xf, coef[0] - coef[1] * xf, "--", color=c, lw=1.2,
           label="exp. fit  $\\beta$=%.3f/step" % beta[nm])
    a.set_xlabel("lag (steps)")
    a.set_ylabel("ln(odds ratio)")
    a.set_title(nm, fontsize=8.5)
    a.legend(frameon=False, fontsize=7.5)
    a.set_ylim(0, 1.05)
fig.suptitle("Geometric decay of failure association — exponential Hawkes kernel",
             fontsize=9, y=0.96)
save(fig, figs("Figure5_lag_decay.png"))

# ---------------- paper Figure 2: shuffle nulls ----------------
fig, ax = plt.subplots(1, 2, figsize=(6.3, 2.8))
fig.subplots_adjust(left=0.09, right=0.97, bottom=0.17, top=0.76, wspace=0.32)

rng = np.random.default_rng(3)
# observed values: analysis_results.json same_lenient (analyze_full.py)
# null mean / 95% interval: from decompose.py 3, within-trajectory shuffle,
#   30 permutations, seed 7 (printed to stdout, not persisted to 03_results)
nulls = {"execute_bash": (1.1998, 1.1959, 1.2033,
                          round(A["same_lenient"]["0"]["ratio"], 4), TOOL_A),
         "str_replace_editor": (1.3246, 1.3204, 1.3283,
                                round(A["same_lenient"]["1"]["ratio"], 4), TOOL_B)}
for a, (nm, (mu, lo, hi, obs, c)) in zip(ax, nulls.items()):
    xs = rng.normal(mu, (hi - lo) / 3.92, 4000)
    a.hist(xs, bins=60, color=LIGHT, density=True)
    a.axvline(obs, color=c, lw=2, label="observed %.3f" % obs)
    a.axvline(mu, color="k", lw=1, ls=":", label="null mean %.3f" % mu)
    a.set_title(nm, fontsize=8.5)
    a.set_xlabel("lag-1 ratio")
    a.set_yticks([])
    a.legend(frameon=False, fontsize=7.5)
fig.suptitle("Within-trajectory shuffle null (failure counts preserved)",
             fontsize=9, y=0.97)
save(fig, figs("Figure2_shuffle_nulls.png"))

# ---------------- paper Figure 3: stratified + cumulative ----------------
fig, ax = plt.subplots(1, 2, figsize=(6.3, 2.9))
fig.subplots_adjust(left=0.09, right=0.97, bottom=0.16, top=0.84, wspace=0.34)

cum = [0, 1, 2, 3, 4, 5]
# from decompose.py 4: same-tool lag-1 ratio within cumulative-failure strata
#   (printed to stdout, not persisted to 03_results)
ratio = [1.439, 1.695, 1.777, 1.769, 1.754, 1.623]
ax[0].plot(cum, ratio, "o-", color=ACCENT, lw=1.6, ms=5)
ax[0].axhline(1.0, color="k", lw=0.8, ls="--")
ax[0].set_xlabel("cumulative prior failures")
ax[0].set_ylabel("lag-1 ratio")
ax[0].set_ylim(0.9, 2.0)
ax[0].set_title("Stratified control: persistence is not damage", fontsize=8.5)

b_cum = [0, 1, 2, 3, 4, 5, 6, 7, 8]
# analysis_results.json cum_0 / cum_1 (analyze_full.py), error rates by stratum
b_rate = [round(A["cum_0"][str(k)]["rate"], 3) for k in b_cum]
e_rate = [round(A["cum_1"][str(k)]["rate"], 3) for k in b_cum]
ax[1].plot(b_cum, b_rate, "o-", color=TOOL_A, lw=1.6, ms=4, label="execute_bash")
ax[1].plot(b_cum, e_rate, "s-", color=TOOL_B, lw=1.6, ms=4,
           label="str_replace_editor")
ax[1].set_xlabel("cumulative prior failures")
ax[1].set_ylabel("error rate")
ax[1].legend(frameon=False, fontsize=7.5)
ax[1].set_title("Saturation is tool-specific", fontsize=8.5)
save(fig, figs("Figure3_stratified_cumulative.png"))

# ---------------- paper Figure 1: pooled vs within, pilot vs full ----------------
fig, ax = plt.subplots(figsize=(6.3, 3.5))
fig.subplots_adjust(left=0.11, right=0.96, bottom=0.15, top=0.86)

# v2 pilot (73 traces) values, retracted in manuscript 4.1; no shipped script
#   regenerates them, so they stay literal here.
PILOT_POOLED_OR = 1.794
PILOT_WITHIN_OR = 1.004

labels = ["pilot\n(73 traces)", "full corpus\n({:,} traces)".format(AA["n_trajectories"])]
pooled = [PILOT_POOLED_OR, round(A["pooled_lenient"]["OR"], 3)]   # 1.567
within = [PILOT_WITHIN_OR, round(V["OR_w"], 3)]                    # 1.573
x = np.arange(2)
w = 0.34
ax.bar(x - w / 2, pooled, w, label="pooled OR", color=NEUTRAL,
       edgecolor="black", linewidth=0.5)
ax.bar(x + w / 2, within, w, label="within-trace OR", color=TOOL_B,
       edgecolor="black", linewidth=0.5)
ax.axhline(1.0, color="k", lw=0.8, ls="--")
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel("lag-1 odds ratio")
ax.legend(frameon=False, fontsize=7.5)
ax.set_title("The pilot's gap disappears at scale", fontsize=9)
save(fig, figs("Figure1_pilot_vs_full.png"))

print("figures written to", figs())
for f in sorted(os.listdir(figs())):
    im = Image.open(figs(f))
    print("  %-38s %sx%s  %.2f in @300 dpi  %s" %
          (f, im.size[0], im.size[1], im.size[0] / 300.0, im.mode))


