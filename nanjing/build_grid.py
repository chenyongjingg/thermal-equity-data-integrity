#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the 1-km analysis grid for the Nanjing planting-priority experiment.

Inputs are the public products named in the manuscript (Section 4.4):

  * a Landsat 8 thermal band (Collection 2 Level-2 ``ST_B10`` or any band whose
    digital numbers can be converted to brightness temperature with a gain and
    an offset),
  * the red and near-infrared bands of the same scene, for NDVI,
  * a gridded population layer (GHS-POP R2023A, 30 arc-seconds, 2020 epoch),
  * optionally a built-up surface layer (GHS-BUILT-S) used as an urban mask.

Everything is reprojected to a 1-km grid in UTM zone 50N (EPSG:32650), the
zone that contains Nanjing.  Population is handled as a density: GHS-POP
stores persons per cell, and a cell is not a constant area, so counts are
converted to persons per square metre before resampling and multiplied back
by the target cell area afterwards.  Treating counts as intensities would
bias the dense central districts downward.

Output: a CSV with one row per cell.  No filtering on outcome variables is
performed beyond dropping cells that lack LST or NDVI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds

UTM = "EPSG:32650"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--lst", required=True, help="Landsat thermal band (GeoTIFF)")
    p.add_argument("--red", required=True, help="Red band (GeoTIFF)")
    p.add_argument("--nir", required=True, help="Near-infrared band (GeoTIFF)")
    p.add_argument("--pop", required=True, help="GHS-POP raster (persons per cell)")
    p.add_argument("--built", default=None, help="GHS-BUILT surface raster (m2 per cell)")
    p.add_argument("--bbox", nargs=4, type=float, default=[118.70, 31.92, 119.20, 32.22],
                   metavar=("W", "S", "E", "N"))
    p.add_argument("--res", type=float, default=1000.0, help="grid resolution, metres")
    p.add_argument("--lst-scale", type=float, default=0.00341802,
                   help="DN -> kelvin gain (Landsat C2 L2 ST_B10 default)")
    p.add_argument("--lst-offset", type=float, default=149.0,
                   help="DN -> kelvin offset (Landsat C2 L2 ST_B10 default)")
    p.add_argument("--no-kelvin", action="store_true",
                   help="thermal band is already in degrees Celsius")
    p.add_argument("--min-built", type=float, default=0.0,
                   help="drop cells whose built-up fraction is below this value")
    p.add_argument("--out", default="outputs/cells.csv")
    p.add_argument("--meta", default="outputs/grid_metadata.json")
    return p.parse_args(argv)


def read_raster(path):
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype("float64")
        if ds.nodata is not None:
            arr[arr == ds.nodata] = np.nan
        return arr, ds.transform, ds.crs


def target_grid(bbox, res):
    w, s, e, n = bbox
    xmin, ymin, xmax, ymax = transform_bounds("EPSG:4326", UTM, w, s, e, n)
    width = int(np.ceil((xmax - xmin) / res))
    height = int(np.ceil((ymax - ymin) / res))
    transform = from_origin(xmin, ymax, res, res)
    return transform, height, width


