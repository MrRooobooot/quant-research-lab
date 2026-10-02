"""Bounded operations watchdog; never edits strategy or training files."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path('~/freqtrade')
STATE_FILE = ROOT / 'logs/health-watch-state.json'
REPORT = ROOT / 'logs/health-watch-report.json'
SERVICES = {
    'small': 'small-live.log', 'nfipaper': 'nfi-paper-live.log',
    'simplefut': 'simple-fut-live.log',
}


def panel_health(snapshot, now):
    if snapshot is None:
        return 'unreachable'
    if now - snapshot.get('last_tick_ms', 0) / 1000 > 120:
        return 'stale_feed'
    return 'ok'


def restart_allowed(snapshot, now, last_restart, attempts):
    return snapshot is None and now - last_restart >= 1800 and attempts < 3


def atomic_json(path, data):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as file:
        json.dump(data, file, indent=2, allow_nan=False)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def get_panel():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8123/api/state', timeout=8) as response:
            data = json.load(response)
        return data if isinstance(data, dict) and isinstance(data.get('last_tick_ms'), (int, float)) else None
    except (OSError, ValueError):
        return None


def recent_log_status(path, now):
    if not path.exists():
        return {'health': 'missing_log'}
    with path.open('rb') as file:
        file.seek(max(0, path.stat().st_size - 128000))
        lines = file.read().decode(errors='replace').splitlines()
    recent = []
    for line in lines:
        try:
            stamp = datetime.datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S').timestamp()
        except ValueError:
            continue
        if 0 <= now - stamp <= 600:
            recent.append(line)
    warnings = sum('WARNING' in line or 'ERROR' in line for line in recent)
    stale = sum('Outdated history' in line for line in recent)
    heartbeat = any('heartbeat' in line for line in recent)
    return {'health': 'stale_feed' if stale else ('warnings' if warnings else ('heartbeat_only' if heartbeat else 'no_recent_heartbeat')),
            'warnings_last_10m': warnings, 'stale_last_10m': stale,
            'note': 'heartbeat does not verify fresh candles; report-only, no strategy edits'}


def main():
    repair = '--repair' in sys.argv
    STATE_FILE.parent.mkdir(exist_ok=True)
    with STATE_FILE.with_suffix('.lock').open('a') as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('watchdog already running')
            return
        now = time.time()
        day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        state = {'day': day, 'attempts': 0, 'last_restart': 0}
        if STATE_FILE.exists():
            try:
                state = json.loads(STATE_FILE.read_text())
                assert isinstance(state, dict) and isinstance(state['attempts'], int)
                assert isinstance(state['last_restart'], (int, float))
            except (ValueError, KeyError, AssertionError):
                print('ERROR: corrupt watchdog state; repair refused')
                return
        if state.get('day') != day:
            state.update(day=day, attempts=0)
        snapshot = get_panel()
        report = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'panel': panel_health(snapshot, now), 'action': 'none',
                  'bots': {name: recent_log_status(ROOT / 'logs' / log, now) for name, log in SERVICES.items()}}
        if snapshot:
            report['panel_stats'] = snapshot.get('stats')
        if repair and restart_allowed(snapshot, now, state['last_restart'], state['attempts']):
            # Retry once to avoid restarting after a transient HTTP timeout.
            if get_panel() is None:
                state.update(last_restart=now, attempts=state['attempts'] + 1)
                atomic_json(STATE_FILE, state)  # reserve attempt before external action
                result = subprocess.run(['/bin/launchctl', 'kickstart', '-k', f'gui/{os.getuid()}/com.aidin.trade.panel'],
                                        capture_output=True, text=True, timeout=20)
                report['action'] = 'restart_requested' if result.returncode == 0 else 'restart_failed'
                report['restart_exit_code'] = result.returncode
                report['note'] = 'next scheduled probe verifies recovery; success not assumed'
        atomic_json(STATE_FILE, state)
        atomic_json(REPORT, report)
        print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
