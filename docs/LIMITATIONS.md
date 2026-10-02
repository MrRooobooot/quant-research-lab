# Limitations

Written to be read before any number in this repository is reused. The research optimizes for rigor; its boundaries are part of the result.

## Methodological

1. **No slippage / order-book model.** Backtests charge fees (0.1%/side typical; sweeps where stated) and nothing else. Real fills move against you, especially at size. Every conclusion that leans on "close to the fee line" (1h, marginally 4h) is optimistic. The live panel partially compensates with a realized-move gate, but that is a live proxy, not a backtest model.
2. **Aggregate percentages of overlapping trades are not portfolio returns.** Where historical artifacts did this, they are explicitly marked invalid (see RESULTS §5). Any reader reuse of those old numbers as portfolio returns would be wrong.
3. **Windows were often previously researched.** Expanding chronological validation inside already-seen periods is weaker than a virgin holdout; the repo labels each case honestly. The fresh-window tests (2020–2023 decade; NFI six-week OOS) are the strongest evidence here precisely because the data was never used before — and they are the ones that collapsed.
4. **Small samples at the candidate.** The one measured-positive family has 1–4 recent trades. No confidence interval of any practical width. "Unproven" is the correct state, not "promising".
5. **No short-side, funding-rate, or derivatives modeling** in the standalone experiments (the five-cycle gate-futures baseline is the only leveraged/derivative-touching set, and it was rejected).
6. **Venue constraints approximated.** No exchange minimum order sizes or lot quantization in the return-learning experiments (stated there as "conservative cost-screening proxy, not exchange executable proof"). KuCoin constraints are used for replays even where historical Binance execution rules would have applied.
7. **Single-machine, single-operator.** No distributed compute, no fault-tolerant reruns; one data corpus, one venue tier, one fee tier (retail 0.1%/side). Results may not transfer to other fee tiers — in fact the fee-wall logic says higher tiers make short horizons *worse*, lower tiers are untested.
8. **Feature set intentionally small.** ~10 causal features, no alternative data, no order-flow, no news, no cross-sectional fundamentals. The LightGBM negative may be about this feature set as much as about markets.
9. **LightGBM negative is threshold-family specific.** Running more thresholds on already-viewed data would be exploration, not validation; the repo records it as such rather than claiming universality.
10. **Checks/tests prove internal consistency, not profitability.** check suites assert plumbing (alignment, purging, isolation); math errors caught earlier (aggregation artifact, drawdown accounting, replay reporting bug) show why this matters, but passing checks says nothing about edge.

## Results-specific

11. **Buy-and-hold comparisons** are single-window and unhedged; they are context, not benchmarks in a professional sense.
12. **The 36-pair screen** dropped or repaired data per protocol (2 pairs unpublished on the mirror; one duplicate day block; one timestamp-encoding quirk) — every drop is recorded in its artifacts, none were papered over or synthesized.
13. **Five-cycle baseline numbers** are independent windows, explicitly not a continuous compound return; leverage columns do not imply the strategy scales.
14. **NFI is third-party** (external strategy, GPL-family project, referenced only). Its +111.21% archive cannot be reproduced from this repository alone; the config and evidence hashes are shipped, not the strategy code.

## Operational

15. Live-panel checks depend on a local runtime; only a subset is meaningfully runnable outside the original machine. The executed-today suite is documented with its exact environment in `VERIFICATION.md`.
16. Machine-specific service files (launchd plists) are excluded; the *design* (bounded deterministic watchdog, isolated checks) is documented, the deployment is not shipped.
17. No financial advice. No predictions. Historical results, even correct ones, do not imply future performance.
