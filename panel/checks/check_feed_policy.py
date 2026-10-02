"""Self-check for the feed-alert policy + real-cause extraction. Run: ~/freqtrade-venv/bin/python check_feed_policy.py"""
import ccxt
from server import should_alert, root_cause

# a single blip must not alert; a sustained outage must
assert should_alert(True, 1) is False
assert should_alert(True, 2) is False
assert should_alert(True, 3) is True
assert should_alert(True, 30) is True
assert should_alert(True, 60) is True
assert should_alert(True, 31) is False
assert should_alert(False, 1) is True      # code errors always alert

# ccxt NetworkError carries only id+method+url; the socket reason is one level down
try:
    raise ccxt.NetworkError("kucoin GET https://api.kucoin.com/x") from OSError("Connection reset by peer")
except ccxt.NetworkError as e:
    r = root_cause(e)
    assert "Connection reset by peer" in r and "cause" in r, r

print("ok")

# logging path must actually write the captured reason (temp file, no touching real log)
import os, tempfile
import server
tmp = tempfile.mkdtemp()
server.FEED_FAILS = os.path.join(tmp, "f.log")
server.log_feed_fail(2, "NetworkError: x | cause: ConnectionResetError: boom")
line = open(server.FEED_FAILS).read().strip()
assert "streak=2" in line and "boom" in line, line
print("ok-log")
