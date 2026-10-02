# Results

All results are **historical** (September 2026 research runs; artifacts preserved in the matching `experiments/` folders) unless marked otherwise. The only currently-verified item is the panel self-check suite — see `VERIFICATION.md`. Nothing here is a forecast; nothing here is financial advice.

Status legend: **[R] reproduced/rerunnable** · **[A] archived artifact** · **[I] invalidated historical artifact (kept for honesty)**

---

## 1. The fee wall (why 1m–15m fail)

Median absolute candle move vs the 0.2% round-trip fee used throughout:

| Timeframe | Median move | Verdict |
|---|---:|---|
| 1m | 0.024% | fee-dominated ❌ |
| 5m | 0.056% | ❌ |
| 15m | 0.098% | ❌ |
| 1h | 0.194% | marginal ❌ |
| 4h | 0.6% | ✅ |
| 1d | 2.0% | ✅ |

Profitable timeframes for this fee tier start at 4h. Every short-horizon experiment below is a variation of hitting this wall. **[A: panel verdicts + wide-screen protocol]**

## 2. Active strategies, annual replay (BTC/SOL, 100 USDT, 2025-09 → 2026-08)

Accelerated annual paper replay (`experiments/year-replay/`): continuous wallet, native 5m strategy, 0.1%/side fees.

| Run | Final USDT | Trades |
|---|---:|---:|
| Native 5m control | 105.46 | 2 |
| 1m execution detail, 2 slots | 101.32 | 2 |
| 1m execution detail, 1 slot | 102.69 | 2 |
| Equal-weight BTC/SOL buy-and-hold, fees included | 61.86 | — |

The candidate ("improved" slot sizing) was **NOT approved**: both runs made all profit in the first half of the year, the slot-1 selection happened after prefix inspection, and two trades cannot establish an edge. Higher returns reflect sizing, not better entry prediction. **[A: RESULT.md, ACTIVE_RESULT.md, selection.json, comparison.json]**

Same year, same data — the plain active rule (SMA-cross family), full activity, rejected:

| Case | Trades | Days with entries | Final USDT | Net |
|---|---:|---:|---:|---:|
| 0.1% per-side fee | 320 | 200 | 50.22 | −49.78 |
| Zero fees | 359 | 214 | 69.71 | −30.29 |

A family that **loses even at zero fees** on this window cannot be rescued by fee engineering. Rejected as a family. (A reporting bug — the wallet snapshot retaining open holdings vs final realized cash — was found and documented; daily rows use the authoritative reconciliation.) **[A: ACTIVE_RESULT.md]**

## 3. Wide-universe screen — fee survival elsewhere? (36 pairs, annual)

Predeclared protocol: same acceptance rule, widened universe, zero-fee twins reserved for fee-positive runs only.

| Family | Trades | Final USDT (from 100) | Verdict |
|---|---:|---:|---|
| Demo (1m RSI dip) | 4,240 | 1.72 | REJECT |
| Scalp (1m) | 4,156 | 1.71 | REJECT |
| Trend (15m EMA) | 1,563 | 2.48 | REJECT |
| SampleStrategy (5m) | 480 | 22.20 | REJECT |
| Strategy001 (5m EMA) | 518 | 21.84 | REJECT |

The zero-fee twin step was never earned (protocol spends it only on fee-positive runs). Widening the universe multiplied trade counts but produced no fee-surviving family — evidence that the per-trade edge stays below round-trip cost at 1m–15m **regardless of pair count**. Hypothesis "a fee-surviving active family exists elsewhere in this venue's majors" **closed**. **[A: wide-screen/WIDE_RESULT.md, wide_ledger.json]**

Complementary grid: 81 gate configurations of the SMA9/21 entry family over 1y of 1m data — all negative (BTC best −5.6%). **[A: panel verdicts]**

## 4. Out-of-sample collapse (fresh 2020–2023 decade, BTC 5m)

The same "rise-2%-over-12-bars" rule that looked usable in earlier windows, tested on a decade it had never seen (407 trades; stop-first; next-open entries):

| Fee per side | Final wallet (from 1.0) | Return | Max DD |
|---|---:|---:|---:|
| 0.1% | 1.6007 | **−84.0%** | 99.9% |
| 0.05% | 2.3957 | −76.0% | 99.8% |
| 0.0% | 3.5847 | **−64.2%** | 99.8% |

Buy-and-hold on the same window: **+486%**. Verdict, stored in the artifact itself: `does_not_beat_buyhold`, `deployment_approved: false`. Yearly strategy returns: 2020 −32.7%, 2021 −60.0%, 2022 −44.6%, 2023 +13.3%. The strategy loses **even with zero fees** — the signal itself did not survive the decade. **[A: oos_result.json, oos_test.py]**

## 5. ML campaign (LightGBM, walk-forward) — and its invalidation

First-generation evaluation (2.8M samples, 10 pairs, 5m, 5 time-ordered folds, triple-barrier labels, 0.2% round-trip cost assumption):

| Probability threshold | Trades (aggregate) | Aggregate % **[I]** |
|---|---:|---:|
| 0.50 | 22,739 | −2,260 |
| 0.55 | — | −620 |
| 0.60 | — | −129 |

**[I] Invalidation:** these percentage totals were later found to be **sums of overlapping hypothetical trade returns — not portfolio returns** — and the pre-purge splits additionally had **label-horizon leakage**. The numbers are preserved as historical artifacts, explicitly marked invalid, and are superseded by the purged pipeline. What survived the correction: the qualitative conclusion (no fee-surviving signal) and the diagnostic that probability separation between winners and the rest was only ~0.01–0.02 — far too weak to clear a 0.2% round trip. **[I/A: experiments/walk-forward/]**

