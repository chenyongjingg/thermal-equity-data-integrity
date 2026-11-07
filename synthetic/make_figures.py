#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate Figures 1-3 for the manuscript from simulation outputs.

Figure specification
--------------------
Target journal: MDPI *Forests* (single column, text width 17.4 cm = 6.85 in).
MDPI house style governs: preferably >= 600 dpi raster, legible sans-serif type, no
chartjunk. The Nature-derived sizes requested by the pipeline (8 pt bold panel
labels, 7 pt axis titles, 6 pt tick labels, 89/183 mm widths) are applied where
they do not conflict with MDPI; where they do, MDPI wins and the deviation is
recorded in pipeline/04_figures.md.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

TEXT_WIDTH_IN = 6.85          # 17.4 cm, MDPI text width

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 7,
    "axes.titlesize": 8,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 600,
    "svg.fonttype": "none",   # keep text as text in the SVG for editing
})


def save_both(fig, path):
    """Write a 600 dpi PNG (MDPI: preferably >= 600 dpi) and a vector SVG."""
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    fig.savefig(path.rsplit(".", 1)[0] + ".svg", bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------------
# Figure 1: three-layer compound system
# ----------------------------------------------------------------------
def figure1(path):
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN, 4.9))
    ax.set_xlim(0, 10); ax.set_ylim(0.7, 7.1); ax.axis("off")

    layers = [
        (5.45, "Social layer", "#f2e6d9",
         "Illicit data economy (black market)\n  • modular supply chain\n  • enforcement arbitrage\nGovernance actors  |  community verification"),
        (3.30, "Digital layer", "#dce9f5",
         "Remote sensing  •  sensors  •  human-activity data\n        ↓  AI training / inference\n   heat model  →  priority map"),
        (1.15, "Ecological layer", "#dcefd8",
         "UHI diagnosis  →  green-space allocation\n      →  heat exposure  →  health outcomes"),
    ]
    for y, title, colour, body in layers:
        box = FancyBboxPatch((0.95, y), 8.1, 1.35, boxstyle="round,pad=0.05",
                             linewidth=1.0, edgecolor="#555555", facecolor=colour)
        ax.add_patch(box)
        ax.text(1.15, y + 1.12, title, fontsize=8, fontweight="bold", va="center")
        ax.text(1.22, y + 0.55, body, fontsize=6.8, va="center", linespacing=1.4)

    def arrow(x, y0, y1, text, colour="#b03a2e", side="right"):
        ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>",
                                     mutation_scale=11, linewidth=1.2, color=colour))
        ty = (y0 + y1) / 2
        if side == "right":
            ax.text(x - 0.18, ty, text, fontsize=6.2, color=colour,
                    va="center", ha="right")
        else:
            ax.text(x + 0.18, ty, text, fontsize=6.2, color=colour,
                    va="center", ha="left")

    arrow(9.35, 5.42, 4.68, "poisoned inputs")
    arrow(9.35, 3.27, 2.53, "distorted outputs")
    arrow(0.55, 2.53, 3.27, "allocation feedback", colour="#2e6da4", side="left")
    arrow(0.55, 4.68, 5.42, "demand signal", colour="#2e6da4", side="left")

    fig.tight_layout()
    save_both(fig, path)


