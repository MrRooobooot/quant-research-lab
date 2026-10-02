#!/usr/bin/env python3
"""Live paper-trading panel: 30s/1m candles, realtime simulated trades, self-healing loop.

- Serves a dashboard at http://localhost:8123
- Builds 30s bars from 5-second polls (KuCoin has no native 30s candles) or uses native 1m bars
- Simple SMA cross + RSI filter, one long position at a time, fees charged (0.1%/side)
- Any exception -> appended to alerts.jsonl and the loop restarts itself (no crash)
- Repeated/slow-data conditions are reported as "needs_fix" alerts for the assistant to fix
"""
import json, math, os, sqlite3, sys, threading, time, traceback, urllib.parse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import ccxt

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "panel.db")
ALERTS = os.path.join(ROOT, "alerts.jsonl")
FEED_FAILS = os.path.join(ROOT, "feed_fails.log")
LOG = os.path.join(ROOT, "panel.log")
PORT = 8123
FEE = 0.001          # per side
STAKE_RATIO = 0.25   # fraction of wallet risked per trade
START_WALLET = 1000.0
TAKE_PROFIT = 0.008
STOP_LOSS = -0.004
POLL_SECS = 5
GAP_BLIND_SECS = 120  # >2min without a tick = Mac slept / feed dead: SL/TP never ran
FETCH_TIMEOUT_SECS = 15  # hard ceiling per ticker call (covers unbounded DNS hangs)
MOVE_REALISM = 0.17  # conservative discount, measured median realized/predicted 0.174 over 443 clean closed-bar 10m windows (check_move_realism.py):
# vol*20 is ~3x optimistic, so the gate must discount it before comparing to TP

STATE = {
    "pair": "BTC/USDT", "tf": 30, "running": True, "wallet": START_WALLET, "equity": START_WALLET,
    "position": None, "bars": [], "trades": [], "errors": [], "error_count": 0,
    "last_tick_ms": 0, "started_ms": int(time.time() * 1000), "status": "booting",
    "feed_fail_streak": 0,
    "tp": TAKE_PROFIT, "sl": STOP_LOSS, "stake_ratio": STAKE_RATIO,
}
STATE_FILE = os.path.join(ROOT, "panel_state.json")  # validated pair/tf/tp/sl/running, written atomically

ex = ccxt.kucoin({"enableRateLimit": True})
lock = threading.RLock()  # reentrant: control paths close positions while already holding it
# pair/tf are locked to the market bars.jsonl was collected for: history files are single-market,
# so switching here would mix BTC/USD bars into one calibration series. Per-market history first.
PAIR_TF_LOCKED = True
TP_BOUNDS = (0.0005, 0.05)   # 0.05% .. 5%
SL_BOUNDS = (0.0005, 0.05)   # magnitude of the negative fraction


def _finite_bounded(x, lo, hi):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and lo <= x <= hi


def validate_tp(v):
    """Accept percent (>=0.05) or fraction; return finite fraction or None."""
    if not _finite_bounded(v, 1e-9, 100.0):
        return None
    frac = v / 100.0 if v >= 0.05 else v
    return frac if TP_BOUNDS[0] <= frac <= TP_BOUNDS[1] else None


def validate_sl(v):
    """SL is always negative; accept percent (abs>=0.05) or fraction. Returns -|mag| or None."""
    if not _finite_bounded(v, -100.0, 100.0) or v == 0:
        return None
    mag = abs(v) / 100.0 if abs(v) >= 0.05 else abs(v)
    if not (SL_BOUNDS[0] <= mag <= SL_BOUNDS[1]):
        return None
    return -mag


def save_settings():
    """Persist controllable settings atomically (tmp + rename) so a crash never half-writes."""
    try:
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"pair": STATE["pair"], "tf": STATE["tf"], "tp": STATE.get("tp"),
                       "sl": STATE.get("sl"), "running": STATE["running"]}, f)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        log(f"settings save failed: {type(e).__name__}: {e}")


def restore_settings():
    """Restore validated settings; anything nonfinite/out-of-bounds/foreign is dropped.

    Called BEFORE wallet/position restore so running/pair/tf are already correct.
    """
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    with lock:
        tp = validate_tp(data.get("tp"))
        if tp is not None:
            STATE["tp"] = tp
        sl = validate_sl(data.get("sl"))
        if sl is not None:
            STATE["sl"] = sl
        if data.get("pair") == STATE["pair"] and _finite_bounded(data.get("tf"), 1, 86400) \
                and int(data["tf"]) == STATE["tf"]:
            pass  # only stored pair/tf is accepted; anything else stays locked
        if isinstance(data.get("running"), bool):
            STATE["running"] = data["running"]
    log(f"settings restored from {os.path.basename(STATE_FILE)}: tp={STATE['tp']} sl={STATE['sl']} running={STATE['running']}")
bars = deque(maxlen=600)
_seeded_t = set()      # timestamps produced by seed_from_ohlcv (synthetic 1m-splits, not polled)
_last_persisted_t = 0  # bars.jsonl must stay strictly increasing; dupes/out-of-order break calibration


def _tail_t(path):
    """Last t already written to the bar log (0 if none/unreadable)."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 4096))
            return json.loads(fh.read().decode("utf-8", "replace").strip().splitlines()[-1])["t"]
    except Exception:
        return 0
last_poll_price = None


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def alert(kind, msg, tb=None):
    rec = {"ts": int(time.time() * 1000), "kind": kind, "msg": str(msg)[:500],
           "tb": (tb or "")[-1500:], "tf": STATE["tf"], "pair": STATE["pair"],
           "errors_total": STATE["error_count"]}
    try:
        with open(ALERTS, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    with lock:
        STATE["errors"] = (STATE["errors"] + [rec])[-10:]
    log(f"ALERT[{kind}] {msg}")


def db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS trades(
        id INTEGER PRIMARY KEY AUTOINCREMENT, opened_ms INTEGER, closed_ms INTEGER,
        entry REAL, exit REAL, size REAL, pnl_abs REAL, pnl_pct REAL,
        open_reason TEXT, close_reason TEXT)""")
    have = {r[1] for r in c.execute("PRAGMA table_info(trades)")}
    for col in ("e_gap", "e_rsi", "e_vol", "e_spread", "e_trend", "lesson"):
        if col not in have:
            c.execute(f"ALTER TABLE trades ADD COLUMN {col} REAL" if col != "e_trend" and col != "lesson"
                      else f"ALTER TABLE trades ADD COLUMN {col} TEXT")
    c.commit()
    return c


