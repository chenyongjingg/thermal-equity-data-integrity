#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Collapse the per-date condition tables into one comparison table.

Reads ``outputs/date_*/conditions.csv`` (written by ``run_dates.py``) and writes
``outputs/date_summary.csv``: one row per Landsat date with the scene metadata,
the clean-model composition, the directional and random drop-out at each
contamination rate and, where present, the placebo arm at 10%.  No value is
recomputed or rounded differently from the source tables; the script only
selects rows, so that a typo cannot enter the comparison.

    python summarise_dates.py --out outputs --dst outputs/date_summary.csv
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
                    help="output path (default <out>/date_summary.csv)")
    args = ap.parse_args(argv)

    rows = []
    for ddir in sorted(glob.glob(os.path.join(args.out, "date_*"))):
        if not os.path.isdir(ddir):
            continue
        cond = os.path.join(ddir, "conditions.csv")
        meta = os.path.join(ddir, "run_metadata.json")
        if not (os.path.exists(cond) and os.path.exists(meta)):
            continue
        d = pd.read_csv(cond)
        # run_dates.py writes the placebo arm to its own file so that the draws
        # behind the main conditions are untouched; read it beside them here
        pcond = os.path.join(ddir, "placebo.csv")
        if os.path.exists(pcond):
            pl = pd.read_csv(pcond)
            if len(pl):
                d = pd.concat([d, pl.loc[:, pl.columns.isin(d.columns)]], ignore_index=True)
        with open(meta, encoding="utf-8") as fh:
            m = json.load(fh)
        meta_date = {}
        dpath = os.path.join(ddir, "date.json")
        if os.path.exists(dpath):
            with open(dpath, encoding="utf-8") as fh:
                meta_date = json.load(fh)
        clean = d[d.condition == "clean"].iloc[0]
        rec = dict(date=meta_date.get("date", os.path.basename(ddir)[5:]),
                   scene=meta_date.get("scene", ""),
                   scene_datetime=(meta_date.get("scene_datetime") or "")[:10],
                   scene_cloud_pct=meta_date.get("scene_cloud_pct", ""),
                   cells=m["cells"], vulnerable=m["vulnerable_cells"],
                   vulnerable_share_top_pct=m["vulnerable_share_of_clean_top_pct"],
                   rho_clean=clean["spearman_rho"])
        for cond_name, tag in (("directional", "dir"), ("random", "rnd"),
                               ("placebo", "plc")):
            for rate in (5.0, 10.0, 15.0):
                sel = d[(d.condition == cond_name) &
                        (d.contamination_pct == rate) &
                        (d.delta_t == args.main_delta)]
                if len(sel):
                    r = sel.iloc[0]
                    rec["{}_drop{}".format(tag, int(rate))] = r["dropout_pct"]
                    rec["{}_jacc{}".format(tag, int(rate))] = r["jaccard"]
                    rec["{}_rho{}".format(tag, int(rate))] = r["spearman_rho"]
        d10 = rec.get("dir_drop10")
        r10 = rec.get("rnd_drop10")
        if d10 is not None and r10 is not None:
            rec["gap_10"] = round(d10 - r10, 1)
            rec["ratio_10"] = round(d10 / r10, 1) if r10 else float("inf")
        rows.append(rec)

    if not rows:
        raise SystemExit("no date_* directories with conditions.csv under " + args.out)
    out = pd.DataFrame(rows).sort_values("date")
    dst = args.dst or os.path.join(args.out, "date_summary.csv")
    out.to_csv(dst, index=False, lineterminator="\n")
    print(out.to_string(index=False))
    print("\nwrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
