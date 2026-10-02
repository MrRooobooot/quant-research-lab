#!/usr/bin/env python3
"""Generate a tiny synthetic OHLCV fixture (no market data involved).

Schema matches the research corpus bar columns: date, open, high, low, close, volume.
Deterministic: fixed seed, so regenerating produces byte-identical output.
Stdlib only. Self-checks (row count, monotonic timestamps, OHLC sanity) run on every execution.
"""
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROWS = 600
START = datetime(2026, 1, 1, tzinfo=timezone.utc)
STEP = timedelta(minutes=5)
SEED = 7
OUT = Path(__file__).with_name("synthetic-5m-sample.csv")


def main() -> None:
    rng = random.Random(SEED)
    price = 100.0
    t = START
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for _ in range(ROWS):
            o = price
            c = max(0.01, o * (1 + rng.gauss(0, 0.0015)))
            h = max(o, c) * (1 + abs(rng.gauss(0, 0.0008)))
            low = min(o, c) * (1 - abs(rng.gauss(0, 0.0008)))
            v = round(abs(rng.gauss(50, 20)) + 1, 3)
            w.writerow([t.isoformat(), f"{o:.4f}", f"{h:.4f}", f"{low:.4f}", f"{c:.4f}", v])
            price = c
            t += STEP

    rows = list(csv.DictReader(OUT.open()))
    assert len(rows) == ROWS, "row count mismatch"
    prev = ""
    for r in rows:
        assert r["date"] > prev, "timestamps must be strictly increasing"
        o, h, low, c = (float(r[k]) for k in ("open", "high", "low", "close"))
        assert low <= min(o, c) and max(o, c) <= h, "OHLC sanity violated"
        prev = r["date"]
    print(f"OK: {OUT.name}: {len(rows)} rows, deterministic seed {SEED}")


if __name__ == "__main__":
    main()
