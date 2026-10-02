# Standing iteration protocol (user directive, 2026-09-18)

Directive: keep iterating strategies, learn from each result, do not stop, no intermediate output to the user until the goal is reached. Goal restated by user across sessions: an active, profitable strategy on virtual funds.

Standing rules that bind every iteration (skill trading-strategy-validation, this repo's journals):
- Virtual funds only; no live-bot or real-money changes. Live dir ~/freqtrade untouched.
- No optimize-until-green on one window: every candidate tested on the fixed annual window 2025-09-01→2026-08-31, BTC/SOL, 100 USDT, fee 0.001 plus a zero-fee control when it survives fees.
- Activity screen: >=100 trades/year (NFI's ~2 trades/year is already rejected as too sparse for the user's stated goal). Profit screen: positive net after fees AND non-loss at zero fee.
- One bounded exploration per round; each round's loser is recorded in iteration_ledger.json and never retried with cosmetic changes. Any tuning to escape a loss must move to a fresh, previously-unseen window before any approval claim.
- Stop conditions (report to user even though directive says silent): any real-money or live change needed; two consecutive rounds with zero new candidates; or goal reached.

Budget: max 6 rounds. If after 6 rounds no candidate passes both screens, the honest result is: goal not reached with this data/universe; report once with the ledger.
