# Fixed-horizon return-learning experiment

Predeclared before this experiment's outcomes; prior market periods have already been researched, so this is retrospective chronological validation, not a virgin holdout.

Question: do simple causal price/volume features forecast the actual next-open to 60-minute-later-open return better than the prior asymmetric barrier classifier?

- Existing sklearn StandardScaler + Ridge(alpha=100), no new dependencies, no parameter search.
- BTC, ETH, SOL; Binance native 5m local history, Jan2024 onward.
- Reuse existing ten causal features; predict continuous gross return rather than a class whose base rate encourages never trading.
- Signal after candle close; simulated entry next candle open, exit exactly 12 bars later at open. Reject gaps spanning the label horizon. No intrabar stops or targets.
- Fit expanding data before each of Apr, May, Jun, Jul, Aug 2026. Purge labels ending on/after test start. Never fit a scaler on test data.
- Select only expected gross return >0.0034 (0.24% round-trip cost allowance plus 0.10% buffer). Threshold fixed, not tuned to observed trades.
- Portfolio: 10 USDT, one position, no leverage, compound 99% of cash, choose largest forecast among simultaneous pairs. Entry/exit commission assumption 0.12% per side inclusive of a simple cost allowance; fractional units, no venue minimums modeled. Thus this is a conservative cost-screening proxy, not exchange executable proof.
- Report all five months including no-trade months; acceptance requires >=30 total trades, >=4 profitable months, positive concatenated return, <=10% closed-equity drawdown. Also report unfiltered same-horizon gross returns and prediction ranges.
- If accepted, next gate is actual venue/order-minimum-aware Freqtrade replay and a future forward paper holdout, not immediate live promotion.
- No live files, balances, settings or strategies changed. Reject failure; never loosen threshold post hoc and call it a validated result.
