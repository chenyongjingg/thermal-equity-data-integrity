# -*- coding: utf-8 -*-
"""Cross-platform entry point.  The Makefile wraps the same commands.

    python run.py synthetic    regenerate the synthetic-city results and verify them
    python run.py nanjing      run the Nanjing pipeline (needs LST/RED/NIR/QA/POP/BUILT)
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

def sh(args, cwd=ROOT):
    print("$ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def synthetic():
    sh([sys.executable, "simulate_poisoning.py"], cwd=SYN)
    sh([sys.executable, "make_figures.py"], cwd=SYN)
    checksums()


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(directory, checksum_file):
    """Check every file named in a CHECKSUMS.txt against its MD5."""
    bad = 0
    checked = 0
    with open(checksum_file, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            digest, name = line.split(None, 1)
            name = name.strip().lstrip("*")
            # keep sub-directories (results/cities/<name>/...); the basename
            # would collapse every city file onto results/cells.csv
            path = os.path.join(directory, name.replace("/", os.sep))
            if not os.path.exists(path):
                print("FAIL missing {}".format(name))
                bad += 1
                continue
            got = md5_of(path)
            ok = got == digest
            bad += 0 if ok else 1
            checked += 1
            print("{} {} {}".format("OK  " if ok else "FAIL", got, name))
    return checked, bad


def checksums():
    """Verify the synthetic results and the committed Nanjing tables."""
    checked, bad = verify(SYN, os.path.join(SYN, "CHECKSUMS.txt"))
    res = os.path.join(NAN, "results")
    res_sums = os.path.join(res, "CHECKSUMS.txt")
    if os.path.exists(res_sums):
        n2, b2 = verify(res, res_sums)
        checked += n2
        bad += b2
    else:
        print("note: {} not found; skipped".format(res_sums))
    if bad:
        raise SystemExit("{} file(s) differ from CHECKSUMS.txt".format(bad))
    print("all {} files match".format(checked))


def nanjing():
    """Run the specification reported in the paper (Section 4.4, Table 2)."""
    env = {k: os.environ.get(k) for k in ("LST", "RED", "NIR", "QA", "POP", "BUILT")}
    missing = [k for k in ("LST", "RED", "NIR", "QA", "POP", "BUILT")
               if not env[k]]
    if missing:
        raise SystemExit("set " + ", ".join(missing) + " (see nanjing/README.md)")
    os.makedirs(OUT, exist_ok=True)
    cells = os.path.join(OUT, "cells_m0.05.csv")
    conds = os.path.join(OUT, "conditions_heat_m0.05_r30.csv")
    sh([sys.executable, os.path.join(NAN, "build_grid.py"),
        "--lst", env["LST"], "--red", env["RED"], "--nir", env["NIR"],
        "--qa", env["QA"], "--max-cloud-frac", "0.10",
        "--pop", env["POP"], "--built", env["BUILT"], "--min-built", "0.05",
        "--sr-scale", "2.75e-05", "--sr-offset", "-0.2",
        "--bbox", "118.70", "31.92", "119.20", "32.22", "--res", "1000",
        "--out", cells, "--meta", os.path.join(OUT, "grid_metadata_m0.05.json")])
    sh([sys.executable, os.path.join(NAN, "model_and_poison.py"),
        "--cells", cells, "--out", conds,
        "--meta", os.path.join(OUT, "run_metadata_heat_m0.05_r30.json"),
        "--contamination", "0.05", "0.10", "0.15",
        "--delta", "1", "2", "3", "--main-delta", "2", "--sweep-rate", "0.10",
        "--trees", "300", "--seed", "7", "--repeats", "30", "--priority", "heat"])
    sh([sys.executable, os.path.join(NAN, "make_figures.py"),
        "--conditions", conds, "--outdir", os.path.join(OUT, "figs_m0.05_r30")])


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
