import os
import time
import pandas as pd
from binance.client import Client
from datetime import datetime, timezone

INTERVAL_MAP = {
    '5m': Client.KLINE_INTERVAL_5MINUTE,
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
}

def get_binance_candles_period(symbol: str, interval: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    client = Client(api_key, api_secret)

    if interval not in INTERVAL_MAP:
        raise ValueError(f"Unsupported interval: {interval}. Only: {list(INTERVAL_MAP.keys())}")

    binance_interval = INTERVAL_MAP[interval]
    all_klines = []
    
    # Convert to miliseconds for Binance API
    current_start = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)

    print(f"[*] Fetching {symbol} ({interval}) from {start_dt}...")

    while current_start < end_ts:
        klines = client.get_klines(
            symbol=symbol,
            interval=binance_interval,
            startTime=current_start,
            endTime=end_ts,
            limit=1000
        )
        
        if not klines:
            break
            
        all_klines.extend(klines)
        
        # Next starts is time of last candle close + 1ms
        current_start = klines[-1][6] + 1
        
        # Pause for Rate Limit
        if len(klines) == 1000:
            time.sleep(0.1)

    if not all_klines:
        return pd.DataFrame()

    df = pd.DataFrame(all_klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_volume", "taker_buy_quote_volume", "ignore"
    ])

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df["timestamp"] = pd.to_datetime(df["open_time"], unit='ms', utc=True)
    df = df.set_index("timestamp")
    # Removing overlaps
    return df[~df.index.duplicated(keep='last')]