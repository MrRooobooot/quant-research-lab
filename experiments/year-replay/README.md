# year-replay — accelerated annual paper replay + iteration protocols

The annual replay camp: BTC/SOL, 2025-09-01 → 2026-08-31, 100 USDT virtual cash, native freqtrade engine, 0.1%/side fees, continuous wallet/positions, daily records. Everything here is **retrospective rule-based backtesting — virtual funds only** (stated in each result file; no live service was touched).

## Protocols (written before outcomes)

| File | Governs |
|---|---|
| `PROTOCOL.md` | Base annual replay design. |
| `ACTIVE_PROTOCOL.md` | Active-family diagnostic (full-activity run). |
| `CANDIDATE_PROTOCOL.md` | The sizing-improvement candidate. |
| `GRID_PROTOCOL.md` | Bounded grid screen. |
| `ITERATION_PROTOCOL.md` | Standing iteration rules (bounded rounds, ledger, stop conditions, acceptance screens). |

## Results

| File | Verdict |
|---|---|
| `RESULT.md` | Annual replay: candidate **unapproved** — profit concentrated in first half; sizing, not edge. |
| `ACTIVE_RESULT.md` | Active rule: **rejected** — loses with fees (−49.78 from 100) and even at zero fees (−30.29); reporting bug found & documented. |
| `CANDIDATE_RESULT.md` | Candidate evaluation detail. |
| `GRID_RESULT.md` | Grid screen outcome. |
| `GOAL_STATUS.md` | Standing-goal status: tuning path closed; two materially different paths remain (longer holding vs wider universe), both requiring scope decisions. |

## Code

`replay.py` (annual replay), `active.py`, `candidate.py`, `grid_screen.py`, `improve.py`, `iterate.py`, `verify_comparison.py`, and `check_replay.py` — the latter is a data-integrity check that **passes missing/duplicate/invalid-data rejection checks** (annual interval/OHLCV/warmup checks for higher-timeframe files; trade-sum, fee and daily-equity reconciliations in the runs).

## Ledgers & comparisons (audit trail)

`iteration_ledger.json` (every round's loser, never retried cosmetically), `comparison.json`, `active_comparison.json`, `verified_comparison.json`, `selection.json` (rejected/unapproved findings preserved), `buy_hold.json` (comparator), `manifest.json`/`minute_manifest.json` (run inventories), `config.json`.

## Notable honesty items preserved here

- The 1m files for this window had a real data error (microsecond epoch integers mislabeled as milliseconds → year 57637); corrected in isolated research copies only, sources untouched, exactly 525,600 real minutes per file.
- The 2-slot vs 1-slot "improvement" was selected after prefix inspection and is recorded as **not** validated (no fresh-holdout claim).
- Drawdown figures in the replay are engine wallet snapshots, explicitly "not tick-level worst loss or a forecast of risk."
