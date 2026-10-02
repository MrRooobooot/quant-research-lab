"""Self-check: bars.jsonl must be strictly increasing polled bars, no dups, no synthetic seed rows.

Run: ~/freqtrade-venv/bin/python check_bars_log.py
"""
import json, os, tempfile, importlib

tmp = tempfile.mkdtemp()
os.environ.setdefault("PANEL_TEST", "1")
import server
server.ROOT = tmp
LOG = os.path.join(tmp, "bars.jsonl")


def rows():
    if not os.path.exists(LOG):
        return []
    return [json.loads(l) for l in open(LOG)]


T0 = 1789612800000
server.bars.clear(); server._seeded_t.clear(); server._last_persisted_t = 0

server.add_bar(100, T0)                 # bucket T0, n=1
server.add_bar(101, T0 + 1000)          # merges -> n=2, range 100..101
assert rows() == [], "open bar must not be logged yet"
server.add_bar(102, T0 + 30000)         # closes T0 -> write
assert len(rows()) == 1 and rows()[0]["t"] == T0 and rows()[0]["n"] == 2, rows()
assert rows()[0]["h"] == 101 and rows()[0]["l"] == 100, rows()

# duplicate / stale re-emit: same t again must not be appended
server._last_persisted_t = T0
server.bars.clear()
server.bars.append({"t": T0, "o": 100, "h": 100, "l": 100, "c": 100, "n": 9})
server.add_bar(105, T0 + 30000)
assert len(rows()) == 1, ("duplicate t logged", rows())

# synthetic seed rows must never be logged
server.bars.clear(); server._seeded_t.clear(); server._last_persisted_t = 0
os.remove(LOG)
for i in range(3):
    t = T0 - (3 - i) * 30000
    server.bars.append({"t": t, "o": 1, "h": 1, "l": 1, "c": 1, "n": 1})
    server._seeded_t.add(t)
server.add_bar(200, T0)                 # rolls: last bar is seeded -> no write
assert rows() == [], ("seeded bar logged", rows())
server.add_bar(201, T0 + 30000)         # rolls the polled T0 bar -> write
assert [r["t"] for r in rows()] == [T0], rows()
assert rows()[0]["n"] == 1 and rows()[0]["c"] == 200, rows()

# order guarantee across restart: _tail_t reads the last written t
assert server._tail_t(LOG) == T0, server._tail_t(LOG)
assert server._tail_t(os.path.join(tmp, "nope.jsonl")) == 0

print("SELF-CHECK OK | rows:", [ (r["t"], r["n"]) for r in rows() ])
