import os
from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
import argparse

INTERVAL_MAP = {
    '1m': Client.KLINE_INTERVAL_1MINUTE,
    '3m': Client.KLINE_INTERVAL_3MINUTE,
    '5m': Client.KLINE_INTERVAL_5MINUTE,
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '2h': Client.KLINE_INTERVAL_2HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR,
    '6h': Client.KLINE_INTERVAL_6HOUR,
    '8h': Client.KLINE_INTERVAL_8HOUR,
    '12h': Client.KLINE_INTERVAL_12HOUR,
    '1d': Client.KLINE_INTERVAL_1DAY,
    '3d': Client.KLINE_INTERVAL_3DAY,
    '1w': Client.KLINE_INTERVAL_1WEEK,
    '1M': Client.KLINE_INTERVAL_1MONTH
}
symbol = "BTCUSDT"
interval = Client.KLINE_INTERVAL_15MINUTE
candle_interval = "15MIN"
days = 7

def get_binance_candles(symbol: str, interval: str, days: int) -> pd.DataFrame:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    client = Client(api_key, api_secret)

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    klines = client.get_klines(
        symbol=symbol,
        interval=interval,
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000)
    )

    if not klines:
            raise ValueError("No data returned from Binance API. Please check the parameters.")

    df = pd.DataFrame(klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_volume", "taker_buy_quote_volume", "ignore"
    ])

    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    df["timestamp"] = pd.to_datetime(df["open_time"], unit='ms')
    df = df.set_index("timestamp")

    return df

def save_candles(df: pd.DataFrame, symbol: str, interval: str, days: int):
    begTime = df.index[0]
    endTime = df.index[-1]
    
    begTime_str = begTime.strftime('%d-%m-%Y_%H-%M-%S')
    endTime_str = endTime.strftime('%d-%m-%Y_%H-%M-%S')
    
    dir = Path("data") / symbol
    dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{interval}_{days}D_{begTime_str}___{endTime_str}.parquet"
    filepath = dir / filename
    
    df.to_parquet(filepath, compression='snappy')
    
    return filepath

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('symbol', type=str, help="The trading pair symbol (e.g., 'BTCUSDT')")
    parser.add_argument('interval', type=str, help="The interval for the candlesticks (e.g., '1m', '1h', '1d')")
    parser.add_argument('days', type=int, help="The number of days of data to fetch")

    args = parser.parse_args()

    interval_str = args.interval

    if interval_str not in INTERVAL_MAP:
        raise ValueError(f"Invalid interval '{interval_str}'. Supported intervals: {', '.join(INTERVAL_MAP.keys())}")
    
    interval = INTERVAL_MAP[interval_str]

    try:
        df = get_binance_candles(args.symbol, interval, args.days)
        save_candles(df, args.symbol, interval_str, args.days)
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()