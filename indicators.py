import pandas as pd

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()