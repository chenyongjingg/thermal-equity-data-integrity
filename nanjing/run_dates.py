#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Repeat the Nanjing specification on several dates of the same city.

The multi-city run changes the city and therefore the scene; this driver holds
the city fixed and changes only the date, so that scene date is separated from
city identity.  The bounding box, grid, masks, vulnerability definition,
estimator and contamination protocol are the ones used for the paper's main
table; only the Landsat acquisition changes.

    python run_dates.py --proxy http://127.0.0.1:7897
    python run_dates.py --dates 2021-05,2021-09 --skip-fetch

Each date writes ``outputs/date_<tag>/{cells.csv,conditions.csv,draws.csv,
placebo.csv,placebo_draws.csv,grid_metadata.json,run_metadata.json,date.json}``;
``summarise_dates.py`` collapses the condition tables into one comparison table.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from run_cities import CITIES, ensure_ghs, ghs_tile, run, utm_zone  # noqa: E402

BBOX = CITIES["nanjing"]

# tag -> (first day, last day) of the search window.  One window per month, so
# two dates cannot silently resolve to the same scene; the August window is the
# paper's main date and is run by rerun_all.sh, not here.
DATES = {
    "2021-05": ("2021-05-01", "2021-05-31"),
    "2021-09": ("2021-09-01", "2021-09-30"),
    "2021-10": ("2021-10-01", "2021-10-31"),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join("..", "data", "raw"))
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--dates", default=",".join(DATES))
    ap.add_argument("--max-cloud", type=float, default=40.0,
                    help="scene-level ceiling; the per-cell QA mask (<=10%% of a "
                         "cell's pixels flagged) still applies, so a cloudy scene "
                         "loses cells rather than precision")
    ap.add_argument("--min-built", default="0.05")
    ap.add_argument("--repeats", type=int, default=30)
    ap.add_argument("--priority", default="heat")
    ap.add_argument("--model", default="rf")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--skip-fetch", action="store_true",
                    help="use rasters already in --raw")
    args = ap.parse_args(argv)

    os.makedirs(args.raw, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)
    zone = utm_zone(BBOX)
    tile = ghs_tile(BBOX)
    ghs = ensure_ghs(args.raw, tile, args.proxy, BBOX)

    seen = []
    for tag in [d.strip() for d in args.dates.split(",") if d.strip()]:
        if tag not in DATES:
            raise SystemExit("unknown date {!r}; known: {}".format(tag, ", ".join(DATES)))
        start, end = DATES[tag]
        ddir = os.path.join(args.out, "date_" + tag)
        os.makedirs(ddir, exist_ok=True)
        # never mix a fresh grid with stale condition tables
        for stale in ("conditions.csv", "draws.csv", "run_metadata.json",
                      "date.json", "placebo.csv", "placebo_draws.csv"):
            p = os.path.join(ddir, stale)
            if os.path.exists(p):
                os.remove(p)
        print("\n== {}  {}..{}".format(tag, start, end), flush=True)

        if not args.skip_fetch:
            fetch = [sys.executable, os.path.join(HERE, "fetch_inputs.py"),
                     "--outdir", args.raw,
                     "--bbox", *[str(v) for v in BBOX],
                     "--start", start, "--end", end,
                     "--max-cloud", str(args.max_cloud), "--tag", tag]
            if args.proxy:
                fetch += ["--proxy", args.proxy]
            run(fetch)

        scene_path = os.path.join(args.raw, "scene_{}.json".format(tag))
        if not os.path.exists(scene_path):
            raise SystemExit("no scene metadata for {}; run without --skip-fetch".format(tag))
        with open(scene_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        if meta.get("id") in seen:
            raise SystemExit("date {} resolved to an already-used scene {}".format(tag, meta.get("id")))
        seen.append(meta.get("id"))

        prefix = os.path.join(args.raw, tag)
        run([sys.executable, os.path.join(HERE, "build_grid.py"),
             "--lst", prefix + "__ST_B10.tif", "--red", prefix + "__SR_B4.tif",
             "--nir", prefix + "__SR_B5.tif", "--qa", prefix + "__QA_PIXEL.tif",
             "--max-cloud-frac", "0.10",
             "--pop", ghs["GHS_POP"], "--built", ghs["GHS_BUILT_S"],
             "--min-built", args.min_built,
             "--sr-scale", "2.75e-05", "--sr-offset", "-0.2",
             "--utm-zone", str(zone),
             "--bbox", *[str(v) for v in BBOX], "--res", "1000",
             "--out", os.path.join(ddir, "cells.csv"),
             "--meta", os.path.join(ddir, "grid_metadata.json")])

        run([sys.executable, os.path.join(HERE, "model_and_poison.py"),
             "--cells", os.path.join(ddir, "cells.csv"),
             "--out", os.path.join(ddir, "conditions.csv"),
             "--meta", os.path.join(ddir, "run_metadata.json"),
             "--draws-out", os.path.join(ddir, "draws.csv"),
             "--placebo-out", os.path.join(ddir, "placebo.csv"),
             "--placebo-draws-out", os.path.join(ddir, "placebo_draws.csv"),
             "--contamination", "0.05", "0.10", "0.15",
             "--delta", "1", "2", "3", "--main-delta", "2", "--sweep-rate", "0.10",
             "--trees", "300", "--seed", "7", "--repeats", str(args.repeats),
             "--priority", args.priority, "--model", args.model])

        with open(os.path.join(ddir, "date.json"), "w", encoding="utf-8",
                  newline="\n") as fh:
            json.dump(dict(date=tag, bbox=list(BBOX), utm_zone=zone, ghs_tile=tile,
                           scene=meta.get("id"),
                           scene_cloud_pct=meta.get("cloud_cover_pct"),
                           scene_datetime=meta.get("datetime"),
                           min_built=float(args.min_built), priority=args.priority,
                           model=args.model, repeats=args.repeats), fh, indent=2)

    print("\nfinished: " + ", ".join(t for t in [d.strip() for d in args.dates.split(",")]))
    print("run summarise_dates.py to build the comparison table")
    return 0


if __name__ == "__main__":
    sys.exit(main())
