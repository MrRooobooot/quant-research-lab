# Verification

What was checked **when**, with **what command**, and what that does and does not establish. Never promote a claim across categories without a re-run.

## 1. Panel self-check suite — VERIFIED NOW (2026-10-03)

The `panel/checks/` suite was re-executed on 2026-10-03 (the same physical run that produced `selfchecks-2026-10-03.log` in this folder).

- **Command:** for each check, from the panel working directory:
  `~/freqtrade-venv/bin/python check_<name>.py`
- **Environment:** macOS, Python from the research venv (3.12), live panel service running throughout; checks are written to be isolated from it.
- **Result: 10/10 green (exit 0).** Re-confirmed by a second live run the same day: 2026-10-03 01:47:10 +0330, 10/10 exit 0.

| Check | Verifies |
|---|---|
| `check_bars_log.py` | bars log integrity (ordering/duplication/counts) |
| `check_blind_gap.py` | feed-state handling after blindness (sleep/outage) with a position open |
| `check_calibration_contract.py` | the calibration contract (what the engine believes about move sizes) |
| `check_entry_gate.py` | entry gate behavior |
| `check_feed_policy.py` | alert/root-cause policy functions |
| `check_fetch_bound.py` | a hung fetch cannot stall the feed loop (timeout bound) |
| `check_move_realism.py` | realized move vs assumed, from completed polled bars |
| `check_rule_proposals.py` | rule-proposal mechanics (temp dirs) |
| `check_server_safety.py` | server persistence/API regressions — isolated temp dirs + ephemeral localhost port, **never touches live DB / rules / bars, no exchange network** (per its docstring; whole check imported the server module in an isolated sandbox) |
| `check_training_safety.py` | training-safety regressions — **synthetic test data only** (its own final line: "Synthetic TEST DATA only; no live service writes") |

History: an earlier audit noted the claim "all 10 self-checks green" as **not verified by that audit**. That claim has now been independently re-run and captured above — the correct date for it is **2026-10-03**, not any earlier date.

## 2. Code-level facts — VERIFIED NOW (2026-10-03, read from current files)

- All backtest/paper configs are **dry-run** (`"dry_run": true`); no real-money trading configuration exists.
- **No credentials anywhere**: all credential fields are empty strings; no key patterns found by scans (gitleaks clean on this package).
- **No LLM/API references in the execution path** (grep for openai/anthropic/llm/gpt across panel and research code: zero hits). An LLM-driven cron was deliberately paused/removed and replaced by the deterministic watchdog (`health_watch.py --repair`).
- **Purged splits exist and are asserted** by `check_training_safety.py` (`train_lgbm.purged_splits` present; purge behavior exercised).
- **Versioned purged dataset (v2) built**: `v2_<schema-hash>_<stamp>` directory with `features/labels/meta` parquet + label schema; old unversioned artifacts rejected for reuse.
- Transport for the research corpus: Binance public dump downloads with ZIP magic-byte validation; NFI backtests via the freqtrade CLI.

## 3. Historical results — HISTORICALLY VERIFIED (artifacts archived, not re-run in 2026-10-03 session)

All tables in `RESULTS.md` are drawn from archived artifacts (result files, ledgers, evidence JSONs, result ZIPs) preserved in the corresponding `experiments/` folders, with these statuses:

- Re-runnable in principle where code + data acquisition instructions are present (fee-wall screen, OOS test, replay) — requires the external freqtrade install and multi-GB public data downloads; not re-executed for this publication.
- Archive-hash recorded: NFI original result ZIP, SHA-256 `385bf358b16d…` (full value in `experiments/oos/nfi_original_evidence.json`).
- Invalidated historical artifacts (pre-purge ML evaluations; the withdrawn "+78%") are kept in-tree **explicitly marked invalid** and are not evidence.

## 4. NOT VERIFIED

- Long-hold candidate edge in the current regime (1–4 trades recent; unproven by design).
- Any "makes money" claim in forward terms. None is made in this repository at any location.
- Future returns; forecasts. Not attempted here.

## 5. Scan gates run on this package (2026-10-03)

- Secret/injection scan (gitleaks, both no-git and git modes): **clean** (0 findings).
- Absolute-path scan (`/Users/...`): **0 remaining** after sanitization to `~`.
- Private-database scan: none included (live DBs excluded by policy).
- Third-party asset scan: no market data, PDFs, images, or third-party strategy code included.
