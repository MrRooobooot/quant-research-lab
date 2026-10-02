"""Isolated watchdog policy fixtures, not market evidence."""
import importlib.util
import sys
from pathlib import Path

path = Path(__file__).with_name('health_watch.py')
assert path.exists(), 'deterministic watchdog not implemented'
spec = importlib.util.spec_from_file_location('health_watch', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
assert m.restart_allowed(None, 2000, 0, 0)
assert not m.restart_allowed(None, 2000, 1900, 0), 'restart storm'
assert not m.restart_allowed(None, 2000, 0, 3), 'daily retry cap'
assert not m.restart_allowed({'last_tick_ms': 1}, 2000, 0, 0), 'stale network is not a crashed process'
assert m.panel_health({'last_tick_ms': 1999000, 'status': 'running'}, 2000) == 'ok'
assert m.panel_health({'last_tick_ms': 1000, 'status': 'running'}, 2000) == 'stale_feed'
assert m.panel_health(None, 2000) == 'unreachable'
print('PASS: watchdog only restarts unreachable panel, bounded retries')
