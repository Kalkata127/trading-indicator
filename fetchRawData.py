import os
from binance.client import Client
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import argparse

INTERVAL_MAP = {
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '2h': Client.KLINE_INTERVAL_2HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR,
    '1d': Client.KLINE_INTERVAL_1DAY,
}

def get_binance_candles_fixed(symbol: str, interval: str, start_str: str, end_str: str) -> pd.DataFrame:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    client = Client(api_key, api_secret)

    #Parse data format DD-MM-YYYY:HH:mm to objects with time zone UTC
    dt_start = datetime.strptime(start_str, '%d-%m-%Y:%H:%M').replace(tzinfo=timezone.utc)
    dt_end = datetime.strptime(end_str, '%d-%m-%Y:%H:%M').replace(tzinfo=timezone.utc)

    klines = client.get_klines(
        symbol=symbol,
        interval=interval,
        startTime=int(dt_start.timestamp() * 1000),
        endTime=int(dt_end.timestamp() * 1000)
    )

    if not klines:
        raise ValueError("Binance API doesn't return data for this period.")

    # Orginal colums
    df = pd.DataFrame(klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_volume", "taker_buy_quote_volume", "ignore"
    ])

    # Data type conversion
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df["timestamp"] = pd.to_datetime(df["open_time"], unit='ms')
    df = df.set_index("timestamp")

    return df

def save_candles(df: pd.DataFrame, symbol: str, interval: str):
    begTime_str = df.index[0].strftime('%d-%m-%Y_%H-%M-%S')
    endTime_str = df.index[-1].strftime('%d-%m-%Y_%H-%M-%S')
    
    dir = Path("data") / symbol
    dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{interval}_FIXED_{begTime_str}___{endTime_str}.parquet"
    filepath = dir / filename
    
    df.to_parquet(filepath, compression='snappy')
    print(f"File saved in: {filepath}")
    return filepath

def main():
    parser = argparse.ArgumentParser(description="Fetch historical Binance candles for a fixed period.")
    parser.add_argument('symbol', type=str, help="Trading pair (e.g., 'BTCUSDT')")
    parser.add_argument('interval', type=str, help="Interval (e.g., '15m', '1h')")
    parser.add_argument('start_time', type=str, help="Start time in format 'DD-MM-YYYY:HH:MM'")
    parser.add_argument('end_time', type=str, help="End time in format 'DD-MM-YYYY:HH:MM'")

    args = parser.parse_args()

    if args.interval not in INTERVAL_MAP:
        raise ValueError(f"Invalid interval. Supported: {', '.join(INTERVAL_MAP.keys())}")
    
    interval = INTERVAL_MAP[args.interval]

    try:
        df = get_binance_candles_fixed(args.symbol, interval, args.start_time, args.end_time)
        save_candles(df, args.symbol, args.interval)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()