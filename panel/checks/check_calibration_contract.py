"""Synthetic constant-price fixtures validate measurement, not performance."""
import ast
from pathlib import Path
source = Path(__file__).with_name('check_move_realism.py').read_text()
assert any(isinstance(n, ast.FunctionDef) and n.name == 'measure' for n in ast.parse(source).body), 'calibration lacks testable same-feature measurement'
from check_move_realism import measure
rows = [{'t': i * 30000, 'c': 100 * 1.001**i, 'h': 100 * 1.001**i, 'l': 100 * 1.001**i, 'n': 6} for i in range(100)]
r = measure(rows, 0.32)
assert r['windows'] == 20
assert abs(r['median_ratio'] - ((1.001**20 - 1) * 100 / 2)) < 0.001
assert r['discounted_pass'] <= r['unadjusted_pass']
try:
    measure(rows + [rows[-1]], 0.32)
    raise AssertionError('duplicate timestamp accepted')
except ValueError:
    pass
rows[65]['n'] = 0
assert measure(rows, 0.32)['windows'] == 0, 'outage padding included in calibration'
print('PASS: identical trailing-return feature, clean windows, duplicate rejection')
