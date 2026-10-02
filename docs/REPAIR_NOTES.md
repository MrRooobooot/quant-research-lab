> **Snapshot note:** this is the mid-repair status record (September 2026). The bounded deterministic watchdog described here as *being prepared* was subsequently deployed and verified — see `VERIFICATION.md` for the current, re-executed status. Kept in-tree as an honest historical artifact.

# Repair status — evidence, not profit claims

## Verified before deployment

- Snapshot and SQLite consistent backups: `~/freqtrade/repair-backups/20260917-220959`.
- Unrestricted LLM-editing cron job paused (its output was surfaced in the panel fixes API). A bounded deterministic watchdog is being prepared; deployment not yet verified.
- `check_rule_proposals.py`: failed before fix with `unvalidated loss proposal applied`; passes after `apply_fixes` became proposal-only. No live rule mutation from individual losses.
- `check_calibration_contract.py`: passed after fixing measurement to match the live trailing 60-close absolute-return feature. Previous calibration wrongly used one bar high-low range. Correct diagnostic: 443 clean overlapping windows, median ratio 0.173878 versus configured 0.32; drift flagged (exit 2), not hidden.
- `check_health_watch.py`: passed bounded restart policy; read-only live probe reports panel healthy. Watchdog never edits trading code or tunes rules; stale feeds are reported, not automatically diagnosed as WS faults.

## Corrections to older reports

- No demonstrated forward profit or continuously improving trading knowledge. Offline training and runtime resilience are distinct.
- Backtest +111.21% used 10 pairs / 5 slots / 10,000 wallet. The current large paper bot uses 39 pairs / 5 slots / 2,000 wallet: its matching backtest is +12.73%, not +111.21%. Same strategy hash does not mean same configuration.
- Historical monthly equivalent is not a forecast. At a hypothetical constant 2.5% compounded monthly, 10 to 100 requires about 93.25 months (94 whole months), not 360.
- Median bar movement below fees does NOT prove every short-timeframe trade loses. Signal horizon, holding duration, selective entries and actual execution costs matter. Existing negative experiments reject their tested configurations, not all possible strategies.
- A small observed maximum crossing gap does not prove the panel can never trade again; future market conditions differ. Do not loosen gates merely to manufacture activity.
- KeepAlive restarts exited processes; it cannot prove recovery from a running-but-stale feed. A healthy heartbeat is not evidence of fresh candles.
- Old ML percentage totals are sums of overlapping hypothetical trade returns, not portfolio return. Old splits have label-horizon leakage. Preserve those artifacts as invalid historical evaluations, not validated evidence.
- The long historical run has about 7.28% marked-equity drawdown, not its 2.14% trade-result drawdown. KuCoin wallet terminal accounting discrepancy needs reconciliation; do not claim a verified corrected equity drawdown there.
- Historical audit reports 66 completed and 27 failed cron executions; not 27 failures out of 66 total. Delivery failure differs from execution failure.

## Remaining acceptance checks

Server/API/persistence fixes, offline dataset/split repairs, integrated isolated tests, controlled deployment with database continuity, and versioned final evidence are still pending. Profitable fast trading remains unproven and is not promised by these engineering repairs.
