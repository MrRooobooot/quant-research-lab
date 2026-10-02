# Methodology

Every item below is backed by code or artifacts in this repository (or by protocols preserved in the experiment folders). Anything not present in the code is marked as a limitation instead of being described as fact.

## 1. Data

- **Source:** Binance public monthly klines dumps (`https://data.binance.vision/data/spot/monthly/klines/...`), spot timeframes 1m / 5m / 15m. The live panel separately polls exchanges in real time to build bars (15s bucketing).
- **Universes used:**
  - ML campaigns: 10 pairs (BTC, ETH, SOL, XRP, DOGE, ADA, LINK, LTC, AVAX, DOT).
  - Wide screen: 36 pairs with complete 1m data for the window (2 pairs dropped because they are not published on the dump mirror for that period; no synthesized candles).
  - Annual fixed-window replays: BTC/SOL.
  - Return-learning experiments: BTC, ETH, SOL.
- **Validation pipeline (implemented in the fetch/screen code, and in `check_replay.py` for replays):**
  - exact expected row counts per pair-window (e.g. 525,600 × 1m rows for an annual window), with exchange-listing gaps recorded per pair;
  - monotonic timestamps and OHLC sanity checks;
  - duplicate detection and removal (one repeated-day block was found in a public dump and dropped);
  - repair of a documented dump quirk: microsecond-epoch integers mislabeled as milliseconds (year 57637) remapped to milliseconds for isolated research copies; original sources untouched;
  - pairs failing the completeness bar (>2% missing candles, or listed late) are dropped from the universe and reported, never interpolated.
- **Honesty rule about periods:** windows that had already been researched are never described as virgin holdouts. Fresh-window OOS tests state explicitly that the data was never used before (e.g. the 2020–2023 decade for the momentum rule).

## 2. Cost model

- **Fees:** pinned at **0.1% per side (0.2% round trip)** in every backtest config (`"fee": 0.001`), so a run cannot silently inherit a different exchange default. OOS tests sweep **0.1% / 0.05% / 0%** per side to locate the fee cliff. Hourly return-learning variants use 0.12%/side; the ML cost proxy uses 0.2% round trip.
- **Slippage:** **no order-book or tick-level slippage model exists.** Backtests charge fees only; this is stated in every experiment's own result notes and repeated in `LIMITATIONS.md`. The live panel partially compensates with a realized-move gate (a calibration contract check measures achieved move size, not assumed).
- **Entry mechanics:** signal evaluated at candle close, simulated entry at **next candle open**; one position at a time (unless a multi-slot config is explicit); stop-first resolution on same-bar TP/SL ties; incomplete-horizon label rows dropped (v2 dataset).
- **Buy-and-hold comparator:** every OOS/annual test reports the buy-and-hold outcome on the same window.

## 3. Splits, walk-forward, and purging

- **ML folds:** 5 time-ordered **expanding** folds — train on all past chunks, test on the next chunk; the future never enters training.
- **Inner validation** is chronological and used only for model selection/diagnostics; **the outer test never selects thresholds** (stated in protocol docs; violated variations would be recorded as new exploratory experiments, not validation).
- **Purging (leakage control):** `purged_splits()` groups identical entry timestamps and **purges the full label horizon at every fold boundary** (a training row may not overlap the test window's label span). Empty folds raise an error instead of silently training on shrunk data.
- **Dataset versioning:** labels carry `label_end` (full information horizon — the field purging uses) and `exit_time` (actual barrier/timeout bar). Datasets are written as `v2_<schema-hash>_<utcstamp>` with a `label_schema.json`; **old unversioned artifacts are explicitly rejected for reuse, never overwritten.**
- **Leakage history:** the pre-purge evaluation runs were declared invalid (label-horizon leakage; percentage totals that were sums of overlapping hypothetical trades, not portfolio returns) and are kept in `experiments/walk-forward/` as historical artifacts, not as evidence. The fix lives in `experiments/leakage/` and is regression-locked by `check_training_safety.py` (asserts purged splits exist and behave).
- **Feature hygiene:** only causal price/volume/context features (gap metrics, RSI, realized vol, distance-to-high/low, hour-of-day; an efficiency-ratio regime feature in the 1h variant). Scalers are fit on training data only.

## 4. Acceptance and rejection criteria

Applied consistently (protocols preserved in `experiments/year-replay/`):

- **Activity screen:** ≥100 trades/year (a candidate whose natural frequency is ~2 trades/year is explicitly rejected as too sparse for the original goal — that is a scope decision, not a quality judgment).
- **Profit screen:** net-positive after 0.1% per-side fees **and** non-loss at zero fees. A family that only wins when fees vanish has no edge above cost.
- **Fresh-window rule:** any positive result must additionally survive a previously-unseen window before any approval claim. No optimize-until-green on a single window.
- **One bounded exploration per round**; the round's loser is appended to a ledger (`iteration_ledger.json`) and never retried with cosmetic changes.
- **Bounded budget:** max 6 rounds per campaign; if exhausted, the honest output is "goal not reached with this data/universe," reported once.
- **Stop conditions:** any real-money or live-config change requirement stops the loop.

## 5. Evaluation metrics

- Final wallet value, trade count, wins/losses, and **drawdown with an explicit distinction between trade-result (closed) drawdown and marked-equity drawdown** — the marked-equity number is the conservative one and is used in summaries.
- Per-trade **gross** vs **net-of-cost** means (the spread between them is the fee wall made visible).
- Buy-and-hold performance on the same window.
- Aggregate totals of overlapping hypothetical trades are **never** presented as portfolio returns; when such totals exist historically, both the number and its invalidity are reported together (aggregation-artifact correction; see `docs/RESULTS.md`).

## 6. Engineering-safety methodology (live panel)

- Deterministic watchdog (`health_watch.py --repair`) supervised by the OS service manager, with a state file and bounded repair actions; no LLM in the execution path (verified: zero LLM API references in execution code).
- `PRETRAIN_FLOOR` gate constants enforced in both `load_rules` and history retraining — a stale rules file cannot disarm entry gates.
- Self-healing feed loop: exceptions are logged to an alerts file and the loop continues.
- Manual interventions never mutate rules; only closed auto-trades feed the learning layer.
- Isolation discipline for checks: synthetic fixtures, temp directories, ephemeral localhost HTTP — no exchange network calls, no writes to live state (per check docstrings; executed and confirmed on 2026-10-03).

## 7. Non-claims

- No claim of future profitability, no forecast, no financial advice.
- No claim that "no strategy can ever work": the correct claim is that the tested families at these horizons failed these screens on these windows.
- No claim is promoted from HISTORICALLY VERIFIED to CURRENT without a re-run; the classification of each claim is kept in `docs/VERIFICATION.md`.
