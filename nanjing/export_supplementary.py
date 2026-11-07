#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Write the supplementary tables in the column names used in the paper.

The working tables under ``outputs/`` are wide and carry every rate and metric.
The supplementary tables keep the columns the manuscript refers to, with names
that read on their own, so a reader can open them without the code:

  Table_S2.csv  estimator families (rows: rf, gbm, ridge, knn)
  Table_S3.csv  cities (rows: nanjing + the seven replications)
  Table_S4.csv  design-choice sensitivity (resolution, seed, vulnerable set)
  Table_S5.csv  mean and 95% interval over the 30 draws, plus the
                directional-minus-random contrast

    python export_supplementary.py --out ../submission/supplementary
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd


def read_rows(path):
    if not os.path.exists(path):
        raise SystemExit("missing {} — run the pipeline first".format(path))
    return pd.read_csv(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="supplementary")
    ap.add_argument("--work", default="outputs")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    # ---- Table S2: estimator families ----------------------------------
    m = read_rows(os.path.join(args.work, "model_summary.csv"))
    s2 = pd.DataFrame({
        "estimator": m.model,
        "clean_rho": m.rho_clean,
        "dropout_5_directional": m.dir_drop5,
        "dropout_5_random": m.rnd_drop5,
        "dropout_10_directional": m.dir_drop10,
        "dropout_10_random": m.rnd_drop10,
        "dropout_15_directional": m.dir_drop15,
        "dropout_15_random": m.rnd_drop15,
        "jaccard_10_directional": m.dir_jacc10,
        "jaccard_10_random": m.rnd_jacc10,
        "bias_10_directional": m.dir_bias10,
        "bias_10_random": m.rnd_bias10,
    })
    s2.to_csv(os.path.join(args.out, "Table_S2.csv"), index=False,
              lineterminator="\n")

    # ---- Table S3: cities ----------------------------------------------
    c = read_rows(os.path.join(args.work, "city_summary.csv"))
    s3 = pd.DataFrame({
        "city": c.city,
        "landsat_scene": c.scene,
        "scene_cloud_pct": c.scene_cloud_pct,
        "cells": c.cells,
        "vulnerable_cells": c.vulnerable,
        "clean_rho": c.rho_clean,
        "dropout_10_directional": c.dir_drop10,
        "dropout_10_random": c.rnd_drop10,
        "jaccard_10_directional": c.dir_jacc10,
        "jaccard_10_random": c.rnd_jacc10,
    })
    s3.to_csv(os.path.join(args.out, "Table_S3.csv"), index=False,
              lineterminator="\n")

    # ---- Table S4: design choices --------------------------------------
    s = read_rows(os.path.join(args.work, "sensitivity_summary.csv"))
    s4 = pd.DataFrame({
        "variation": s.tag,
        "cells": s.cells,
        "vulnerable_cells": s.vulnerable,
        "planting_budget_share": s.top_fraction,
        "clean_rho": s.rho_clean,
        "dropout_5_directional": s.dir_drop5,
        "dropout_5_random": s.rnd_drop5,
        "dropout_10_directional": s.dir_drop10,
        "dropout_10_random": s.rnd_drop10,
        "dropout_15_directional": s.dir_drop15,
        "dropout_15_random": s.rnd_drop15,
    })
    s4.to_csv(os.path.join(args.out, "Table_S4.csv"), index=False,
              lineterminator="\n")

    # ---- Table S5: draw-level intervals --------------------------------
    # uncertainty.py writes the interval table and the contrast table
    # separately; the supplementary table puts them side by side so that the
    # directional row of every condition carries its difference from the
    # random control.  The contrast is blank on random rows, and on the shift
    # sweep, which has no random counterpart.
    u = read_rows(os.path.join(args.work, "uncertainty_nanjing.csv"))
    u = u.rename(columns={"group": "estimator"})
    cpath = os.path.join(args.work, "uncertainty_nanjing_contrasts.csv")
    if os.path.exists(cpath):
        k = read_rows(cpath).rename(columns={"group": "estimator"})
        k = k[["estimator", "contamination_pct", "delta_t", "metric",
               "diff", "ci95_lo", "ci95_hi", "p_welch"]].rename(columns={
                   "diff": "diff_vs_random",
                   "ci95_lo": "diff_ci95_lo", "ci95_hi": "diff_ci95_hi"})
        u = u.merge(k, on=["estimator", "contamination_pct", "delta_t", "metric"],
                    how="left")
        # the contrast is directional minus random; keep it on the directional
        # row only, so the table never shows the same number twice
        u.loc[u.condition != "directional",
              ["diff_vs_random", "diff_ci95_lo", "diff_ci95_hi", "p_welch"]] = float("nan")
    u.to_csv(os.path.join(args.out, "Table_S5.csv"), index=False,
             lineterminator="\n", na_rep="")

    for name in ("Table_S2.csv", "Table_S3.csv", "Table_S4.csv", "Table_S5.csv"):
        print("wrote", os.path.join(args.out, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
