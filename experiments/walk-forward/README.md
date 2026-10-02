# walk-forward — first-generation ML pipeline (pre-purge, INVALIDATED)

⚠️ **Historical, invalidated artifacts.** This folder is retained for honesty, not as evidence.

## What this was

The first supervised ML campaign: LightGBM on ~2.8M 5m samples across 10 pairs, triple-barrier labels (TP +0.8% / SL −0.4% / 60-bar horizon), 5 time-ordered folds, 0.2% round-trip cost assumption, thresholds swept {0.5, 0.55, 0.6}.

## Why it is invalidated

A later internal audit found two problems (both recorded and fixed, not hidden):

1. **Aggregation artifact** — the reported percentage totals were **sums of overlapping hypothetical trade returns**, not portfolio returns. The old totals (e.g. −2260% aggregate) are therefore *not* portfolio outcomes.
2. **Label-horizon leakage** — the pre-purge splits did not remove training rows whose label window overlapped the test window. Old evaluations were declared invalid and kept as historical artifacts.

The corrected pipeline (purged splits, versioned datasets) lives in `../leakage/`. The qualitative conclusion — no fee-surviving signal, winner/rest probability separation only ~0.01–0.02 — survived the correction, but it is a statement about this feature set, this label design, and these thresholds, not a universal impossibility result.

## Files

| File | What it is |
|---|---|
| `build_dataset_v1` → `ml-build-dataset.py` | Dataset builder, v1 (pre-versioning). |
| `ml-train-lgbm.py` | Walk-forward trainer (5 folds, threshold sweep, cost-aware scoring). |
| `ml-findings.md` | Original findings write-up (read together with the invalidation above). |

Status: **INVALIDATED** for aggregate numbers; qualitative conclusion retained; superseded pipeline in `../leakage/`.
