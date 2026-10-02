#!/usr/bin/env python3
"""Safety/persistence/API regressions for the panel server.

Isolated temp dirs + private HTTP server on an ephemeral port: never touches
panel.db / rules.json / bars.jsonl of the live panel, no network to exchanges.
Run: ~/freqtrade-venv/bin/python check_server_safety.py
"""
import json, math, os, sys, tempfile, threading, time, urllib.request, urllib.error
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as S

TMP = tempfile.mkdtemp(prefix="panel-safety-TEST-")
S.ROOT = TMP
S.DB_PATH = os.path.join(TMP, "panel.db")
S.ALERTS = os.path.join(TMP, "alerts.jsonl")
S.FEED_FAILS = os.path.join(TMP, "feed_fails.log")
S.LOG = os.path.join(TMP, "panel.log")
S.RULES_FILE = os.path.join(TMP, "rules.json")
S.STATE_FILE = os.path.join(TMP, "panel_state.json")
S.bars.clear(); S._seeded_t.clear(); S._last_persisted_t = 0
S.db().close()
S.STATE.update({"pair": "BTC/USDT", "tf": 30, "running": True, "position": None,
                "wallet": S.START_WALLET, "tp": S.TAKE_PROFIT, "sl": S.STOP_LOSS})

srv = ThreadingHTTPServer(("127.0.0.1", 0), S.Handler)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{PORT}"


def req(method, path, body=None, origin=True, xreq=True, extra=None):
    h = {"Content-Type": "application/json"}
    if origin:
        h["Origin"] = BASE
    if xreq:
        h["X-Panel-Request"] = "1"
    h.update(extra or {})
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


def add_closed_trades(n, pnl=-1.0):
    c = S.db()
    now = int(time.time() * 1000)
    for _ in range(n):
        c.execute("INSERT INTO trades(opened_ms,closed_ms,entry,exit,size,pnl_abs,pnl_pct,"
                  "open_reason,close_reason) VALUES(?,?,?,?,?,?,?,?,?)",
                  (now - 60000, now, 100.0, 99.0, 0.1, pnl, -1.0, "sma_cross_up", "stop_loss"))
    c.commit(); c.close()


def expect(cond, msg):
    assert cond, msg


# 1. destructive reset removed: 409 + history preserved
add_closed_trades(2, pnl=-1.0)
st, resp = req("POST", "/api/control", {"action": "reset"})
expect(st == 409, f"reset must be 409, got {st} {resp}")
expect("preserv" in json.dumps(resp).lower() or "حفظ" in json.dumps(resp), f"409 must explain history preserved: {resp}")
c = S.db(); n = c.execute("SELECT COUNT(*) FROM trades").fetchone()[0]; c.close()
expect(n == 2, f"reset deleted history: {n} rows")

# 2. unknown action rejected
st, resp = req("POST", "/api/control", {"action": "nuke_everything"})
expect(st == 400, f"unknown action must 400, got {st}")

# 3. GET must not mutate state
S.STATE["running"] = True
st, resp = req("GET", "/api/control?action=stop")
expect(st == 405, f"GET control must 405, got {st}")
expect(S.STATE["running"] is True, "GET control mutated running")

# 4. mutation boundary: same-origin POST + custom header required
for kwargs, why in [
    (dict(origin=False), "missing Origin"),
    (dict(extra={"Origin": "http://evil.example"}), "cross-origin"),
    (dict(xreq=False), "missing custom header"),
]:
    st, _ = req("POST", "/api/control", {"action": "stop"}, **kwargs)
    expect(st == 403, f"{why} must 403, got {st}")
expect(S.STATE["running"] is True, "rejected requests mutated state")
st, resp = req("POST", "/api/control", {"action": "stop"})
expect(st == 200 and S.STATE["running"] is False, f"valid POST stop failed: {st} {resp}")
req("POST", "/api/control", {"action": "start"})

# 5. tp/sl validation: nonfinite / out-of-bounds rejected, state untouched
good_tp = S.STATE["tp"]
for bad in [float("nan"), float("inf"), 99.0, -1.0, 0.0]:
    st, _ = req("POST", "/api/control", {"tp": bad})
    expect(st == 400, f"tp={bad} must 400, got {st}")
expect(S.STATE["tp"] == good_tp, f"rejected tp mutated state: {S.STATE['tp']}")
good_sl = S.STATE["sl"]
for bad in [float("nan"), float("inf"), 99.0, 0.0]:  # sl=1.0% (0.01 fraction) is in-bounds
    st, _ = req("POST", "/api/control", {"sl": bad})
    expect(st == 400, f"sl={bad} must 400, got {st}")
expect(S.STATE["sl"] == good_sl, f"rejected sl mutated state: {S.STATE['sl']}")
st, resp = req("POST", "/api/control", {"tp": 0.8, "sl": 0.4})
expect(st == 200 and abs(S.STATE["tp"] - 0.008) < 1e-9 and S.STATE["sl"] == -0.004,
       f"valid percent tp/sl failed: {st} {resp} tp={S.STATE['tp']} sl={S.STATE['sl']}")

# 6. pair/tf locked (bars-log mixing + open-position safety)
S.STATE["position"] = {"id": 1, "entry": 100.0, "size": 0.1, "opened_ms": 0}
st, resp = req("POST", "/api/control", {"tf": 60})
expect(st == 409, f"tf change must 409, got {st} {resp}")
st, resp = req("POST", "/api/control", {"pair": "ETH/USDT"})
expect(st == 409, f"pair change must 409, got {st} {resp}")
S.STATE["position"] = None
st, resp = req("POST", "/api/control", {"pair": "ETH/USDT", "tf": 60})
expect(st == 409, f"pair/tf change without position must still be locked, got {st}")
expect(S.STATE["pair"] == "BTC/USDT" and S.STATE["tf"] == 30, "pair/tf mutated while locked")
expect("BTC" in json.dumps(resp) or "قفل" in json.dumps(resp), f"409 must explain lock: {resp}")

