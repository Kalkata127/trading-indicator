import os
import pandas as pd
import argparse
from datetime import datetime

def get_interval(df):
    if df.empty:
        return None
    
    open_t = df["open_time"].iloc[0]
    close_t = df["close_time"].iloc[0]

    #timestamp is in miliseconds
    diff_seconds = (close_t - open_t) / 1000 
    diff_minutes = diff_seconds / 60
    print(round(diff_minutes))
    return round(diff_minutes)


def aggregate_candles(input_file, output_dir="data/"):
    if not os.path.exists(input_file):
        print(f"[Error] File '{input_file}' not found!")
        return

    try:
        df = pd.read_parquet(input_file)
    except Exception as e:
        print(f"[Error] Failed reading file: {e}")
        return

    if df.empty:
        print(f"[Warning] File '{input_file}' is empty.")
        return

    interval = get_interval(df)
    if interval not in [15.0, 30.0]:
        print(f"[Отказ] Интервалът е {interval} мин. Поддържат се само 15м или 30м.")
        return

    print(f"Aggregating {int(interval)}min to 2h...")

    # Index prep
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.set_index("timestamp", inplace=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        # If is not column and index isnt timestamp, convert index
        df.index = pd.to_datetime(df.index, utc=True)

    df_2h = df.resample("2h").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()

    # Join to previous 2h.parquet if exists
    output_path = os.path.join(output_dir, "2h.parquet")
    if os.path.exists(output_path):
        existing_df = pd.read_parquet(output_path)
        existing_df.index = pd.to_datetime(existing_df.index, utc=True)
        
        # Copy, sort, remove duplicates
        combined = pd.concat([existing_df, df_2h])
        combined = combined[~combined.index.duplicated(keep="last")]
        df_2h = combined.sort_index()

    os.makedirs(output_dir, exist_ok=True)
    df_2h.to_parquet(output_path)
    print(f"Done '{output_path}' updated. Total rows: {len(df_2h)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to input file")
    parser.add_argument("--out", default="data/", help="Output folder")
    args = parser.parse_args()

    aggregate_candles(args.file, args.out)