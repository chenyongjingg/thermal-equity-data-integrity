#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Train the planting-priority model, contaminate training labels, measure harm.

The model is deliberately plain: a random forest predicts land surface
temperature from the cell covariates, and planting priority is predicted heat
burden multiplied by population.  Contamination is applied to training labels
only; the evaluation labels stay clean, so every metric below is measured
against the same ground truth in every condition.

Metrics (one row per condition, matching Table 2 of the manuscript):

  dropout_pct        share of vulnerable cells that were in the clean-label
                     top decile and leave it after retraining
  jaccard            overlap of the contaminated and the clean top-decile sets
  spearman_rho       rank correlation between planting priority and a
                     continuous vulnerability score, z(population) - z(NDVI)
  bias_vulnerable_c  mean (prediction - observation) over vulnerable cells

The vulnerability score is continuous on purpose: with a binary indicator the
rank correlation would be dominated by ties.  The vulnerable *set* is the
threshold definition used in the manuscript (population at or above the 70th
percentile and NDVI at or below the median).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
import sklearn
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["ndvi", "built_frac", "log_pop", "x_km", "y_km"]
TOP_FRACTION = 0.10
POP_PERCENTILE = 70.0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cells", default="outputs/cells.csv")
    p.add_argument("--out", default="outputs/conditions.csv")
    p.add_argument("--meta", default="outputs/run_metadata.json")
    p.add_argument("--trees", type=int, default=300)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--repeats", type=int, default=1,
                   help="draws of the contaminated label set; metrics are averaged")
    p.add_argument("--contamination", nargs="+", type=float,
                   default=[0.05, 0.10, 0.15])
    p.add_argument("--delta", nargs="+", type=float, default=[1.0, 2.0, 3.0])
    p.add_argument("--main-delta", type=float, default=2.0,
                   help="shift used for the contamination-rate sweep")
    p.add_argument("--sweep-rate", type=float, default=0.10,
                   help="contamination rate held fixed in the shift-size sweep")
    p.add_argument("--pop-percentile", type=float, default=POP_PERCENTILE,
                   help="population percentile defining vulnerable cells")
    p.add_argument("--ndvi-quantile", type=float, default=0.5,
                   help="NDVI quantile defining vulnerable cells (0.5 = median)")
    p.add_argument("--top-fraction", type=float, default=TOP_FRACTION,
                   help="share of cells retained in the planting priority list")
    p.add_argument("--model", choices=["rf", "gbm", "ridge", "knn"], default="rf",
                   help="estimator: random forest (the paper), gradient boosting, "
                        "ridge regression, or k-nearest neighbours")
    p.add_argument("--draws-out", default=None,
                   help="optional CSV with one row per contamination draw, for "
                        "confidence intervals and paired tests")
    p.add_argument("--placebo-out", default=None,
                   help="optional CSV for the placebo arm: the same rate and "
                        "shift applied to the non-vulnerable complement, which "
                        "is the same magnitude of corruption aimed elsewhere")
    p.add_argument("--placebo-draws-out", default=None,
                   help="optional draws behind --placebo-out")
    p.add_argument("--priority", choices=["heat_x_pop", "heat"], default="heat_x_pop",
                   help="planting priority: predicted LST times population "
                        "(heat_x_pop) or predicted LST alone (heat)")
    return p.parse_args(argv)


def zscore(x):
    sd = np.std(x)
    return (x - np.mean(x)) / sd if sd > 0 else np.zeros_like(x)


def make_model(kind, trees, seed):
    if kind == "rf":
        return RandomForestRegressor(
            n_estimators=trees,
            random_state=seed,
            n_jobs=1,      # deterministic: parallel prediction accumulates
            min_samples_leaf=2,
        )
    if kind == "gbm":
        return GradientBoostingRegressor(
            n_estimators=trees, max_depth=3, learning_rate=0.05,
            random_state=seed,
        )
    if kind == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    if kind == "knn":
        return make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=15))
    raise ValueError(kind)


def fit_predict(df, y, trees, seed, kind="rf"):
    model = make_model(kind, trees, seed)
    model.fit(df[FEATURES].to_numpy(), y)
    return model.predict(df[FEATURES].to_numpy())


def priority_score(pred, pop, mode):
    return pred * pop if mode == "heat_x_pop" else pred


def metrics(df, pred, y, clean_top, clean_priority, vuln, vuln_score, top_n, mode):
    priority = priority_score(pred, df["pop"].to_numpy(), mode)
    order = np.argsort(-priority)
    top = np.zeros(len(df), dtype=bool)
    top[order[:top_n]] = True

    vuln_in_clean = vuln & clean_top
    dropped = vuln_in_clean & ~top
    dropout = 100.0 * dropped.sum() / max(vuln_in_clean.sum(), 1)

    inter = np.logical_and(top, clean_top).sum()
    union = np.logical_or(top, clean_top).sum()
    jaccard = inter / union if union else np.nan

    rho = spearmanr(priority, vuln_score).statistic
    bias = float(np.mean(pred[vuln] - y[vuln]))
    return dict(dropout_pct=round(dropout, 1),
                jaccard=round(float(jaccard), 3),
                spearman_rho=round(float(rho), 2),
                bias_vulnerable_c=round(bias, 2))


