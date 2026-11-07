# Committed outputs of the Nanjing run

Every file here is produced by `nanjing/rerun_all.sh`, which runs
`build_grid.py` → `model_and_poison.py` → `make_figures.py` on the inputs named
in `../README.md`. No value in these tables was typed by hand.

| File | What it is |
|---|---|
| `cells_m0.05.csv` | the analysis grid: one row per 1-km cell (727 rows), columns `lst_c`, `ndvi`, `pop`, `built_frac`, `cloud_frac` and coordinates |
| `grid_metadata_m0.05.json` | how many cells each filter removed and why |
| `conditions_heat_m0.05_r30.csv` | **Table 2** — the reported condition table (built fraction ≥ 0.05, priority = predicted heat, 30 draws) |
| `run_metadata_heat_m0.05_r30.json` | cell counts, thresholds, estimator settings, package versions, clean top-decile composition |
| `conditions_heat_m0.02_r30.csv`, `conditions_heat_m0.10_r30.csv` | urban-mask sensitivity reported in Section 4.4 (963 and 492 cells) |
| `conditions_heat_x_pop_r30.csv` | priority = predicted heat × population; drop-out 0.0% and Jaccard 1.000 at every rate |
| `Figure_3.png/.svg`, `Figure_4.png/.svg` | the manuscript figures, drawn from `conditions_heat_m0.05_r30.csv` |
| `CHECKSUMS.txt` | MD5 of every CSV and JSON above (PNG/SVG are shipped but not summed: their bytes depend on the matplotlib and freetype versions) |

## Headline values (`conditions_heat_m0.05_r30.csv`)

| Condition | Rate (%) | ΔT (°C) | Dropped (%) | Jaccard | ρ | Bias (°C) |
|---|---|---|---|---|---|---|
| Clean | 0 | — | 0.0 | 1.000 | 0.64 | 0.03 |
| Directional | 5 | 2 | 19.6 | 0.803 | 0.62 | −0.38 |
| Directional | 10 | 2 | 35.2 | 0.686 | 0.60 | −0.82 |
| Directional | 15 | 2 | 50.0 | 0.585 | 0.58 | −1.25 |
| Random | 5 | 2 | 6.1 | 0.880 | 0.64 | −0.07 |
| Random | 10 | 2 | 9.0 | 0.850 | 0.64 | −0.17 |
| Random | 15 | 2 | 11.3 | 0.786 | 0.63 | −0.26 |
| Directional | 10 | 1 | 20.9 | 0.798 | 0.63 | −0.40 |
| Directional | 10 | 3 | 46.3 | 0.603 | 0.57 | −1.25 |

727 analysis cells, 162 vulnerable, clean top decile 73 cells of which 52.1% are
vulnerable.

## Platform

Produced on Windows 11 (10.0.26200) with CPython 3.14.4,
numpy 2.4.6, pandas 3.0.3, scikit-learn 1.8.0, rasterio 1.5.2, matplotlib 3.10.x;
Landsat window read through GDAL `/vsicurl/` from the Microsoft Planetary
Computer. The exact package versions are recorded in every `run_metadata_*.json`
and the grid construction parameters in every `grid_metadata_*.json`.

## Regenerating

```bash
cd ..
sh rerun_all.sh        # ends with pack_results.py, which rewrites this directory
```

`pack_results.py` copies the tables, metadata and figures from `outputs/` into
this directory and rewrites `CHECKSUMS.txt`, so the checksums are never typed by
hand. If a checksum
differs while the condition values agree, the difference is in float
formatting or in the GDAL resampling path, not in the analysis; if a value
differs, the raster version differs — check `grid_metadata_*.json` first.
