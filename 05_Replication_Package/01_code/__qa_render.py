"""TEMPORARY QA: font-size floor, text/text and text/bar overlap, canvas overflow.

Monkeypatches figstyle.save so the checks run on the exact post-calibration
figure state, then delegates the write to the real save().
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.text import Text, Annotation
from matplotlib.legend import Legend
from matplotlib.patches import Rectangle

import figstyle
import paths

_real_save = figstyle.save
problems = []


def _texts(fig):
    out = []
    for ax in fig.axes:
        out += [t for t in ax.texts]
        out += list(ax.get_xticklabels()) + list(ax.get_yticklabels())
        out += [ax.title, ax.xaxis.label, ax.yaxis.label]
        for lg in [c for c in ax.children if isinstance(c, Legend)]:
            out += [t for t in lg.texts]
    out += [fig._suptitle] if fig._suptitle is not None else []
    return [t for t in out if t.get_text().strip()]


def _rects(fig):
    out = []
    for ax in fig.axes:
        out += [p for p in ax.patches
                if p.get_visible() and p.get_facecolor() is not None]
        for lg in [c for c in ax.children if isinstance(c, Legend)]:
            out += [p for p in lg.get_patches() if p.get_visible()]
    return out


def _ext(artist, r):
    try:
        return artist.get_window_extent(renderer=r)
    except Exception:
        return None


def qa(fig, path, width_in=figstyle.FIG_WIDTH_IN):
    target = int(round(width_in * figstyle.DPI))
    for _ in range(3):
        w = figstyle._tight_render(fig).size[0]
        if abs(w - target) <= 2:
            break
        fw, fh = fig.get_size_inches()
        fig.set_size_inches(fw * target / w, fh * target / w)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    name = path.split("\\")[-1].split("/")[-1]

    ts = _texts(fig)
    sizes = sorted({round(float(t.get_fontsize() or 0), 2) for t in ts})
    print("\n=== %s  figsize=%.2fx%.2f in" % (name, *fig.get_size_inches()))
    print("  font sizes used: %s   min=%.2f pt" % (sizes, min(sizes)))
    if min(sizes) < figstyle.MIN_FONT_PT:
        problems.append("%s: font %.2f pt < %.2f pt" %
                        (name, min(sizes), figstyle.MIN_FONT_PT))

    box = fig.bbox
    for t in ts:
        e = _ext(t, r)
        if e is None:
            continue
        if not box.contains(e.x0, e.y0) or not box.contains(e.x1, e.y1):
            problems.append("%s: text outside canvas: %r" %
                            (name, t.get_text()[:40]))

    pairs = [(a, b) for i, a in enumerate(ts) for b in ts[i + 1:]]
    for a, b in pairs:
        ea, eb = _ext(a, r), _ext(b, r)
        if ea is None or eb is None:
            continue
        inter = ea.intersection(eb.x0, eb.y0, eb.x1, eb.y1)
        if inter is not None and inter.width > 1.5 and inter.height > 1.5:
            problems.append("%s: text overlap %r <-> %r (%.0fx%.0f px)" %
                            (name, a.get_text()[:26], b.get_text()[:26],
                             inter.width, inter.height))

    for t in ts:
        if str(t.get_color()).lower() in ("white", "#ffffff", "w"):
            continue                      # white in-bar labels are intentional
        e = _ext(t, r)
        if e is None:
            continue
        for p in _rects(fig):
            if getattr(p, "_is_legend_patch", False):
                continue
            ep = _ext(p, r)
            if ep is None:
                continue
            inter = e.intersection(ep.x0, ep.y0, ep.x1, ep.y1)
            if inter is not None and inter.width > 2 and inter.height > 2:
                problems.append("%s: text on bar %r <-> %r (%.0fx%.0f px)" %
                                (name, t.get_text()[:26],
                                 str(p.get_facecolor())[:22],
                                 inter.width, inter.height))
    return _real_save(fig, path)


figstyle.save = qa

import make_figs      # noqa: E402
import make_fig5      # noqa: E402
import make_fig6      # noqa: E402

print("\n\n############ QA SUMMARY ############")
if problems:
    print("%d potential geometry problems:" % len(problems))
    for p in problems:
        print("  -", p)
else:
    print("no geometry problems detected")
