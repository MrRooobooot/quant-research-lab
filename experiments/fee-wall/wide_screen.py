"""Wide-universe family screen: 37 pairs, annual window, fee + zero-fee.

Reuses replay verification pattern. One run per family per fee level, all pairs
in one backtest. Pairs with incomplete coverage excluded by fetch report.
"""
import json
import os
import subprocess
import zipfile
from pathlib import Path
import io
import pandas as pd

ROOT = Path(__file__).resolve().parent
UNIVERSE = ROOT/'universe.json'
FAMILIES = [('Demo', 'none'), ('Scalp', 'none'), ('Trend', 'none'), ('SampleStrategy', '1m'), ('Strategy001', '1m')]

def universe():
    report = json.loads((ROOT/'download_report.json').read_text())
    pairs = [f'{p[:-4]}/USDT' for p, v in report.items()
             if not v['missing_months'] and v['rows'] >= 520_000]
    UNIVERSE.write_text(json.dumps(pairs, indent=2))
    return pairs

def run(family, fee, detail):
    label = f'wide_{family.lower()}_fee{fee}'
    folder = ROOT/label
    folder.mkdir(exist_ok=True)
    (folder/'results').mkdir(exist_ok=True)
    zips = list((folder/'results').glob('*.zip'))
    if zips:
        with zipfile.ZipFile(zips[0]) as z:
            stats = next(p['strategy'][family] for n in z.namelist()
                         if n.endswith('.json') and not n.endswith(('_config.json', '.meta.json'))
                         and isinstance((p := json.loads(z.read(n))).get('strategy'), dict))
        return stats, folder
    config = json.loads((ROOT.parent/'year-replay/config.json').read_text())
    config.pop('grinding_enable', None)
    config.update(dry_run=True, dry_run_wallet=100, fee=fee, max_open_trades=2,
                  exchange={'name': 'binance', 'pair_whitelist': json.loads(UNIVERSE.read_text()), 'pair_blacklist': []})
    (folder/'config.json').write_text(json.dumps(config, indent=2))
    cmd = ['~/freqtrade-venv/bin/freqtrade', 'backtesting',
           '--userdir', str(ROOT/'user_data'), '-c', str(folder/'config.json'), '-s', family,
           '--strategy-path', str(ROOT.parent/'year-replay/strategies'),
           '--datadir', str(ROOT/'data/binance'),
           '--timerange', '20250901-20260901', '--cache', 'none', '--fee', str(fee),
           '--export', 'trades', '--backtest-directory', str(folder/'results'), '--no-color']
    if detail != 'none':
        cmd += ['--timeframe-detail', detail]
    (folder/'command.json').write_text(json.dumps(cmd, indent=2))
    with (folder/'run.log').open('w') as log:
        result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                env={k: v for k, v in os.environ.items() if not k.startswith('FREQTRADE__')},
                                timeout=7200)
    assert result.returncode == 0, f'{label} failed, see run.log'
    zips = list((folder/'results').glob('*.zip'))
    assert len(zips) == 1
    with zipfile.ZipFile(zips[0]) as z:
        stats = next(p['strategy'][family] for n in z.namelist()
                     if n.endswith('.json') and not n.endswith(('_config.json', '.meta.json'))
                     and isinstance((p := json.loads(z.read(n))).get('strategy'), dict))
    return stats, folder

def main():
    pairs = universe()
    print('universe', len(pairs), flush=True)
    ledger_path = ROOT/'wide_ledger.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    for family, detail in FAMILIES:
        if family in ledger and 'fee' in ledger[family]:
            continue
        print('FAMILY', family, flush=True)
        stats, folder = run(family, .001, detail)
        entry = {'trades': stats['total_trades'], 'final_usdt': stats['final_balance'],
                 'profit_usdt': stats['profit_total_abs']}
        assert abs(stats['final_balance']-100-stats['profit_total_abs']) < 1e-6
        trades = stats['trades']
        assert all(t['fee_open'] == t['fee_close'] == .001 for t in trades)
        ledger[family] = {'fee': entry}
        ledger_path.write_text(json.dumps(ledger, indent=2))
        print(json.dumps({'family': family, **entry}), flush=True)
        if entry['profit_usdt'] > 0 and entry['trades'] >= 100:
            print('FEE_POSITIVE', family, '- running zero-fee twin', flush=True)
            zero, _ = run(family, 0.0, detail)
            ledger[family]['zero_fee'] = {'trades': zero['total_trades'], 'final_usdt': zero['final_balance']}
            ledger_path.write_text(json.dumps(ledger, indent=2))
            print(json.dumps({'family': family, 'zero_fee_final': zero['final_balance']}), flush=True)
    print('WIDE_SCREEN_COMPLETE', flush=True)

if __name__ == '__main__':
    main()
