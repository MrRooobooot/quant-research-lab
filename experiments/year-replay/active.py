"""Execute the installed sample unchanged; measure activity, not promise profit."""
import io
import json
import os
import subprocess
import zipfile
import pandas as pd
from replay import ROOT, LIVE

source = LIVE/'strategies/sample_strategy.py'
(ROOT/'strategies/sample_strategy.py').write_bytes(source.read_bytes())
rows = []
for name, fee in [('active_fee', .001), ('active_zero_fee', 0.0)]:
    folder = ROOT/name
    folder.mkdir(exist_ok=True)
    (folder/'results').mkdir(exist_ok=True)
    config = json.loads((ROOT/'config.json').read_text())
    config.pop('grinding_enable', None)
    config.update(ignore_roi_if_entry_signal=False, fee=fee)
    (folder/'config.json').write_text(json.dumps(config, indent=2))
    cmd = json.loads((ROOT/'detail_two/command.json').read_text())
    for option, value in [('-c',str(folder/'config.json')),('-s','SampleStrategy'),('--fee',str(fee)),('--backtest-directory',str(folder/'results'))]:
        cmd[cmd.index(option)+1] = value
    (folder/'command.json').write_text(json.dumps(cmd, indent=2))
    if not list((folder/'results').glob('*.zip')):
        with (folder/'run.log').open('w') as log:
            result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env={k:v for k,v in os.environ.items() if not k.startswith('FREQTRADE__')}, timeout=600)
        assert result.returncode == 0, f'Inspect {folder}/run.log'
    log_text = (folder/'run.log').read_text()
    assert ' - ERROR - ' not in log_text and 'Traceback (most recent call last)' not in log_text
    archives = list((folder/'results').glob('*.zip'))
    assert len(archives) == 1
    with zipfile.ZipFile(archives[0]) as archive:
        stats = next(o for n in archive.namelist() if n.endswith('.json') and not n.endswith(('_config.json','.meta.json')) and isinstance((o:=json.loads(archive.read(n))).get('strategy'),dict))['strategy']['SampleStrategy']
        wallet = pd.read_feather(io.BytesIO(archive.read(next(n for n in archive.namelist() if n.endswith('_wallet.feather')))))
    trades = stats['trades']
    assert len(trades) == stats['total_trades'] and stats['starting_balance'] == 100
    assert abs(sum(t['profit_abs'] for t in trades)-stats['profit_total_abs']) < 1e-6
    assert all(t['fee_open'] == t['fee_close'] == fee for t in trades)
    equity = wallet.groupby('date').total_quote.sum().sort_index()
    daily = equity.resample('D').last()
    assert len(daily) == 365 and daily.notna().all()
    final_cash = float(stats['final_balance'])
    snapshot = float(daily.iloc[-1])
    print(json.dumps({'case': name, 'last_wallet_snapshot': snapshot,
                      'starting_capital': stats['starting_balance'],
                      'profit_total_abs': stats['profit_total_abs'],
                      'final_cash_after_exits': final_cash,
                      'snapshot_minus_final_cash': snapshot-final_cash}), flush=True)
    assert abs(final_cash-stats['starting_balance']-stats['profit_total_abs']) < 1e-5
    if abs(snapshot-final_cash) >= 1e-5:
        assert any(t['exit_reason']=='force_exit' for t in trades), 'Unexplained wallet mismatch'
    # The engine snapshots holdings before its final forced liquidation.
    daily.iloc[-1] = final_cash
    daily.rename('equity_usdt').to_csv(folder/'daily.csv')
    pd.DataFrame(trades).drop(columns=['orders'],errors='ignore').to_csv(folder/'trades.csv',index=False)
    record = {'case':name,'trades':len(trades),'trades_per_day':len(trades)/365,'active_entry_days':len({t['open_date'][:10] for t in trades}),'profit_usdt':stats['profit_total_abs'],'final_equity':100+stats['profit_total_abs'],'snapshot_drawdown_pct':float(((equity.cummax().clip(lower=100)-equity)/equity.cummax().clip(lower=100)).max()*100),'start':stats['backtest_start'],'end':stats['backtest_end'],'approved':False}
    (folder/'evidence.json').write_text(json.dumps(record,indent=2))
    rows.append(record)
    (ROOT/'active_comparison.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(record),flush=True)
assert len(rows) == 2
print('PASS: both annual runs; wallet, fees, trade sums, 365 daily records')
