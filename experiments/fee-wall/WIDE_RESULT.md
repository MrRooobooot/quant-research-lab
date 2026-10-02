# Wide-universe screen: all five families fee-negative (36 pairs, annual)

Approved path 2 executed. Universe: 36 pairs with complete Binance 1m data (XMR, HYPE not published on data.binance.vision for 2025-09..2026-08; dropped, no synthesized candles). Window 2025-09-01→2026-08-31, wallet 100 USDT, 2 slots, fee 0.001/side, --cache none, native timeframes (1m Demo/Scalp; 15m Trend; 5m SampleStrategy/Strategy001). Data validated: exactly 525600 1m rows/pair, OHLC sanity, duplicates dropped (one repeated-day block in BBUSDT 2026-01 dump), microsecond-labeled dump repaired (BBUSDT quirk), 36/36 pairs complete after 4 fetch passes.

| family | trades | final USDT | verdict |
|---|---:|---:|---|
| Demo (1m RSI dip) | 4240 | 1.72 | REJECT |
| Scalp (1m) | 4156 | 1.71 | REJECT |
| Trend (15m EMA) | 1563 | 2.48 | REJECT |
| SampleStrategy (5m) | 480 | 22.20 | REJECT |
| Strategy001 (5m EMA) | 518 | 21.84 | REJECT |

Zero-fee twins were not reached: the protocol only spends them on fee-positive runs, and none occurred. Per-fee verdict matches the two-pair screen: widening the universe multiplied trade counts (480-4240/year) but did not produce a fee-surviving family. Per-trade edge stays below round-trip cost at 1m-15m horizons regardless of pair count. This closes the hypothesis "a fee-surviving active family exists elsewhere in this venue's majors". Both protocols (ITERATION, wide-screen) are now exhausted; the only measured-positive configurations remain NFI-style long holds (~+2.5%/month backtest, ~1-2 trades/week) - active and profitable are opposed on this universe at these timeframes.

Artifacts: wide_ledger.json, wide_console*.log, per-family config/command/run.log + result zips in wide_*/; data/binance (36 pairs 1m+5m+15m); download_report.json. No live bot/config touched; no real money. Disk freed: zips deleted after conversion; data ~1.6GB total.
