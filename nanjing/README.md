# Nanjing experiment (manuscript Section 4.4, Table 2, Figures 3–4)

## Design in one paragraph

The main urban area of Nanjing (118.70–119.20° E, 31.92–32.22° N) is gridded
at 1 km in UTM zone 50N. A cell is kept when it carries land surface temperature
and NDVI, has a built-up fraction of at least 5% (GHS-BUILT-S, 2020), and is at
least 90% free of QA_PIXEL flags (cloud, dilated cloud, cirrus, shadow, fill).
Land surface temperature comes from a single Landsat 8 scene; population comes
from GHS-POP R2023A (2020 epoch, 30 arc-seconds) and is treated as a density.
A cell is **vulnerable** when its population is at or above the 70th percentile
and its NDVI at or below the median — 162 of the 727 retained cells.

A random forest predicts LST from the cell covariates, and planting priority is
the **predicted heat burden**. Contamination is applied to training labels only:
a fraction *p* of labels in vulnerable cells is shifted down by ΔT
(directional), or the same number of labels is drawn from all cells (random
control). Both arms are scored against the same clean ground truth. Each
condition is the mean of 30 independent draws.

## Inputs

| Role | File | Notes |
|---|---|---|
| LST | `*_ST_B10.tif` | Collection 2 Level-2 surface temperature, DN → K with gain 0.00341802 and offset 149.0 (defaults). Pass `--no-kelvin` if your band is already °C. |
| Red | `*_SR_B4.tif` | for NDVI; reflectance = DN × 2.75e-05 − 0.2 |
| NIR | `*_SR_B5.tif` | for NDVI, same scaling |
| QA | `*_QA_PIXEL.tif` | cloud mask; bits 0–4 count as flagged, `--max-cloud-frac 0.10` |
| Population | `GHS_POP_E2020_GLOBE_R2023A_4326_30ss_*.tif` | persons per cell; converted to density internally |
| Built-up | `GHS_BUILT_S_E2020_GLOBE_R2023A_4326_30ss_*.tif` | `--min-built 0.05` |

The scene used in the paper is **LC08_L2SP_120038_20210801_02_T1** (1 August
2021, cloud cover 12.86%, WRS-2 path 120 / row 038). `find_scene.py` recovers
this identification from the public STAC endpoint and writes
`scene_metadata.json`; run it if you want to check the scene before downloading
anything.

```bash
python find_scene.py > scene_metadata.json
```

`fetch_inputs.py` then copies only the window covering the study area (about
19 MB for the four bands, versus roughly 360 MB for full scenes). The USGS S3
bucket is requester-pays and the Azure mirror is private without a signature, so
the script signs the read with a Planetary Computer SAS token and uses
`/vsicurl/` windowed reads:

```bash
python fetch_inputs.py --outdir ../data/raw
```

## Run

The whole reported matrix — three urban-mask definitions plus the
population-weighted priority variant — is in `rerun_all.sh`:

```bash
sh rerun_all.sh          # ~25 min, mostly random-forest fits
```

The single specification used in the paper, step by step:

```bash
python build_grid.py \
  --lst "$LST" --red "$RED" --nir "$NIR" --qa "$QA" --max-cloud-frac 0.10 \
  --pop "$POP" --built "$BUILT" --min-built 0.05 \
  --sr-scale 2.75e-05 --sr-offset -0.2 \
  --bbox 118.70 31.92 119.20 32.22 --res 1000 \
  --out outputs/cells_m0.05.csv --meta outputs/grid_metadata_m0.05.json

python model_and_poison.py \
  --cells outputs/cells_m0.05.csv \
  --out outputs/conditions_heat_m0.05_r30.csv \
  --meta outputs/run_metadata_heat_m0.05_r30.json \
  --contamination 0.05 0.10 0.15 --delta 1 2 3 --main-delta 2 --sweep-rate 0.10 \
  --trees 300 --seed 7 --repeats 30 --priority heat

python make_figures.py --conditions outputs/conditions_heat_m0.05_r30.csv \
  --outdir outputs/figs_m0.05_r30
```

`python run.py nanjing` (repository root) runs the same three steps from the
`LST`, `RED`, `NIR`, `QA`, `POP` and `BUILT` environment variables.

## Outputs

`conditions_*.csv` has one row per condition:

| Column | Meaning |
|---|---|
| `condition` | `clean`, `directional`, `random` |
| `contamination_pct` | share of training labels contaminated |
| `delta_t` | downward shift applied, °C |
| `dropout_pct` | share of vulnerable cells in the clean top decile that leave it |
| `jaccard` | overlap of the contaminated and clean top-decile sets |
| `spearman_rho` | rank correlation between priority and the vulnerability score z(pop) − z(NDVI) |
| `bias_vulnerable_c` | mean(prediction − observation) over vulnerable cells |
| `repeats` | number of contamination draws averaged |

`run_metadata_*.json` records the cell count, the vulnerable count, the
thresholds, the estimator settings, the package versions and the priority
variant — quote these with any number you take from the output.

The tables the paper is built from are committed, with MD5 sums, in
`results/`: see `results/README.md`.

## Parameters that change the result

- `--min-built` (urban mask). The paper's run uses 0.05 (727 cells); 0.02 and
  0.10 are reported as sensitivity (963 and 492 cells). With no mask the grid
  keeps cropland and water cells that survive the missing-data filter.
- `--max-cloud-frac` (0.10 here). A cell is 1 km and a Landsat pixel 30 m, so
  requiring zero flagged pixels discards roughly half the grid.
- `--priority` (`heat` in the paper, `heat_x_pop` as a sensitivity — the
  population-weighted variant shows a 0.0% drop-out at every rate).
- `--res` (grid size, default 1000 m), `--seed` (label sampling and forest).
- The vulnerability thresholds — `--pop-percentile` (default 70),
  `--ndvi-quantile` (default 0.5) and `--top-fraction` (default 0.10) — change
  both the vulnerable set and ρ. The defaults are the ones used in the paper.

## What this code does not do

- Feature-level contamination (fabricated canopy polygons, suppressed sensor
  records). The pipeline shifts labels only.
- Multi-city or multi-date replication.
- Any estimate of how often contamination occurs, or of the temperature effect
  of the resulting reallocation.

These are the extensions named in Section 6.3 of the paper.

## Test

```bash
python -m pytest tests -q
```

The test builds a 40 × 40 raster stack in a temporary directory, runs the whole
path, and checks the output schema and metric ranges. It needs no real data. It
is a smoke test: passing means the pipeline runs, not that it reproduces the
paper's numbers.
