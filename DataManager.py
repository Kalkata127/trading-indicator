import pandas as pd
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
import fetch_raw_data as fetcher

class DataManager:
    def __init__(self, base_dir: str = "data"):
        self.base_dir: Path = Path(base_dir)
        # Limit
        self.absolute_min_date: datetime = datetime(2025, 1, 1, tzinfo=timezone.utc)

    def get_token_dir(self, symbol: str) -> Path:
        return self.base_dir / symbol

    def fetch_backtest_data(self, symbol: str, start_str: str, end_str: str, interval: str = "15m") -> None:
        try:
            dt_start: datetime = datetime.strptime(start_str, '%d-%m-%Y:%H:%M').replace(tzinfo=timezone.utc)
            dt_end: datetime = datetime.strptime(end_str, '%d-%m-%Y:%H:%M').replace(tzinfo=timezone.utc)
        except ValueError:
            print("[-] Error: Invalid date format. Use DD-MM-YYYY:HH:MM")
            return

        # LIMIT: Period range cannot exceed 30 days
        if (dt_end - dt_start) > timedelta(days=30):
            print("[-] Error: Backtest period is too long! Maximum allowed: 1 month (30 days).")
            return

        if dt_start < self.absolute_min_date:
            print(f"[-] Error: Start date cannot be before {self.absolute_min_date.strftime('%d-%m-%Y')}")
            return

        # VALIDATION BEFORE FOLDER CREATION: Attempt to fetch a small sample
        print(f"[*] Validating symbol {symbol} with Binance...")
        # Check if the symbol is valid by fetching 1 candle before creating directories
        test_fetch = fetcher.get_binance_candles_period(symbol, interval, dt_start, dt_start + timedelta(minutes=15))
        
        if test_fetch is None or test_fetch.empty:
            print(f"[-] Error: Symbol '{symbol}' is invalid or has no data on Binance. Folder will not be created.")
            return

        # DIRECTORY CREATION: (after validation)
        token_dir = self.get_token_dir(symbol)
        folder_name: str = f"backtest_{dt_start.strftime('%d-%m-%Y')}_{dt_end.strftime('%d-%m-%Y')}"
        bt_dir: Path = token_dir / folder_name
        bt_dir.mkdir(parents=True, exist_ok=True)
        
        raw_file: Path = bt_dir / f"{interval}.parquet"

        print(f"[*] Fetching historical data for {symbol} into {folder_name}...")
        # Fetch actual data range
        df: pd.DataFrame = fetcher.get_binance_candles_period(symbol, interval, dt_start, dt_end)
        
        if df.empty:
            print("[-] Error: No data returned from Binance.")
            return

        df.to_parquet(raw_file)
        self.recalculate_all(symbol, interval, bt_dir)
        print(f"[OK] Backtest data ready in: {bt_dir}")

    def update_live_data(self, symbol: str, interval: str = "15m") -> None:
        token_dir = self.get_token_dir(symbol)
        live_dir: Path = token_dir / "live"
        
        # Initial check for new symbol
        if not live_dir.exists():
             start_dt = datetime.now(timezone.utc) - timedelta(days=7)
             test_fetch = fetcher.get_binance_candles_period(symbol, interval, start_dt, start_dt + timedelta(minutes=15))
             if test_fetch is None or test_fetch.empty:
                 print(f"[-] Error: Invalid symbol '{symbol}'. Live update aborted.")
                 return
             live_dir.mkdir(parents=True, exist_ok=True)
        
        raw_file: Path = live_dir / f"{interval}.parquet"
        
        old_df: pd.DataFrame = pd.DataFrame()
        if raw_file.exists():
            old_df = pd.read_parquet(raw_file)
            start_dt = old_df.index[-1].to_pydatetime()
        else:
            start_dt = datetime.now(timezone.utc) - timedelta(days=7)

        new_candles: pd.DataFrame = fetcher.get_binance_candles_period(symbol, interval, start_dt, datetime.now(timezone.utc))
        if new_candles.empty:
            print(f"[-] No new data for {symbol}.")
            return

        df: pd.DataFrame = pd.concat([old_df, new_candles])
        df = df[~df.index.duplicated(keep='last')].sort_index()
        df.to_parquet(raw_file)
        
        self.recalculate_all(symbol, interval, live_dir)

    def recalculate_all(self, symbol: str, interval: str, target_dir: Path) -> None:
        raw_file: Path = target_dir / f"{interval}.parquet"
        vector_file: Path = target_dir / f"{interval}.vector.parquet"
        two_h_file: Path = target_dir / "2h.parquet"
        
        print(f"[*] Processing started for {symbol} in {target_dir.name}...")
        subprocess.run(["python", "make_vector_candles.py", str(raw_file)], check=True)
        subprocess.run(["python", "aggregator.py", "--file", str(raw_file), "--out", str(target_dir)], check=True)
        subprocess.run(["python", "support_resistance_finder.py", "--file", str(two_h_file), "--out", str(target_dir)], check=True)
        subprocess.run(["python", "pois_finder.py", str(vector_file)], check=True)
        print(f"[OK] Recalculation complete.")

def main() -> None:
    parser = argparse.ArgumentParser(description="DataManager CLI - Manage Crypto Data.")
    parser.add_argument("action", choices=["live", "backtest"], help="Operation mode: live update or backtest fetch")
    parser.add_argument("symbol", type=str, help="Trading symbol (e.g., BTCUSDC)")
    parser.add_argument("--start", type=str, help="Start date (Backtest only) format: DD-MM-YYYY:HH:MM")
    parser.add_argument("--end", type=str, help="End date (Backtest only) format: DD-MM-YYYY:HH:MM")
    parser.add_argument("--interval", type=str, default="15m", help="Candle interval (default 15m)")

    args: argparse.Namespace = parser.parse_args()
    manager: DataManager = DataManager()

    if args.action == "live":
        manager.update_live_data(args.symbol, args.interval)
    elif args.action == "backtest":
        if not args.start or not args.end:
            print("[-] Error: Backtest mode requires --start and --end parameters.")
            return
        manager.fetch_backtest_data(args.symbol, args.start, args.end, args.interval)

if __name__ == "__main__":
    main()