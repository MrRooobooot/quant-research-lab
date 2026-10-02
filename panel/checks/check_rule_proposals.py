"""Regression: loss proposals must not mutate deployed rules (isolated)."""
import tempfile
from pathlib import Path
import server

with tempfile.TemporaryDirectory() as directory:
    server.RULES_FILE = str(Path(directory) / 'rules.json')
    server.RULES.update(server.PRETRAIN_FLOOR)
    original = dict(server.RULES)
    for _ in range(3):
        lesson = {'fixes': [{'param': 'min_gap_pct', 'value': 0.05, 'why': 'test fixture'}]}
        applied = server.apply_fixes(lesson)
        assert applied == [], 'unvalidated loss proposal applied'
        assert server.RULES == original, 'loss ratchet changed live rules'
        assert lesson['promotion']['approved'] is False
    assert not Path(server.RULES_FILE).exists(), 'proposal overwrote rules file'
print('PASS: proposals recorded, live rules unchanged')
