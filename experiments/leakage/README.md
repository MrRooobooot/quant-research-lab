# leakage — the fix: purged splits + versioned datasets

This folder contains the **corrected** training pipeline that replaced the invalidated first generation (see `../walk-forward/`).

## What was fixed

1. **Purged splits.** `train_lgbm.py` exposes `purged_splits(m, n_folds)` — it groups identical entry timestamps and **purges the full label horizon at every fold boundary**, so no training row's label window overlaps the test window. Empty folds raise an error rather than silently shrinking the purge.
2. **Versioned dataset with full metadata.** `build_dataset.py` writes datasets as `v2_<schema-hash>_<utcstamp>/` with `features/labels/meta` parquet plus `label_schema.json`. Every label row carries:
   - `label_end` — the full information horizon (what purging uses);
   - `exit_time` — the actual barrier/timeout exit bar.
   Incomplete-horizon rows are dropped; old unversioned artifacts are **rejected for reuse, never overwritten**.
3. **Regression lock.** `check_training_safety.py` asserts the purged-split machinery exists and behaves (and runs entirely on **synthetic TEST DATA** — no live writes).

## Files

| File | What it is |
|---|---|
| `build_dataset.py` | v2 dataset builder (triple-barrier labels, `label_end`/`exit_time`, schema hash, versioned output). |
| `train_lgbm.py` | Purged walk-forward trainer ("offline research ONLY. No model persistence/activation"). |
| `check_training_safety.py` | The regression check (asserts `purged_splits` present; exercises purge; synthetic fixtures only). |

## Running the check

From the panel working directory, with that environment's Python:

```
python check_training_safety.py
```

Last verified: **2026-10-03, exit 0** (full suite log: `../../docs/selfchecks-2026-10-03.log`).

## Design notes carried forward

- Purging uses the *information* horizon (`label_end`), not the realized exit (`exit_time`) — a row whose label *could* have looked into the test window is purged even if it exited early.
- Same rule applies to the five-cycle loop (full-horizon purging inside expanding folds; documented in `../five-cycle/`).
