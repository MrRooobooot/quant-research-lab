"""Archive + fresh-month OOS test of the validated +111.21% NFI 2.5y run.

1) Copy the original backtest ZIP (2024-02-01→2026-08-01, 120 trades) into
   the research repo with its config; record sha256.
2) Fresh-OOS: backtest the SAME strategy/config on 2026-08-01→2026-09-16 —
   six weeks of data the +111% run never saw.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

LIVE = Path('~/freqtrade')
CLI = '~/freqtrade-venv/bin/freqtrade'
ROOT = Path(__file__).resolve().parent
FT = 'NostalgiaForInfinityX8'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_zip_stats(zpath: Path) -> dict:
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            if n.endswith('.json') and not n.endswith(('_config.json', '.meta.json')):
                data = json.loads(z.read(n))
                if isinstance(data.get('strategy'), dict) and FT in data['strategy']:
                    s = data['strategy'][FT]
                    return {'trades': s['total_trades'], 'profit_pct': round(s['profit_total']*100, 4),
                            'wins': s['wins'], 'losses': s['losses'],
                            'dd_pct': round(s.get('max_drawdown_account', 0)*100, 4),
                            'start': s['backtest_start'], 'end': s['backtest_end']}
    raise RuntimeError('no strategy result in zip')


if len(sys.argv) == 1:
    # Step 1: locate the original zip by exact signature.
    matches = []
    for zpath in (LIVE/'backtest_results').glob('backtest-result-*.zip'):
        try:
            stats = read_zip_stats(zpath)
        except Exception:
            continue
        if (stats['trades'] == 120 and abs(stats['profit_pct'] - 111.21) < 0.05
                and stats['start'].startswith('2024-02-01') and stats['end'].startswith('2026-08-01')):
            matches.append((zpath, stats))
    assert len(matches) == 1, f'expected exactly one +111.21% zip, got {matches}'
    zpath, stats = matches[0]
    (ROOT/'original').mkdir(exist_ok=False)
    shutil.copy2(zpath, ROOT/'original'/'result.zip')
    with zipfile.ZipFile(zpath) as z:
        cfgname = next(n for n in z.namelist() if n.endswith('_config.json'))
        raw = json.loads(z.read(cfgname))
    # redact exchange credentials before writing anywhere
    raw.get('exchange', {}).pop('key', None)
    raw.get('exchange', {}).pop('secret', None)
    raw.get('exchange', {}).pop('password', None)
    (ROOT/'original'/'config.json').write_text(json.dumps(raw, indent=2))
    evidence = {'source_zip': str(zpath), 'source_sha256': sha(zpath),
                'archived_sha256': sha(ROOT/'original'/'result.zip'), 'stats': stats}
    (ROOT/'original'/'evidence.json').write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))
else:
    # Step 2: fresh-month OOS with the same strategy + 10-pair list.
    assert sys.argv[1] == 'oos'
    run = ROOT/'oos-run'
    run.mkdir(exist_ok=False)
    cfg = json.loads((ROOT/'original'/'config.json').read_text())
    pairs = cfg['exchange']['pair_whitelist']
    results = run/'results'
    results.mkdir()
    cmd = [CLI, 'backtesting', '--userdir', str(LIVE), '-c', str(ROOT/'original'/'config.json'),
           '-s', FT, '--timerange', '20260801-20260916', '--cache', 'none', '--export', 'trades',
           '--backtest-directory', str(results), '--no-color']
    env = {k: v for k, v in __import__('os').environ.items() if not k.startswith('FREQTRADE__')}
    log = (run/'run.log').open('w')
    code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=ROOT, timeout=1800).returncode
    log.close()
    archives = list(results.glob('*.zip'))
    assert code == 0 and len(archives) == 1, (code, archives, (run/'run.log').read_text()[-3000:])
    record = {'timerange': '20260801-20260916', 'pairs': pairs, 'command': cmd,
              'archive_sha256': sha(archives[0]), **read_zip_stats(archives[0])}
    (run/'evidence.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))
