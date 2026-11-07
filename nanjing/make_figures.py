#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figures 3 and 4 of the manuscript from a conditions.csv file.

Figure 3  effect at the main contamination rate, directional vs random
Figure 4  dose-response in contamination rate and in shift size

The script plots whatever rows the conditions file contains.  If a sweep is
absent (for example because only one shift size was run), the corresponding
panel is skipped rather than filled with made-up points.
"""

from __future__ import annotations

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TEXT_WIDTH_IN = 6.85          # 17.4 cm, MDPI text width
RED = "#b03a2e"
BLUE = "#2e6da4"
GREY = "#666666"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 7,
    "axes.labelsize": 7,
    "axes.titlesize": 8,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 600,
    "svg.fonttype": "none",
})


def save_both(fig, path):
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    fig.savefig(path.rsplit(".", 1)[0] + ".svg", bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--conditions", default="outputs/conditions.csv")
    p.add_argument("--outdir", default="outputs")
    args = p.parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)

    d = pd.read_csv(args.conditions)
    clean = d[d.condition == "clean"].iloc[0]
    main = d[(d.delta_t == d.delta_t.mode().iloc[0])]
    dir_main = main[main.condition == "directional"].sort_values("contamination_pct")
    rnd_main = main[main.condition == "random"].sort_values("contamination_pct")

    # ---- Figure 3: one rate, two conditions -------------------------------
    if len(dir_main) and len(rnd_main):
        rate = dir_main.contamination_pct.iloc[len(dir_main) // 2]
        a = dir_main[dir_main.contamination_pct == rate].iloc[0]
        b = rnd_main[rnd_main.contamination_pct == rate].iloc[0]
        fig, axes = plt.subplots(1, 2, figsize=(TEXT_WIDTH_IN, 2.5))
        ax = axes[0]
        bars = ax.bar([0, 1], [a.dropout_pct, b.dropout_pct], width=0.55,
                      color=[RED, BLUE], edgecolor="black", linewidth=0.5)
        for bar, v in zip(bars, [a.dropout_pct, b.dropout_pct]):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.2, f"{v:.1f}",
                    ha="center", fontsize=6.5)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Directional", "Random\n(control)"])
        ax.set_ylabel("Vulnerable cells removed\nfrom top decile (%)")
        ax.set_ylim(0, max(a.dropout_pct, b.dropout_pct) * 1.25)
        ax.set_title(f"(a) Rate = {rate:.0f}%", fontsize=8, fontweight="bold", loc="left")
        ax.tick_params(width=0.6, length=2.5)

        ax = axes[1]
        vals = [clean.spearman_rho, a.spearman_rho, b.spearman_rho]
        bars = ax.bar([0, 1, 2], vals, width=0.55, color=[GREY, RED, BLUE],
                      edgecolor="black", linewidth=0.5)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.012, f"{v:.2f}",
                    ha="center", fontsize=6.5)
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["Clean", f"Directional\n{rate:.0f}%", f"Random\n{rate:.0f}%"])
        ax.set_ylabel("Spearman $\\rho$:\npriority vs. vulnerability")
        ax.set_ylim(0, max(vals) * 1.25)
        ax.set_title("(b) Coupling of priority to need", fontsize=8,
                     fontweight="bold", loc="left")
        ax.tick_params(width=0.6, length=2.5)
        fig.tight_layout(w_pad=1.8)
        save_both(fig, os.path.join(args.outdir, "Figure_3.png"))

    # ---- Figure 4: dose-response ------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(TEXT_WIDTH_IN, 2.4))
    ax = axes[0]
    if len(dir_main):
        ax.plot(dir_main.contamination_pct, dir_main.dropout_pct, marker="o",
                markersize=3.4, linewidth=1.2, color=RED, label="Directional")
    if len(rnd_main):
        ax.plot(rnd_main.contamination_pct, rnd_main.dropout_pct, marker="s",
                markersize=3.4, linewidth=1.2, color=BLUE, label="Random (control)")
    ax.set_xlabel("Contaminated training labels (%)")
    ax.set_ylabel("Vulnerable cells removed\nfrom top decile (%)")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left", handlelength=1.6)
    ax.set_title("(a) Dose-response", fontsize=8, fontweight="bold", loc="left")
    ax.tick_params(width=0.6, length=2.5)

    ax = axes[1]
    if len(dir_main):
        ax.plot(dir_main.contamination_pct, dir_main.jaccard, marker="o",
                markersize=3.4, linewidth=1.2, color=RED, label="Directional")
    if len(rnd_main):
        ax.plot(rnd_main.contamination_pct, rnd_main.jaccard, marker="s",
                markersize=3.4, linewidth=1.2, color=BLUE, label="Random (control)")
    ax.set_xlabel("Contaminated training labels (%)")
    ax.set_ylabel("Jaccard overlap with\nclean top decile")
    ax.set_ylim(0.0, 1.0)
    ax.legend(frameon=False, loc="lower left", handlelength=1.6)
    ax.set_title("(b) Stability of the list", fontsize=8, fontweight="bold", loc="left")
    ax.tick_params(width=0.6, length=2.5)

    # shift-size sweep: directional rows at one contamination rate, all shifts
    ax = axes[2]
    main_delta = d.delta_t.mode().iloc[0]
    shifted = d[(d.condition == "directional") & (d.delta_t != main_delta)]
    sweep = d[(d.condition == "directional")].copy()
    if len(shifted):
        sweep_rate = shifted.contamination_pct.mode().iloc[0]
        sweep = sweep[sweep.contamination_pct == sweep_rate]
    sweep = sweep.sort_values("delta_t")
    if len(sweep) > 1:
        ax.plot(sweep.delta_t, sweep.dropout_pct, marker="o", markersize=3.4,
                linewidth=1.2, color=RED, label="Removed (left)")
        ax.set_xlabel("Downward shift $\\Delta T$ (°C)")
        ax.set_ylabel("Vulnerable cells removed\nfrom top decile (%)")
        ax.set_ylim(bottom=0)
        ax2 = ax.twinx()
        ax2.plot(sweep.delta_t, sweep.spearman_rho, marker="^", markersize=3.4,
                 linewidth=1.0, linestyle="--", color=GREY,
                 label="$\\rho$ (right)")
        ax2.set_ylabel("Spearman $\\rho$", color=GREY)
        ax2.tick_params(axis="y", colors=GREY, width=0.6, length=2.5)
        ax2.spines["right"].set_visible(True)
        ax2.spines["right"].set_color(GREY)
        ax2.spines["top"].set_visible(False)
        ax2.set_ylim(0, 1)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left",
                  handlelength=1.8)
        ax.set_title("(c) Shift size", fontsize=8, fontweight="bold", loc="left")
        ax.tick_params(width=0.6, length=2.5)
    fig.tight_layout(w_pad=2.0)
    save_both(fig, os.path.join(args.outdir, "Figure_4.png"))

    print(f"figures written to {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
