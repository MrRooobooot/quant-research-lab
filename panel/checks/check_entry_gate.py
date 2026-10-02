"""Self-check on REAL market bars: would the panel take the setups that lost money (#2/#3)?

Run: ~/freqtrade-venv/bin/python check_entry_gate.py
Reads the panel's own recorded 30s bars from http://localhost:8123/api/state — no synthetic data.
"""
import json
import sqlite3
import urllib.request

import server

server.open_position = lambda *a, **k: None  # never write a test trade into panel.db

state = json.load(urllib.request.urlopen("http://localhost:8123/api/state"))
bars = state["bars"]
assert bars, "panel returned no bars"


def tick(closes, price, up_prev=None):
    server.bars.clear()
    for i, c in enumerate(closes):
        server.bars.append({"t": 1000 * i, "c": c})
    server.PREV["up"] = up_prev
    server.STATE["position"] = None
    server.DECISIONS.clear()
    ticker = {"last": price, "bid": price - 0.1, "ask": price + 0.1,
              "high": max(closes), "low": min(closes), "percentage": 0.0, "quoteVolume": 1e9}
    server.strategy_tick(price, ticker)
    return server.DECISIONS[-1] if server.DECISIONS else None


# 1) replay every recorded bar through the current strategy: how many entries would it take?
opens, refusals = 0, 0
closes = []
for i, b in enumerate(bars):
    closes.append(b["c"])
    d = tick(closes, b["c"])
    if d and d["action"] == "open":
        opens += 1
    if d and "حرکت انتظاری" in (d.get("reason") or ""):
        refusals += 1
print(f"replay of {len(bars)} real bars: opens={opens} expected-move refusals={refusals}")

# 2) trade #3 (worst loss, -1.00) was entered at a fresh cross; would it be taken now?
c = sqlite3.connect("panel.db")
c.row_factory = sqlite3.Row
t = dict(c.execute("select * from trades where id=3").fetchone())
hist = [b["c"] for b in bars if b["t"] <= t["opened_ms"]]
if not hist:
    # the live buffer only keeps recent bars, so once trade #3 scrolls out of it the entry
    # context cannot be rebuilt from panel data (30s bars are not on the exchange) — skip.
    print("trade #3 entry replay: SKIPPED — live bar buffer no longer covers that window")
else:
    d = tick(hist, t["entry"], up_prev=False)  # force the same "fresh cross" the bot saw then
    reason = (d or {}).get("reason") or ""
    print(f"trade #3 entry replay: action={(d or {}).get('action')} reason={reason[:120]}")
    assert d and d["action"] == "hold" and "حرکت انتظاری" in reason, "trade #3 setup would be taken again"
assert opens == 0, f"strategy still opens trades in this market: {opens}"
print("OK")

# 3) feed-outage gap: a 4-minute hole must come back as flat padded bars, never a jump in time
server.bars.clear()
server.STATE["tf"] = 30
server.add_bar(100.0, 0)
server.add_bar(101.0, 4 * 60_000)  # 8 missing 30s buckets
gaps = [b["t"] for b in server.bars if b["n"] == 0]
assert len(server.bars) == 9 and gaps == [30_000 * i for i in range(1, 8)], server.bars
assert server.bars[-1]["c"] == 101.0 and [b["c"] for b in list(server.bars)[1:8]] == [100.0] * 7
print(f"feed-outage padding: {len(gaps)} flat bars inserted, series contiguous")
server.bars.clear()

# 4) same continuity rule, but on the panel's LIVE buffer: a real outage (iPhone-hotspot DNS
#    drop) must show up as flat n=0 bars, never as a time jump the indicators would stretch over.
tf_ms = state["tf"] * 1000
holes = [(bars[i]["t"], bars[i + 1]["t"] - bars[i]["t"])
         for i in range(len(bars) - 1) if bars[i + 1]["t"] - bars[i]["t"] != tf_ms]
assert not holes, f"live bar buffer not contiguous: {holes[:3]}"
live_pads = [b["t"] for b in bars if b.get("n") == 0]
assert all(b["o"] == b["h"] == b["l"] == b["c"] for b in bars if b.get("n") == 0), "pad bar is not flat"
print(f"live buffer continuity: {len(bars)} bars, 0 gaps, {len(live_pads)} flat pad bars")
print("OK")
