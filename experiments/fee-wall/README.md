# fee-wall — why short horizons lose, and whether any family escapes

Two related experiments, both concluded **negative**:

1. **Fee wall quantification** — median candle move vs 0.2% round-trip cost, per timeframe. Result: 1m–15m and (marginally) 1h are fee-dominated; profitable timeframes start at 4h. Source artifacts: panel verdicts (kept with the workspace) and the wide-screen protocol below.
2. **Wide-universe fee-survival screen** — 36 pairs, one year, five strategy families, predeclared protocol.

## Files

| File | What it is |
|---|---|
| `PROTOCOL.md` | Predeclared rules (universe, validation, acceptance, budget) — written before results. |
| `WIDE_RESULT.md` | Verdict: all five families fee-negative; hypothesis closed. |
| `wide_screen.py` | The screen harness (universe build, per-family runs, ledger). |
| `wide_ledger.json` | Per-family outcome ledger. |
| `universe.json`, `pairs.json` | The 36-pair universe (+ the pair list used). |
| `download_report.json` | Data provenance: per-pair download/validation record. |

## Key numbers

| Family | Trades | Final USDT (from 100) | Verdict |
|---|---:|---:|---|
| Demo (1m RSI dip) | 4,240 | 1.72 | REJECT |
| Scalp (1m) | 4,156 | 1.71 | REJECT |
| Trend (15m EMA) | 1,563 | 2.48 | REJECT |
| SampleStrategy (5m) | 480 | 22.20 | REJECT |
| Strategy001 (5m EMA) | 518 | 21.84 | REJECT |

Zero-fee twin runs (reserved for fee-positive candidates under the protocol) were never triggered — no candidate earned them.

## Re-running

Requires a local freqtrade install and ~1.6 GB of public Binance monthly dumps (see `PROTOCOL.md` for the exact validation: 525,600-row 1m annual grids, gap recording, drop-don't-interpolate policy). Historical run: September 2026.
