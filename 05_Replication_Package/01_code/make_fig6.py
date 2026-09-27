"""Figure 6: the attempt axis.

Panel A: the distribution of successes within a task against the binomial
         (independence) prediction. The U-shape is the finding.
Panel B: dispersion phi under each robustness specification.

Saved 6.30 in wide at 300 dpi (figstyle.save) so no scaling is needed at
manuscript insertion.
"""
import collections
import json
import math

import matplotlib.pyplot as plt
import numpy as np

import figstyle
from figstyle import HATCH_B, RAMP, TOOL_A, TOOL_B, apply, save
from paths import derived, figs, results

apply()

A = json.load(open(results('attempt_axis.json'), encoding='utf-8'))
R = json.load(open(derived('instance_repeat.json'), encoding='utf-8'))

RES = R['res']
n5 = [v for v in RES.values() if len(v) >= 5]
rows = A['u_shape']
bins = [r['bin'] for r in rows]
obs = [r['obs'] for r in rows]
expected = [r['exp'] for r in rows]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.3, 3.35),
                               gridspec_kw={"width_ratios": [1.15, 1.3]})
fig.subplots_adjust(left=0.085, right=0.985, bottom=0.22, top=0.85, wspace=0.20)

# ---------------- Panel A ----------------
positions = np.arange(len(bins))
w = 0.38
ax1.bar(positions - w/2, obs, width=w, label="observed",
        color=TOOL_A, edgecolor="black", linewidth=0.4)
ax1.bar(positions + w/2, expected, width=w, label="independence expectation",
        color=TOOL_B, edgecolor="black", linewidth=0.4, hatch=HATCH_B)
ax1.set_yscale("symlog", linthresh=1)
ax1.set_xlabel("successes within a task", fontsize=8)
ax1.set_ylabel("number of tasks", fontsize=8)
ax1.set_title("A. Success counts are overdispersed", fontsize=8.5)
ax1.set_xticks(positions)
ax1.set_xticklabels(bins, fontsize=6.4)
ax1.grid(axis="y", alpha=0.22, linewidth=0.6)
ax1.set_ylim(0.7, 5000)
ax1.text(0.5, -0.25, "tasks with $\\geq$5 attempts: n = %s; $p$ = %.4f"
         % ("{:,}".format(len(n5)), A['p5']),
         transform=ax1.transAxes, ha="center", fontsize=6.8, style="italic")

# ---------------- Panel B ----------------
specs = [
    ("baseline", A['dispersion_phi']),
    ("repo-adjusted", A['phi_repo_adjusted']),
    ("≥5 attempts", A['phi_big_only']),
    ("normal submit", A['phi_submit_only']),
]
labels = [s[0] for s in specs]
vals = [s[1] for s in specs]
x = np.arange(len(specs))
ax2.bar(x, vals, color=RAMP, width=0.62, edgecolor="black", linewidth=0.5)
ax2.axhline(1.0, color=TOOL_B, linestyle="--", linewidth=1.6)
ax2.text(-0.42, 1.28, "independence ($\\phi$ = 1)",
         fontsize=7, color=TOOL_B, ha="left",
         bbox=dict(facecolor="white", edgecolor="none", pad=1.2, alpha=0.9))
ax2.set_xticks(x)
ax2.set_xticklabels(labels, fontsize=6.3)
ax2.set_ylabel("")
ax2.set_title("B. Dispersion $\\phi$ across specifications", fontsize=8.5)
ax2.set_ylim(0, 10.4)
ax2.grid(axis="y", alpha=0.22, linewidth=0.6)
for xi, v in enumerate(vals):
    ax2.text(xi, v + 0.18, "%.2f" % v, ha="center", va="bottom", fontsize=7)

save(fig, figs("Figure6_attempt_axis.png"))

