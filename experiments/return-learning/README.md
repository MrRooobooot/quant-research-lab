# return-learning — fixed-horizon & cross-sectional learners (both rejected)

Two label redesigns of the same ML idea, both predeclared (see `PROTOCOL.md`) and both **rejected**. Periods: Apr–Aug 2026, already-researched data — explicitly *not* virgin holdouts.

## 1. Fixed-horizon Ridge learner (`RESULT.md`)

Predict the continuous next-open → 60-minute-open return (instead of an asymmetric barrier class). Enter only if expected gross > 0.34% (0.24% round-trip + 0.10% buffer).

| Test month | Training rows | Max predicted gross | Trades |
|---|---:|---:|---:|
| April | 709,114 | 0.117% | 0 |
| May | 735,034 | 0.093% | 0 |
| June | 761,816 | 0.270% | 0 |
| July | 787,736 | 0.084% | 0 |
| August | 814,520 | 0.326% | 0 |

Zero qualifying trades in all five months — the model never forecast a move worth paying fees for. The wallet stayed at 10 USDT because nothing qualified, **not** because trading was demonstrated.

- `abstention_diagnostic.json`: forcing only the highest-forecast row through the executor each month executes and reconciles to independently computed fees/cash — isolating **abstention**, not a broken executor. (Diagnostic only; best-forecast selection is not a tradable rule.)
- `check_return_learning.py`: passes next-open alignment, missing-bar rejection, simultaneous selection, non-overlapping positions, cost and abstention checks. `result.json` carries source hashes + protocol hash.

## 2. Cross-sectional top-1 learner (`CROSSSECTION_RESULT.md`)

Instead of a high entry bar, force a trade every bar: best forecast of 3 assets, one position, 12-bar hold, 0.12%/side.

| Month | Trades | Wins | Net USDT |
|---|---:|---:|---:|
| April | 719 | 163 | −8.20 |
| May | 743 | 157 | −1.50 |
| June | 719 | 221 | −0.25 |
| July | 743 | 188 | −0.04 |
| August | 743 | 182 | −0.01 |

Final wallet **0.002 USDT** from 10. Average net ≈ −0.11%/trade — consistent with paying 0.24% round-trip on moves the model cannot forecast beyond zero. Rejected harder than the fixed-horizon variant.

## Status of these periods

Exploration on Apr–Aug 2026 is **exhausted**; any future variant requires a fresh period. No deployment; no live files changed. The standing profit goal remains unmet.
