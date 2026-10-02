# oos — out-of-sample collapse tests

Two independent fresh-window tests. Both are kept because they *collapsed* earlier positive-looking results — that is the point of the folder.

## 1. Fresh decade, BTC 5m (2020–2023)

`oos_test.py` + `oos_result.json`

A fixed momentum rule ("rise ≥2% over 12 bars, RSI<70; entry next open; TP +6% / SL −3%, stop-first; one position") that looked usable in-sample, tested on **four years of data it had never seen** (407 trades):

| Fee per side | Return | Max DD |
|---|---:|---:|
| 0.1% | −84.0% | 99.9% |
| 0.05% | −76.0% | 99.8% |
| 0.0% | **−64.2%** | 99.8% |

Buy-and-hold same window: +486%. The artifact's own verdict fields: `"verdict": "does_not_beat_buyhold"`, `"deployment_approved": false`. Losing at **zero fees** means the signal itself did not survive the decade — fees were not even the (only) killer.

Data: BTC 5-monthly zips from data.binance.vision (ZIP magic-byte checked; cached under `binance-5m/` locally — not redistributed here; gaps recorded in the result).

## 2. Fresh six weeks, NFI long-hold candidate (2026-08 → 2026-09)

`nfi_fresh_month_RESULT.md`, `nfi_archive_and_oos.py`, `nfi_original{,_config,_evidence}.json`, `nfi_fresh_evidence.json`

The only measured-positive family in the workspace: a +111.21% 2.5-year backtest (120 trades, 117W/3L; result ZIP archived with SHA-256 `385bf358b16d…`, archived copy verified identical). Fresh OOS on six weeks it never saw: **1 trade, +0.07%** — positive but statistically meaningless at this sample; consistent with an earlier 63-day window on 39 pairs (−4.18%). Framing recorded in the result file: the edge "stays unproven at this sample size."

Also included: `nfi_39pair_148d.json` — a separate 148-day / 39-pair backtest of the same family (+11.31%, 31 trades, 29W/2L, marked DD 6.95%).

## Notes

- The NFI strategy itself is third-party and **not** included; only configs (sanitized, empty credential fields), evidence hashes, and results are shipped.
- `nfi_archive_and_oos.py` documents the archive procedure (copy ZIP + config → record SHA-256 → run fresh window via the local freqtrade CLI). Machine paths in it are rewritten to `~`.
