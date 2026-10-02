"""Monitor the live gate's trailing-close-return proxy; never auto-tune it.

Uses completed polled 30s bars. The live tick may be incomplete, so this is a
closed-bar diagnostic, not an exact tick replay or a profitability test.
"""
import json
import math
from pathlib import Path
import re
import statistics
import sys


def measure(rows, realism, tp=0.8):
    if not 0 < realism <= 1:
        raise ValueError('discount must be finite in (0,1]')
    for i, row in enumerate(rows):
        if not all(isinstance(row.get(k), (int, float)) and math.isfinite(row[k]) and row[k] > 0 for k in ('c', 'h')):
            raise ValueError('invalid price')
        if i and row['t'] <= rows[i-1]['t']:
            raise ValueError('timestamps must be strictly increasing')
    ratios, old_pass, new_pass, removed_winners = [], 0, 0, 0
    for i in range(60, len(rows)-20):
        span = rows[i-60:i+21]
        if any(r.get('n', 0) <= 0 for r in span):
            continue
        if any(b['t']-a['t'] != 30000 for a,b in zip(span,span[1:])):
            continue
        closes = [r['c'] for r in rows[i-60:i+1]]
        # Identical feature to server.market_snapshot: mean absolute last 60 close returns.
        vol = round(statistics.mean(abs(b/a-1)*100 for a,b in zip(closes,closes[1:])), 4)
        predicted = vol * 20
        if predicted <= 0:
            continue
        achieved = max(0, (max(r['h'] for r in rows[i+1:i+21])/closes[-1]-1)*100)
        ratios.append(achieved/predicted)
        before, after = predicted >= tp, predicted * realism >= tp
        old_pass += before
        new_pass += after
        removed_winners += before and not after and achieved >= tp
    measured = statistics.median(ratios) if ratios else None
    return {'windows': len(ratios), 'median_ratio': measured, 'configured_discount': realism,
            'unadjusted_pass': old_pass, 'discounted_pass': new_pass,
            'removed_windows_reaching_tp': removed_winners,
            'calibration_status': 'insufficient_data' if len(ratios) < 100 else ('drift' if abs(measured-realism)>0.10 else 'within_tolerance'),
            'note': 'overlapping diagnostic windows, not independent trades; no automatic parameter changes'}


def main():
    root = Path(__file__).parent
    source = (root/'server.py').read_text()
    match = re.search(r'^MOVE_REALISM\s*=\s*([0-9.]+)', source, re.M)
    assert match, 'missing discount'
    path = Path(sys.argv[1]) if len(sys.argv)>1 else root/'bars.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    result = measure(rows, float(match.group(1)))
    print(json.dumps(result, indent=2))
    assert result['discounted_pass'] <= result['unadjusted_pass'], 'discount widened gate'
    # Losing some eventual winners is normal for a filter; do not assert zero missed winners.
    if result['calibration_status'] != 'within_tolerance':
        print('MONITOR WARNING: calibration requires review; not a passing calibration result')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
