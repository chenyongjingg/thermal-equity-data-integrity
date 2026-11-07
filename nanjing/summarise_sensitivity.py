#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Collapse the sensitivity runs into one table.

Reads ``outputs/sens_*/conditions.csv`` written by ``run_sensitivity.py`` and
writes ``outputs/sensitivity_summary.csv``: for each design choice, the number
of cells, the size of the vulnerable set, and the directional / random drop-out
at the three contamination rates.  Values are copied from the source tables.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import pandas as pd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--main-delta", type=float, default=2.0)
    ap.add_argument("--dst", default=None)
    args = ap.parse_args(argv)

    rows = []
    for cdir in sorted(glob.glob(os.path.join(args.out, "sens_*"))):
        tag = os.path.basename(cdir)[len("sens_"):]
        cond = os.path.join(cdir, "conditions.csv")
        meta = os.path.join(cdir, "run_metadata.json")
        if not (os.path.exists(cond) and os.path.exists(meta)):
            print("skipping {} (incomplete)".format(tag), file=sys.stderr)
            continue
        d = pd.read_csv(cond)
        with open(meta, encoding="utf-8") as fh:
            m = json.load(fh)
        clean = d[d.condition == "clean"].iloc[0]
        rec = dict(tag=tag, cells=m["cells"], vulnerable=m["vulnerable_cells"],
                   top_fraction=m.get("top_fraction"),
                   rho_clean=clean["spearman_rho"])
        for cond_name, pre in (("directional", "dir"), ("random", "rnd")):
            for rate in (5.0, 10.0, 15.0):
                sel = d[(d.condition == cond_name) &
                        (d.contamination_pct == rate) &
                        (d.delta_t == args.main_delta)]
                if len(sel):
                    r = sel.iloc[0]
                    rec["{}_drop{}".format(pre, int(rate))] = r["dropout_pct"]
        d10, r10 = rec.get("dir_drop10"), rec.get("rnd_drop10")
        if d10 is not None and r10:
            rec["ratio_10"] = round(d10 / r10, 1)
        rows.append(rec)

    if not rows:
        raise SystemExit("no sens_* directories with conditions.csv under " + args.out)
    out = pd.DataFrame(rows)
    dst = args.dst or os.path.join(args.out, "sensitivity_summary.csv")
    out.to_csv(dst, index=False, lineterminator="\n")
    print(out.to_string(index=False))
    print("\nwrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
