# five-cycle — self-learning loop verdict: no candidate approved

Five expanding chronological learning cycles over a 2.8M-row, 10-pair, 5m dataset **with full label-horizon purging** inside every fold.

## Verdict (from `RESULT.md`)

- Five fitted LightGBM models: **zero approved candidates**.
- A separate fixed-default logistic regression (ten causal features) made **zero positive predictions** in all five tests — abstention, not a trading strategy.
- Exploratory threshold-0.25 check: 441,000 overlapping label outcomes, mean gross −0.00547% vs assumed 0.24% costs → −0.24547%. Explicitly *not* 441,000 executable trades or a portfolio return.
- At the predeclared 0.50/0.55/0.60/0.65 thresholds every cycle selected **zero entries**; lower-threshold exploration was recorded as a new exploratory experiment (mean net −0.19% to −0.27%), not as validation.

## Executable gate-futures baseline (independent windows, not continuous compounding)

Native 5m, rise-2%-over-12-bars, TP6/SL3, six pairs, 100 USDT, fee 0.05%/side:

| Window | Leverage | Trades | Wallet return |
|---|---:|---:|---:|
| Aug14–Aug30 | 1x | 32 | +10.05% |
| Aug14–Aug30 | 2x | 55 | +9.92% |
| Aug30–Sep16 | 1x | 14 | −2.48% |
| Aug30–Sep16 | 2x | 17 | −0.52% |

Controls: 1x loses even at zero fees; 2x's fee-free +0.26% disappears with fees; $10 wallet ≈ −0.502% mean per trade (~−0.11%/day). **No leverage justification; no model promoted; live configs unchanged.**

## Verification trail (in `DIAGNOSTIC.md` + `RESULT.md`)

- `logistic_results.json`: exactly five cycles, no entries. `threshold_probe_result.json`: the exploratory check above.
- Control extraction checks reconciled starting capital, entry fee, trade count and summed PnL against each archive; a missing-directory path bug (freqtrade interpreting a result destination as a file prefix) was fixed by **recovering archives without re-running or fabricating outputs**.
- Live strategy/sidecar/config hashes unchanged.
- Diagnostic: model learns some class distinctions (test accuracy 0.617 vs majority 0.481) but predicted zero take-profit labels — accuracy without a tradable signal.

Deployment gate recorded: no model may be activated from these proxy scores; any future step requires execution-aware portfolio simulation on the actual venue, minimum-size checks, drawdown/cost stress, and future paper evidence. **Leverage does not create predictive edge.**

"Next useful research requires a materially different predeclared signal/label and untouched time periods, not more thresholds optimized on these already-viewed results."
