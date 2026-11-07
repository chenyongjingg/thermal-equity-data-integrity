#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sensitivity of the Nanjing result to the three free design choices.

The main experiment fixes a 1-km grid, a random forest with seed 7, a vulnerable
set defined by the 70th population percentile and the median NDVI, and a
planting budget of the clean top decile.  Each of those is a choice, not a
property of the city.  This driver reruns the same contamination protocol with
one choice moved at a time:

  res500 / res2000      grid resolution, everything else fixed
  seed13 / seed21       estimator seed and label-draw seed, 1 km
  pop60_ndvi25          looser vulnerable set
  pop80_ndvi75          stricter vulnerable set
  top5 / top20          planting budget of the top 5% or top 20% of cells

Outputs go to ``outputs/sens_<tag>/``; the 1-km grid is rebuilt for every tag so
that a tag cannot inherit cells from a different mask.

    python run_sensitivity.py --raw ../data/raw --out outputs --tags res500,seed13
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BBOX = ["118.70", "31.92", "119.20", "32.22"]
SCENE = "LC08_L2SP_120038_20210801_02_T1"

# tag: (resolution_m, seed, pop_percentile, ndvi_quantile, top_fraction)
CONFIGS = {
    "res500":      (500.0, 7, 70.0, 0.5, 0.10),
    "res2000":     (2000.0, 7, 70.0, 0.5, 0.10),
    "seed13":      (1000.0, 13, 70.0, 0.5, 0.10),
    "seed21":      (1000.0, 21, 70.0, 0.5, 0.10),
    "pop60_ndvi25": (1000.0, 7, 60.0, 0.25, 0.10),
    "pop80_ndvi75": (1000.0, 7, 80.0, 0.75, 0.10),
    "top5":        (1000.0, 7, 70.0, 0.5, 0.05),
    "top20":       (1000.0, 7, 70.0, 0.5, 0.20),
}


def run(cmd):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join("..", "data", "raw"))
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--tags", default=",".join(CONFIGS))
    ap.add_argument("--repeats", type=int, default=30)
    args = ap.parse_args(argv)

    for tag in [t.strip() for t in args.tags.split(",") if t.strip()]:
        if tag not in CONFIGS:
            raise SystemExit("unknown tag {!r}; known: {}".format(
                tag, ", ".join(CONFIGS)))
        res, seed, pop_pct, ndvi_q, top_frac = CONFIGS[tag]
        cdir = os.path.join(args.out, "sens_" + tag)
        os.makedirs(cdir, exist_ok=True)
        print("\n== {}  res={} seed={} pop_p={} ndvi_q={} top_f={}".format(
            tag, res, seed, pop_pct, ndvi_q, top_frac), flush=True)

        run([sys.executable, os.path.join(HERE, "build_grid.py"),
             "--lst", os.path.join(args.raw, SCENE + "__ST_B10.tif"),
             "--red", os.path.join(args.raw, SCENE + "__SR_B4.tif"),
             "--nir", os.path.join(args.raw, SCENE + "__SR_B5.tif"),
             "--qa", os.path.join(args.raw, SCENE + "__QA_PIXEL.tif"),
             "--max-cloud-frac", "0.10",
             "--pop", os.path.join(args.raw, "GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30.tif"),
             "--built", os.path.join(args.raw, "GHS_BUILT_S_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30.tif"),
             "--min-built", "0.05",
             "--sr-scale", "2.75e-05", "--sr-offset", "-0.2", "--utm-zone", "50",
             "--bbox", *BBOX, "--res", str(res),
             "--out", os.path.join(cdir, "cells.csv"),
             "--meta", os.path.join(cdir, "grid_metadata.json")])

        run([sys.executable, os.path.join(HERE, "model_and_poison.py"),
             "--cells", os.path.join(cdir, "cells.csv"),
             "--out", os.path.join(cdir, "conditions.csv"),
             "--meta", os.path.join(cdir, "run_metadata.json"),
             "--contamination", "0.05", "0.10", "0.15",
             "--delta", "1", "2", "3", "--main-delta", "2", "--sweep-rate", "0.10",
             "--trees", "300", "--seed", str(seed), "--repeats", str(args.repeats),
             "--priority", "heat", "--model", "rf",
             "--pop-percentile", str(pop_pct), "--ndvi-quantile", str(ndvi_q),
             "--top-fraction", str(top_frac)])

    print("\nrun summarise_sensitivity.py to build the comparison table")
    return 0


if __name__ == "__main__":
    sys.exit(main())
