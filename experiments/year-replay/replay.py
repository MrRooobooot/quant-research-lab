"""Continuous 365-day paper backtest; never modifies live data/config."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parent
LIVE = Path('~/freqtrade')
CLI = '~/freqtrade-venv/bin/freqtrade'
START = pd.Timestamp('2025-09-01', tz='UTC')
END = pd.Timestamp('2026-09-01', tz='UTC')
PAIRS = ['BTC/USDT', 'SOL/USDT']

def validate(frame, minutes):
    dates = frame.date
    assert dates.min() >= pd.Timestamp('2010-01-01', tz='UTC'), 'bad start'
    assert dates.max() < pd.Timestamp('2026-09-19', tz='UTC'), 'bad timestamp unit'
    assert dates.is_monotonic_increasing and dates.is_unique
    part = frame[(dates >= START) & (dates < END)]
    expected = pd.date_range(START, END, freq=f'{minutes}min', inclusive='left')
    assert len(part) == len(expected) and (part.date.array == expected.array).all(), 'incomplete year'
    assert part[['open','high','low','close','volume']].notna().all().all()
    assert (part[['open','high','low','close']] > 0).all().all()
    assert (part.high >= part[['open','close','low']].max(axis=1)).all()
    assert (part.low <= part[['open','close','high']].min(axis=1)).all()
    assert (part.volume >= 0).all()
    return part

def prepare():
    for name in ['data', 'strategies', 'user_data']:
        (ROOT/name).mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT.parent/'nfi-oos/original/result.zip') as archive:
        source = archive.read(next(n for n in archive.namelist() if n.endswith('_NostalgiaForInfinityX8.py')))
    assert source == (LIVE/'strategies/NostalgiaForInfinityX8.py').read_bytes()
    (ROOT/'strategies/NostalgiaForInfinityX8.py').write_bytes(source)
    config = json.loads((ROOT.parent/'nfi-oos/original/config.json').read_text())
    config['exchange'] = {'name':'kucoin', 'pair_whitelist': PAIRS, 'pair_blacklist': []}
    for key in ['config_files','api_server','telegram','db_url']:
        config.pop(key,None)
    config.update(dry_run=True, dry_run_wallet=100, max_open_trades=2, fee=.001)
    manifest=[]
    holds=[]
    for pair in PAIRS:
        for tf,minutes in [('5m',5),('15m',15),('1h',60),('4h',240),('1d',1440)]:
            source = LIVE/'data/binance'/f'{pair.replace("/","_")}-{tf}.feather'
            frame = pd.read_feather(source)
            part = validate(frame, minutes)
            assert frame.date.min() <= pd.Timestamp('2024-02-01',tz='UTC'), 'insufficient warmup'
            dest = ROOT/'data'/source.name
            if not dest.exists():
                frame.to_feather(dest)
            assert dest.read_bytes() == source.read_bytes(), 'snapshot differs'
            manifest.append({'file':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'year_bars':len(part),'start':str(frame.date.min()),'end':str(frame.date.max())})
            if tf=='5m':
                # Same start/end clock as native engine forced exit; fees on both sides.
                exit_price = float(frame.loc[frame.date == END, 'open'].iloc[0]) if (frame.date==END).any() else float(part.close.iloc[-1])
                holds.append({'pair':pair,'return_ratio':exit_price/float(part.open.iloc[0])*(1-.001)/(1+.001)-1})
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (ROOT/'buy_hold.json').write_text(json.dumps({'wallet':100,'pair_returns':holds,'final_equity':100*(1+sum(h['return_ratio'] for h in holds)/len(holds))},indent=2))
    (ROOT/'config.json').write_text(json.dumps(config,indent=2))
    print('PASS: 10 data files; full year and warmup validated',flush=True)
    return config

def run(name, slots, timerange, detail=False):
    folder = ROOT/name
    folder.mkdir(exist_ok=False)
    (folder/'results').mkdir()
    config = json.loads((ROOT/'config.json').read_text())
    config['max_open_trades']=slots
    (folder/'config.json').write_text(json.dumps(config,indent=2))
    cmd=[CLI,'backtesting','--userdir',str(ROOT/'user_data'),'-c',str(folder/'config.json'),'-s','NostalgiaForInfinityX8','--strategy-path',str(ROOT/'strategies'),'--datadir',str(ROOT/'data'),'--timerange',timerange,'--cache','none','--fee','0.001','--breakdown','day','month','--backtest-directory',str(folder/'results'),'--export','trades','--no-color']
    if detail:
        cmd += ['--timeframe-detail','1m']
    (folder/'command.json').write_text(json.dumps(cmd,indent=2))
    print('RUN',name,flush=True)
    with (folder/'run.log').open('w') as log:
        proc=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={k:v for k,v in os.environ.items() if not k.startswith('FREQTRADE__')},timeout=1200)
    assert proc.returncode==0, f'{name} failed: see run.log'
    logs=(folder/'run.log').read_text()
    assert 'Traceback (most recent call last)' not in logs and ' - ERROR - ' not in logs, 'strategy runtime errors'
    archives=list((folder/'results').glob('*.zip')); assert len(archives)==1
    with zipfile.ZipFile(archives[0]) as z:
        stats=next(o for n in z.namelist() if n.endswith('.json') and not n.endswith(('_config.json','.meta.json')) and isinstance((o:=json.loads(z.read(n))).get('strategy'),dict))['strategy']['NostalgiaForInfinityX8']
        wallet=pd.read_feather(io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith('_wallet.feather')))))
    trades=stats['trades']
    assert stats['starting_balance']==100 and len(trades)==stats['total_trades']
    assert abs(sum(t['profit_abs'] for t in trades)-stats['profit_total_abs'])<1e-7
    assert all(t['fee_open']==t['fee_close']==.001 for t in trades)
    equity=wallet.groupby('date').total_quote.sum().sort_index()
    begin=pd.Timestamp(stats['backtest_start'],tz='UTC');end=pd.Timestamp(stats['backtest_end'],tz='UTC')
    assert begin==START, 'engine shortened start'
    days=pd.date_range(begin,end,freq='D',inclusive='left')
    daily=equity[equity.index<end].resample('D').last().reindex(days).ffill()
    daily.iloc[-1]=float(equity.iloc[-1])
    assert daily.notna().all() and abs(daily.iloc[-1]-(100+stats['profit_total_abs']))<1e-5
    changes=daily.diff();changes.iloc[0]=daily.iloc[0]-100
    pd.DataFrame({'equity_usdt':daily,'daily_pnl_usdt':changes}).to_csv(folder/'daily.csv',index_label='date')
    peak=equity.cummax().clip(lower=100)
    drawdown=float(((peak-equity)/peak).max())
    rec={'case':name,'days':len(days),'slots':slots,'trades':len(trades),'profit_usdt':stats['profit_total_abs'],'final_equity':100+stats['profit_total_abs'],'wallet_drawdown_pct':drawdown*100,'forced_exits':sum(t['exit_reason']=='force_exit' for t in trades),'start':str(begin),'end':str(end),'archive_sha256':hashlib.sha256(archives[0].read_bytes()).hexdigest(),'approved':False}
    (folder/'evidence.json').write_text(json.dumps(rec,indent=2))
    print(json.dumps(rec),flush=True)
    return rec

if __name__=='__main__':
    prepare()
    run(sys.argv[1] if len(sys.argv)>1 else 'baseline',2,'20250901-20260901')
