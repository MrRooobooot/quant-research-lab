# ML experiment log — LightGBM walk-forward on 2.8M samples

Setup: 10 pairs x 2.5y of 5m data (2,804,260 samples), features = the panel's own indicators
(gap_pct, gap_slope, RSI, bar_vol, returns, vol_z, distance from 60-bar high/low, hour).
Label = triple-barrier: +1 if +0.8% hit before −0.4% within 60 bars (5h), −1 if opposite,
0 if neither. Class balance: −1: 1.69M, +1: 873k, 0: 246k.

Method: 5 time-ordered folds (train on past, test on the next chunk; the future never leaks
into training). Fee-aware scoring: every hypothetical trade pays the 0.2% round trip.

## Final results (all thresholds, all folds)

| P(+1) threshold | trades | total net % | verdict |
|---|---|---|---|
| 0.50 | 22,739 | −2,260% | worse than random |
| 0.55 | 9,769 | −620% | negative |
| 0.60 | 4,256 | −129% | negative |

Probability separation between label=+1 rows and the rest: ~0.01–0.02 — near zero.
Fold-level noise (one fold +34%, next −197%) is exactly what no-signal looks like at
this sample size.

## Interpretation (this is the important finding)

Two independent measurement campaigns now agree:
1. Grid-searched SMA gates on 1y of 1m data: all 81 configs negative.
2. LightGBM (far more expressive) on 2.8M samples x 5m horizon: no usable separation either.

Within THESE features and horizons, the accessible retail price data does not contain a
learnable short-horizon edge that survives 0.2% fees. That is a result, not a failure of
effort: it kills the fantasy that "more ML on the same bars" fixes the 30s scalper.

## What this means for the roadmap

- Step 1 verdict: LightGBM gate on the 30s/5m SMA strategy — **REJECTED by walk-forward
  evidence**. Do not wire it into the panel; it would only cut trade count, not improve
  expectancy.
- Step 2 (FreqAI) redirected to where measured edge lives: the +111%/30mo NFI profile —
  daily-scale hold-and-heal. ML there should be regime classification (when to enable /
  throttle the strategy), not minute-level entry prediction.
- Step 3 (RL) stays parked. Fee wall unchanged: 0.2% vs 0.024% median 1m move.

## The honest conclusion about "realtime training on past data"

We built it (build_dataset.py, pretrain.py, train.py, the retrain loop) and it works
mechanically. But training harder on data that contains no edge produces confident losses,
not profit. The next real upgrades are: (a) longer-horizon strategies where fee pressure is
small (the NFI lane), (b) features not derived from the same price series (order-book depth,
funding rates, cross-exchange flows), (c) regime detection wrapped around the proven engine.
