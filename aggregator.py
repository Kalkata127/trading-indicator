import os
import pandas as pd
import argparse
from pathlib import Path

def get_interval(df: pd.DataFrame) -> str:
    if df.empty:
        return None
    
    if len(df) > 1:
        diff_sec = (df.index[1] - df.index[0]).total_seconds()
        return round(diff_sec / 60)
    
    return None

def aggregate_candles(input_file: Path, output_dir: Path) -> None:
    if not os.path.exists(input_file):
        print(f"[Error] Input file '{input_file}' not found!")
        return

    # Make out folder if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        df = pd.read_parquet(input_file)
    except Exception as e:
        print(f"[Error] Error when reading file: {e}")
        return

    if df.empty:
        print(f"[Warning] File '{input_file}' is empty.")
        return

    # Preparing index (standard to UTC)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.set_index("timestamp", inplace=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    else:
        df.index = pd.to_datetime(df.index, utc=True)

    interval = get_interval(df)

    if interval not in [5.0, 15.0, 30.0]:
        print(f"[Error] Interval is {interval} min. Supproted only 5, 15 or 30min.")
        return

    print(f"[*] Aggregating {int(interval)}min to 2h...")

    # Resamble to 2h 
    df_2h = df.resample("2h").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()

    output_path = os.path.join(output_dir, "2h.parquet")

    # Concatenating logic, if file already exists
    if os.path.exists(output_path):
        existing_df = pd.read_parquet(output_path)
        existing_df.index = pd.to_datetime(existing_df.index, utc=True)
        
        # Important for last 2h candle, may not be filled
        combined = pd.concat([existing_df, df_2h])
        combined = combined[~combined.index.duplicated(keep="last")]
        df_2h = combined.sort_index()

    df_2h.to_parquet(output_path)
    print(f"[OK] File '{output_path}' is updated. Total rows: {len(df_2h)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--file", required=True, help="Path to input parquet file")
    parser.add_argument("--out", required=True, help="Directory to save 2h.parquet")
    args = parser.parse_args()

    aggregate_candles(args.file, args.out)