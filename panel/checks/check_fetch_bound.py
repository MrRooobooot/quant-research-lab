#!/usr/bin/env python3
"""Self-check: a hung ticker call (DNS getaddrinfo ignores socket timeouts) must not stall
the feed loop longer than FETCH_TIMEOUT_SECS."""
import time, importlib.util, sys, ccxt

spec = importlib.util.spec_from_file_location("srv", "~/freqtrade/panel/server.py")
srv = importlib.util.module_from_spec(spec)
sys.modules["srv"] = srv
spec.loader.exec_module(srv)  # imports only; nothing starts until main()

srv.ex = ccxt.kucoin()

# fast call passes through
srv.ex.fetch_ticker = lambda p: {"last": 1.0}
assert srv.fetch_bounded("BTC/USDT", timeout=2)["last"] == 1.0

# slow call is cut at the timeout, not whenever DNS gives up
srv.ex.fetch_ticker = lambda p: (time.sleep(10), {"last": 2.0})[1]
t0 = time.time()
try:
    srv.fetch_bounded("BTC/USDT", timeout=1)
    raise AssertionError("stalled call should not return")
except ccxt.RequestTimeout:
    pass
dt = time.time() - t0
assert 0.9 <= dt < 2.5, f"cut at {dt:.1f}s, expected ~1s"

# a real exchange error still surfaces unchanged (retry logic depends on it)
srv.ex.fetch_ticker = lambda p: (_ for _ in ()).throw(ccxt.NetworkError("boom"))
try:
    srv.fetch_bounded("BTC/USDT", timeout=2)
    raise AssertionError("error should propagate")
except ccxt.NetworkError as e:
    assert "boom" in str(e)

# and NET_ERRORS covers the stall wrapper, so fetch_ticker_retry keeps retrying it
assert issubclass(ccxt.RequestTimeout, srv.NET_ERRORS)
print("pass")
