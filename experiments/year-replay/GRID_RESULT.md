# Trend fee-wall screen: verdict stands

45 structured knob runs (center, all corners, single-axis probes) of the Trend family on the fixed annual BTC/SOL window, fee 0.001. Trend's zero-fee twin was +11.37%; the entire knob space could not lift any with-fee result above 100 USDT.

| top result | knobs | trades | final USDT |
|---|---|---:|---:|
| corner_10-51-100-30-60 | fast10/slow51/trend100/rsi30-60 | 0 | 100.00 |
| corner_50-150-300-30-90 | fast50/slow150/trend300/rsi30-90 | 64 | 99.60 |
| corner_50-150-300-30-60 | fast50/slow150/trend300/rsi30-60 | 65 | 99.01 |

Tight entry filters only abstain (0-6 trades); loose ones trade 64+ times and still end below start. The fee wall verdict is confirmed by exhaustion, not tuning: no stop-rule escape exists in this family on this window. Two consecutive knob families (Strategy001, Trend) rejected; per ITERATION_PROTOCOL this closes the tuning path for this universe. Ledger: grid_results.json (45 rows), iteration_ledger.json (5 rounds). Cumulative rejected families this session: NFI (sparse), SampleStrategy, Strategy001, Trend, Scalp, Demo. Zero-fee survivors: Trend 111.37, Demo 117.37, Scalp 115.14, all below water after real fees - the market microstructure on 1m-15m windows does not cover costs here.
