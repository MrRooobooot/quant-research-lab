# quant-research-lab

Research workspace built around one question:

> **Does a retail-accessible short-horizon trading edge survive realistic fees, walk-forward validation, and out-of-sample testing?**

Short answer after five months of experiments: **no fee-surviving short-horizon edge was found on the tested venues, universes, and timeframes — and that negative result is documented, instrumented, and reproducible here rather than hidden.** The long-hold candidate that did measure positive over a 2.5-year backtest could not yet be confirmed out-of-sample at meaningful sample size.

**Status:** research and virtual-funds paper trading only. No real money was ever traded, no live deployment is provided or recommended, and nothing here is financial advice or a prediction of future returns.

---

## Overview

This repository turns a private quantitative research workspace into an auditable record of *how* it reached its conclusions:

- a **fee-wall analysis** showing why 1m–15m horizons are structurally fee-negative at retail fee tiers;
- a **walk-forward ML pipeline** (LightGBM, triple-barrier labels, purged expanding folds) that failed to beat costs, including a documented **label-leakage discovery and fix**;
- an **out-of-sample harness** (a fresh 2020–2023 decade and a fresh six-week window) that collapsed backtests which looked positive in-sample;
- a **live self-healing paper-trading panel** with a deterministic watchdog in the execution path (LLM automation was deliberately removed from it);
- a disciplined **falsification loop**: every rejected strategy is recorded, no result is re-litigated without new evidence, nothing is "tuned until green."

## Why fees come first — the fee wall

Median absolute move per candle vs a 0.2% round-trip retail cost (KuCoin fee tier used throughout, 0.1% per side):

| Timeframe | Median move | vs 0.2% round trip |
|---|---:|---|
| 1m | 0.024% | ❌ fee-dominated |
| 5m | 0.056% | ❌ |
| 15m | 0.098% | ❌ |
| 1h | 0.194% | ❌ (marginal) |
| 4h | 0.6% | ✅ |
| 1d | 2.0% | ✅ |

For this fee tier, **profitable timeframes start at 4h**. Everything the workspace tried at 1m–15m had to demonstrate per-trade edge above the round-trip cost; none did. This single table explains most of the negative results in this repository.

## Experimental design (summary)

- **Data:** Binance public monthly klines dumps (`data.binance.vision`), 1m/5m/15m, plus a locally polled live feed for the panel. Full validation pipeline (row-count grids, monotonicity, OHLC sanity, duplicate/gap repair) — see `docs/METHODOLOGY.md`.
- **Costs:** fees pinned at 0.1%/side in every backtest config, with 0.05%/0% sweeps for OOS tests. No order-book slippage model — stated as a limitation, not hidden.
- **Validation:** expanding chronological folds, train on past → test on next chunk; **purged splits** (full label horizons purged at fold boundaries); inner-validation used only for selection; outer test never used to select thresholds.
- **Acceptance:** ≥100 trades/year, net-positive after fees, non-loss at zero fee, and a positive result must additionally survive a fresh previously-unseen window before any approval claim.
- **Rejection is the default.** A loss is recorded in a ledger and never retried with cosmetic changes.

Full details: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Results (highlights)

Full tables, including every failed experiment: [`docs/RESULTS.md`](docs/RESULTS.md).

- **Annual wide screen (36 pairs, 5 strategy families, 100 USDT wallet):** every family finished between 1.71 and 22.20 USDT — all fee-negative, all rejected. Zero-fee control twins (only spent on fee-positive runs) were never earned.
- **Standalone OOS — fresh 2020–2023 BTC 5m decade:** a simple momentum rule (previously positive in-sample) returned **−84.0% at 0.1% fee, −64.2% even at zero fee**, vs buy-and-hold +486%. Verdict: `does_not_beat_buyhold`.
- **LightGBM ML campaign (2.8M samples, 10 pairs):** negative at every threshold. Old aggregate totals were later invalidated as *sums of overlapping hypothetical trades* (not portfolio returns) — the aggregation-artifact correction below.
- **Five chronological learning cycles:** zero approved candidates; diagnostics showed model abstention, not profitability.
- **Fixed-horizon and cross-sectional return learners:** rejected — the cross-sectional variant paid 0.24% round-trip on moves the model could not forecast, ending at 0.002 USDT from 10.
- **The one measured-positive path — NFI long-hold family:** +111.21% over a 2.5-year backtest (120 trades, 117W/3L, archived and SHA-256 verified). A fresh six-week OOS window produced **+0.07% on 1 trade** — positive but statistically meaningless; the recent-regime edge is **unproven at this sample size and stated as such**.

## Falsification — the actual chain

The central artifact of this repository is not a profitable system; it is the correction chain:

```
positive backtest
  → realistic cost model      → fee wall appears
  → walk-forward ML           → no fee-surviving signal
  → out-of-sample replay      → backtest collapse (2020–2023)
  → leakage discovery         → old ML splits had label-horizon leakage;
                                old totals were overlapping-trade sums
  → purge + dataset v2        → versioned datasets, purged folds, guarded by tests
  → aggregation-artifact fix  → +78% claim withdrawn → +111.21% continuous run
  → revised conclusion        → "current regime edge unproven at this sample size"
```

Specific corrections, all preserved in this repository rather than deleted:

