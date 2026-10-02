# NFI +111.21%: archived + fresh-month OOS

Original backtest (2024-02-01→2026-08-01, KuCoin 10 pairs, fee 0.001, 5 slots):
120 trades, **+111.21%**, 117W/3L, closed-DD 2.14%. ZIP + redacted config archived;
sha256 `385bf358b16d…` verified copy identical.

**Fresh OOS (2026-08-01→2026-09-16), same strategy/config, data it never saw:
1 trade, +0.07%, 1W/0L.** Positive but tiny — NFI's own entry rate is ~0.02/day;
six weeks = ~1 trade is the design, not a fault. No contradiction with the
2.5y run, but the recent-regime edge stays unproven at this sample size
(consistent with the earlier 63d window −4.18% on 39 pairs).

Deliverable: `original/` (archived evidence) + `oos-run/` (fresh evidence).
No deployment change; live NFI bots stay dry-run.
