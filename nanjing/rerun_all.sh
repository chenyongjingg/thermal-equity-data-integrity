#!/bin/sh
# Reproduce every table and figure committed in nanjing/results/.
#
# Needs the four Landsat bands of scene LC08_L2SP_120038_20210801_02_T1 and the
# GHS-POP / GHS-BUILT-S R6_C30 tiles in ../data/raw; see ../data/README.md.
# The output is deterministic: running this twice reproduces the committed
# checksums byte for byte.
#
#   sh rerun_all.sh            # from inside nanjing/
#   RAW=/path/to/raw sh rerun_all.sh
set -eu

PY=${PYTHON:-python}
RAW=${RAW:-../data/raw}
SCENE=LC08_L2SP_120038_20210801_02_T1
LST=$RAW/${SCENE}__ST_B10.tif
RED=$RAW/${SCENE}__SR_B4.tif
NIR=$RAW/${SCENE}__SR_B5.tif
QA=$RAW/${SCENE}__QA_PIXEL.tif
POP=$RAW/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30.tif
BUILT=$RAW/GHS_BUILT_S_E2020_GLOBE_R2023A_4326_30ss_V1_0_R6_C30.tif
OUT=outputs

mkdir -p "$OUT"

# three urban-mask definitions, heat priority (Table 2, Figures 3-4)
for mb in 0.02 0.05 0.10; do
    "$PY" build_grid.py \
        --lst "$LST" --red "$RED" --nir "$NIR" --qa "$QA" --max-cloud-frac 0.10 \
        --pop "$POP" --built "$BUILT" --min-built "$mb" \
        --sr-scale 2.75e-05 --sr-offset -0.2 --utm-zone 50 \
        --bbox 118.70 31.92 119.20 32.22 --res 1000 \
        --out "$OUT/cells_m$mb.csv" --meta "$OUT/grid_metadata_m$mb.json"
    # the reported mask also carries the placebo arm: same rate and shift,
    # aimed at the non-vulnerable complement
    extra=""
    if [ "$mb" = "0.05" ]; then
        extra="--placebo-out $OUT/placebo_heat_m0.05_r30.csv --placebo-draws-out $OUT/placebo_draws_heat_m0.05_r30.csv"
    fi
    "$PY" model_and_poison.py \
        --cells "$OUT/cells_m$mb.csv" \
        --out "$OUT/conditions_heat_m${mb}_r30.csv" \
        --meta "$OUT/run_metadata_heat_m${mb}_r30.json" \
        --contamination 0.05 0.10 0.15 --delta 1 2 3 \
        --main-delta 2 --sweep-rate 0.10 \
        --trees 300 --seed 7 --repeats 30 --priority heat $extra
done

# population-weighted priority on the reported mask
"$PY" model_and_poison.py \
    --cells "$OUT/cells_m0.05.csv" \
    --out "$OUT/conditions_heat_x_pop_r30.csv" \
    --meta "$OUT/run_metadata_heat_x_pop_r30.json" \
    --contamination 0.05 0.10 0.15 --delta 1 2 3 \
    --main-delta 2 --sweep-rate 0.10 \
    --trees 300 --seed 7 --repeats 30 --priority heat_x_pop

"$PY" make_figures.py --conditions "$OUT/conditions_heat_m0.05_r30.csv" \
    --outdir "$OUT/figs_m0.05_r30"
"$PY" pack_results.py --core
echo "done: results/ now matches the committed tables"