# 7. settings persisted atomically + validated restore
expect(os.path.exists(S.STATE_FILE), "settings file not persisted")
saved = json.load(open(S.STATE_FILE))
expect(saved["tp"] == S.STATE["tp"] and saved["running"] in (True, False), f"bad settings file: {saved}")
S.STATE["running"] = True
json.dump({"tp": 9.9, "sl": 0.0, "running": "yes", "pair": "ETH/USDT", "tf": 60},
          open(S.STATE_FILE, "w"))
S.restore_settings()
expect(S.STATE["running"] is True, "out-of-bounds settings adopted")
expect(S.STATE["tp"] != 9.9 and S.STATE["pair"] == "BTC/USDT" and S.STATE["tf"] == 30,
       "invalid pair/tf/tp adopted from settings")
open(S.STATE_FILE, "w").write("{corrupt json")
S.restore_settings()  # must not raise
json.dump({"tp": 0.01, "sl": -0.005, "running": False}, open(S.STATE_FILE, "w"))
S.STATE["tp"] = S.TAKE_PROFIT
S.restore_settings()
expect(S.STATE["tp"] == 0.01 and S.STATE["sl"] == -0.005 and S.STATE["running"] is False,
       "valid settings not restored")

# 8. rules.json adopted only if finite + bounded (startup safety)
json.dump({"rules": {"min_gap_pct": float("nan"), "min_bar_vol_pct": 99.0, "max_rsi_entry": -5.0}},
          open(S.RULES_FILE, "w"))
S.RULES.update({"min_gap_pct": 0.0, "min_bar_vol_pct": 0.0, "max_rsi_entry": 100.0})
S.load_rules()
expect(all(math.isfinite(v) for v in S.RULES.values()), f"nonfinite rule adopted: {S.RULES}")
expect(S.RULES["min_gap_pct"] == S.PRETRAIN_FLOOR["min_gap_pct"], f"floor not applied: {S.RULES}")
expect(S.RULES["min_bar_vol_pct"] == S.PRETRAIN_FLOOR["min_bar_vol_pct"], f"out-of-bounds vol adopted: {S.RULES}")
expect(50.0 <= S.RULES["max_rsi_entry"] <= 70.0, f"out-of-bounds rsi adopted: {S.RULES}")
json.dump({"rules": {"min_gap_pct": 0.04, "min_bar_vol_pct": 0.03, "max_rsi_entry": 60.0}},
          open(S.RULES_FILE, "w"))
S.load_rules()
expect(S.RULES["min_gap_pct"] == 0.04 and S.RULES["max_rsi_entry"] == 60.0, f"valid rules rejected: {S.RULES}")

# 9. stats aggregate FULL history, display keeps last 30
S.STATE["trades"] = []; S.STATE["stats"] = {}
add_closed_trades(33, pnl=1.0)
S.load_state()
expect(S.STATE["stats"]["trades"] == 35, f"stats counted only display rows: {S.STATE['stats']}")
expect(S.STATE["stats"]["pnl"] == 31.0, f"pnl aggregated wrong: {S.STATE['stats']}")  # 2*-1 + 33*1
expect(S.STATE["stats"]["wins"] == 33, f"wins aggregated wrong: {S.STATE['stats']}")
expect(len(S.STATE["trades"]) == 30, f"display rows must stay 30: {len(S.STATE['trades'])}")

# 10. reentrant lock: control-side close while lock held must not deadlock
c = S.db(); now = int(time.time() * 1000)
cur = c.execute("INSERT INTO trades(opened_ms,entry,size,open_reason) VALUES(?,?,?,?)",
                (now, 100.0, 0.1, "manual")); rid = cur.lastrowid; c.commit(); c.close()
S.STATE["position"] = {"id": rid, "entry": 100.0, "size": 0.1, "opened_ms": now, "ctx": {}}
box = {}
def _close():
    try:
        with S.lock:
            box["pnl"] = S.close_position(101.0, "manual")
    except Exception as e:
        box["err"] = e
th = threading.Thread(target=_close, daemon=True); th.start(); th.join(5)
expect(th.is_alive() is False, "close_position deadlocked holding lock (lock not reentrant)")
expect(isinstance(box.get("pnl"), float), f"close under lock failed: {box}")

# 11. retrain is report-only: no rule mutation, correct nonzero handling
before = dict(S.RULES)
st, resp = req("POST", "/api/control", {"action": "retrain"})
expect(resp.get("applied") is False, f"retrain applied rules: {resp}")
expect(S.RULES == before, "retrain mutated RULES")
expect(st in (200, 500), f"retrain status odd: {st}")
if st == 500:
    expect(resp.get("ok") is False, "nonzero train.py exit must report ok=false")

# 12. no blind periodic adoption thread (function must be gone; main() must not start it)
expect(not hasattr(S, "retrain_loop"), "periodic blind adoption thread still exists")
src = open(os.path.abspath("server.py")).read() if os.path.exists("server.py") else ""
if "def main()" in src:
    main_src = src.split("def main()")[1]
    expect("retrain_loop" not in main_src, "main() still starts the blind adoption thread")

srv.shutdown()
os.remove(S.STATE_FILE) if os.path.exists(S.STATE_FILE) else None
print("PASS: server safety regressions OK (isolated temp dir, private port)")
