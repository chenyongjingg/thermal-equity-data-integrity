#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Copy the reported run into ``results/`` and write ``results/CHECKSUMS.txt``.

Everything under ``results/`` is generated: the condition tables written by
``model_and_poison.py``, the grid it was fitted on, the metadata that records
the thresholds and package versions, and the two manuscript figures.  Running
this script after ``rerun_all.sh`` is what keeps the committed tables and the
paper in step; the checksums are computed here rather than typed by hand.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
RES = os.path.join(HERE, "results")
FIG = os.path.join(OUT, "figs_m0.05_r30")

FILES = [
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
FIGS = ["Figure_3.png", "Figure_3.svg", "Figure_4.png", "Figure_4.svg"]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(RES, exist_ok=True)
    copied = []
    for name in FILES:
        src = os.path.join(OUT, name)
        if not os.path.exists(src):
            raise SystemExit("missing {} — run rerun_all.sh first".format(src))
        shutil.copy2(src, os.path.join(RES, name))
        copied.append(name)
    for name in FIGS:
        src = os.path.join(FIG, name)
        if not os.path.exists(src):
            raise SystemExit("missing {} — run rerun_all.sh first".format(src))
        shutil.copy2(src, os.path.join(RES, name))
        copied.append(name)

    # checksums cover the tables and metadata only; PNG/SVG bytes depend on the
    # matplotlib, freetype and font versions, so they are shipped but not summed
    summed = [n for n in copied if not n.endswith((".png", ".svg"))]
    with open(os.path.join(RES, "CHECKSUMS.txt"), "w", encoding="utf-8",
              newline="\n") as fh:
        for name in sorted(summed):
            fh.write("{}  {}\n".format(md5(os.path.join(RES, name)), name))
    for name in sorted(summed):
        print("{}  {}".format(md5(os.path.join(RES, name)), name))
    print("wrote {} files and CHECKSUMS.txt to results/".format(len(copied)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
