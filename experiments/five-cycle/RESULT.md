# Five-cycle research verdict: no candidate approved

Goal not achieved: profitable forward paper trading is not demonstrated.

## Learning
Five expanding chronological LightGBM fits: zero approved candidates. A separate fixed-default logistic regression using ten causal price/volume/context features also made zero positive predictions in all five tests; this is abstention, not a successful trading strategy. Scaling and feature ranking were fit on training data only. These periods have now been researched and must not be described as a fresh untouched holdout.

Lowering the first LightGBM model threshold to 0.25 selected 441,000 overlapping historical label outcomes. Mean gross -0.00547%, mean after assumed 0.24% costs -0.24547%. This exploratory check is not 441,000 executable trades or portfolio return.

## Executable Gate futures baseline
Native 5m, rise 2% over 12 bars, TP6/SL3, six pairs, 100 USDT, fee 0.05% per side. Independent windows, not a continuous compound return:

| Window | Leverage | Trades | Wallet return |
|---|---:|---:|---:|
| Aug14–Aug30 | 1x | 32 | +10.0504% |
| Aug14–Aug30 | 2x | 55 | +9.9209% |
| Aug30–Sep16 | 1x | 14 | -2.4841% |
| Aug30–Sep16 | 2x | 17 | -0.5203% |

## Additional controls (Aug30 23:50–Sep16 23:40 UTC)
| Wallet | Leverage | Fee/side | Trades | Wallet return | USDT profit |
|---:|---:|---:|---:|---:|---:|
| 100 | 1x | 0 | 14 | -2.1445% | -2.1445 |
| 100 | 2x | 0 | 17 | +0.2623% | +0.2623 |
| 10 | 2x | 0.05% | 12 | -1.8656% | -0.18656 |
| 10 | 2x | 0.10% | 12 | -2.4028% | -0.24028 |

The actual $10 backtest differs from scaling the $100 result: 12 versus 17 trades. Baseline 1x loses even without trading fees; 2x's tiny fee-free gain disappears with fees. Funding remains in the zero-trading-fee controls. No new high leverage deployment justified.

$10 normal-cost mean trade return -0.502%; wallet return/day approximately -0.1098% over 16.993 days. These historical numbers are not a monthly forecast. Fee stress is not an explicit slippage/order-book model.

## Evidence and verification
- `run-20260918-000241/cycles.jsonl`: exactly five cycles.
- `logistic_results.json`: exactly five cycles, no entries.
- `freqtrade-baseline/summary.json`: four initial executable backtests.
- `freqtrade-baseline/controls/summary.json`: four additional executable backtests.
- Control extraction checks starting capital, entry fee, trade count and summed PnL against each archive. A missing-directory path had made Freqtrade interpret the result destination as a file prefix; actual archives were recovered without re-running or fabricating outputs.
- Live strategy, sidecar and config hashes remain unchanged.
- No models promoted; no real money used; no live configuration changed.

Next useful research requires a materially different predeclared signal/label and untouched time periods, not more thresholds optimized on these already-viewed results. Native 5m is the tested baseline, not proof that every faster strategy is impossible. Five research iterations are complete; profitable self-learning bot remains unproven.
