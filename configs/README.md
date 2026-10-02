# configs — sanitized example configurations

Two representative freqtrade configs from the research workspace, sanitized for publication:

| File | Used for |
|---|---|
| `config-nfi-paper.json` | The NFI long-hold paper bots (dry-run). |
| `config-nfi-hist.json` | NFI historical backtests (the archived +111.21% configuration family). |

What was sanitized:

- **Credentials:** all exchange credential fields are empty strings **by design** (this was true in the source as well — no API keys ever lived in these files; the paper panel uses no trading credentials).
- **Machine paths:** absolute paths rewritten to `~` (e.g. `~/freqtrade/user_data/...`).
- **Remote pairs list:** unchanged (public market data identifiers).

Key settings preserved verbatim: `"dry_run": true`, `"fee": 0.001` (pinned per-side fee so runs cannot silently inherit an exchange default).

Per the research policy: real-money configurations do not exist in this workspace; had any existed, they would be excluded from publication rather than sanitized.
