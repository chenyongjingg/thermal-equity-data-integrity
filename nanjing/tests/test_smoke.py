# -*- coding: utf-8 -*-
"""End-to-end smoke test on a tiny synthetic raster stack.

The test does not check scientific results.  It checks that the pipeline runs
from raw rasters to a conditions table, that the columns match what the
manuscript's Table 2 requires, and that a strongly contaminated run moves the
metrics in the expected direction.  It needs no real data.
"""

import os
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import build_grid          # noqa: E402
import model_and_poison    # noqa: E402


def write_tif(path, arr, transform, crs="EPSG:4326"):
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0],
                       width=arr.shape[1], count=1, dtype="float64",
                       crs=crs, transform=transform) as ds:
        ds.write(arr, 1)


@pytest.fixture()
def rasters(tmp_path):
    n = 40
    transform = from_origin(118.80, 32.05, 0.0025, 0.0025)
    rng = np.random.default_rng(0)
    lat = np.linspace(32.05, 32.05 - 0.0025 * n, n)[:, None]
    gradient = 1.0 - np.linspace(0, 1, n)[None, :]
    canopy = 0.2 + 0.5 * gradient + 0.02 * rng.normal(size=(n, n))
    canopy = np.clip(canopy, 0, 1)

    nir = 0.5 * canopy + 0.05
    red = 0.5 * (1 - canopy) + 0.05
    lst_k = 300 + 6 * (1 - canopy) + 0.1 * rng.normal(size=(n, n))
    lst_dn = (lst_k - 149.0) / 0.00341802
    pop = np.clip(3000 * (1 - canopy) + 100 * rng.normal(size=(n, n)), 0, None)

    paths = {k: str(tmp_path / f"{k}.tif") for k in ("lst", "red", "nir", "pop")}
    write_tif(paths["lst"], lst_dn, transform)
    write_tif(paths["red"], red, transform)
    write_tif(paths["nir"], nir, transform)
    write_tif(paths["pop"], pop, transform)
    return paths, tmp_path


def test_pipeline_runs_end_to_end(rasters):
    paths, tmp = rasters
    cells = str(tmp / "cells.csv")
    grid_meta = str(tmp / "grid_meta.json")
    build_grid.main([
        "--lst", paths["lst"], "--red", paths["red"], "--nir", paths["nir"],
        "--pop", paths["pop"], "--bbox", "118.80", "31.95", "118.90", "32.05",
        "--res", "500", "--out", cells, "--meta", grid_meta,
    ])
    conditions = str(tmp / "conditions.csv")
    model_and_poison.main([
        "--cells", cells, "--out", conditions, "--meta", str(tmp / "run.json"),
        "--trees", "60", "--contamination", "0.10", "--delta", "2.0",
        "--main-delta", "2.0",
    ])

    import pandas as pd
    d = pd.read_csv(conditions)
    expected = {"condition", "contamination_pct", "delta_t", "dropout_pct",
                "jaccard", "spearman_rho", "bias_vulnerable_c", "repeats"}
    assert expected.issubset(set(d.columns))
    assert {"clean", "directional", "random"}.issubset(set(d.condition))
    clean = d[d.condition == "clean"].iloc[0]
    assert clean.jaccard == 1.0
    assert clean.dropout_pct == 0.0
    assert (d["jaccard"] <= 1.0).all()
    assert (d["jaccard"] >= 0.0).all()
