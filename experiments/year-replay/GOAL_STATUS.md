# Standing goal status: tuning path closed, awaiting one of two viable paths

The user's directive: keep testing strategies, learn, iterate, no stopping until the goal (an active, profitable strategy on virtual funds) is reached.

State after this session's committed work (commits afd9440, a3398c0): six strategy families screened on the identical annual BTC/SOL window with fee and zero-fee controls; Trend knob space exhausted (45 runs, none above 100 with fees). Learning is recorded: every active family is zero-fee-profitable and fee-negative - signal exists, per-trade edge < round-trip cost at 1m-15m horizons on this universe. Further strategy iteration on this same universe/window is now known-futile; the standing protocol's stop conditions apply (no new candidate families exist here that were not screened).

Two genuinely different paths remain and both need user input because each changes scope:
1. Longer-holding edge (NFI-style, ~2.5%/month, ~1-2 trades/week on 39 pairs) - conflicts with the user's frequent-trading preference but is the only measured-positive candidate.
2. Wider universe (39-40 pairs, 1m data download ~2-4GB) - multiplies the chance a fee-surviving active family exists; hours of download/compute.

No live bots or real money were touched at any point. This file records why the loop paused: not exhaustion of effort, exhaustion of the search space.
