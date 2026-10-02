#!/usr/bin/env python3
"""ML upgrade path — supervised dataset from local Binance 5m history.

Labels: complete-horizon triple-barrier over OHLC (stop-first on same-bar ties),
timeout rows exit at the horizon close. Every label row carries label_end (full
information horizon, used for purging) and exit_time (actual barrier/timeout bar).

Output: versioned ml/v2_<utcstamp>/{features,labels,meta}.parquet + label_schema.json.
Old unversioned artifacts are explicitly REJECTED for reuse, never overwritten.
"""
import glob
import hashlib
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.expanduser("~/freqtrade/data/binance")
OUT = os.path.join(ROOT, "ml")

TP, SL, HORIZON = 0.008, -0.004, 60
LABEL_SCHEMA = {"tp": TP, "sl": SL, "horizon_bars": HORIZON, "stop_first_same_bar": True,
                "timeout_exit": "close_at_horizon", "incomplete_horizon_rows": "dropped",
                "gross_only": "NOT wallet return"}


def label_schema_hash():
    return hashlib.sha256(json.dumps(LABEL_SCHEMA, sort_keys=True).encode()).hexdigest()[:12]


def dataset_version():
    return f"v2_{label_schema_hash()}"


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
    """Complete-horizon OHLC proxy; same-bar ties stop first, no wallet simulation.

    label_end is the FULL information horizon (even for an early exit), for purging.
    Entry assumes the current close. Barrier fills omit slippage/gaps/spread.
    """
    if not isinstance(horizon, int) or horizon < 1 or not np.isfinite([tp, sl]).all() or not -1 < sl < 0 < tp:
        raise ValueError("Invalid barriers/horizon")
    prices = df[["close", "high", "low"]].to_numpy(dtype=float)
    dates = pd.to_datetime(df["date"], utc=True)
    if (not np.isfinite(prices).all() or (prices <= 0).any()
            or (df.high < df.close).any() or (df.low > df.close).any()
            or dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing):
        raise ValueError("Finite valid prices and strictly chronological dates required")
    c, high, low = prices.T
    n = max(0, len(c) - horizon)
    entry = c[:n]
    labels = np.zeros(n, dtype=np.int8)
    gross = c[horizon:] / entry - 1
    exit_pos = np.arange(n) + horizon
    active = np.ones(n, dtype=bool)
    # Vectorize across entries, bounded memory O(rows), not rows * horizon.
    for step in range(1, horizon + 1):
        stop = active & (low[step:step+n] <= entry * (1 + sl))
        take = active & ~stop & (high[step:step+n] >= entry * (1 + tp))
        labels[stop], labels[take] = -1, 1
        gross[stop], gross[take] = sl, tp
        exit_pos[stop | take] = np.flatnonzero(stop | take) + step
        active[stop | take] = False
    return pd.DataFrame({"label": labels, "gross_return": gross,
                         "label_end": dates.iloc[horizon:].to_numpy(),
                         "exit_time": dates.iloc[exit_pos].to_numpy()}, index=df.index[:n])


def load_dataset(ml_dir=OUT):
    """Load features/labels/meta ONLY if they carry the current label schema metadata."""
    labels = pd.read_parquet(os.path.join(ml_dir, "labels.parquet"))
    meta = pd.read_parquet(os.path.join(ml_dir, "meta.parquet"))
    schema_path = os.path.join(ml_dir, "label_schema.json")
    schema = {}
    if os.path.exists(schema_path):
        with open(schema_path, encoding="utf-8") as stream:
            schema = json.load(stream)
    if not ({"label", "gross_return", "label_end", "exit_time"}.issubset(labels.columns)
            and {"pair", "date", "label_end"}.issubset(meta.columns)
            and schema.get("label_schema_sha") == label_schema_hash()
            and schema.get("label_schema") == LABEL_SCHEMA):
        raise ValueError(f"{ml_dir}: dataset lacks required label metadata (label_end/schema) — "
                         "explicitly rejected; rebuild with build_dataset.py, no silent reuse")
    X = pd.read_parquet(os.path.join(ml_dir, "features.parquet"))
    if len(X) != len(labels) or len(labels) != len(meta):
        raise ValueError("features/labels/meta misaligned")
    dates = pd.to_datetime(meta.date, utc=True)
    ends = pd.to_datetime(meta.label_end, utc=True)
    exits = pd.to_datetime(labels.exit_time, utc=True)
    if (not len(X) or not np.isfinite(X.to_numpy(dtype=float)).all()
            or not np.isfinite(labels.gross_return).all() or not labels.label.isin([-1, 0, 1]).all()
            or dates.isna().any() or ends.isna().any() or exits.isna().any()
            or not ends.equals(pd.to_datetime(labels.label_end, utc=True))
            or (ends <= dates).any() or (exits <= dates).any() or (exits > ends).any()
            or meta.duplicated(["pair", "date"]).any()):
        raise ValueError("Invalid or misaligned finite data/label horizon metadata")
    return X, labels, meta


def main():
    files = sorted(glob.glob(os.path.join(DATA, "*-5m.feather")))
    if not files:
        raise SystemExit(f"no source feather files under {DATA} — old artifacts left untouched")
    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d-%H%M%S")
    out = os.path.join(OUT, f"{dataset_version()}_{stamp}")
    os.makedirs(out, exist_ok=False)
    Xs, Ls, Ms = [], [], []
    for path in files:
        sym = os.path.basename(path).replace("-5m.feather", "")
        df = pd.read_feather(path)
        required = {"date", "close", "high", "low", "volume"}
        if not required.issubset(df.columns):
            raise ValueError(f"{path}: missing OHLCV source columns")
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").reset_index(drop=True)
        if not np.isfinite(df["volume"]).all() or (df["volume"] < 0).any():
            raise ValueError(f"{path}: invalid volume")
        X = features_from(df)
        L = triple_barrier_labels(df)
        ok = X.notna().all(axis=1).to_numpy()[:len(L)]
        Xs.append(X.iloc[:len(L)][ok])
        Ls.append(L[ok])
        Ms.append(pd.DataFrame({"pair": sym, "date": df["date"].iloc[:len(L)][ok].to_numpy(),
                                "label_end": L.label_end[ok].to_numpy()}))
        lab = L.label[ok].value_counts().to_dict()
        print(f"{sym:12s} rows={int(ok.sum()):7d}  +1={lab.get(1, 0):6d}  -1={lab.get(-1, 0):6d}  0={lab.get(0, 0):6d}")
    X = pd.concat(Xs, ignore_index=True)
    L = pd.concat(Ls, ignore_index=True)
    M = pd.concat(Ms, ignore_index=True)
    X.to_parquet(os.path.join(out, "features.parquet"))
    L.to_parquet(os.path.join(out, "labels.parquet"))
    M.to_parquet(os.path.join(out, "meta.parquet"))
    schema = {"label_schema": LABEL_SCHEMA, "label_schema_sha": label_schema_hash(),
              "dataset_version": dataset_version(), "built_utc": stamp,
              "source_files": [os.path.basename(p) for p in files], "rows": len(X),
              "note": "proxy labels; gross_return is NOT wallet return"}
    with open(os.path.join(out, "label_schema.json"), "w", encoding="utf-8") as stream:
        json.dump(schema, stream, indent=1, allow_nan=False)
    print(f"saved {len(X)} rows -> {out} (schema {label_schema_hash()}); previous artifacts untouched")


if __name__ == "__main__":
    main()
