# Accelerated annual paper replay: completed; improvement unvalidated

100 USDT virtual cash; BTC/SOL Binance prices; 2025-09-01 to 2026-08-31. Native Freqtrade, 5m NFI signals, continuous wallet/positions, 0.1% fee each side. Current KuCoin market constraints are used, not historical Binance execution rules. No live service changes. This is retrospective rule-based backtesting, not ML training or a live market simulation with measured slippage.

| Run | Final USDT | Trades | Daily rows |
|---|---:|---:|---:|
| Native 5m control | 105.45726309 | 2 | 365 |
| 1m execution detail, 2 slots | 101.32006448 | 2 | 365 |
| 1m execution detail, 1 slot | 102.69139268 | 2 | 365 |
| Equal-weight BTC/SOL holding, fees included | 61.85896196 | N/A | N/A |

One slot was selected from the first 181 days before the full minute-detail runs. Both strategies made all their profit in that prefix; second-half profit was zero. Higher returns reflect greater sizing, not demonstrated improved entry prediction. The 5m annual control was viewed before prefix selection; the period was previously researched. No fresh holdout claim. Candidate remains unapproved: two trades cannot establish a reliable edge.

Observed equity-snapshot drawdown: 0.04439% two slots, 0.04840% one slot. These are engine wallet snapshots, not tick-level worst loss or a forecast of risk. End timestamps are 2026-08-31 23:55 UTC: the engine ends on its last 5m candle, not a separate midnight quote. Daily reports have all 365 calendar dates. No forced exits. Five runs completed with no ERROR/Traceback log records; logs were inspected after execution, not continuously watched.

Fixed an actual data error: local 1m files held microsecond epoch integers mislabeled as milliseconds (year 57637). Converted isolated research copies only; both contain exactly 525600 real, ordered minutes. Original sources were untouched. Ten higher-timeframe files passed annual interval/OHLCV/warmup checks. check_replay.py passes missing/duplicate/invalid data rejection checks. Fees, starting wallets, trade-profit sums and daily final-equity reconciliation were asserted.

Commands/configs/logs/result ZIPs remain in each case folder. Daily downloadable report: detail_one/daily.csv. selection.json and comparison.json preserve rejected/unapproved findings. Main deliverable completed: one year replayed quickly with virtual funds and daily records. Strong recurring profitability and an adaptive day-by-day learning system were NOT achieved.
