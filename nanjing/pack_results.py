#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Copy the reported runs into ``results/`` and write ``results/CHECKSUMS.txt``.

Everything under ``results/`` is generated: the condition tables written by
``model_and_poison.py``, the grid it was fitted on, the metadata that records
the thresholds and package versions, the cross-estimator and cross-city
comparison tables, the draw-level uncertainty tables, and the manuscript
figures.  Running this script after the pipeline is what keeps the committed
tables and the paper in step; the checksums are computed here rather than typed
by hand.

    python pack_results.py            # everything, fails if a piece is missing
    python pack_results.py --core     # the Nanjing main run only

``--core`` exists for the small case: it copies what the main experiment needs
and leaves the robustness runs out.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
RES = os.path.join(HERE, "results")
FIG = os.path.join(OUT, "figs_m0.05_r30")

CORE = [
    "cells_m0.05.csv",
    "grid_metadata_m0.05.json",
    "conditions_heat_m0.05_r30.csv",
    "run_metadata_heat_m0.05_r30.json",
    "conditions_heat_m0.02_r30.csv",
    "run_metadata_heat_m0.02_r30.json",
    "conditions_heat_m0.10_r30.csv",
    "run_metadata_heat_m0.10_r30.json",
    "conditions_heat_x_pop_r30.csv",
    "run_metadata_heat_x_pop_r30.json",
]
CORE_FIGS = ["Figure_3.png", "Figure_3.svg", "Figure_4.png", "Figure_4.svg"]

# robustness runs: model families, cities, draw-level uncertainty
MODELS = ["rf", "gbm", "ridge", "knn"]
ROBUST_TABLES = (
    ["model_summary.csv", "city_summary.csv", "sensitivity_summary.csv",
     "uncertainty_nanjing.csv", "uncertainty_nanjing_contrasts.csv",
     "uncertainty_cities.csv", "uncertainty_cities_contrasts.csv",
     "placebo_heat_m0.05_r30.csv", "placebo_draws_heat_m0.05_r30.csv"]
    + ["model_{}.csv".format(m) for m in MODELS]
    + ["model_{}.json".format(m) for m in MODELS]
    + ["draws_{}.csv".format(m) for m in MODELS]
)
ROBUST_FIGS = ["Figure_S2.png", "Figure_S2.svg", "Figure_S2_source.csv"]
CITY_FILES = ["cells.csv", "conditions.csv", "draws.csv",
              "grid_metadata.json", "run_metadata.json", "city.json"]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy(src, dst, copied):
    if not os.path.exists(src):
        raise SystemExit("missing {} — run the pipeline first".format(src))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(os.path.relpath(dst, RES))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--core", action="store_true",
                    help="copy only the Nanjing main run and Figures 3/4")
    args = ap.parse_args(argv)
    os.makedirs(RES, exist_ok=True)
    copied = []

    for name in CORE:
        copy(os.path.join(OUT, name), os.path.join(RES, name), copied)
    for name in CORE_FIGS:
        copy(os.path.join(FIG, name), os.path.join(RES, name), copied)

    if not args.core:
        for name in ROBUST_TABLES:
            copy(os.path.join(OUT, name), os.path.join(RES, name), copied)
        for name in ROBUST_FIGS:
            copy(os.path.join(OUT, name), os.path.join(RES, name), copied)
        cities = sorted(d for d in os.listdir(OUT)
                        if d.startswith("city_") and
                        os.path.isdir(os.path.join(OUT, d)))
        for c in cities:
            for name in CITY_FILES:
                src = os.path.join(OUT, c, name)
                if not os.path.exists(src):
                    raise SystemExit("missing {} — rerun run_cities.py".format(src))
                copy(src, os.path.join(RES, "cities", c[len("city_"):], name),
                     copied)

    # checksums cover every shipped table and metadata file, not only the ones
    # this invocation copied: ``--core`` (used by rerun_all.sh) must not drop
    # the robustness entries from a repository that already ships them.  PNG/SVG
    # are shipped but not summed, because their bytes depend on the matplotlib,
    # freetype and font versions.
    summed = []
    for root, _dirs, files in os.walk(RES):
        for f in files:
            if f.endswith((".csv", ".json")):
                rel = os.path.relpath(os.path.join(root, f), RES)
                summed.append(rel.replace(os.sep, "/"))
    with open(os.path.join(RES, "CHECKSUMS.txt"), "w", encoding="utf-8",
              newline="\n") as fh:
        for name in sorted(summed):
            fh.write("{}  {}\n".format(
                md5(os.path.join(RES, name.replace("/", os.sep))), name))
    for name in sorted(summed):
        print("{}  {}".format(
            md5(os.path.join(RES, name.replace("/", os.sep))), name))
    print("wrote {} files and CHECKSUMS.txt to results/".format(len(copied)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
