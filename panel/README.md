# panel — the live paper-trading lab (sanitized extract)

The panel is the always-on paper-trading system that the research feeds. This folder ships a **sanitized extract** of its code — enough to inspect the engineering-safety design, not enough to be a deployable trading bot. Machine-specific service files (launchd plists), live databases, logs, and dossiers are deliberately excluded.

## What the running system does (design summary)

- **Feed loop:** polls exchanges continuously, builds bars in fixed buckets (15s), maintains a bars log; appends anomalies to an alerts log and **continues** instead of crashing (self-healing).
- **Strategy layer:** rule-based entries with hard gate constants (`PRETRAIN_FLOOR` family). The gates are enforced in **both** `load_rules` and the history retrainer, so a stale `rules.json` cannot silently disarm them.
- **Learning layer:** only closed auto-trades feed rule proposals; **manual interventions never mutate rules**.
- **Deterministic watchdog:** `health_watch.py --repair` (OS-service-managed) performs bounded repairs from a state file. An earlier scheduled LLM-driven automation was deliberately removed from the execution path — verified: **zero LLM API references** in any execution-path file.
- **Web panel:** a single-file server (stdlib HTTP) exposing state and a control API; included here for review.

## Files

| File | What it is |
|---|---|
| `server.py` | Panel server + feed/strategy engine (sanitized; credential fields empty; no secrets). |
| `health_watch.py` | Deterministic watchdog (`--repair` bounded actions, state file). |
| `check_health_watch.py` | Watchdog's own regression check. |
| `rules.json` | Current rule/gate state (constants in force). |
| `checks/` | The 10-self-check suite (see below). |

## The 10 self-checks

Isolation discipline: each check uses synthetic fixtures / temp directories / an ephemeral localhost port — **no exchange network, no writes to live state** (per each script's docstring; `check_training_safety.py` ends with "Synthetic TEST DATA only; no live service writes"; `check_server_safety.py` runs the server module in a sandbox on a random local port).

Check list: `bars_log` · `blind_gap` · `calibration_contract` · `entry_gate` · `feed_policy` · `fetch_bound` · `move_realism` · `rule_proposals` · `server_safety` · `training_safety`.

**Last executed: 2026-10-03 — 10/10 exit 0**, from the original panel working directory with its virtualenv Python. Full log: `../docs/selfchecks-2026-10-03.log`; classification notes: `../docs/VERIFICATION.md`.

## Runnability note

`server.py` and `health_watch.py` expect the local runtime (data files, venv, service context) and are **not** standalone-runnable here. The checks are the runnable subset in the original environment; outside it they still communicate the guarantees they assert. Paths were sanitized: machine-specific absolute paths rewritten to `~`.
