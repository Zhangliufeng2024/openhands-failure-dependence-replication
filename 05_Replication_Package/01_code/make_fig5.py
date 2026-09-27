"""Figure 4: Simpson's paradox in the positional profile of failure hazard.

Panel A: the aggregate within-trajectory first-half/second-half contrast, for
         the raw two-tool split (which suggests opposite drifts) and for the
         composition-corrected layers (which show every layer rising or flat).
Panel B: the command-type mix shift that generates the spurious decline.

Saved 6.30 in wide at 300 dpi (figstyle.save) so no scaling is needed at
manuscript insertion.
"""
import json

import matplotlib.pyplot as plt
import numpy as np

import figstyle
from figstyle import GRID, HATCH_B, TOOL_A, TOOL_B, apply, save
from paths import figs, results

apply()

pf = json.load(open(results("positional_final.json"), encoding='utf-8'))
sp = json.load(open(results("simpson.json"), encoding='utf-8'))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.3, 3.6),
                               gridspec_kw={"width_ratios": [1.25, 1.0]})
fig.subplots_adjust(left=0.10, right=0.92, bottom=0.24, top=0.82, wspace=0.28)

# ---------------- Panel A ----------------
labels = ["non-test", "test + build", "view", "create", "str_replace"]
keys = ["bash, non-test", "bash, test/build", "editor, view",
        "editor, create", "editor, str_replace"]
diffs = [pf[k]["diff"] for k in keys]
ts = [pf[k]["t"] for k in keys]
# one colour per tool; the editor series is hatched so the two series stay
# separable in a black-and-white print (blue/red alone are not)
cols = [TOOL_A, TOOL_A, TOOL_B, TOOL_B, TOOL_B]
hatches = ["", "", HATCH_B, HATCH_B, HATCH_B]

x = np.arange(len(labels))
ax1.bar(x, diffs, color=cols, width=0.62, edgecolor="black", linewidth=0.5,
        hatch=hatches)
ax1.axhline(0, color="black", linewidth=0.9)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=7, rotation=28, ha="right", rotation_mode="anchor")
ax1.set_ylabel("Paired failure-rate difference", fontsize=8)
ax1.set_title("A. Paired hazard change by command type", fontsize=8.5)
ax1.grid(axis="y", alpha=0.25, linewidth=0.6)
ax1.set_ylim(-0.075, 0.092)
ax1.set_xlim(-0.62, 4.95)

for xi, (d, t) in enumerate(zip(diffs, ts)):
    off = 0.004 if d >= 0 else -0.004
    va = "bottom" if d >= 0 else "top"
    ax1.text(xi, d + off, "t=%+.1f" % t, ha="center", va=va, fontsize=7)

# reference: the raw two-tool split that produced the spurious reading
ax1.axhline(-0.0681, color=GRID, linestyle=":", linewidth=1.7)
ax1.text(4.9, -0.0648, "raw editor  -0.068", fontsize=7,
         color="#606a6d", ha="right", va="bottom")
ax1.axhline(+0.0183, color=GRID, linestyle="--", linewidth=1.7)
ax1.text(4.9, 0.0183, "raw bash  +0.018", fontsize=7,
         color="#606a6d", ha="right", va="bottom")

# ---------------- Panel B ----------------
view_share = [0.992, 0.321]          # from conditional.py B2 (stdout only)
srep_share = [0.001, 0.476]
create_share = [1 - v - s for v, s in zip(view_share, srep_share)]
xs = np.arange(2)
ax2.bar(xs, view_share, width=0.5, label="view", color="#2980b9",
        edgecolor="black", linewidth=0.5)
ax2.bar(xs, srep_share, width=0.5, bottom=view_share, label="str_replace",
        color="#e67e22", edgecolor="black", linewidth=0.5)
ax2.bar(xs, create_share, width=0.5,
        bottom=[v + s for v, s in zip(view_share, srep_share)],
        label="create / other", color="#95a5a6",
        edgecolor="black", linewidth=0.5)
ax2.set_xticks(xs)
ax2.set_xticklabels(["first half", "second half"], fontsize=7.5)
ax2.set_ylabel("share of editor calls", fontsize=8)
ax2.set_ylim(0, 1.0)
ax2.set_title("B. Editor-call mix", fontsize=8.5, pad=4)
# legend outside the axes: inside it covered the white "0.992" bar label
ax2.legend(fontsize=7.5, loc="center left", bbox_to_anchor=(1.01, 0.5),
           frameon=False)

for xi, v in enumerate(view_share):
    ax2.text(xi, v / 2, "%.3f" % v, ha="center", va="center",
             fontsize=7, color="white", fontweight="bold")
for xi, v in enumerate(srep_share):
    if v < 0.05:
        continue
    ax2.text(xi, view_share[xi] + v / 2, "%.3f" % v, ha="center",
             va="center", fontsize=7, color="white", fontweight="bold")

save(fig, figs("Figure4_simpson_paradox.png"))