- **Aggregation artifact:** an earlier "+78%" figure was withdrawn; the correct continuous-compounding replay of the same strategy is +111.21%. Both the mistake and the fix are documented.
- **Drawdown accounting:** trade-result drawdown (2.14%) was distinguished from marked-equity drawdown (≈7.3%) of the same run. The higher number is the honest one.
- **Label leakage:** old ML evaluations were declared invalid and kept as historical artifacts; the rebuilt v2 dataset carries `label_end` and purging metadata, and a regression check (`check_training_safety.py`) asserts purged splits exist.
- **Second-scale numbers** from a superseded script were withdrawn, not re-litigated.
- A **data-repair fix** (microsecond-epoch timestamps mislabeled as milliseconds in public dumps) was documented in the replay experiment.

## Engineering safety (live paper-trading panel)

The companion live lab (`panel/`) runs paper trades against real-time data. Its safety posture:

- **Deterministic watchdog replaced LLM automation in the execution path.** Scheduled LLM-driven automation was removed; a bounded deterministic `health_watch.py --repair` service (launchd-supervised) handles health now. Verified: zero LLM API references exist in any execution-path file.
- **Hard floor constants** (entry gates) are enforced in both the live rule loader and the history retrainer, so a stale `rules.json` cannot silently disarm them.
- **Self-healing loop:** any exception in the feed/engine is appended to an alerts log and the loop continues — no crash-restart at the exchange level.
- **Manual overrides are not bot lessons:** manually closed trades never mutate the rule set.
- **10 isolated self-checks** (bars log integrity, blind-gap flattening, calibration contract, entry gate, feed policy, fetch bound, move realism, rule proposals, server safety, training safety). They use synthetic fixtures, temp directories and an ephemeral localhost port: **no exchange network, no writes to live state.** All **10/10 executed green on 2026-10-03** — evidence in [`docs/VERIFICATION.md`](docs/VERIFICATION.md) and `docs/selfchecks-2026-10-03.log`.

## What did NOT work (kept on purpose)

- SMA-cross scalping family (1m–15m): 81 gate configurations, all negative (best BTC config −5.6%).
- Five strategy families on a widened 36-pair universe: all fee-negative.
- LightGBM on 2.8M samples: negative at every probability threshold; winner/rest probability separation only ~0.01–0.02.
- A fresh 2020–2023 decade OOS on a rule that looked good in-sample: loses even at zero fees.
- Fixed-horizon return learner: zero qualifying trades over five monthly tests.
- Cross-sectional top-1 learner: ≈ −0.11% per trade — exactly the fee drag.
- Five-cycle self-learning loop: abstention, no candidates.

## Conclusions

1. At 0.1%/side retail fees, **1m–15m horizons are structurally fee-dominated** on the tested venues; edges must first clear the round-trip cost, and none did.
2. **Walk-forward + purging + fresh-window OOS are non-negotiable.** Every result that looked good without them collapsed under them.
3. The only measured-positive family (long-hold, ~2.5%/month in backtest, 1–2 trades/week) remains **unconfirmed out-of-sample** and too sparse for the original frequent-trading goal; it is reported as a candidate, not a result.
4. Negative results, correctly recorded, are more valuable than unsupported positive ones. This repository optimizes for that.

## Limitations

Key ones (full list: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)): no order-book/tick slippage model; small OOS samples (1–2 trades) around the long-hold candidate; several windows were previously researched and are explicitly **not** virgin holdouts; single-machine, single-venue-pair setup; results are historical and say nothing about future returns.

## Reproducibility

- `experiments/datasets/` ships a **tiny synthetic OHLCV fixture** (stdlib generator, deterministic seed) demonstrating the expected schema. No third-party market data is redistributed in this repository.
- Panel self-checks run offline: see `panel/README.md` for the exact command.
- Full backtests require a local freqtrade install (not vendored here) plus public dumps from `data.binance.vision`; every experiment folder documents its own command and parameters.

## Repository structure

```
quant-research-lab/
├── README.md
├── LICENSE
├── .gitignore
├── docs/                  METHODOLOGY · RESULTS · LIMITATIONS · VERIFICATION
├── experiments/
│   ├── fee-wall/          fee-wall + wide-universe screen (code, protocol, results)
│   ├── walk-forward/      ML pipeline (v1, pre-purge) + findings
│   ├── leakage/           leakage fix: purged splits, versioned datasets, regression check
│   ├── oos/               fresh-window OOS tests (2020–2023 decade; NFI fresh month)
│   ├── year-replay/       accelerated annual paper replay + protocols + ledgers
│   ├── five-cycle/        five-cycle learning loop verdict + diagnostics
│   ├── return-learning/   fixed-horizon & cross-sectional learners (rejected)
│   └── datasets/          synthetic fixture + schema
├── panel/                 live paper-trading panel (sanitized) + 10 self-checks
└── configs/               sanitized example freqtrade configs (dry-run, no credentials)
```

## What is NOT in this repository

Deliberately excluded: third-party market-data corpora (1.3 GB+ local experiments), live databases, private logs and personal trading records, machine-specific launchd plists, exchange credentials (none existed in the source either — configs carry empty credential fields), the upstream freqtrade framework (used as an external dependency), and the third-party NFI strategy code (referenced by name in results only, never copied).

## Owner note

Research code and documentation written by Aidin Nemati (2026). The MIT license covers original code in this repository; it does not cover the referenced third-party projects (freqtrade, NostalgiaForInfinity) which are external and separately licensed.
