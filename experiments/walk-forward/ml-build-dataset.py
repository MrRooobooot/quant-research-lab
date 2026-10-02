#!/usr/bin/env python3
"""ML upgrade path for the panel — step 1: trainable features + labels from past data.

Builds a supervised dataset from the local Binance 5m history (2024-01 -> 2026-08, 10 pairs):
- features: the exact indicators the live panel computes (sma9/21 gap, RSI14, bar volatility,
  spread proxy) plus volume/return features — all computed identically to server.py
- label: triple-barrier outcome. +1 if price touches +0.8% before -0.4% within 60 bars,
  -1 if the opposite, 0 if neither (time exit). Fee-aware: |label|=1 requires the move to
  exceed the 0.2% round trip meaningfully (TP/SL already account for fees).

Output: features.parquet + labels.parquet in ~/freqtrade/panel/ml/ — ready for LightGBM.
"""
import glob, os
import numpy as np
import pandas as pd

DATA = os.path.expanduser("~/freqtrade/data/binance")
OUT = os.path.expanduser("~/freqtrade/panel/ml")
os.makedirs(OUT, exist_ok=True)

TP, SL, HORIZON = 0.008, -0.004, 60  # same as live panel (60 x 5m = 5h window)


def features_from(df):
    c = df["close"]
    v = df["volume"]
    f = pd.DataFrame(index=df.index)
    f["gap_pct"] = (c.rolling(9).mean() - c.rolling(21).mean()) / c.rolling(21).mean() * 100
    f["gap_slope"] = f["gap_pct"].diff(5)
    delta = c.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    dn = (-delta.clip(upper=0)).rolling(14).mean()
    f["rsi"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    f["bar_vol"] = c.pct_change().abs().rolling(30).mean() * 100
    f["ret_1"] = c.pct_change() * 100
    f["ret_12"] = c.pct_change(12) * 100
    f["vol_z"] = (v - v.rolling(60).mean()) / (v.rolling(60).std() + 1e-9)
    f["dist_high60"] = (c / c.rolling(60).max() - 1) * 100
    f["dist_low60"] = (c / c.rolling(60).min() - 1) * 100
    f["hour"] = df["date"].dt.hour
    return f


def triple_barrier_labels(df, tp=TP, sl=SL, horizon=HORIZON):
    """+1 / -1 / 0: which barrier is touched first within `horizon` bars (5m bars)."""
    c = df["close"].to_numpy()
    n = len(c)
    labels = np.zeros(n, dtype=np.int8)
    tp_a = c * (1 + tp)
    sl_a = c * (1 + sl)
    for i in range(n - horizon - 1):
        hi_seg = np.maximum.accumulate(c[i + 1:i + 1 + horizon])
        lo_seg = np.minimum.accumulate(c[i + 1:i + 1 + horizon])
        hit_tp = np.argmax(hi_seg >= tp_a[i]) if (hi_seg >= tp_a[i]).any() else horizon
        hit_sl = np.argmax(lo_seg <= sl_a[i]) if (lo_seg <= sl_a[i]).any() else horizon
        if hit_tp < hit_sl:
            labels[i] = 1
        elif hit_sl < hit_tp:
            labels[i] = -1
    return labels


def main():
    files = sorted(glob.glob(os.path.join(DATA, "*_USDT-5m.feather")))
    Xs, Ys, meta = [], [], []
    for path in files:
        sym = os.path.basename(path).replace("-5m.feather", "")
        df = pd.read_feather(path)
        ts = pd.to_datetime(df["date"]).astype("int64") // 1000
        df["date"] = pd.to_datetime(ts, unit="ms", utc=True)
        df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
        X = features_from(df)
        y = triple_barrier_labels(df)
        ok = X.notna().all(axis=1).to_numpy()
        Xs.append(X[ok])
        Ys.append(pd.Series(y[ok], name="label"))
        meta.append(pd.DataFrame({"pair": sym, "date": df.loc[ok, "date"]}))
        lab = pd.Series(y[ok]).value_counts().to_dict()
        print(f"{sym:12s} rows={ok.sum():7d}  labels: +1={lab.get(1,0):6d}  -1={lab.get(-1,0):6d}  0={lab.get(0,0):6d}")

    X = pd.concat(Xs, ignore_index=True)
    y = pd.concat(Ys, ignore_index=True)
    m = pd.concat(meta, ignore_index=True)
    X.to_parquet(os.path.join(OUT, "features.parquet"))
    y.to_frame().to_parquet(os.path.join(OUT, "labels.parquet"))
    m.to_parquet(os.path.join(OUT, "meta.parquet"))
    print(f"\nsaved {len(X)} samples x {X.shape[1]} features -> {OUT}")
    print("class balance:", y.value_counts().to_dict())


if __name__ == "__main__":
    main()
