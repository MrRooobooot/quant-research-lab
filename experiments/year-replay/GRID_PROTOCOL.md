# Fee-screen grid on Trend family (exploratory, declared)

Why: only Trend showed a nonzero-fee-relevant structure (zero-fee +11.4%, with-fee 66.6 -> fee eats ~45). Explore whether entry-frequency/exit-cost knobs push the with-fee run above 100 on the SAME annual window. Pure screening, not validation; anything positive here must then survive a fresh unseen window before any approval claim.

Grid: 5 TrendKnobs, 5x5x5x5x5 -> 3125 combos is too many; run a structured subsample (corners + center, 33 runs) varying ema_fast (10/30/50), ema_slow (51/100/150), trend_len (100/200/300), buy_rsi (30/50/65), sell_rsi (60/75/90) via trend-knobs.json rewrite per run. --cache none mandatory (knob-JSON defeats freqtrade reuse detection). Fee fixed 0.001; zero-fee twin only for the best 3 combos.

Budget: 33 fee runs + up to 6 twin runs, each ~2min, under 90min wall. Stop-rule: if best with-fee result stays below 100 USDT, the fee wall verdict stands; write result and stop. If a combo clears 100, it goes to protocol-proper walk-forward on new windows, not to deployment.
