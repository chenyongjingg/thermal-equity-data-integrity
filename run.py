# -*- coding: utf-8 -*-
"""Cross-platform entry point.  The Makefile wraps the same commands.

    python run.py synthetic    regenerate the synthetic-city results and verify them
    python run.py nanjing      run the Nanjing pipeline (needs LST/RED/NIR/POP env vars)
    python run.py test         smoke-test the Nanjing pipeline on tiny rasters
    python run.py checksums    verify synthetic/results_*.csv against CHECKSUMS.txt

`make` is not installed everywhere (it is absent from a default Windows setup),
so this script is the canonical way to run the repository; the Makefile exists
for POSIX users and calls nothing else.
"""

import argparse
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SYN = os.path.join(ROOT, "synthetic")
NAN = os.path.join(ROOT, "nanjing")
OUT = os.path.join(NAN, "outputs")

FILES = ["results_per_seed.csv", "results_summary.csv",
         "results_clean_baseline.csv"]


def sh(args, cwd=ROOT):
    print("$ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def synthetic():
    sh([sys.executable, "simulate_poisoning.py"], cwd=SYN)
    sh([sys.executable, "make_figures.py"], cwd=SYN)
    checksums()


def checksums():
    bad = 0
    expected = {}
    with open(os.path.join(SYN, "CHECKSUMS.txt"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            digest, name = line.split(None, 1)
            name = name.strip().lstrip("*")          # md5sum writes "hash *file"
            expected[os.path.basename(name)] = digest
    for name in FILES:
        path = os.path.join(SYN, name)
        h = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        got = h.hexdigest()
        ok = got == expected.get(name)
        bad += 0 if ok else 1
        print("{} {} {}".format("OK  " if ok else "FAIL", got, name))
    if bad:
        raise SystemExit("{} file(s) differ from CHECKSUMS.txt".format(bad))
    print("all {} files match".format(len(FILES)))


def nanjing():
    lst, red, nir, pop = (os.environ.get(k) for k in ("LST", "RED", "NIR", "POP"))
    missing = [k for k, v in zip(("LST", "RED", "NIR", "POP"),
                                 (lst, red, nir, pop)) if not v]
    if missing:
        raise SystemExit("set " + ", ".join(missing) + " (see nanjing/README.md)")
    os.makedirs(OUT, exist_ok=True)
    cells = os.path.join(OUT, "cells.csv")
    conds = os.path.join(OUT, "conditions.csv")
    sh([sys.executable, os.path.join(NAN, "build_grid.py"),
        "--lst", lst, "--red", red, "--nir", nir, "--pop", pop,
        "--bbox", "118.70", "31.92", "119.20", "32.22", "--res", "1000",
        "--out", cells, "--meta", os.path.join(OUT, "grid_metadata.json")])
    sh([sys.executable, os.path.join(NAN, "model_and_poison.py"),
        "--cells", cells, "--out", conds,
        "--meta", os.path.join(OUT, "run_metadata.json"),
        "--contamination", "0.05", "0.10", "0.15",
        "--delta", "1", "2", "3", "--main-delta", "2",
        "--trees", "300", "--seed", "7"])
    sh([sys.executable, os.path.join(NAN, "make_figures.py"),
        "--conditions", conds, "--outdir", OUT])


def test():
    sh([sys.executable, "-m", "pytest", os.path.join(NAN, "tests"), "-q"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", choices=["synthetic", "nanjing", "test", "checksums"])
    args = ap.parse_args(argv)
    {"synthetic": synthetic, "nanjing": nanjing,
     "test": test, "checksums": checksums}[args.target]()


if __name__ == "__main__":
    main()
