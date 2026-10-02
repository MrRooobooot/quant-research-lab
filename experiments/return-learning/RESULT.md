# Fixed-horizon return learner: rejected

Five expanding chronological monthly tests, April–August 2026. Existing Ridge model trained on continuous next-open-to-60-minute-open returns, not the asymmetric barrier classes. Three assets, ten causal features. Protocol frozen before these outcomes; periods previously researched, not a fresh holdout.

| Test month | Training rows | Max predicted gross return | Trades |
|---|---:|---:|---:|
| April | 709114 | 0.11737% | 0 |
| May | 735034 | 0.09313% | 0 |
| June | 761816 | 0.27033% | 0 |
| July | 787736 | 0.08371% | 0 |
| August | 814520 | 0.32608% | 0 |

Fixed entry threshold 0.34%, including 0.24% assumed round-trip costs and a 0.10% buffer. No threshold tuning after test inspection. Simulated wallet remained 10 USDT because no trades qualified, not because profitable trading was demonstrated. No model promoted, no live files changed.

`check_return_learning.py` passes next-open entry/exit alignment, missing-bar rejection, simultaneous selection, non-overlapping positions, costs and abstention checks. `result.json` contains source hashes, protocol hash and all five tests. Five months counted and reconciled against trade list.

Diagnostic: in each month, force only the highest-forecast real row through the entry gate. All five entries execute and reconcile to independently computed fees and cash; normal eligible-row count remains zero in all months. This isolates abstention rather than a broken trade executor. Full-month best-forecast selection is diagnostic only, not a causal tradable rule; its profits are not strategy evidence. See `abstention_diagnostic.json`.

Conclusion: changing the label from barrier class to continuous return did not produce a deployable signal with this linear model and these features. This does not establish that no strategy can work. Larger leverage or removing the entry buffer is not a demonstrated remedy. The standing profit goal remains unmet.
