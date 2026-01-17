import os
import pandas as pd

def load_or_empty(path):
    """Load a parquet file if exists, otherwise return empty DataFrame."""
    if os.path.exists(path):
        return pd.read_parquet(path)
    return pd.DataFrame()


def aggregate_to_tf(df_15m: pd.DataFrame, tf="1h"):
    if not isinstance(df_15m.index, pd.DatetimeIndex):
        df_15m.index = pd.to_datetime(df_15m["timestamp"], utc=True)

    df = df_15m.resample(tf).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()

    df["timestamp"] = df.index

    return df


def merge_and_deduplicate(old_df, new_df):
    if old_df is None or len(old_df) == 0:
        return new_df

    combined = pd.concat([old_df, new_df])

    combined = combined.sort_index()

    combined = combined[~combined.index.duplicated(keep="last")]

    return combined


class Aggregator:

    def __init__(self, output_dir="data/"):
        self.output_dir = output_dir
        self.path_1h = os.path.join(output_dir, "1h.parquet")
        self.path_2h = os.path.join(output_dir, "2h.parquet")

    # Aggregate a 15m parquet file and update 1h/2h storage
    def process_15m_file(self, path_15m: str):
        print(f"[INFO] Loading 15m file: {path_15m}")

        df_15m = pd.read_parquet(path_15m)

        if not isinstance(df_15m.index, pd.DatetimeIndex):
            df_15m.index = pd.to_datetime(df_15m["timestamp"], utc=True)

        df_15m = df_15m.sort_index()

        # Aggregate into 1H
        df_1h_new = aggregate_to_tf(df_15m, "1H")
        df_1h_existing = load_or_empty(self.path_1h)

        df_1h_merged = merge_and_deduplicate(df_1h_existing, df_1h_new)
        df_1h_merged.to_parquet(self.path_1h)
        print(f"[OK] Updated 1h.parquet → {len(df_1h_merged)} rows")

        # Aggregate into 2H
        df_2h_new = aggregate_to_tf(df_15m, "2h")
        df_2h_existing = load_or_empty(self.path_2h)

        df_2h_merged = merge_and_deduplicate(df_2h_existing, df_2h_new)
        df_2h_merged.to_parquet(self.path_2h)
        print(f"[OK] Updated 2h.parquet → {len(df_2h_merged)} rows")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate 15m candles into 1h and 2h.")
    parser.add_argument("--file", required=True, help="Path to a 15m parquet file")
    parser.add_argument("--out", default="data/", help="Output directory")
    args = parser.parse_args()

    agg = Aggregator(output_dir=args.out)
    agg.process_15m_file(args.file)
