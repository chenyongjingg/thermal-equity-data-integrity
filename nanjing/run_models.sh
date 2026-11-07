#!/bin/sh
# Estimator-family robustness run: Table S2 and the draws behind it.
#
# Repeats the reported experiment on the reported grid with four learners.
# build_grid.py has to have run first (rerun_all.sh does it), because the grid
# is held fixed and only the learner changes.
#
#   sh run_models.sh           # from inside nanjing/
#   PYTHON=/usr/bin/python3 sh run_models.sh
#
# Random forest is included on purpose: model_rf.csv must reproduce
# results/conditions_heat_m0.05_r30.csv byte for byte, which is the check that
# the rest of the family was run under the same protocol.
set -eu

PY=${PYTHON:-python}
OUT=${OUT:-outputs}
CELLS=$OUT/cells_m0.05.csv

[ -f "$CELLS" ] || { echo "missing $CELLS: run 'sh rerun_all.sh' first" >&2; exit 1; }

for model in gbm ridge knn rf; do
    "$PY" model_and_poison.py \
        --cells "$CELLS" \
        --out "$OUT/model_${model}.csv" \
        --meta "$OUT/model_${model}.json" \
        --draws-out "$OUT/draws_${model}.csv" \
        --contamination 0.05 0.10 0.15 --delta 1 2 3 \
        --main-delta 2 --sweep-rate 0.10 \
        --trees 300 --seed 7 --repeats 30 --priority heat \
        --model "$model"
done

"$PY" summarise_models.py --out "$OUT" --dst "$OUT/model_summary.csv"
echo "done: model_summary.csv is Table S2"
