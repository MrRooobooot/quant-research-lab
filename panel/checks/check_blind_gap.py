"""Self-check for check_blind_gap: no alert on a normal tick or a fresh start, alert +
flatten once the loop has been blind (Mac sleep / long feed outage) with a position open.
Run: ~/freqtrade-venv/bin/python check_blind_gap.py
"""
import os, time, json
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import server as S

now = int(time.time() * 1000)
calls = []
S.close_position = lambda price, reason: calls.append((price, reason))
S.alert = lambda kind, msg, tb=None: calls.append((kind, msg))

assert S.check_blind_gap(76000.0, now) is False, "restart (last_tick_ms=0) must not alert"
S.STATE["last_tick_ms"] = now - 10_000
assert S.check_blind_gap(76000.0, now) is False, "10s tick gap must not alert"
S.STATE["last_tick_ms"] = now - 600_000
assert S.check_blind_gap(76000.0, now) is True and calls[0][0] == "feed_gap", "10min gap must alert"
assert len(calls) == 1, "no position -> alert only, no close"
S.STATE["position"] = {"id": 999, "entry": 76000.0, "size": 0.001, "opened_ms": now}
calls.clear()
assert S.check_blind_gap(75000.0, now) is True and ("feed_gap" in calls[-1][1]), "must report gap"
print("check_blind_gap OK", json.dumps(calls, ensure_ascii=False))
