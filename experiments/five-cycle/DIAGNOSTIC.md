# Five chronological learning cycles — research result

Run: `run-20260918-000241`; exact five cycles counted from cycles.jsonl.

- Existing corrected dataset: 2,803,660 rows, ten pairs, 5m bars.
- Expanding training: 466,700 to 2,335,841 rows; full label-horizon purge.
- Each cycle compares price-only features against price+volume/context using inner chronological validation. Outer test never selects thresholds.
- Five fitted LightGBM models saved as research-only artifacts; none activated.
- At the predeclared 0.50/0.55/0.60/0.65 take-profit probability thresholds, every cycle selected ZERO entries in validation and test. Thus no candidate qualified. Zero trades is neither profit nor proof that no possible strategy works. This threshold family is too selective for these fitted probabilities; changing it after seeing tests would be a new exploratory experiment, not successful validation.
- Returns of all hypothetical entries average about -0.24% to -0.26% net per selection, including assumed spot fees/slippage. These overlap and are NOT portfolio return.

## Independent classification diagnostic (not profit)

Existing BTC 5m source only. Train ends 2026-08-24 18:55 UTC; final training label ends 23:55; test begins 2026-08-25 00:00 and ends 2026-08-31 18:55. Train 278,363 rows, test 1,956.

| Model | Train accuracy | Test accuracy | Test macro-F1 |
|---|---:|---:|---:|
| Majority baseline | 0.54927 | 0.48057 | 0.21639 |
| Default LightGBM | 0.59354 | 0.61708 | 0.44490 |

Model learns some distinctions better than majority baseline in this one retrospective period. Test predictions: 1,604 stop labels; 352 timeout labels; zero take-profit labels. Accuracy improvement does not establish a profitable BUY signal or a viable short strategy. No short model was tested.

## Why no entries: inner-validation diagnostic

Cycle-1 training/validation only, no new outer-test tuning: price-only predicted TP probabilities ranged 0.160–0.420; price+volume/context 0.139–0.445. Therefore thresholds ≥0.50 could never select these validation entries. Exploring lower thresholds on that same inner validation did not yield an eligible profitable candidate: price-only 0.35 selected 425 with mean net −0.19397%; 0.40 selected only 13 (below the predeclared 100 minimum). Context 0.35 selected 2,771 with mean net −0.27243%; 0.40 selected 64 with mean net −0.23298%. Zero-entry results do not prove no edge universally; these measured alternatives also failed the current acceptance criteria. No live threshold was changed.

## Deployment gate

No new model may be activated from these proxy scores. Require execution-aware portfolio simulation on the actual venue, minimum-size checks on the intended wallet, drawdown/cost stress tests, and future paper evidence. Leverage does not create predictive edge. Existing live configs and sidecars were not changed by these cycles. Gate futures baseline execution tests are a separate evidence stream.
