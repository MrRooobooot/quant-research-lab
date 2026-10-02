#!/usr/bin/env python3
"""Offline safety regression checks. ALL fixtures are synthetic TEST DATA."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

import train
import build_dataset
import numpy as np
import pandas as pd


class SafetyChecks(unittest.TestCase):
    def test_dataset_requires_metadata_and_versioning(self):
        with tempfile.TemporaryDirectory(prefix="training-TEST-DATA-") as tmp:
            output = Path(tmp) / "ml"
            with patch.object(build_dataset, "OUT", output), patch.object(build_dataset, "DATA", tmp):
                pd.DataFrame({"date": pd.date_range("2025-01-01", periods=10, freq="5min", tz="UTC")}).to_feather(Path(tmp) / "FAKE-5m.feather")
                with self.assertRaises(ValueError):
                    build_dataset.main()
                self.assertFalse(list(output.glob("**/features.parquet")),
                                 "invalid source must not produce a dataset")
                self.assertTrue(build_dataset.dataset_version().startswith("v2_"))
                self.assertTrue(build_dataset.LABEL_SCHEMA["stop_first_same_bar"])
                with self.assertRaises(FileNotFoundError):
                    build_dataset.load_dataset(Path(tmp))
        # Current unversioned artifacts lack label metadata -> explicitly reject reuse.
        current = Path("~/freqtrade/panel/ml/features.parquet")
        if current.exists():
            with self.assertRaises(ValueError):
                build_dataset.load_dataset(Path("~/freqtrade/panel/ml"))

    def test_grouped_purged_ml_and_net_proxy(self):
        import train_lgbm
        self.assertTrue(hasattr(train_lgbm, "purged_splits"), "timestamp-grouped purged splits missing")
        dates = pd.date_range("2025-01-01", periods=30, freq="5min", tz="UTC").repeat(2)
        m = pd.DataFrame({"date": dates, "label_end": dates + pd.Timedelta(minutes=15)})
        for tr, te in train_lgbm.purged_splits(m, n_folds=2):
            self.assertLess(m.label_end.iloc[tr].max(), m.date.iloc[te].min())
            self.assertEqual(set(m.date.iloc[tr]) & set(m.date.iloc[te]), set())
            self.assertEqual(len(te) % 2, 0)
        result = train_lgbm.proxy_metrics(np.array([.003, -.004]), np.array([True, True]))
        self.assertAlmostEqual(result["mean_net_return_pct"], -.25)
        self.assertNotIn("total_pct", result)
        self.assertIn("NOT wallet return", result["metric_scope"])
        with self.assertRaises(ValueError):
            train_lgbm.load()

    def test_negative_pretrain_never_exports_rules(self):
        import pretrain
        self.assertTrue(hasattr(pretrain, "recommendation"), "explicit rejection missing")
        result = pretrain.recommendation({"avg_net_proxy_pct": -.1})
        self.assertEqual(result["status"], "rejected")
        self.assertIs(result["approved"], False)
        self.assertEqual(pretrain.recommendation({"avg_net_proxy_pct": .1})["status"], "pending_validation")
        with tempfile.TemporaryDirectory(prefix="training-TEST-DATA-") as tmp:
            fixture = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=40, freq="min", tz="UTC"),
                                    "close": np.full(40, 100.), "high": np.full(40, 100.),
                                    "low": np.full(40, 100.), "volume": np.full(40, 1.)})
            with patch.multiple(pretrain, ROOT=tmp, DATA=tmp), patch.object(sys, "argv", ["pretrain.py", "FAKE"]), contextlib.redirect_stdout(io.StringIO()):
                fixture.to_feather(Path(tmp) / "FAKE-1m.feather")
                pretrain.main()
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["FAKE-1m.feather"])

    def test_dataset_roundtrip_and_no_future_features(self):
        n = 180
        dates = pd.date_range("2025-01-01", periods=n, freq="5min", tz="UTC")
        close = 100 + np.sin(np.arange(n))
        df = pd.DataFrame({"date": dates, "close": close, "high": close + .2,
                           "low": close - .2, "volume": np.ones(n)})
        changed = df.copy()
        changed.loc[121:, "close"] *= 2
        pd.testing.assert_frame_equal(build_dataset.features_from(df).iloc[:121],
                                      build_dataset.features_from(changed).iloc[:121])
        with tempfile.TemporaryDirectory(prefix="training-TEST-DATA-") as tmp:
            out = Path(tmp) / "ml"
            df.to_feather(Path(tmp) / "FAKE_USDT-5m.feather")
            with patch.multiple(build_dataset, OUT=out, DATA=tmp), contextlib.redirect_stdout(io.StringIO()):
                build_dataset.main()
            folder = next(out.iterdir())
            X, L, M = build_dataset.load_dataset(folder)
            self.assertEqual(len(X), 61)
            self.assertEqual(M.date.iloc[-1], dates[119])
            self.assertEqual(M.label_end.iloc[-1], dates[179])
            # Tampering with horizon metadata must fail closed before training.
            M.loc[0, "label_end"] = M.loc[0, "date"]
            M.to_parquet(folder / "meta.parquet")
            with self.assertRaises(ValueError):
                build_dataset.load_dataset(folder)

    def test_pretrain_barriers_and_dates(self):
        import pretrain
        n = 34
        df = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=n, freq="min", tz="UTC"),
                           "close": np.full(n, 100.), "high": np.full(n, 100.),
                           "low": np.full(n, 100.), "volume": np.ones(n),
                           "fresh_up": np.arange(n) == 30, "gap_pct": np.ones(n),
                           "bar_vol": np.ones(n), "rsi": np.full(n, 50.)})
        df.loc[31, ["high", "low"]] = [102, 99]
        self.assertEqual(pretrain.simulate(df, 0, 0, 100, horizon_bars=2), [-.6])
        with tempfile.TemporaryDirectory(prefix="training-TEST-DATA-") as tmp:
            df.to_feather(Path(tmp) / "FAKE-1m.feather")
            with patch.object(pretrain, "DATA", tmp):
                self.assertEqual(pretrain.load_pair("FAKE").date.iloc[0], df.date.iloc[0])

    def test_barriers_drop_tail_and_record_horizon(self):
        df = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=5, freq="5min", tz="UTC"),
                           "close": [100, 100, 100.2, 100.3, 100.4],
                           "high": [100, 102, 100.2, 100.3, 100.4],
                           "low": [100, 99, 100, 100.1, 100.2]})
        labels = build_dataset.triple_barrier_labels(df, horizon=2)
        self.assertIsInstance(labels, pd.DataFrame, "labels require end timestamps and actual returns")
        self.assertEqual(labels.index.tolist(), [0, 1, 2])
        self.assertEqual(labels.label.tolist(), [-1, 0, 0])
        self.assertAlmostEqual(labels.gross_return.iloc[0], -.004)
        self.assertAlmostEqual(labels.gross_return.iloc[1], .003)
        self.assertEqual(labels.label_end.tolist(), df.date.iloc[2:].tolist())
        self.assertEqual(labels.exit_time.iloc[0], df.date.iloc[1])
        with self.assertRaises(ValueError):
            build_dataset.triple_barrier_labels(df.assign(high=float("inf")), horizon=2)

    def test_trade_eligibility_and_order(self):
        with tempfile.TemporaryDirectory(prefix="training-TEST-DATA-") as tmp:
            db = str(Path(tmp) / "panel.db")
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE trades(opened_ms INTEGER, closed_ms INTEGER, pnl_pct REAL, e_gap REAL, e_rsi REAL, e_vol REAL, open_reason TEXT, close_reason TEXT)")
                conn.executemany("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?)", [
                    (20, 30, 2, .1, 60, .03, "sma_cross_up", "tp"),
                    (float("inf"), float("inf"), 95, .1, 60, .03, "sma_cross_up", "tp"),
                    (-float("inf"), 5, 94, .1, 60, .03, "sma_cross_up", "tp"),
                    (1, 2, 93, "bad", 60, .03, "sma_cross_up", "tp"),
                    (1, 2, 92, .1, 60, .03, "manual_open", "tp"),
                    (1, 2, 91, .1, 60, .03, "sma_cross_up", "manual_close"),
                    (1, 2, 99, .1, 60, .03, "manual", "tp"),
                    (3, 4, 98, .1, 60, .03, "sma_cross_up", "manual"),
                    (5, 6, float("inf"), .1, 60, .03, "sma_cross_up", "tp"),
                    (7, 8, 97, .1, None, .03, "sma_cross_up", "tp"),
                    (9, 10, 96, .1, 60, .03, None, "tp"),
                    (10, 11, 1, .1, 60, .03, "sma_cross_up", "tp")])
            with patch.object(train, "DB", db):
                self.assertEqual([r[0] for r in train.load_trades()], [1, 2])
        with self.assertRaises(ValueError):
            train.threshold_fit([1, float("inf")], [1, 2])
        with self.assertRaises(ValueError):
            train.threshold_fit([1], [1, 2])

    def test_apply_is_report_only(self):
        with tempfile.TemporaryDirectory(prefix="training-TEST-DATA-") as tmp:
            root = Path(tmp)
            rules = root / "rules.json"
            original = b'{"rules":{"min_gap_pct":0,"min_bar_vol_pct":0,"max_rsi_entry":100}}'
            rules.write_bytes(original)
            db = root / "panel.db"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE trades(opened_ms INTEGER, closed_ms INTEGER, pnl_pct REAL, e_gap REAL, e_rsi REAL, e_vol REAL, open_reason TEXT, close_reason TEXT)")
                conn.executemany("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?)", [
                    (i, i+1, 1, .1, 60, .03, "sma_cross_up", "tp") for i in range(6)])
            output = io.StringIO()
            with patch.multiple(train, ROOT=tmp, DB=str(db), RULES_FILE=str(rules)), patch.object(sys, "argv", ["train.py", "--apply"]), contextlib.redirect_stdout(output):
                train.main()
            self.assertEqual(rules.read_bytes(), original, "--apply mutated live rules")
            report = json.loads(output.getvalue())
            self.assertIs(report["approved"], False)
            self.assertEqual(report["reason"], "pending out-of-sample validation")
            self.assertTrue(report["candidates"])
            self.assertNotIn("rules", report)
            self.assertEqual(set(p.name for p in root.iterdir()), {"rules.json", "panel.db"})


if __name__ == "__main__":
    print("Synthetic TEST DATA only; no live service writes.")
    unittest.main()
