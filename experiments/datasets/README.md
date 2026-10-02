# datasets — schema + synthetic fixture

This folder ships **no market data** (exchange dumps are not redistributable here and the local corpus is GB-scale). Instead it documents the corpus schema and provides a tiny, deterministic, synthetic fixture demonstrating it.

## Schema (OHLCV bars)

| Column | Type | Notes |
|---|---|---|
| `date` | ISO-8601 timestamp (UTC) | bar open time; monotonic; no duplicates |
| `open` `high` `low` `close` | float | OHLC sanity: low ≤ min(open, close) ≤ max(open, close) ≤ high |
| `volume` | float | base volume |

Research corpus specifics (not shipped): Binance public monthly dumps, native 1m/5m/15m, validated to exact expected row counts per pair-window with gaps recorded (drop-don't-interpolate). ML datasets (v2) additionally carry `label_end` / `exit_time` per row — see `../leakage/`.

## Files

| File | What it is |
|---|---|
| `make_synthetic_sample.py` | Stdlib-only generator (fixed seed 7) of a 600-row 5m fixture, with built-in assert self-checks (row count, monotonic timestamps, OHLC sanity). |
| `synthetic-5m-sample.csv` | The generated fixture (regenerating is byte-identical). |

## Usage

```
python3 make_synthetic_sample.py
```

Prints `OK: synthetic-5m-sample.csv: 600 rows, deterministic seed 7` after its assertions pass.

Why synthetic: reproducibility without redistribution — anyone can run the generator and diff against the committed CSV; nobody needs exchange data to validate the format handling.