def main(argv=None):
    args = parse_args(argv)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    df = pd.read_csv(args.cells)
    df["built_frac"] = df["built_frac"].fillna(0.0)
    df["log_pop"] = np.log1p(df["pop"].clip(lower=0))
    df["x_km"] = df["x_utm"] / 1000.0
    df["y_km"] = df["y_utm"] / 1000.0

    pop_thr = np.percentile(df["pop"], args.pop_percentile)
    ndvi_thr = float(df["ndvi"].quantile(args.ndvi_quantile))
    vuln = ((df["pop"] >= pop_thr) & (df["ndvi"] <= ndvi_thr)).to_numpy()
    vuln_score = zscore(df["pop"].to_numpy()) - zscore(df["ndvi"].to_numpy())

    y = df["lst_c"].to_numpy()
    top_n = int(round(args.top_fraction * len(df)))

    pred_clean = fit_predict(df, y, args.trees, args.seed, args.model)
    priority_clean = priority_score(pred_clean, df["pop"].to_numpy(), args.priority)
    order = np.argsort(-priority_clean)
    clean_top = np.zeros(len(df), dtype=bool)
    clean_top[order[:top_n]] = True
    share_vuln_top = 100.0 * (clean_top & vuln).sum() / max(clean_top.sum(), 1)
    rho_clean = spearmanr(priority_clean, vuln_score).statistic

    rows = [dict(condition="clean", contamination_pct=0.0, delta_t=0.0,
                 dropout_pct=0.0, jaccard=1.0,
                 spearman_rho=round(float(rho_clean), 2),
                 bias_vulnerable_c=round(float(np.mean(pred_clean[vuln] - y[vuln])), 2),
                 repeats=1)]

    rng = np.random.default_rng(args.seed)

    draws = []

    def run_condition(condition, rate, delta, sink=None):
        # ``sink`` lets the placebo arm write its draws to its own file without
        # touching the draws behind Table 2
        sink = draws if sink is None else sink
        acc = []
        for draw in range(args.repeats):
            y_c = y.copy()
            n = int(round(rate * len(df)))
            if condition == "directional":
                pool = np.flatnonzero(vuln)
            elif condition == "placebo":
                pool = np.flatnonzero(~vuln)   # same magnitude, opposite target
            else:
                pool = np.arange(len(df))
            idx = rng.choice(pool, size=min(n, len(pool)), replace=False)
            y_c[idx] -= delta
            pred = fit_predict(df, y_c, args.trees, args.seed, args.model)
            m = metrics(df, pred, y, clean_top, priority_clean,
                        vuln, vuln_score, top_n, args.priority)
            acc.append(m)
            sink.append(dict(condition=condition,
                             contamination_pct=round(100 * rate, 1),
                             delta_t=delta, draw=draw, model=args.model, **m))
        out = {k: round(float(np.mean([a[k] for a in acc])), 3) for k in acc[0]}
        return dict(condition=condition, contamination_pct=round(100 * rate, 1),
                    delta_t=delta, dropout_pct=round(out["dropout_pct"], 1),
                    jaccard=round(out["jaccard"], 3),
                    spearman_rho=round(out["spearman_rho"], 2),
                    bias_vulnerable_c=round(out["bias_vulnerable_c"], 2),
                    repeats=args.repeats)

    for rate in args.contamination:
        rows.append(run_condition("directional", rate, args.main_delta))
    # negative control: same fraction, drawn from all cells
    for rate in args.contamination:
        rows.append(run_condition("random", rate, args.main_delta))
    # shift-size sweep, contamination rate held at --sweep-rate
    rate_main = args.sweep_rate
    for delta in args.delta:
        if abs(delta - args.main_delta) < 1e-9:
            continue
        rows.append(run_condition("directional", rate_main, delta))

    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False, lineterminator="\n")

    # placebo arm: same rate and shift, applied to the complement of the
    # vulnerable set.  It is written to its own table because Table 2 keeps the
    # two arms the paper compares; nothing above this line depends on it.
    if args.placebo_out:
        prows, pdraws = [], []
        for rate in args.contamination:
            prows.append(run_condition("placebo", rate, args.main_delta,
                                       sink=pdraws))
        pout = pd.DataFrame(prows)
        pout.to_csv(args.placebo_out, index=False, lineterminator="\n")
        if args.placebo_draws_out:
            pd.DataFrame(pdraws).to_csv(args.placebo_draws_out, index=False,
                                        lineterminator="\n")
        print(pout.to_string(index=False))

    if args.draws_out:
        pd.DataFrame(draws).to_csv(args.draws_out, index=False,
                                   lineterminator="\n")

    meta = {
        "cells": int(len(df)),
        "vulnerable_cells": int(vuln.sum()),
        "pop_percentile": args.pop_percentile,
        "ndvi_quantile": args.ndvi_quantile,
        "top_fraction": args.top_fraction,
        "priority": args.priority,
        "ndvi_threshold": float(ndvi_thr),
        "top_decile_cells": int(top_n),
        "vulnerable_share_of_clean_top_pct": round(float(share_vuln_top), 1),
        "model": args.model,
        "trees": args.trees,
        "seed": args.seed,
        "repeats": args.repeats,
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
    }
    with open(args.meta, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=2)

    print(out.to_string(index=False))
    print(f"\ncells={len(df)} vulnerable={int(vuln.sum())} "
          f"vulnerable share of clean top decile={share_vuln_top:.1f}% "
          f"rho_clean={rho_clean:.2f}")
    print(f"wrote {args.out} and {args.meta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
