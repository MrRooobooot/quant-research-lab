# Path 2: wider universe fee-survival screen

Approved by user ("2", 2026-09-18). Goal: find whether an ACTIVE, fee-surviving strategy family exists beyond BTC/SOL, where the six-family screen showed every active family loses only to fees.

Universe: 39-pair KuCoin spot whitelist (the live nfi-paper list). Fixed annual window 2025-09-01→2026-08-31. Fee 0.001 per side + zero-fee twin for any fee-run candidate that finishes positive. Wallet 100 USDT, 2 slots, dry-run only.

Data: Binance public monthly 1m zips from data.binance.vision for the 39 pairs, 2025-09..2026-08 (12 months x 39 pairs). Downloaded into year-replay/data/binance_wide/ - NEVER into the live dir. Validate each pair-year: exact 525600-row grid (minus exchange-listing gaps, recorded per pair), monotonic, OHLC sane. Pairs listed after 2025-09 or with >2% missing candles are dropped from the screen universe and reported.

Screen: reuse the already-installed families in priority order by their zero-fee surplus (Demo > Scalp > Trend > SampleStrategy > Strategy001), because zero-fee surplus measures raw signal; the question is only whether any family's per-trade edge beats fees once trade selection diversifies across 39 pairs. Same acceptance rule as ITERATION_PROTOCOL: >=100 trades/year AND positive after 0.1% fees AND non-loss at zero fee. Any positive candidate must then pass a fresh previously-unseen window before approval; nothing deploys.

Budget: ~2-4 GB download, disk check first; delete each zip after feather conversion. If a family passes, stop and report. If all 39-pair runs stay fee-negative, the honest verdict is: the fee wall is structural on this venue/year at 1m-15m horizons, and the only measured-positive path is longer holding (NFI). No live changes; no real money.
