#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Collapse the per-city condition tables into one comparison table.

Reads ``outputs/city_*/conditions.csv`` (written by ``run_cities.py``) and
writes ``outputs/city_summary.csv``: one row per city with the clean-model
composition and the directional / random drop-out at each contamination rate.
No value is recomputed or rounded differently from the source tables; the
script only selects rows so that a typo cannot enter the comparison.
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
    ap.add_argument("--dst", default=None,
                    help="output path (default <out>/city_summary.csv)")
    args = ap.parse_args(argv)

    rows = []
    for cdir in sorted(glob.glob(os.path.join(args.out, "city_*"))):
        if not os.path.isdir(cdir):      # city_summary.csv matches city_* too
            continue
        cond = os.path.join(cdir, "conditions.csv")
        meta = os.path.join(cdir, "run_metadata.json")
        city = os.path.join(cdir, "city.json")
        if not (os.path.exists(cond) and os.path.exists(meta)):
            continue
        d = pd.read_csv(cond)
        with open(meta, encoding="utf-8") as fh:
            m = json.load(fh)
        c = {}
        if os.path.exists(city):
            with open(city, encoding="utf-8") as fh:
                c = json.load(fh)
        clean = d[d.condition == "clean"].iloc[0]
        rec = dict(city=c.get("city", os.path.basename(cdir)[5:]),
                   scene=c.get("scene", ""),
                   scene_cloud_pct=c.get("scene_cloud_pct", ""),
                   utm_zone=c.get("utm_zone", ""),
                   cells=m["cells"], vulnerable=m["vulnerable_cells"],
                   vulnerable_share_top_pct=m["vulnerable_share_of_clean_top_pct"],
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
                    rec["{}_rho{}".format(tag, int(rate))] = r["spearman_rho"]
                    rec["{}_bias{}".format(tag, int(rate))] = r["bias_vulnerable_c"]
        d10 = rec.get("dir_drop10")
        r10 = rec.get("rnd_drop10")
        if d10 is not None and r10 is not None:
            rec["ratio_10"] = round(d10 / r10, 1) if r10 else float("inf")
        rows.append(rec)

    if not rows:
        raise SystemExit("no city_* directories with conditions.csv under " + args.out)
    out = pd.DataFrame(rows)
    dst = args.dst or os.path.join(args.out, "city_summary.csv")
    out.to_csv(dst, index=False, lineterminator="\n")
    print(out.to_string(index=False))
    print("\nwrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
