# -*- coding: utf-8 -*-
"""Shared figure style for the paper's six figures.

Centralises, for make_figs.py / make_fig5.py / make_fig6.py:

  * one set of matplotlib rcParams (DejaVu Sans, no top/right spines, 300 dpi,
    tight bbox, white background);
  * one palette, so the two-tool comparison uses the same pair of colours in
    every figure;
  * `save()`, which writes the PNG at a fixed canvas width (6.30 in at 300 dpi,
    i.e. exactly 1890 px) so the figures can be inserted into the Word
    manuscript at 6.3 in with no scaling, and flattens the RGBA framebuffer to
    RGB because several submission systems flag a redundant alpha channel.

Canvas-width calibration. `bbox_inches="tight"` crops the figure to its drawn
content, so the saved width is generally not `figsize[0]`. `save()` therefore
renders once, measures the tight width, rescales the figure (font sizes stay
fixed in points, so no text can fall below the journal minimum), and re-renders
until the saved width matches the target.
"""
import io
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

DPI = 300                     # journal minimum for halftone/colour figures
FIG_WIDTH_IN = 6.30           # manuscript insertion width -> 1890 px at 300 dpi
MIN_FONT_PT = 7.0             # smallest text any figure may use
PAD_IN = 0.05                 # tight-bbox padding, in inches (keeps ink
                             # away from the border after width calibration)

# --- the single palette -------------------------------------------------
TOOL_A = "#1b6ca8"            # execute_bash / observed / first series
TOOL_B = "#c0392b"            # str_replace_editor / binomial / second series
HATCH_B = "//"                # redundant encoding: keeps the pair readable
                             # in a black-and-white print (gray 91 vs 96)
NEUTRAL = "#8c8c8c"           # pooled / reference bars
ACCENT = "#2ca02c"            # single-series plots
LIGHT = "0.75"                # null histograms
GRID = "#7f8c8d"              # reference lines
RAMP = ["#1b6ca8", "#2e86c1", "#5dade2", "#85c1e9"]   # sequential (robustness)

RCPARAMS = {
    "font.family": "DejaVu Sans",
    "font.size": 8.0,
    "axes.titlesize": 8.5,
    "axes.labelsize": 8.0,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
}


def apply():
    """Install the shared rcParams."""
    plt.rcParams.update(RCPARAMS)


def _tight_render(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
                pad_inches=PAD_IN, facecolor="white")
    buf.seek(0)
    return Image.open(buf)


def save(fig, path, width_in=FIG_WIDTH_IN):
    """Write `fig` to `path` at exactly `width_in` inches, flattened to RGB.

    Returns (path, (width_px, height_px)) of the written PNG.
    """
    target = int(round(width_in * DPI))
    for _ in range(3):                     # width calibration, converges in 2
        w = _tight_render(fig).size[0]
        if abs(w - target) <= 2:
            break
        fw, fh = fig.get_size_inches()
        fig.set_size_inches(fw * target / w, fh * target / w)

    im = _tight_render(fig)
    if im.mode != "RGB":                   # flatten RGBA -> RGB on white
        im = im.convert("RGB")
    if im.size[0] != target:               # fallback: exact pixel resize
        ratio = target / im.size[0]
        im = im.resize((target, int(round(im.size[1] * ratio))), Image.LANCZOS)

    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    im.save(path, dpi=(DPI, DPI))
    plt.close(fig)
    return path, im.size