Fix (see `experiments/leakage/`): `purged_splits()` with full label-horizon purging, versioned datasets with `label_end` metadata, regression check asserting purge behavior. **[R-ish: code + check_training_safety.py passes]**

## 6. Five-cycle learning loop verdict

Five expanding chronological LightGBM fits (466,700 → 2,335,841 training rows, full-horizon purge): **zero approved candidates**. A separate logistic-regression model made **zero positive predictions** in all five tests — abstention, not a trading strategy. Exploratory threshold-0.25 check: 441,000 overlapping label outcomes, mean gross −0.00547% vs assumed 0.24% costs → −0.24547% (explicitly *not* an executable-trades result).

Executable gate-futures baseline (independent windows, native 5m, six pairs, 0.05%/side):

| Window | Leverage | Trades | Wallet return |
|---|---:|---:|---:|
| Aug14–Aug30 | 1x | 32 | +10.05% |
| Aug14–Aug30 | 2x | 55 | +9.92% |
| Aug30–Sep16 | 1x | 14 | −2.48% |
| Aug30–Sep16 | 2x | 17 | −0.52% |

Controls: the 1x baseline loses even without fees; the 2x fee-free gain (+0.26%) disappears at 0.05% and is worse at 0.10%; the $10 wallet costs ≈ −0.502% mean per trade (~−0.11%/day). No leverage justification, no model promoted, no live config changed. **[A: five-cycle/RESULT.md, DIAGNOSTIC.md]**

## 7. Return learning (fixed-horizon and cross-sectional) — rejected

Fixed-horizon Ridge learner (predict the continuous 1h-ahead return, expect >0.34% gross before trading: 0.24% round-trip + 0.10% buffer). Five monthly chronological tests, Apr–Aug 2026:

| Test month | Training rows | Max predicted gross | Trades |
|---|---:|---:|---:|
| April | 709,114 | 0.117% | 0 |
| May | 735,034 | 0.093% | 0 |
| June | 761,816 | 0.270% | 0 |
| July | 787,736 | 0.084% | 0 |
| August | 814,520 | 0.326% | 0 |

Zero qualifying trades in every month — the model never forecast a move worth paying fees for. Diagnostics confirmed the executor works (forcing the best forecast executes and reconciles fees); this is abstention, not a broken pipeline. **[A: return-learning/RESULT.md, abstention_diagnostic.json]**

Cross-sectional variant (forced trade every bar, best of 3 assets, 12-bar hold, 0.12%/side):

| Month | Trades | Wins | Net USDT |
|---|---:|---:|---:|
| April | 719 | 163 | −8.20 |
| May | 743 | 157 | −1.50 |
| June | 719 | 221 | −0.25 |
| July | 743 | 188 | −0.04 |
| August | 743 | 182 | −0.01 |

Final wallet: **0.002 USDT** from 10. Average net ≈ −0.11% per trade — the fee drag, made visible. **[A: CROSSSECTION_RESULT.md]**

## 8. The one measured-positive candidate (NFI long-hold) — and its missing OOS confirmation

Long-hold dip-buy family (external third-party strategy, referenced not bundled):

- **2.5-year backtest archive:** 120 trades, 117W/3L, **+111.21%**, 5 slots, 0.1%/side. Result ZIP archived with SHA-256 `385bf358b16d…` (full hash in `nfi_original_evidence.json`); archived copy verified identical. **[A]**
- **Marked-equity vs trade-result drawdown correction:** the correct marked-equity drawdown of this run is ≈7.3%, not the 2.14% trade-result figure (see corrections ledger). **[A]**
- **Fresh six-week OOS** (2026-08 → 2026-09, data the run never saw): **1 trade, +0.07%, 1W/0L**. Positive but tiny — the strategy's own entry rate is ~0.02/day, so one trade in six weeks is by design, and **the recent-regime edge remains unproven at this sample size** (consistent with an earlier 63-day window on 39 pairs: −4.18%). **[A: nfi_fresh_month_RESULT.md, both evidence.json]**
- A separate 148-day, 39-pair backtest: +11.31% (31 trades, 29W/2L, marked DD 6.95%). **[A: nfi_39pair_148d.json]**

Honest framing, as recorded in the workspace: "positive after 30 months of backtest, unconfirmed out-of-sample, sparse by design — a candidate, not a result."

## 9. Corrections ledger (kept, not hidden)

| Correction | Wrong version | Correct version |
|---|---|---|
| Aggregation artifact | "+78%" (sum of windows) | **+111.21%** continuous compounding |
| Drawdown accounting | 2.14% (trade-result) quoted as DD | **≈7.3% marked-equity** is the honest figure |
| ML totals | aggregate % as if portfolio return | **overlapping hypothetical trades** — invalid as portfolio return |
| ML splits (pre-purge) | label-horizon leakage | **purged splits**; old artifacts invalidated |
| Second-scale results | superseded script numbers | **withdrawn** |
| Data integrity | microsecond-epoch timestamps mislabeled as ms (year 57637) | remapped for research copies; sources untouched |
| Replay reporting | wallet snapshot vs realized cash mismatch ($0.10) | reconciled; daily rows use final balance |

## 10. What remains NOT VERIFIED

- The long-hold candidate's edge in the **current regime** (sample too small: 1–4 recent trades).
- Any claim of the form "X makes money" — no system in this workspace has demonstrated sustained forward paper profitability.
- Anything about **future** returns. This repository contains no forecast and no financial advice.
