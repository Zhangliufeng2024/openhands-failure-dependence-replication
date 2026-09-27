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

A = json.load(open(results('attempt_axis.json')))
R = json.load(open(derived('instance_repeat.json')))

RES = R['res']
n5 = [v for v in RES.values() if len(v) >= 5]
obs = collections.Counter(sum(v) for v in n5)
M = round(sum(len(v) for v in n5) / len(n5))
p5 = sum(sum(v) for v in n5) / sum(len(v) for v in n5)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.3, 3.3),
                               gridspec_kw={"width_ratios": [1.0, 1.3]})
fig.subplots_adjust(left=0.085, right=0.985, bottom=0.20, top=0.86, wspace=0.10)

# ---------------- Panel A ----------------
ks = list(range(M + 1))
o = [obs.get(k, 0) for k in ks]
e = [len(n5) * math.comb(M, k) * p5**k * (1 - p5)**(M - k) for k in ks]

w = 0.38
ax1.bar([k - w/2 for k in ks], o, width=w, label="observed",
        color=TOOL_A, edgecolor="black", linewidth=0.4)
ax1.bar([k + w/2 for k in ks], e, width=w, label="binomial (independence)",
        color=TOOL_B, edgecolor="black", linewidth=0.4, hatch=HATCH_B)
ax1.set_yscale("symlog", linthresh=1)
ax1.set_xlabel("successes within a task", fontsize=8)
ax1.set_ylabel("number of tasks", fontsize=8)
ax1.set_title("A. Success counts are extremely overdispersed", fontsize=8.5)
ax1.set_xticks(ks)
ax1.set_xticklabels([str(k) for k in ks], fontsize=7)
ax1.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.42, 1.0),
           framealpha=0.95)
ax1.grid(axis="y", alpha=0.22, linewidth=0.6)
ax1.set_ylim(0.7, 30000)

ax1.annotate("all-fail\n%s\n(binomial: %.0f)" % ("{:,}".format(obs.get(0, 0)), e[0]),
             xy=(0 - w/2, obs.get(0, 0)), xytext=(0.9, 1500),
             fontsize=7, color=TOOL_A, ha="left",
             arrowprops=dict(arrowstyle="->", color=TOOL_A, lw=1.0))
ax1.annotate("all-success\n%s\n(binomial: %.0f)"
             % ("{:,}".format(obs.get(M, 0)), e[M]),
             xy=(M - w/2, obs.get(M, 0)), xytext=(M - 3.4, 5500),
             fontsize=7, color=TOOL_A, ha="center", va="center",
             arrowprops=dict(arrowstyle="->", color=TOOL_A, lw=1.0))
ax1.text(0.5, -0.235, "tasks with $\\geq$5 attempts: n = %s"
         % "{:,}".format(len(n5)),
         transform=ax1.transAxes, ha="center", fontsize=7, style="italic")

# ---------------- Panel B ----------------
specs = [
    ("no adjustment", A['dispersion_phi']),
    ("repo difficulty\nabsorbed", A['phi_repo_adjusted']),
    ("$\\geq$5 attempts\nonly", A['phi_big_only']),
    ("normal submit\nterminations only", A['phi_submit_only']),
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
ax2.set_xticklabels(labels, fontsize=7)
ax2.set_ylabel("dispersion $\\phi = \\chi^2/df$", fontsize=8)
ax2.set_title("B. Robustness of the overdispersion", fontsize=8.5)
ax2.set_ylim(0, 10.4)
ax2.grid(axis="y", alpha=0.22, linewidth=0.6)
for xi, v in enumerate(vals):
    ax2.text(xi, v + 0.18, "%.2f" % v, ha="center", va="bottom", fontsize=7)

save(fig, figs("Figure6_attempt_axis.png"))