# ----------------------------------------------------------------------
# Figure 2: transmission chain with observable indicators
# ----------------------------------------------------------------------
def figure2(path):
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN, 3.2))
    ax.set_xlim(0.1, 9.95); ax.set_ylim(0.82, 3.28); ax.axis("off")

    boxes = [
        (0.25, "1. Data\npoisoning", "anomaly rate;\nprovenance\nfailure rate", "#f6dcd8"),
        (2.85, "2. Model\nbias", "spatial clustering\nof residuals", "#fbe8cc"),
        (5.45, "3. Investment\nmisallocation", "priority-rank\nreversal rate", "#e3e8f4"),
        (8.05, "4. Thermal\ninequity", "coverage gap ×\nheat under-\nestimation", "#dfe9dd"),
    ]
    for x, title, indicator, colour in boxes:
        box = FancyBboxPatch((x, 1.55), 1.75, 1.55, boxstyle="round,pad=0.05",
                             linewidth=1.0, edgecolor="#555555", facecolor=colour)
        ax.add_patch(box)
        ax.text(x + 0.875, 2.72, title, fontsize=8, fontweight="bold",
                ha="center", va="center", linespacing=1.3)
        ax.text(x + 0.875, 1.98, indicator, fontsize=6.6, ha="center",
                va="center", style="italic", color="#333333", linespacing=1.35)

    for x in (2.02, 4.62, 7.22):
        ax.add_patch(FancyArrowPatch((x, 2.32), (x + 0.80, 2.32),
                                     arrowstyle="-|>", mutation_scale=11,
                                     linewidth=1.1, color="#444444"))

    ax.text(5.0, 1.02, "Each arrow is a testable link; each italic line is a signal a planning agency can monitor.",
            fontsize=6.6, ha="center", color="#444444")
    fig.tight_layout()
    save_both(fig, path)


# ----------------------------------------------------------------------
# Figure 3: simulation results
# ----------------------------------------------------------------------
def figure3(summary_path, baseline_path, path):
    s = pd.read_csv(summary_path)
    b = pd.read_csv(baseline_path, index_col=0)

    fig, axes = plt.subplots(1, 3, figsize=(TEXT_WIDTH_IN, 2.6))
    colours = {"targeted": "#b03a2e", "random": "#2e6da4"}
    labels = {"targeted": "Directional poisoning\n(low-income labels)",
              "random": "Random poisoning\n(negative control)"}

    for mode in ("targeted", "random"):
        d = s[s["mode"] == mode].sort_values("contamination")
        x = d["contamination"] * 100
        axes[0].errorbar(x, d["top_reversal_mean"] * 100, yerr=d["top_reversal_sd"] * 100,
                         marker="o", markersize=3.2, capsize=2.2, linewidth=1.1,
                         color=colours[mode], label=labels[mode])
        axes[1].errorbar(x, d["low_share_top_mean"] * 100, yerr=d["low_share_top_sd"] * 100,
                         marker="o", markersize=3.2, capsize=2.2, linewidth=1.1,
                         color=colours[mode], label=labels[mode])
        axes[2].errorbar(x, d["mean_pct_low_mean"], yerr=d["mean_pct_low_sd"],
                         marker="o", markersize=3.2, capsize=2.2, linewidth=1.1,
                         color=colours[mode], label=labels[mode])

    base_low = b.loc["clean_low_share_top", "mean"] * 100
    base_pct = b.loc["clean_mean_pct_low", "mean"]
    axes[1].axhline(base_low, ls=":", lw=0.9, color="#666666")
    axes[2].axhline(base_pct, ls=":", lw=0.9, color="#666666")

    axes[0].set_ylabel("Top-quintile reversal (%)")
    axes[0].set_title("(a) Priority instability", fontsize=8, fontweight="bold")
    axes[1].set_ylabel("Low-income share of top quintile (%)")
    axes[1].set_title("(b) Distributional shift", fontsize=8, fontweight="bold")
    axes[2].set_ylabel("Mean priority percentile,\nlow-income areas")
    axes[2].set_title("(c) Rank position", fontsize=8, fontweight="bold")

    for ax in axes:
        ax.set_xlabel("Contaminated training labels (%)")
        ax.set_xticks([5, 10, 15])
        ax.tick_params(width=0.6, length=2.5)

    axes[0].legend(fontsize=5.8, frameon=False, loc="upper left",
                   handlelength=1.6, borderaxespad=0.2)
    fig.tight_layout(w_pad=1.6)
    save_both(fig, path)


if __name__ == "__main__":
    # Figure S1 of the paper: synthetic replication of the contamination effect.
    # Figures 1 and 2 are conceptual diagrams and live in the manuscript build.
    figure3("results_summary.csv", "results_clean_baseline.csv", "Figure_S1.png")
    print("Figure_S1.png written (png + svg)")
