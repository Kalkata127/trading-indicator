import pandas as pd
import subprocess
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import fetchRawData as fetcher

class DataManager:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)

    def get_live_dir(self, symbol):
        path = self.base_dir / symbol / "live"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def update_live_data(self, symbol, interval="15m"):
        live_dir = self.get_live_dir(symbol)
        raw_file = live_dir / f"{interval}.parquet"
        
        # 1. Avalable data check
        old_df = pd.DataFrame()
        if raw_file.exists():
            old_df = pd.read_parquet(raw_file)
            start_dt = old_df.index[-1].to_pydatetime()
            ltimestamp = old_df.index[-1]
        else:
            start_dt = datetime.now(timezone.utc) - timedelta(days=7)
            ltimestamp = None


        # 2. Fetch data
        new_candles = fetcher.get_binance_candles_period(symbol, interval, start_dt, datetime.now(timezone.utc))
        if new_candles.empty:
            print(f"[-] No new data for {symbol}.")
            return

        # 3. Concatenate and write
        df = pd.concat([old_df, new_candles])
        df = df[~df.index.duplicated(keep='last')].sort_index()
        df.to_parquet(raw_file)
        
        # 4. Recalculating the rest of folder files
        self.recalculate_all(symbol, interval, live_dir, ltimestamp)

    def recalculate_all(self, symbol, interval, live_dir, ltimestamp):

        raw_file = live_dir / f"{interval}.parquet"
        vector_file = live_dir / f"{interval}.vector.parquet"
        
        print(f"[*] Started processing for {symbol} in {live_dir}...")

        subprocess.run(["python", "make_vector_candles.py", str(raw_file)], check=True)

        subprocess.run(["python", "aggregator.py", "--file", str(raw_file), "--out", str(live_dir)], check=True)

        two_h_file = live_dir / "2h.parquet"
        subprocess.run(["python", "support_resistance_finder.py", "--file", str(two_h_file), "--out", str(live_dir)], check=True)

        subprocess.run(["python", "pois_finder.py", str(vector_file)], check=True)

        print(f"[OK] All files for {symbol} are updated in {live_dir}")