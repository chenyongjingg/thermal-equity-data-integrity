#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Collapse the per-estimator condition tables into one comparison table.

``model_and_poison.py --model {rf,gbm,ridge,knn}`` writes one condition table
per estimator.  The paper's main experiment uses a random forest; this script
puts the other three side by side so that the claim does not rest on the choice
of learner.  Values are copied from the source tables, never recomputed, so a
rounding typo cannot enter the comparison.

    python summarise_models.py --out outputs --dst outputs/model_summary.csv
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import pandas as pd

MODELS = ["rf", "gbm", "ridge", "knn"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--main-delta", type=float, default=2.0)
    ap.add_argument("--dst", default=None)
    args = ap.parse_args(argv)

    rows = []
    for model in MODELS:
        cond = os.path.join(args.out, "model_{}.csv".format(model))
        meta = os.path.join(args.out, "model_{}.json".format(model))
        if not os.path.exists(cond):
            print("skipping {} (no {})".format(model, cond), file=sys.stderr)
            continue
        d = pd.read_csv(cond)
        m = {}
        if os.path.exists(meta):
            with open(meta, encoding="utf-8") as fh:
                m = json.load(fh)
        clean = d[d.condition == "clean"].iloc[0]
        rec = dict(model=model, cells=m.get("cells"), vulnerable=m.get("vulnerable_cells"),
                   rho_clean=clean["spearman_rho"])
        for cond_name, tag in (("directional", "dir"), ("random", "rnd")):
            for rate in (5.0, 10.0, 15.0):
                sel = d[(d.condition == cond_name) &
                        (d.contamination_pct == rate) &
                        (d.delta_t == args.main_delta)]
                if len(sel):
                    r = sel.iloc[0]
                    rec["{}_drop{}".format(tag, int(rate))] = r["dropout_pct"]
                    rec["{}_jacc{}".format(tag, int(rate))] = r["jaccard"]
                    rec["{}_bias{}".format(tag, int(rate))] = r["bias_vulnerable_c"]
        d10, r10 = rec.get("dir_drop10"), rec.get("rnd_drop10")
        if d10 is not None and r10:
            rec["ratio_10"] = round(d10 / r10, 1)
        rows.append(rec)

    if not rows:
        raise SystemExit("no model_*.csv under " + args.out)
    out = pd.DataFrame(rows)
    dst = args.dst or os.path.join(args.out, "model_summary.csv")
    out.to_csv(dst, index=False, lineterminator="\n")
    print(out.to_string(index=False))
    print("\nwrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