def warp_to(arr, src_transform, src_crs, dst_transform, shape, resampling):
    """Reproject one band to the target grid; NaN outside the source footprint."""
    dst = np.full(shape, np.nan, dtype="float64")
    reproject(
        source=arr,
        destination=dst,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=UTM,
        resampling=resampling,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    return dst


def pixel_area_m2(transform, crs, height, width):
    """Approximate per-row pixel area in square metres (geographic grids)."""
    if crs is not None and crs.is_projected:
        return np.full(height, abs(transform.a * transform.e))
    rows = np.arange(height)
    lat = rasterio.transform.xy(transform, rows, 0, offset="ul")[1]
    lat = np.asarray(lat, dtype="float64")
    dy = abs(transform.e) * 111_320.0
    dx = abs(transform.a) * 111_320.0 * np.cos(np.deg2rad(lat))
    return (dx * dy)[:, None] * np.ones((1, width))


def main(argv=None):
    args = parse_args(argv)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    lst, lst_t, lst_crs = read_raster(args.lst)
    red, red_t, red_crs = read_raster(args.red)
    nir, nir_t, nir_crs = read_raster(args.nir)
    pop, pop_t, pop_crs = read_raster(args.pop)

    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi = (nir - red) / (nir + red)
    ndvi[~np.isfinite(ndvi)] = np.nan

    pop_area = pixel_area_m2(pop_t, pop_crs, pop.shape[0], pop.shape[1])
    with np.errstate(invalid="ignore", divide="ignore"):
        pop_density = pop / pop_area          # persons per m2
    pop_density[~np.isfinite(pop_density)] = np.nan

    dst_t, height, width = target_grid(args.bbox, args.res)
    shape = (height, width)

    lat_c = warp_to(lst, lst_t, lst_crs, dst_t, shape, Resampling.average)
    ndvi_c = warp_to(ndvi, red_t, red_crs, dst_t, shape, Resampling.average)
    dens_c = warp_to(pop_density, pop_t, pop_crs, dst_t, shape, Resampling.average)
    built_c = np.full(shape, np.nan)
    if args.built:
        built, b_t, b_crs = read_raster(args.built)
        b_area = pixel_area_m2(b_t, b_crs, built.shape[0], built.shape[1])
        with np.errstate(invalid="ignore", divide="ignore"):
            frac = built / b_area
        frac[~np.isfinite(frac)] = np.nan
        built_c = warp_to(frac, b_t, b_crs, dst_t, shape, Resampling.average)

    rows, cols = np.mgrid[0:height, 0:width]
    xs, ys = rasterio.transform.xy(dst_t, rows, cols, offset="center")
    xs = np.asarray(xs).ravel()
    ys = np.asarray(ys).ravel()

    cells = pd.DataFrame({
        "cell_id": np.arange(height * width),
        "row": rows.ravel(),
        "col": cols.ravel(),
        "x_utm": xs,
        "y_utm": ys,
        "lst_c": lat_c.ravel(),
        "ndvi": ndvi_c.ravel(),
        "pop": np.maximum(dens_c.ravel(), 0.0) * (args.res ** 2),
        "built_frac": built_c.ravel(),
    })

    before = len(cells)
    cells = cells.dropna(subset=["lst_c", "ndvi", "pop"]).copy()
    dropped_nan = before - len(cells)

    dropped_built = 0
    if args.min_built > 0:
        keep = cells["built_frac"].fillna(0.0) >= args.min_built
        dropped_built = int((~keep).sum())
        cells = cells[keep].copy()

    if args.no_kelvin:
        pass
    else:
        cells["lst_c"] = cells["lst_c"] * args.lst_scale + args.lst_offset - 273.15

    lonlat = rasterio.warp.transform(UTM, "EPSG:4326",
                                     cells["x_utm"].to_numpy(),
                                     cells["y_utm"].to_numpy())
    cells["lon"] = lonlat[0]
    cells["lat"] = lonlat[1]
    cells = cells[["cell_id", "lon", "lat", "x_utm", "y_utm",
                   "lst_c", "ndvi", "pop", "built_frac"]]
    cells.to_csv(args.out, index=False)

    meta = {
        "bbox_wsen": args.bbox,
        "crs": UTM,
        "resolution_m": args.res,
        "grid_height": height,
        "grid_width": width,
        "cells_in_grid": int(height * width),
        "cells_written": int(len(cells)),
        "dropped_missing_data": int(dropped_nan),
        "dropped_below_min_built": dropped_built,
        "min_built": args.min_built,
        "lst_input": os.path.basename(args.lst),
        "lst_scale": None if args.no_kelvin else args.lst_scale,
        "lst_offset": None if args.no_kelvin else args.lst_offset,
        "pop_input": os.path.basename(args.pop),
    }
    with open(args.meta, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    print(f"cells written: {len(cells)} of {height * width} grid cells "
          f"({dropped_nan} dropped for missing LST/NDVI/population, "
          f"{dropped_built} below built-up threshold)")
    print(f"wrote {args.out} and {args.meta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