def sma(vals, n):
    return sum(vals[-n:]) / n if len(vals) >= n else None


def rsi(vals, n=14):
    if len(vals) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(-n, 0):
        d = vals[i] - vals[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return 100 - 100 / (1 + rs)


def add_bar(price, ts_ms):
    """Bucket polls into bars of STATE['tf'] seconds.

    A feed outage writes no bars, leaving a hole in the series: indicators then span
    more wall clock than they assume and the expected-move gate (vol * 20 bars) reads
    ~10 minutes of an hour, i.e. too permissive. Pad the missed buckets flat with the
    last close (n=0) so wall clock and bar count stay in sync — flat bars add zero
    return, which biases bar_vol_pct down, i.e. the gate errs strict, never loose.
    """
    tf = STATE["tf"] * 1000
    bucket = ts_ms - (ts_ms % tf)
    global _last_persisted_t
    if bars and bucket - bars[-1]["t"] > tf:
        prev = bars[-1]["c"]
        for t in range(bars[-1]["t"] + tf, bucket, tf):
            bars.append({"t": t, "o": prev, "h": prev, "l": prev, "c": prev, "n": 0})
    if bars and bars[-1]["t"] == bucket:
        b = bars[-1]
        b["h"] = max(b["h"], price); b["l"] = min(b["l"], price); b["c"] = price
        b["n"] += 1
    else:
        if (bars and bars[-1]["n"] and bars[-1]["t"] not in _seeded_t
                and bars[-1]["t"] > _last_persisted_t):
            # Survey data: the 240-bar memory window (2h) is too short to calibrate the
            # TP/gate floors, and it dies with every restart. Persist each closed POLLED bar,
            # once, in order — seeded (synthetic) and re-emitted old bars are skipped, else
            # the calibration series gets duplicates with conflicting OHLC and time going
            # backwards.
            # ponytail: no rotation; bars.jsonl ~0.5MB/day — add rotation when it passes ~50MB
            try:
                with open(os.path.join(ROOT, "bars.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(bars[-1]) + "\n")
                _last_persisted_t = bars[-1]["t"]
            except Exception:
                pass
        bars.append({"t": bucket, "o": price, "h": price, "l": price, "c": price, "n": 1})


def seed_from_ohlcv():
    """Prefill history: 5m for tf>=300, 1m for tf<=60, with sub-minute halves/quarters."""
    tf = STATE["tf"]
    tf_req = "5m" if tf >= 300 else "1m"
    ohlcv = ex.fetch_ohlcv(STATE["pair"], tf_req, limit=200)
    if not ohlcv:
        return
    bars.clear()
    if tf >= 60:
        for t, o, h, l, c, v in ohlcv:
            bars.append({"t": t, "o": o, "h": h, "l": l, "c": c, "n": 1})
    elif tf == 30:
        for t, o, h, l, c, v in ohlcv:
            mid = (o + c) / 2
            bars.append({"t": t, "o": o, "h": max(o, mid), "l": min(o, mid), "c": mid, "n": 1})
            bars.append({"t": t + 30000, "o": mid, "h": max(mid, c, h), "l": min(mid, c, l),
                         "c": c, "n": 1})
    elif tf <= 15:
        for t, o, h, l, c, v in ohlcv:
            step = (c - o) / 4
            for i in range(4):
                sub_o = o + step * i
                sub_c = o + step * (i + 1)
                bars.append({"t": t + i * 15000, "o": sub_o, "h": max(sub_o, sub_c), "l": min(sub_o, sub_c),
                             "c": sub_c, "n": 1})
    # everything just appended is synthetic (1m candle split / exchange candle): never log it
    _seeded_t.update(b["t"] for b in bars)


RULES = {"min_gap_pct": 0.0, "min_bar_vol_pct": 0.0, "max_rsi_entry": 100.0}
RULES_FILE = os.path.join(ROOT, "rules.json")
LESSONS = deque(maxlen=200)

# Pre-training verdict (pretrain.py, 1y 1m data, BTC+SOL, fee 0.2% RT):
# every gate config tested was net-negative for the SMA9/21 entry family.
# The "recommended common rules" from that run are therefore only LOSS-LIMITERS,
# not profit-makers — adopt them as a floor, never quote them as an edge.
PRETRAIN_FLOOR = {"min_gap_pct": 0.02, "min_bar_vol_pct": 0.03, "max_rsi_entry": 65.0}
# min_gap 0.12 was unreachable: entry fires on the tick right after an SMA cross, and the
# gap at that instant measured p90 0.013% / max 0.092% over 16.7h of real 30s bars
# (94 crosses, 0 above 0.12) => the panel was structurally frozen (0 entries in 16.7h replay
# and 0 in 6h live). 0.02 keeps only the top ~2% of crossings (~1-2 entries/day) while the
# fee guard (expected move >= TP) stays untouched. Loosening to "enter anywhere in an
# up-regime with gap>=0.02" replayed far worse (-37 USDT/16.7h) - do not do that.


def save_rules():
    try:
        json.dump({"rules": RULES, "updated": int(time.time() * 1000),
                   "lessons_seen": len(LESSONS)}, open(RULES_FILE, "w"), ensure_ascii=False, indent=1)
    except Exception as e:
        alert("rules_save_error", f"{type(e).__name__}: {e}", traceback.format_exc())


def load_rules():
    """Learned rules must survive a restart, otherwise the panel forgets its own lessons.
    Pre-trained floor (from pretrain.py grid search) is the minimum strictness."""
    try:
        if os.path.exists(RULES_FILE):
            data = json.load(open(RULES_FILE, encoding="utf-8"))
            for k, v in (data.get("rules") or {}).items():
                if k in RULES:
                    RULES[k] = v
        # never weaker than the pre-trained floor; drop anything nonfinite/out-of-bounds
        ok = (lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v))
        if ok(RULES["min_gap_pct"]) and 0 <= RULES["min_gap_pct"] <= 1.0:
            RULES["min_gap_pct"] = max(RULES["min_gap_pct"], PRETRAIN_FLOOR["min_gap_pct"])
        if ok(RULES["min_bar_vol_pct"]) and 0 <= RULES["min_bar_vol_pct"] <= 1.0:
            RULES["min_bar_vol_pct"] = max(RULES["min_bar_vol_pct"], PRETRAIN_FLOOR["min_bar_vol_pct"])
        if ok(RULES["max_rsi_entry"]) and 0 <= RULES["max_rsi_entry"] <= 100:
            RULES["max_rsi_entry"] = min(RULES["max_rsi_entry"], PRETRAIN_FLOOR["max_rsi_entry"])
        for k, fb in (("min_gap_pct", PRETRAIN_FLOOR["min_gap_pct"]),
                      ("min_bar_vol_pct", PRETRAIN_FLOOR["min_bar_vol_pct"])):
            if not (ok(RULES[k]) and 0 <= RULES[k] <= 1.0):
                RULES[k] = fb
        if not (ok(RULES["max_rsi_entry"]) and 0 <= RULES["max_rsi_entry"] <= 100):
            RULES["max_rsi_entry"] = PRETRAIN_FLOOR["max_rsi_entry"]
        log(f"learned rules restored (validated, floor applied): {RULES}")
    except Exception as e:
        RULES.update(PRETRAIN_FLOOR)  # corrupt/missing rules.json must never disarm the gates
        alert("rules_load_error", f"{type(e).__name__}: {e}", traceback.format_exc())


def analyze_loss(pnl, t, ctx):
    """Deterministic root-cause analysis of a losing trade + the behaviour to change."""
    causes, fixes = [], []
    dur_min = max(0.0, (t["closed_ms"] - t["opened_ms"]) / 60000)
    fees = t["size"] * (t["entry"] + t["exit"]) * FEE
    gap = ctx.get("gap_pct")
    rsi_v = ctx.get("rsi")
    vol = ctx.get("bar_vol_pct")
    if abs(pnl) <= fees * 1.25:
        causes.append("ضرر تقریباً برابر کارمزد بود (۰.۲٪ رفت‌وبرگشت)")
        fixes.append(("min_gap_pct", RULES["min_gap_pct"] + 0.01,
                      "ورود فقط با تلاقی قوی‌تر تا حرکت، هزینه کارمزد را بپوشاند"))
    if gap is not None and gap < 0.05:
        causes.append(f"تلاقی ضعیف بود (فاصله میانگین‌ها {gap:.3f}٪)")
        fixes.append(("min_gap_pct", max(RULES["min_gap_pct"], 0.05),
                      "فاصله دو میانگین حداقل ۰.۰۵٪ باشد"))
    if dur_min < 2:
        causes.append(f"عمر معامله خیلی کوتاه بود ({dur_min:.1f} دقیقه)")
        causes.append("یا نویز کندل ۳۰ ثانیه‌ای بود یا روند همان لحظه برگشت")
    if vol is not None and vol < 0.01:
        causes.append(f"بازار کم‌نوسان/رِنج بود (نوسان کندل {vol:.4f}٪)")
        fixes.append(("min_bar_vol_pct", max(RULES["min_bar_vol_pct"], 0.02),
                      "در بازار رِنج معامله نکن؛ حداقل نوسان کندل ۰.۰۲٪"))
    if rsi_v is not None and rsi_v > 70:
        causes.append(f"ورود در اشباع خرید (RSI {rsi_v:.0f})")
        fixes.append(("max_rsi_entry", 70.0, "بالای RSI ۷۰ نخر"))
    if t["close_reason"] == "stop_loss":
        causes.append("حد ضرر خورد → جهت ورود اشتباه بود")
    elif t["close_reason"] == "sma_cross_down":
        causes.append("روند بعد از ورود برگشت (تلاقی نزولی)")
    elif t["close_reason"] == "manual":
        causes.append("دستی بسته شد (آزمایش کاربر) — درس آماری نیست")
    if not causes:
        causes.append("ضرر بدون الگوی مشخص (نمونه کم)")
    if t["close_reason"] == "manual":
        fixes = []  # ponytail: user experiments are not bot lessons — record the cause, change no rule
    return {
        "ts": int(time.time() * 1000), "trade_id": t["id"], "pnl": round(pnl, 4),
        "pnl_pct": round(t["pnl_pct"], 3), "duration_min": round(dur_min, 1),
        "close_reason": t["close_reason"], "entry_gap": gap, "entry_rsi": rsi_v,
        "entry_vol": vol, "causes": causes,
        "fixes": [{"param": p, "value": round(v, 4), "why": w} for p, v, w in fixes],
    }


def apply_fixes(lesson):
    """Keep hypotheses in the lesson; one loss cannot validate a trading rule."""
    lesson["promotion"] = {
        "approved": False,
        "reason": "proposal only; independent out-of-sample validation required",
    }
    return []


def open_position(price, reason, ctx=None):
    if STATE["position"] or not price:
        return None
    size = (STATE["wallet"] * STAKE_RATIO) / price
    ctx = ctx or {}
    c = db()
    cur = c.execute("INSERT INTO trades(opened_ms, entry, size, open_reason, e_gap, e_rsi, e_vol, "
                    "e_spread, e_trend) VALUES(?,?,?,?,?,?,?,?,?)",
                    (int(time.time() * 1000), price, size, reason, ctx.get("gap_pct"), ctx.get("rsi"),
                     ctx.get("bar_vol_pct"), ctx.get("spread_pct"), ctx.get("trend")))
    rid = cur.lastrowid
    c.commit(); c.close()
    with lock:
        STATE["position"] = {"id": rid, "entry": price, "size": size,
                             "opened_ms": int(time.time() * 1000), "ctx": ctx}
    log(f"OPEN {reason} price={price:.2f} size={size:.6f} gap={ctx.get('gap_pct')} rsi={ctx.get('rsi')}")
    return rid


def close_position(price, reason):
    pos = STATE["position"]
    if not pos or not price:
        return None
    pnl_pct = (price - pos["entry"]) / pos["entry"]
    gross = pos["size"] * (price - pos["entry"])
    fees = pos["size"] * (pos["entry"] + price) * FEE
    pnl = gross - fees
    with lock:
        STATE["wallet"] += pnl
        STATE["position"] = None
    c = db()
    closed_ms = int(time.time() * 1000)
    c.execute("UPDATE trades SET closed_ms=?, exit=?, pnl_abs=?, pnl_pct=?, close_reason=? WHERE id=?",
              (closed_ms, price, pnl, pnl_pct * 100, reason, pos["id"]))
    t = {"id": pos["id"], "opened_ms": pos["opened_ms"], "closed_ms": closed_ms, "entry": pos["entry"],
         "exit": price, "size": pos["size"], "pnl_abs": pnl, "pnl_pct": pnl_pct * 100,
         "close_reason": reason}
    lesson = None
    dossier_path = os.path.join(ROOT, "dossiers", f"trade_{pos['id']}.json")
    try:
        os.makedirs(os.path.dirname(dossier_path), exist_ok=True)
        win = [b for b in list(bars) if pos["opened_ms"] <= b["t"] + STATE["tf"] * 1000]
        prices = [b["c"] for b in win] or [pos["entry"], price]
        hi, lo = max(prices), min(prices)
        with lock:
            dec = [d for d in list(DECISIONS) if d["ts"] >= pos["opened_ms"]][-60:]
            mkt = STATE.get("market") or {}
        json.dump({
            "trade": t, "entry_ctx": pos.get("ctx") or {}, "exit_reason": reason,
            "bars_during_trade": win[-300:],
            "mfe_pct": round((hi - pos["entry"]) / pos["entry"] * 100, 4),
            "mae_pct": round((lo - pos["entry"]) / pos["entry"] * 100, 4),
            "market_at_exit": mkt, "decisions_during_trade": dec,
            "params": {"take_profit": TAKE_PROFIT, "stop_loss": STOP_LOSS, "fee_per_side": FEE},
            "rules_at_exit": dict(RULES),
        }, open(dossier_path, "w"), ensure_ascii=False)
    except Exception as e:
        alert("dossier_error", f"{type(e).__name__}: {e}", traceback.format_exc())
    if pnl < 0:
        lesson = analyze_loss(pnl, t, pos.get("ctx") or {})
        applied = apply_fixes(lesson)
        lesson["applied"] = applied
        lesson["rules_after"] = dict(RULES)
        c.execute("UPDATE trades SET lesson=? WHERE id=?",
                  (json.dumps(lesson, ensure_ascii=False), pos["id"]))
        LESSONS.append(lesson)
        alert("loss_lesson", f"ضرر #{pos['id']} {pnl:+.2f}$ — علت: " + "؛ ".join(lesson["causes"]) +
              (" | اعمال شد: " + ", ".join(applied) if applied else " | تغییر قانونی لازم نبود"))
        with open(os.path.join(ROOT, "lessons.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## {time.strftime('%Y-%m-%d %H:%M')} — trade #{pos['id']} {pnl:+.4f} USDT "
                    f"({t['pnl_pct']:+.3f}%)\n")
            f.write(f"- بستن با: {reason} | عمر {lesson['duration_min']} دقیقه | "
                    f"gap ورود {lesson['entry_gap']} | RSI ورود {lesson['entry_rsi']} | "
                    f"نوسان {lesson['entry_vol']}\n")
            for cz in lesson["causes"]:
                f.write(f"- علت: {cz}\n")
            for fx in lesson["fixes"]:
                f.write(f"- پیشنهاد اصلاح: {fx['param']} = {fx['value']} ({fx['why']})\n")
            if applied:
                f.write(f"- اعمال شد: {', '.join(applied)} | قوانین فعلی: {RULES}\n")
    c.commit(); c.close()
    with lock:
        STATE["lessons"] = list(LESSONS)[-60:]
        STATE["rules"] = dict(RULES)
    log(f"CLOSE {reason} entry={pos['entry']:.2f} exit={price:.2f} pnl={pnl:+.2f} | rules={RULES}")
    return pnl


PREV = {"up": None, "cross_ms": 0}
CROSS_GRACE_MS = 10 * 60 * 1000  # 20 bars at 30s: بعد از تلاقی فرصت داریم تا فاصله واقعاً باز شود
DECISIONS = deque(maxlen=400)


def market_snapshot(ticker, closes):
    """Plain-language market state, computed on every tick."""
    last = closes[-1] if closes else None
    # volatility: stddev of 30s bar returns in %, last 60 bars
    rets = []
    for i in range(max(1, len(closes) - 60), len(closes)):
        if closes[i - 1]:
            rets.append(abs(closes[i] / closes[i - 1] - 1) * 100)
    vol = sum(rets) / len(rets) if rets else 0.0
    hi24 = ticker.get("high")
    lo24 = ticker.get("low")
    rng24 = ((hi24 - lo24) / lo24 * 100) if hi24 and lo24 else 0.0
    chg24 = ticker.get("percentage") or 0.0
    return {
        "chg24_pct": round(chg24, 2),
        "range24_pct": round(rng24, 2),
        "bar_vol_pct": round(vol, 4),
        "quote_vol_24h": round(ticker.get("quoteVolume") or 0),
        "bid": ticker.get("bid"), "ask": ticker.get("ask"),
        "spread_pct": round((ticker["ask"] - ticker["bid"]) / ticker["last"] * 100, 4)
        if ticker.get("ask") and ticker.get("bid") and last else None,
    }


def strategy_tick(price, ticker=None):
    closes = [b["c"] for b in bars]
    f, s = sma(closes, 9), sma(closes, 21)
    if f is None or s is None:
        return
    up = f > s
    prev_up = PREV["up"]
    fresh_up = up and prev_up is False
    fresh_dn = (not up) and prev_up is True
    PREV["up"] = up
    now_ms = int(time.time() * 1000)
    if fresh_up:
        PREV["cross_ms"] = now_ms
    gap_pct = (f - s) / s * 100
    r = rsi(closes, 14)
    mkt = market_snapshot(ticker, closes) if ticker else {}
    trend_fa = "صعودی" if gap_pct > 0.02 else ("نزولی" if gap_pct < -0.02 else "خنثی")
    pos = STATE["position"]
    action, rule, reason_fa = "hold", "", ""

    if pos:
        pnl_pct = (price - pos["entry"]) / pos["entry"] * 100
        tp = STATE.get("tp", TAKE_PROFIT)
        sl = STATE.get("sl", STOP_LOSS)
        if pnl_pct >= tp * 100:
            action, rule = "close", "take_profit"
            reason_fa = f"سود به هدف {tp*100:.2f}٪ رسید (الان {pnl_pct:+.2f}٪) → فروش برای قفل کردن سود"
        elif pnl_pct <= sl * 100:
            action, rule = "close", "stop_loss"
            reason_fa = f"ضرر به حد مجاز {sl*100:.2f}٪ رسید (الان {pnl_pct:+.2f}٪) → فروش برای محدود کردن ضرر"
        elif fresh_dn:
            action, rule = "close", "sma_cross_down"
            reason_fa = ("میانگین ۹ تازه از میانگین ۲۱ رو به پایین رد شد → روند عوض شد، "
                         f"پوزیشن بسته می‌شود (سود/ضرر فعلی {pnl_pct:+.2f}٪)")
        else:
            reason_fa = (f"پوزیشن باز است، سود/ضرر فعلی {pnl_pct:+.2f}٪ — منتظر هدف "
                         f"{tp*100:.1f}٪ یا حد ضرر {sl*100:.1f}٪ یا رد شدن میانگین‌ها")
    else:
        gate_fail = []
        if gap_pct < RULES["min_gap_pct"]:
            gate_fail.append(f"فاصله میانگین‌ها {gap_pct:+.3f}٪ کمتر از حداقل قانونی {RULES['min_gap_pct']:.3f}٪ است")
        vol_now = mkt.get("bar_vol_pct") if mkt else None
        if vol_now is not None and vol_now < RULES["min_bar_vol_pct"]:
            gate_fail.append(f"نوسان کندل {vol_now:.4f}٪ کمتر از حداقل {RULES['min_bar_vol_pct']:.3f}٪ است (بازار رِنج)")
        if r is not None and r > RULES["max_rsi_entry"]:
            gate_fail.append(f"RSI {r:.0f} بالای سقف قانونی {RULES['max_rsi_entry']:.0f} است (اشباع خرید)")
        if vol_now is not None:
            tp_now = STATE.get("tp", TAKE_PROFIT)
            exp_move = vol_now * 20 * MOVE_REALISM  # 20 bars = 10 min at 30s; heuristic estimate,
            # NOT a return/profit forecast — MOVE_REALISM is a measured discount of the vol proxy
            if exp_move < tp_now * 100:
                gate_fail.append(
                    f"برآورد تجربی دامنه حرکت ۱۰ دقیقه {exp_move:.3f}٪ (تخفیف تجربی ×{MOVE_REALISM:.2f} روی نوسان) "
                    f"از هدف {tp_now*100:.1f}٪ کمتر است "
                    f"(کارمزد رفت‌وبرگشت {FEE*2*100:.1f}٪) → ورود نمی‌ارزد")
        recent_up = (up and PREV["up"] is True and (now_ms - PREV["cross_ms"]) <= CROSS_GRACE_MS
                     and gap_pct >= RULES["min_gap_pct"])
        if (fresh_up or recent_up) and not gate_fail:
            action, rule = "open", "sma_cross_up"
            reason_fa = (("میانگین ۹ تازه از میانگین ۲۱ رو به بالا رد شد " if fresh_up else
                          "تلاقی صعودی تازه است (کمتر از ۱۰ دقیقه پیش) و فاصله میانگین‌ها اکنون باز شده ")
                         + f"(فاصله {gap_pct:+.3f}٪) و همه قوانین یادگرفته‌شده پاس شدند → خرید")
        elif fresh_up or recent_up:
            reason_fa = "تلاقی صعودی بود ولی قانون یادگرفته‌شده جلوی ورود را گرفت: " + "؛ ".join(gate_fail)
        elif up:
            reason_fa = (f"روند صعودی است (فاصله {gap_pct:+.3f}٪) ولی تلاقی تازه نیست → "
                         "ریسک دیر وارد شدن، منتظر تلاقی بعدی می‌مانیم")
        else:
            reason_fa = (f"میانگین ۹ زیر میانگین ۲۱ است (فاصله {gap_pct:+.3f}٪) → "
                         "در بازار نزولی/خنثی خرید نمی‌کنیم")

        if fresh_up:  # هر تلاقی تازه = یک نمونه شاهد برای کالیبره کردن کف‌ها (پایدار روی دیسک)
            try:
                with open(os.path.join(ROOT, "gates.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": int(time.time() * 1000), "gap_pct": round(gap_pct, 4),
                                         "bar_vol_pct": vol_now,
                                         "rsi": round(r, 1) if r is not None else None,
                                         "exp_move_10m": round((vol_now or 0) * 20 * MOVE_REALISM, 4),
                                         "tp_pct": round(STATE.get("tp", TAKE_PROFIT) * 100, 2),
                                         "blocked": bool(gate_fail), "why": gate_fail},
                                        ensure_ascii=False) + "\n")
            except Exception as e:
                log(f"gate log write failed: {e}")

    if action == "open":
        open_position(price, rule, {"gap_pct": gap_pct, "rsi": r, "trend": trend_fa,
                                    "bar_vol_pct": mkt.get("bar_vol_pct"), "spread_pct": mkt.get("spread_pct")})
    elif action == "close":
        close_position(price, rule)

    DECISIONS.append({
        "ts": int(time.time() * 1000), "price": round(price, 4),
        "sma9": round(f, 4), "sma21": round(s, 4), "gap_pct": round(gap_pct, 4),
        "rsi": round(r, 1) if r is not None else None, "trend": trend_fa,
        "fresh_cross": "up" if fresh_up else ("down" if fresh_dn else None),
        "pos": "long" if pos else "none",
        "action": action, "rule": rule or "-", "reason": reason_fa, "market": mkt,
        "exp_move_estimate": round((mkt.get("bar_vol_pct") or 0) * 20 * MOVE_REALISM, 4),
    })
    with lock:
        STATE["decisions"] = list(DECISIONS)[-120:]
        STATE["market"] = mkt


def save_display_trades():
    """Display only: last 30 closed rows for the UI table (stats are aggregated in load_state)."""
    c = db()
    try:
        rows = c.execute("SELECT id,opened_ms,closed_ms,entry,exit,size,pnl_abs,pnl_pct,open_reason,"
                         "close_reason FROM trades WHERE closed_ms IS NOT NULL ORDER BY id DESC LIMIT 30").fetchall()
    finally:
        c.close()
    trades = [dict(zip(["id", "opened_ms", "closed_ms", "entry", "exit", "size", "pnl_abs",
                        "pnl_pct", "open_reason", "close_reason"], r)) for r in rows]
    with lock:
        STATE["trades"] = trades


def load_state():
    save_display_trades()
    c = db()
    try:
        closed = c.execute("SELECT COUNT(*), "
                           "SUM(CASE WHEN pnl_abs > 0 THEN 1 ELSE 0 END), "
                           "COALESCE(SUM(pnl_abs), 0) FROM trades WHERE closed_ms IS NOT NULL").fetchone()
    finally:
        c.close()
    with lock:
        STATE["stats"] = {
            "trades": int(closed[0] or 0),
            "wins": int(closed[1] or 0),
            "pnl": round(float(closed[2] or 0.0), 4),
            "open": 1 if STATE["position"] else 0,
        }


NET_ERRORS = (ccxt.NetworkError, ccxt.RequestTimeout, ccxt.ExchangeNotAvailable)


def check_blind_gap(price, now_ms):
    """True when the loop was blind longer than GAP_BLIND_SECS (Mac slept / long outage).

    No ticks means TP/SL never ran, so a carried position is unmanaged risk: flatten it
    at the first price we can see and leave the hole visible in alerts.jsonl.
    """
    last = STATE["last_tick_ms"]
    gap_s = (now_ms - last) / 1000 if last else 0
    if gap_s <= GAP_BLIND_SECS:
        return False
    alert("feed_gap", f"gap {gap_s / 60:.1f} min — no ticks, SL/TP did not run; "
                      f"open_position={bool(STATE['position'])}")
    if STATE["position"]:
        close_position(price, "feed_gap")
    return True


def fetch_bounded(pair, timeout=FETCH_TIMEOUT_SECS):
    """Run the ticker call in a throwaway daemon thread: sockets get ccxt's timeout, but
    DNS getaddrinfo does not, so a resolver hang blocks the call for minutes and blinds
    the whole loop (feed_fails.log 17:01 shows ~130s per attempt during a DNS outage).
    ponytail: each hung attempt leaks one stuck thread (rare, short-lived outage); switch
    to a bounded resolver only if that ever shows up in memory."""
    box = {}
    def run():
        try:
            box["t"] = ex.fetch_ticker(pair)
        except Exception as e:  # re-raised in the caller's thread
            box["e"] = e
    th = threading.Thread(target=run, daemon=True)
    th.start()
    th.join(timeout)
    if "t" in box:
        return box["t"]
    if "e" in box:
        raise box["e"]
    raise ccxt.RequestTimeout(f"{pair} fetch stalled >{timeout}s (DNS/network hang)")


def fetch_ticker_retry(pair, tries=4):
    """Transient kucoin hiccups are normal; retry before giving the loop up."""
    for i in range(tries):
        try:
            return fetch_bounded(pair)
        except NET_ERRORS:
            if i == tries - 1:
                raise
            time.sleep(1 + i)


def root_cause(e):
    """ccxt's NetworkError message drops the socket reason (only id+method+url),
    and alert() keeps only the last 1500 chars of the traceback — so walk the
    __cause__ chain and keep the real reason ourselves."""
    c = e
    while c.__cause__ is not None:
        c = c.__cause__
    return f"{type(e).__name__}: {e}" + ("" if c is e else f" | cause: {type(c).__name__}: {str(c)[:300]}")


def log_feed_fail(fail_streak, reason):
    """Every network blip is recorded with its real socket reason — silently, so the
    alert feed stays for things that matter."""
    try:
        with open(FEED_FAILS, "a") as f:
            f.write(f"{int(time.time())} streak={fail_streak} {reason}\n")
    except Exception:
        pass


def should_alert(net, fail_streak):
    """One-iteration blips stay silent (kucoin/cloudflare resets a single call here every
    few minutes); a sustained outage alerts at streak 3, then a rare ping every 30 loops.
    Non-network errors always alert."""
    return (not net) or fail_streak == 3 or fail_streak % 30 == 0


def feed_loop():
    slow_ticks = 0
    fail_streak = 0
    while True:
        if not STATE["running"]:
            time.sleep(1)
            continue
        try:
            ticker = fetch_ticker_retry(STATE["pair"])
            price = float(ticker["last"])
            now_ms = int(time.time() * 1000)
            check_blind_gap(price, now_ms)
            add_bar(price, now_ms)
            strategy_tick(price, ticker)
            with lock:
                STATE["last_tick_ms"] = now_ms
                STATE["equity"] = STATE["wallet"] + (
                    STATE["position"]["size"] * (price - STATE["position"]["entry"])
                    if STATE["position"] else 0.0)
                STATE["price"] = price
                STATE["bars"] = list(bars)[-240:]
            load_state()
            STATE["status"] = "running"
            slow_ticks = 0
        except Exception as e:
            fail_streak += 1
            net = isinstance(e, NET_ERRORS)
            reason = root_cause(e) if net else f"{type(e).__name__}: {e}"
            with lock:
                if net:
                    STATE["feed_fail_streak"] = fail_streak
                    STATE["status"] = "feed_unreachable"
                else:
                    STATE["error_count"] += 1
            if net:
                log_feed_fail(fail_streak, reason)
            # a flaky exchange is not a code bug: alert policy in should_alert()
            if should_alert(net, fail_streak):
                alert("feed_warn" if net else "loop_error", reason, traceback.format_exc())
            time.sleep(min(30, 3 * fail_streak))
        else:
            fail_streak = 0
            with lock:
                STATE["feed_fail_streak"] = 0
            time.sleep(POLL_SECS)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _origin_ok(self):
        """Same-origin + custom-header gate for every state-changing request."""
        host = (self.headers.get("Host") or "").strip()
        origin = (self.headers.get("Origin") or "").strip()
        if not host or not origin:
            return False
        if origin.rstrip("/") != f"http://{host}".rstrip("/"):
            return False
        return self.headers.get("X-Panel-Request") == "1"

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/api/control":
            return self._send(404, {"error": "not found"})
        if not self._origin_ok():
            return self._send(403, {"error": "forbidden: same-origin POST + X-Panel-Request required"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}") if n else {}
        except Exception:
            return self._send(400, {"error": "bad json body"})
        if not isinstance(body, dict):
            return self._send(400, {"error": "bad json body"})
        try:
            return self._control(body)
        except Exception as e:
            alert("http_error", f"{u.path}: {type(e).__name__}: {e}", traceback.format_exc())
            return self._send(500, {"error": str(e)})

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/control":
            # every state change is POST-only: GETs are crawlers/prefetchers and must not mutate
            return self._send(405, {"error": "use POST /api/control with X-Panel-Request header"})
        def _int(v, d):
            # ponytail: bad query params are ignored, not fatal; tighten if UI ever needs an error
            try:
                return int(v)
            except (TypeError, ValueError):
                return d

        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(ROOT, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html")
            if u.path == "/api/state":
                with lock:
                    snap = {k: v for k, v in STATE.items()}
                return self._send(200, snap)
            if u.path == "/api/alerts":
                n = _int(q.get("n", ["20"])[0], 20)
                lines = []
                if os.path.exists(ALERTS):
                    with open(ALERTS) as f:
                        lines = f.readlines()[-n:]
                return self._send(200, [json.loads(x) for x in lines if x.strip()])
            if u.path == "/api/fixes":
                out_dir = os.path.expanduser(os.environ.get("PANEL_FIXES_DIR", "~/panel-fixes"))
                resp, ts = "", ""
                try:
                    files = sorted((os.path.join(out_dir, f) for f in os.listdir(out_dir)),
                                   key=os.path.getmtime, reverse=True)
                    if files:
                        txt = open(files[0], encoding="utf-8").read()
                        resp = txt.split("## Response", 1)[-1].strip() if "## Response" in txt else ""
                        ts = os.path.basename(files[0])[:16]
                except Exception:
                    pass
                return self._send(200, {"ts": ts, "text": resp[-1200:]})
            if u.path == "/api/decisions":
                n = _int(q.get("n", ["40"])[0], 40)
                with lock:
                    dec = list(DECISIONS)[-n:][::-1]
                    mkt = STATE.get("market") or {}
                return self._send(200, {"market": mkt, "decisions": dec})
            if u.path == "/api/lessons":
                n = _int(q.get("n", ["30"])[0], 30)
                c = db()
                rows = c.execute("SELECT lesson FROM trades WHERE lesson IS NOT NULL "
                                 "ORDER BY id DESC LIMIT ?", (n,)).fetchall()
                c.close()
                lessons = [json.loads(r[0]) for r in rows]
                with lock:
                    rules = dict(RULES)
                    errs = list(STATE.get("errors") or [])
                return self._send(200, {"rules": rules, "lessons": lessons,
                                        "errors": errs[-10:], "error_count": STATE["error_count"]})
        except Exception as e:
            alert("http_error", f"{u.path}: {type(e).__name__}: {e}", traceback.format_exc())
            return self._send(500, {"error": str(e)})

    def _control(self, body):
        """All mutations live here (POST-only, same-origin gated). GET never reaches this."""
        with lock:  # serialize control vs feed-loop position mutations (RLock: close_position reenters)
            act = body.get("action")
            if act == "reset":
                return self._send(409, {
                    "ok": False,
                    "error": "reset removed: trade history and wallet are preserved — "
                             "تاریخچه معاملات و کیف‌پول حفظ می‌شود؛ ریست مخرب حذف شد",
                })
            if act == "retrain":
                import subprocess
                r = subprocess.run([sys.executable, os.path.join(ROOT, "train.py")],
                                   capture_output=True, text=True, timeout=120)
                out = (r.stdout or r.stderr)[-1500:]
                ok = r.returncode == 0
                # report-only: rules.json is adopted only through validated load_rules/retrain_from_history
                return self._send(200 if ok else 500, {"ok": ok, "applied": False,
                                                       "exit_code": r.returncode, "output": out})
            if act == "force_open":
                last = DECISIONS[-1] if DECISIONS else {}
                open_position(STATE.get("price"), "manual", {
                    "gap_pct": last.get("gap_pct"), "rsi": last.get("rsi"),
                    "bar_vol_pct": (STATE.get("market") or {}).get("bar_vol_pct"),
                    "spread_pct": (STATE.get("market") or {}).get("spread_pct"),
                    "trend": last.get("trend")})
            elif act == "force_close":
                close_position(STATE.get("price"), "manual")
            elif act in ("stop", "start", "keep", None):
                if act in ("stop", "start"):
                    STATE["running"] = (act == "start")
            else:
                return self._send(400, {"ok": False, "error": f"unknown action: {act!r}"})

            for key, val in (("tp", body.get("tp")), ("sl", body.get("sl"))):
                if val is None:
                    continue
                v = validate_tp(val) if key == "tp" else validate_sl(val)
                if v is None:
                    return self._send(400, {"ok": False,
                                            "error": f"invalid {key}: must be finite percent 0.05–5 "
                                                     f"(or fraction), got {val!r}"})
                STATE[key] = v
                log(f"{key} -> {STATE[key] * 100:.2f}%")

            if "tf" in body or "pair" in body:
                return self._send(409, {
                    "ok": False,
                    "error": "pair/timeframe changes are locked to BTC/USDT @30s: bars.jsonl and the "
                             "calibration history are single-market — mixing markets would corrupt the "
                             "series. Per-market history must exist first. "
                             "تغییر جفت‌ارز/تایم‌فریم تا ساخت تاریخچه جداگانه برای هر بازار قفل است",
                })
            save_settings()
            return self._send(200, {"ok": True, "running": STATE["running"], "tf": STATE["tf"],
                                    "pair": STATE["pair"], "tp": STATE.get("tp"), "sl": STATE.get("sl")})

    def log_message(self, *a):
        pass


def restore_position():
    """A restart must not forget an open trade: adopt the newest open row from the DB."""
    c = db()
    row = c.execute("SELECT id, opened_ms, entry, size, e_gap, e_rsi, e_vol, e_spread, e_trend "
                    "FROM trades WHERE closed_ms IS NULL "
                    "ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    if row:
        ctx = {"gap_pct": row[4], "rsi": row[5], "bar_vol_pct": row[6],
               "spread_pct": row[7], "trend": row[8]}
        with lock:
            STATE["position"] = {"id": row[0], "opened_ms": row[1], "entry": row[2],
                                 "size": row[3], "ctx": ctx}
        log(f"restored open position #{row[0]} entry={row[2]:.2f} size={row[3]:.6f}")


def restore_wallet():
    """Wallet must survive a restart: equity = start + realised pnl of every closed trade.
    ponytail: derived from the DB, not a stored balance — no migration, and /api/control?action=reset
    (which deletes the rows) still returns it to exactly START_WALLET."""
    c = db()
    row = c.execute("SELECT COALESCE(SUM(pnl_abs), 0) FROM trades WHERE closed_ms IS NOT NULL").fetchone()
    c.close()
    with lock:
        STATE["wallet"] = START_WALLET + float(row[0] or 0.0)
        STATE["equity"] = STATE["wallet"]
    log(f"wallet restored: start={START_WALLET:.2f} realised={row[0]:+.4f} -> {STATE['wallet']:.4f}")


def retrain_from_history():
    """Adopt rules.json only after full validation (finite, bounded, floored).

    Called at startup and explicitly; the periodic blind retrain_loop is REMOVED —
    an offline rules.json must never silently re-arm the live gates mid-session.
    """
    try:
        if os.path.exists(RULES_FILE):
            data = json.load(open(RULES_FILE, encoding="utf-8"))
            rules = data.get("rules") or {}
            with lock:
                for k, v in rules.items():
                    if k in RULES and isinstance(v, (int, float)) and not isinstance(v, bool) \
                            and math.isfinite(v):
                        RULES[k] = v
                RULES["min_gap_pct"] = max(RULES["min_gap_pct"], PRETRAIN_FLOOR["min_gap_pct"])
                RULES["min_bar_vol_pct"] = max(RULES["min_bar_vol_pct"], PRETRAIN_FLOOR["min_bar_vol_pct"])
                RULES["max_rsi_entry"] = min(RULES["max_rsi_entry"], PRETRAIN_FLOOR["max_rsi_entry"])
                STATE["rules"] = dict(RULES)
    except Exception as e:
        alert("retrain_error", f"{type(e).__name__}: {e}", traceback.format_exc())


def main():
    db().close()
    load_rules()
    STATE["rules"] = dict(RULES)
    STATE["lessons"] = []
    restore_settings()   # validated pair/tf/tp/sl/running before wallet/position restore
    restore_wallet()
    restore_position()
    global _last_persisted_t
    _last_persisted_t = _tail_t(os.path.join(ROOT, "bars.jsonl"))
    try:
        seed_from_ohlcv()
    except Exception as e:
        alert("seed_error", f"{type(e).__name__}: {e}", traceback.format_exc())
    threading.Thread(target=feed_loop, daemon=True).start()
    log(f"panel on http://localhost:{PORT} pair={STATE['pair']} tf={STATE['tf']}s")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
