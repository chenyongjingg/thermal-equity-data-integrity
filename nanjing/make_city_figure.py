#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figure S2: the Nanjing asymmetry across cities.

One row per city, sorted by the drop-out rate under directional contamination.
Each city contributes two markers at the same contamination rate and shift: the
directional arm and the random control.  Horizontal whiskers are 95% intervals
over the 30 contaminated label draws in ``city_<name>/draws.csv``; a city whose
draws are missing is drawn as a point without an interval rather than with a
guessed one.

    python make_city_figure.py --outdir results
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

TEXT_WIDTH_IN = 6.85          # 17.4 cm, MDPI text width
RED = "#b03a2e"
BLUE = "#2e6da4"

DISPLAY = {"xian": "Xi'an"}   # pinyin without the apostrophe in the directory name

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
    "svg.hashsalt": "thermal-equity",   # stable element ids across runs
})


def ci95(x):
    x = np.asarray(x, dtype="float64")
    m = float(np.mean(x))
    if len(x) < 2:
        return m, m, m
    half = stats.t.ppf(0.975, len(x) - 1) * np.std(x, ddof=1) / np.sqrt(len(x))
    return m, m - half, m + half


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--rate", type=float, default=10.0)
    ap.add_argument("--delta", type=float, default=2.0)
    args = ap.parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)

    rows = []
    for cdir in sorted(glob.glob(os.path.join(args.out, "city_*"))):
        if not os.path.isdir(cdir):      # city_summary.csv matches city_* too
            continue
        name = os.path.basename(cdir)[len("city_"):]
        draws = os.path.join(cdir, "draws.csv")
        if not os.path.exists(draws):
            print("no draws for {}, skipping".format(name), file=sys.stderr)
            continue
        d = pd.read_csv(draws)
        sel = d[(np.isclose(d.contamination_pct, args.rate)) &
                (np.isclose(d.delta_t, args.delta))]
        rec = dict(city=name)
        for cond, tag in (("directional", "dir"), ("random", "rnd")):
            v = sel[sel.condition == cond]["dropout_pct"]
            m, lo, hi = ci95(v)
            rec.update({tag: m, tag + "_lo": lo, tag + "_hi": hi, tag + "_n": len(v)})
        rows.append(rec)

    if not rows:
        raise SystemExit("no city_*/draws.csv under " + args.out)
    t = pd.DataFrame(rows).sort_values("dir", ascending=True).reset_index(drop=True)
    t.to_csv(os.path.join(args.outdir, "Figure_S2_source.csv"), index=False,
             lineterminator="\n")

    fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN, 3.4))
    y = np.arange(len(t))
    for i, r in t.iterrows():
        ax.plot([r.rnd, r.dir], [i, i], color="#999999", linewidth=0.8, zorder=1)
    ax.errorbar(t.rnd, y, xerr=[t.rnd - t.rnd_lo, t.rnd_hi - t.rnd],
                fmt="o", color=BLUE, markersize=3.2, elinewidth=0.7,
                capsize=1.5, label="Random (control)", zorder=3)
    ax.errorbar(t.dir, y, xerr=[t.dir - t.dir_lo, t.dir_hi - t.dir],
                fmt="o", color=RED, markersize=3.2, elinewidth=0.7,
                capsize=1.5, label="Directional", zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels([DISPLAY.get(c, c.capitalize()) for c in t.city])
    ax.set_xlabel("Vulnerable cells removed from the top decile (%), "
                  "{}% contamination at ΔT = {:g} °C".format(
                      "{:g}".format(args.rate), args.delta))
    ax.set_xlim(left=0)
    ax.legend(frameon=False, loc="lower right")
    ax.axvline(0, color="black", linewidth=0.4)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(args.outdir, "Figure_S2." + ext),
                    bbox_inches="tight", facecolor="white",
                    metadata=None if ext == "png" else {"Date": None})
    # matplotlib writes the SVG in text mode, so Windows gives CRLF while the
    # repository stores LF; normalise so the file is not "modified" on checkout
    with open(os.path.join(args.outdir, "Figure_S2.svg"), "rb") as fh:
        data = fh.read()
    if b"\r\n" in data:
        with open(os.path.join(args.outdir, "Figure_S2.svg"), "wb") as fh:
            fh.write(data.replace(b"\r\n", b"\n"))
    plt.close(fig)

    print(t[["city", "dir", "dir_lo", "dir_hi", "rnd", "rnd_lo", "rnd_hi"]]
          .to_string(index=False))
    print("\nwrote", os.path.join(args.outdir, "Figure_S2.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
