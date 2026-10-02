# Active rule diagnostic: trading works; profitability rejected

Same annual BTC/SOL data, 100 USDT virtual cash, native 5m SampleStrategy unchanged, real corrected 1m execution detail. This is a completed historical simulation, not a deployed live bot or learning model.

| Case | Trades | Days with entries | Final USDT | Net USDT |
|---|---:|---:|---:|---:|
| 0.1% per-side fee | 320 | 200 | 50.22243776 | -49.77756224 |
| Zero fees | 359 | 214 | 69.70698890 | -30.29301110 |

NFI's previous two-trade run reported zero rejected signals and zero canceled entries. Switching the strategy alone produced 320 completed trades with fees. This demonstrates functioning execution with much more activity; it does not isolate every NFI entry filter. The sample also loses without fees; reject this family on this window rather than deploying it or claiming a learned edge. No live config/service or real-money account changed.

Reporting bug: wallet feather's last snapshot retains holdings before final forced liquidation. Fee case snapshot 50.3234078376 differs from final realized cash 50.22243776 by 0.1009700776. Two terminal force_exit trades are present. Keep the snapshot metric distinct; daily.csv uses authoritative final_balance on its last day. Assert final_balance = initial balance + summed closed profit. Both runs pass trade sums, fees, 365 daily rows and no runtime ERROR/Traceback log checks.

Artifacts: active_fee/trades.csv, daily.csv, evidence.json, result ZIP; matching files in active_zero_fee. active_comparison.json contains both results. Persistent live paper trading with an active profitable strategy remains unmet.
