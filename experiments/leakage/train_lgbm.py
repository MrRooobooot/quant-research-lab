#!/usr/bin/env python3
"""Offline, purged walk-forward research ONLY. No model persistence/activation.

Old ml/ artifacts are invalid evaluation; rebuild and rerun explicitly. Default
invocation validates only. --run requires an explicit versioned --dataset path.
Scores are overlapping-entry proxies, NOT wallet return or the live entry gate.
Threshold selection needs a separate untouched holdout before any approval.
"""
import argparse
import json
import os
import numpy as np
import pandas as pd
from build_dataset import load_dataset

ROOT = os.path.dirname(os.path.abspath(__file__))
ML = os.path.join(ROOT, "ml")
FEE = 0.002  # additive round-trip cost proxy, not exact exchange fee accounting
FEATURES = ["gap_pct", "gap_slope", "rsi", "bar_vol", "ret_1", "ret_12", "vol_z",
            "dist_high60", "dist_low60", "hour"]
SCOPE = "Overlapping hypothetical entries; NOT wallet return; no live SMA gate, sizing, slippage or funding"


def load(path=ML):
    X, labels, m = load_dataset(path)
    return X[FEATURES], labels.label, m.assign(gross_return=labels.gross_return.to_numpy())


def purged_splits(m, n_folds=5):
    """Group identical entry timestamps; purge FULL label horizons at each boundary."""
    if not {"date", "label_end"}.issubset(m.columns):
        raise ValueError("Required label_end metadata missing; old evaluation invalid, rebuild")
    dates = pd.to_datetime(m.date, utc=True)
    ends = pd.to_datetime(m.label_end, utc=True)
    if dates.isna().any() or ends.isna().any() or (ends <= dates).any():
        raise ValueError("Invalid label time interval")
    times = dates.sort_values().unique()
    if not 1 <= n_folds < len(times):
        raise ValueError("Not enough distinct timestamps for folds")
    folds = np.array_split(times, n_folds + 1)
    for fold in folds[1:]:
        start = fold[0]
        train = np.flatnonzero(((dates < start) & (ends < start)).to_numpy())
        test = np.flatnonzero(dates.isin(fold).to_numpy())
        if not len(train) or not len(test):
            raise ValueError("Empty fold after full-horizon purge; more history required")
        yield train, test


def proxy_metrics(gross, selected):
    gross = np.asarray(gross, dtype=float)
    selected = np.asarray(selected, dtype=bool)
    if gross.ndim != 1 or gross.shape != selected.shape or not np.isfinite(gross).all():
        raise ValueError("Aligned finite gross returns required")
    net = (gross[selected] - FEE) * 100
    return {"selected_entries": len(net), "mean_net_return_pct": float(net.mean()) if len(net) else None,
            "win_pct": float((net > 0).mean() * 100) if len(net) else None,
            "metric_scope": SCOPE}


def walk_forward(X, y, m, n_folds=5, threshold=0.55, rounds=50):
    if not 0 <= threshold <= 1 or not 1 <= rounds <= 300:
        raise ValueError("Invalid threshold/round budget")
    if len(X) != len(y) or len(X) != len(m) or not np.isfinite(X.to_numpy(dtype=float)).all() or not y.isin([-1, 0, 1]).all():
        raise ValueError("Aligned finite features/labels required")
    if "gross_return" not in m or not np.isfinite(m.gross_return).all():
        raise ValueError("Actual gross return metadata required; rebuild old dataset")
    order = np.argsort(m.date.to_numpy(), kind="stable")
    X, y, m = (d.iloc[order].reset_index(drop=True) for d in (X, y, m))
    splits = list(purged_splits(m, n_folds))  # Validate before any training.
    import lightgbm as lgb
    results = []
    for k, (tr, te) in enumerate(splits, 1):
        model = lgb.train({"objective": "multiclass", "num_class": 3, "learning_rate": .05,
                           "num_leaves": 31, "verbose": -1, "seed": 7, "num_threads": 2,
                           "deterministic": True, "force_col_wise": True},
                          lgb.Dataset(X.iloc[tr], label=(y.iloc[tr] + 1).astype(int)),
                          num_boost_round=rounds)
        probs = model.predict(X.iloc[te])[:, 2]
        metrics = proxy_metrics(m.gross_return.iloc[te], probs >= threshold)
        results.append({"fold": k, "train_rows": len(tr), "test_rows": len(te),
                        "train_label_end_max": str(m.label_end.iloc[tr].max()),
                        "test_start": str(m.date.iloc[te].min()), **metrics})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=ML)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--rounds", type=int, default=50)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=.55)
    args = parser.parse_args()
    X, y, m = load(args.dataset)
    report = {"approved": False, "reason": "pending out-of-sample validation",
              "rows": len(X), "metric_scope": SCOPE,
              "historical_artifacts": "Old unpurged evaluations invalid; rerun required"}
    if args.run:
        report["folds"] = walk_forward(X, y, m, args.folds, args.threshold, args.rounds)
    else:
        report["split_rows"] = [{"train": len(tr), "test": len(te)} for tr, te in purged_splits(m, args.folds)]
        report["note"] = "Validation only; no model trained"
    print(json.dumps(report, indent=1, allow_nan=False))


if __name__ == "__main__":
    main()
