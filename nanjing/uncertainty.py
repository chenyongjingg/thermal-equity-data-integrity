#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Confidence intervals and directional-minus-random contrasts from draws.

``model_and_poison.py --draws-out`` writes one row per contamination draw.  The
paper reports the mean over draws; this script supplies what a mean alone does
not: a 95% interval for each condition and a 95% interval for the difference
between the directional arm and the random control at the same rate and shift.

Intervals use the Student t quantile on the draw-to-draw standard deviation
(n = 30 in the reported run).  The contrast is a Welch interval, because the
two arms are separate draws and their variances need not be equal.  Nothing is
pooled across conditions, and no draw is dropped.

    python uncertainty.py --draws outputs/draws_rf.csv --out results/uncertainty_nanjing.csv
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

METRICS = ["dropout_pct", "jaccard", "spearman_rho", "bias_vulnerable_c"]


def mean_ci(x, level=0.95):
    x = np.asarray(x, dtype="float64")
    n = len(x)
    m = float(np.mean(x))
    sd = float(np.std(x, ddof=1)) if n > 1 else 0.0
    if n > 1:
        half = stats.t.ppf(0.5 + level / 2.0, n - 1) * sd / np.sqrt(n)
    else:
        half = 0.0
    return m, sd, m - half, m + half, n


def welch(a, b, level=0.95):
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    diff = float(np.mean(a) - np.mean(b))
    va, vb = np.var(a, ddof=1) / len(a), np.var(b, ddof=1) / len(b)
    se = float(np.sqrt(va + vb))
    if se == 0:
        return diff, 0.0, diff, diff, 1.0
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    crit = stats.t.ppf(0.5 + level / 2.0, df)
    p = 2 * stats.t.sf(abs(diff / se), df)
    return diff, se, diff - crit * se, diff + crit * se, p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--draws", nargs="+", required=True,
                    help="one or more draws.csv files (model column is honoured)")
    ap.add_argument("--out", default="outputs/uncertainty.csv")
    ap.add_argument("--contrasts-out", default=None,
                    help="default: <out stem>_contrasts.csv")
    ap.add_argument("--per-file", action="store_true",
                    help="treat each file as one group (e.g. one city), labelled "
                         "by its file name; otherwise rows are grouped by the "
                         "model column, which is right for draws_<model>.csv")
    args = ap.parse_args(argv)

    frames = []
    for p in args.draws:
        f = pd.read_csv(p)
        if args.per_file:
            label = os.path.splitext(os.path.basename(p))[0]
            if label == "draws":            # city_<name>/draws.csv
                label = os.path.basename(os.path.dirname(os.path.abspath(p)))
            for prefix in ("draws_", "city_"):
                if label.startswith(prefix):
                    label = label[len(prefix):]
            f["group"] = label
        frames.append(f)
    d = pd.concat(frames, ignore_index=True)
    if "group" not in d.columns:
        d["group"] = d.get("model", "rf")

    rows = []
    for (group, cond, rate, delta), g in d.groupby(
            ["group", "condition", "contamination_pct", "delta_t"], dropna=False):
        for metric in METRICS:
            m, sd, lo, hi, n = mean_ci(g[metric])
            rows.append(dict(group=group, condition=cond, contamination_pct=rate,
                             delta_t=delta, metric=metric, n=n, mean=round(m, 3),
                             sd=round(sd, 3), ci95_lo=round(lo, 3),
                             ci95_hi=round(hi, 3)))
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    out.to_csv(args.out, index=False, lineterminator="\n")

    # directional minus random at matching rate and shift (shift sweeps have no
    # random counterpart, so only the rate sweep appears here)
    con = []
    for (group, rate, delta), g in d.groupby(["group", "contamination_pct", "delta_t"]):
        a = g[g.condition == "directional"]
        b = g[g.condition == "random"]
        if not len(a) or not len(b):
            continue
        for metric in METRICS:
            diff, se, lo, hi, p = welch(a[metric], b[metric])
            con.append(dict(group=group, contamination_pct=rate, delta_t=delta,
                            metric=metric, n_dir=len(a), n_rnd=len(b),
                            diff=round(diff, 3), se=round(se, 3),
                            ci95_lo=round(lo, 3), ci95_hi=round(hi, 3),
                            # keep three significant figures as text: float()
                            # would round-trip as 2.5100000000000004e-27
                            p_welch="{:.3g}".format(p)))
    cdf = pd.DataFrame(con)
    cpath = args.contrasts_out or os.path.join(
        os.path.dirname(args.out), os.path.splitext(os.path.basename(args.out))[0] + "_contrasts.csv")
    cdf.to_csv(cpath, index=False, lineterminator="\n")

    show = cdf[cdf.metric == "dropout_pct"].sort_values(["group", "contamination_pct", "delta_t"])
    print(show.to_string(index=False))
    print("\nwrote {} and {}".format(args.out, cpath))
    return 0


if __name__ == "__main__":
    sys.exit(main())
