"""Runnable data-boundary checks; synthetic candles are tests only."""
import pandas as pd
from replay import START, END, validate

frame = pd.DataFrame({'date':pd.date_range(START,END,freq='1D',inclusive='left'),'open':1.,'high':2.,'low':.5,'close':1.,'volume':1.})
assert len(validate(frame,1440)) == 365
for invalid in [frame.iloc[:-1],pd.concat([frame,frame.iloc[-1:]]),frame.assign(high=.1),frame.assign(volume=-1)]:
    try:
        validate(invalid,1440)
    except AssertionError:
        pass
    else:
        raise AssertionError('Invalid candles accepted')
raw=1756684800000000
assert pd.to_datetime(raw,unit='us',utc=True)==START
print('PASS: full-year acceptance; missing, duplicate, invalid OHLCV rejection; timestamp unit')
