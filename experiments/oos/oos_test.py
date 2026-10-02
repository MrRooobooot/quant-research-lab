"""Untouched-period decisive test: fixed rule on 2020-2023 Binance 5m dumps.

One fixed rule (SimpleBot 'rise' variant: +2% over 12 bars, RSI<70, TP6/SL3,
one position, next-open entry, stop-first ties). Strict fee sweep 0.1/0.05/0
per side. Verdict vs buy-and-hold. Fresh 2020-2023 data never used before.
"""
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
CACHE = ROOT/'binance-5m'
CACHE.mkdir(exist_ok=True)
PAIR = 'BTCUSDT'


def month_zip(year: int, month: int) -> bytes | None:
    url = f'https://data.binance.vision/data/spot/monthly/klines/{PAIR}/5m/{PAIR}-5m-{year}-{month:02d}.zip'
    path = CACHE/f'{PAIR}-5m-{year}-{month:02d}.zip'
    if path.exists():
        return path.read_bytes()
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            body = r.read()
    except Exception as error:
        print(f'download_failed {url}: {error}')
        return None
    if not body[:2] == b'PK':
        print(f'not_zip {url}')
        return None
    path.write_bytes(body)
    return body


def load_months() -> pd.DataFrame:
    frames = []
    for year in range(2020, 2024):
        for month in range(1, 13):
            body = month_zip(year, month)
            if body is None:
                continue
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                name = z.namelist()[0]
                raw = pd.read_csv(z.open(name), header=None)
            raw = raw.iloc[:, :6]
            raw.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']
            ts = raw.open_time.astype('int64')
            unit = 'us' if ts.iloc[0] > 10**14 else 'ms'
            raw['date'] = pd.to_datetime(ts, unit=unit, utc=True)
            frames.append(raw[['date', 'open', 'high', 'low', 'close', 'volume']])
    frame = pd.concat(frames, ignore_index=True)
    frame = frame.drop_duplicates('date').sort_values('date').reset_index(drop=True)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        frame[col] = frame[col].astype(float)
    return frame


def rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    up = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    return 100-100/(1+up/dn.replace(0, np.nan))


def run_strategy(df: pd.DataFrame, fee: float) -> dict:
    signal = ((df.close >= df.close.shift(12)*(1+.02)) & (df.rsi < 70) & (df.volume > 0)).to_numpy()
    opens, highs, lows = df.open.to_numpy(), df.high.to_numpy(), df.low.to_numpy()
    cash, equity_curve, trades = 10., [], []
    i, n = 0, len(df)
    while i < n-1:
        open_now = bool(trades) and trades[-1]['exit_i'] is None
        if open_now:
            t = trades[-1]
            sl_price, tp_price = t['entry']*.97, t['entry']*1.06
            low, high, close = lows[i], highs[i], opens[i]*0+df.close.iloc[i]
            units = t['units']
            if low <= sl_price:
                proceeds = units_val = t['units']*sl_price*(1-fee)
                cash += proceeds
                t.update(exit_i=i, exit_price=sl_price, reason='sl')
            elif high >= tp_price:
                cash += t['units']*tp_price*(1-fee)
                t.update(exit_i=i, exit_price=tp_price, reason='tp')
            else:
                equity_curve.append(cash + t['units']*close*(1-fee))
                i += 1
                continue
            equity_curve.append(cash)
            i += 1
            continue
        if signal[i]:
            entry = opens[i+1]
            units = cash*.99*(1-fee)/entry
            cash -= cash*.99
            trades.append({'entry_i': i+1, 'entry': entry, 'units': units, 'exit_i': None})
        equity_curve.append(cash)
        i += 1
    closed = [t for t in trades if t['exit_i'] is not None]
    wins = sum(1 for t in closed if t['exit_price'] > t['entry'])
    curve = np.array(equity_curve)
    dd = float((1-curve/np.maximum.accumulate(curve)).max())*100 if len(curve) else 0.
    bh = 10*(1-fee)*float(df.close.iloc[-1]/df.open.iloc[0])*(1-fee)
    return {'fee_per_side': fee, 'trades': len(closed), 'wins': wins,
            'final_wallet': cash, 'return_pct': (cash/10-1)*100,
            'max_drawdown_pct': dd, 'buyhold_final': bh,
            'buyhold_pct': (bh/10-1)*100, 'open_at_end': any(t['exit_i'] is None for t in trades)}


def main() -> None:
    out = ROOT/'oos_result.json'
    df = load_months()
    print(f'rows={len(df)} {df.date.min()} .. {df.date.max()}')
    assert len(df) > 300000, 'Unexpectedly little data'
    df['rsi'] = rsi(df.close)
    results = [run_strategy(df, fee) for fee in (.001, .0005, 0.0)]
    yearly = []
    for year in range(2020, 2024):
        sub = df.loc[df.date.dt.year == year]
        yearly.append({'year': year, 'strategy_1x_fee_pct': run_strategy(sub.assign(rsi=rsi(sub.close)), .001)['return_pct'],
                       'buyhold_pct': ((sub.close.iloc[-1]/sub.open.iloc[0])-1)*100})
    report = {'pair': PAIR, 'timeframe': '5m', 'window': [str(df.date.min()), str(df.date.max())],
              'rule': 'close >= close[-12]*1.02 and RSI14 < 70; entry next open; TP +6% / SL -3%, stop-first; one position',
              'data_gap_bars': int((df.date.diff().dropna() > pd.Timedelta(minutes=5)).sum()),
              'results': results, 'yearly': yearly,
              'verdict': 'beats_buyhold' if all(r['return_pct'] > r['buyhold_pct'] for r in results[:2]) else 'does_not_beat_buyhold',
              'deployment_approved': False}
    out.write_text(json.dumps(report, indent=2, allow_nan=False))
    assert json.loads(out.read_text()) == report
    for r in results:
        print(json.dumps(r))
    print(json.dumps({'yearly': yearly, 'verdict': report['verdict']}))


if __name__ == '__main__':
    main()
