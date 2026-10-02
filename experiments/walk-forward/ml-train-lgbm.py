#!/usr/bin/env python3
"""Step 2: walk-forward LightGBM on the panel's triple-barrier dataset.

Time-ordered folds (no shuffling across time): train on past, test on next chunk.
Reports per-fold P(+1) calibration and a fee-aware backtest of the gated strategy:
enter only when SMA-cross fires AND model P(+1) >= threshold.
"""
import json, os
import numpy as np
import pandas as pd
import lightgbm as lgb

ROOT = os.path.dirname(os.path.abspath(__file__))
ML = os.path.join(ROOT, "ml")
FEE = 0.002
TP, SL, HORIZON = 0.008, -0.004, 60

FEATURES = ["gap_pct", "gap_slope", "rsi", "bar_vol", "ret_1", "ret_12", "vol_z",
            "dist_high60", "dist_low60", "hour"]


def load():
    X = pd.read_parquet(os.path.join(ML, "features.parquet"))
    y = pd.read_parquet(os.path.join(ML, "labels.parquet"))["label"]
    m = pd.read_parquet(os.path.join(ML, "meta.parquet"))
    return X[FEATURES], y, m


def walk_forward(X, y, m, n_folds=5, threshold=0.55):
    order = np.argsort(m["date"].to_numpy())  # rows are already time-sorted per pair, but sort globally
    X, y, m = X.iloc[order].reset_index(drop=True), y.iloc[order].reset_index(drop=True), m.iloc[order].reset_index(drop=True)
    # LightGBM multiclass wants labels 0..2: map -1->0, 0->1, +1->2
    y_enc = (y + 1).astype(int)
    UP, DOWN = 2, 0
    folds = np.array_split(np.arange(len(X)), n_folds + 1)
    results = []
    for k in range(1, n_folds + 1):
        test_idx = folds[k]
        train_idx = np.concatenate(folds[:k])
        dtrain = lgb.Dataset(X.iloc[train_idx], label=y_enc.iloc[train_idx])
        params = {"objective": "multiclass", "num_class": 3, "learning_rate": 0.05,
                  "num_leaves": 63, "verbose": -1, "seed": 7}
        model = lgb.train(params, dtrain, num_boost_round=300)
        probs = model.predict(X.iloc[test_idx])
        p_up = probs[:, UP]
        yt = y.iloc[test_idx].to_numpy()

        # fee-aware backtest: the model gates the SAME sma-cross entries the panel takes.
        # proxy here: enter when p_up >= threshold; outcome = triple-barrier label with fee.
        sel = p_up >= threshold
        n_trades = int(sel.sum())
        pnl = 0.0
        wins = 0
        for lab, p in zip(yt[sel], p_up[sel]):
            raw = TP if lab == 1 else (SL if lab == -1 else 0.0)
            pnl += (raw - FEE) * 100
            wins += 1 if (raw - FEE) > 0 else 0
        results.append({
            "fold": k, "test_rows": len(test_idx), "trades": n_trades,
            "win_pct": round(wins / n_trades * 100, 1) if n_trades else None,
            "total_pct": round(pnl, 2),
            "base_rate_up": round((yt == 1).mean() * 100, 2),
            "pred_up_rate": round(float(sel.mean()) * 100, 2),
            "mean_p_when_up": round(float(p_up[yt == 1].mean()), 3) if (yt == 1).any() else None,
            "mean_p_when_not": round(float(p_up[yt != 1].mean()), 3),
        })
        print(f"fold {k}: {results[-1]}")
    return results


def main():
    X, y, m = load()
    print(f"dataset: {len(X)} rows, label balance {y.value_counts().to_dict()}")
    for thr in (0.5, 0.55, 0.6):
        print(f"\n=== threshold {thr} ===")
        res = walk_forward(X, y, m, threshold=thr)
        tot_trades = sum(r["trades"] for r in res)
        tot_pnl = sum(r["total_pct"] for r in res)
        print(f"TOTAL: trades={tot_trades} total_pct={tot_pnl:.2f}")
        json.dump({"threshold": thr, "folds": res, "total_trades": tot_trades,
                   "total_pct": tot_pnl},
                  open(os.path.join(ML, f"lgbm_thr_{thr}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
