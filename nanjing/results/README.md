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
| `model_summary.csv` | **Table S2** — the same grid and protocol under four estimators (`model_*.csv` hold the full per-estimator condition tables, `draws_*.csv` the 30 draws behind every mean) |
| `city_summary.csv`, `cities/<name>/` | **Table S3** — the protocol repeated in eight cities; each `cities/<name>/` holds the grid, the condition table, the draws and the scene metadata |
| `sensitivity_summary.csv` (`outputs/sens_*`) | **Table S4** — 500 m and 2 km grids, seeds 13 and 21, two other vulnerable-set definitions, and planting budgets of the top 5% and 20% |
| `uncertainty_nanjing.csv`, `uncertainty_nanjing_contrasts.csv` | **Table S5** — mean, SD and 95% interval over the 30 draws, and the Welch interval for directional minus random |
| `placebo_heat_m0.05_r30.csv`, `placebo_draws_heat_m0.05_r30.csv` | the placebo arm: the same rate and shift applied to the non-vulnerable complement |
| `Figure_S2.png/.svg`, `Figure_S2_source.csv` | **Figure S2** — the directional and random drop-out in the eight cities with 95% intervals |
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

## Robustness headline values (drop-out at 10% contamination, ΔT = 2 °C)

Directional vs random, from `model_summary.csv` and `city_summary.csv`:

| Estimator | Directional | Random |
|---|---|---|
| Random forest (the paper) | 35.2 | 9.0 |
| Gradient boosting | 37.8 | 12.2 |
| Ridge regression | 10.1 | 0.9 |
| k-nearest neighbors | 29.3 | 5.3 |

| City | Scene date | Directional | Random |
|---|---|---|---|
| Nanjing | 2021-08-01 | 35.2 | 9.0 |
| Beijing | 2021-05-02 | 71.2 | 11.8 |
| Shanghai | 2021-04-29 | 64.4 | 12.8 |
| Zhengzhou | 2021-09-30 | 49.5 | 13.5 |
| Wuhan | 2021-10-25 | 47.3 | 7.6 |
| Hefei | 2021-06-05 | 41.0 | 9.3 |
| Hangzhou | 2021-09-27 | 33.9 | 8.3 |
| Xi'an | 2021-04-28 | 33.3 | 7.7 |

The directional-minus-random gap at 10% is 25.6 to 59.4 percentage points
across the eight cities, and its 95% interval excludes zero in every city
(`uncertainty_cities_contrasts.csv`).

Design choices, from `sensitivity_summary.csv` (10% contamination, ΔT = 2 °C):

| Variant | Cells | Vulnerable | Directional | Random |
|---|---|---|---|---|
| 500 m grid | 3040 | 683 | 32.2 | 8.2 |
| 2 km grid | 173 | 38 | 41.1 | 14.4 |
| Seed 13 | 727 | 162 | 36.4 | 9.8 |
| Seed 21 | 727 | 162 | 38.0 | 8.9 |
| Vulnerable set P60 / NDVI 25th | 727 | 110 | 47.3 | 7.8 |
| Vulnerable set P80 / NDVI 75th | 727 | 141 | 48.0 | 10.2 |
| Budget = top 5% | 727 | 162 | 51.4 | 16.7 |
| Budget = top 20% | 727 | 162 | 18.2 | 4.3 |

The direction survives all eight; the directional-to-random ratio stays between
2.9 and 6.1.

The placebo arm, from `placebo_heat_m0.05_r30.csv`, shifts the same share of
labels by the same amount but selects them from the non-vulnerable complement:
at 5%, 10% and 15% it removes 1.6%, 0.7% and 0.7% of vulnerable cells from the
top decile (95% intervals 0.9–2.3, 0.0–1.4 and 0.3–1.1), below the random
control at every rate. Corruption aimed away from the vulnerable set therefore
costs them less than corruption aimed at random, which is what makes the
directional arm informative rather than an artefact of how the metric is built.

Nanjing appears in the city table as a self-check, not as an extra result:
`cities/nanjing/cells.csv` is byte-identical to `cells_m0.05.csv` and
`cities/nanjing/conditions.csv` to `conditions_heat_m0.05_r30.csv`, so the city
driver provably shares the protocol rather than reimplementing it. Beijing and Wuhan need their composition
column read beside the drop-out: 8.0% and 27.3% of their clean top deciles are
vulnerable, so the rate is computed on a small base.

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
