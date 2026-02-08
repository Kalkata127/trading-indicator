import pandas as pd
import argparse
from pathlib import Path
from strategy_controller import StrategyController
import multiprocessing
from typing import List, Dict, Any

def simulate_exit(df: pd.DataFrame, start_idx: int, sig: Dict[str, Any]) -> Dict[str, Any]:
    """Checks future candles for hitting TP/SL using the full dataframe."""
    for j in range(start_idx + 1, len(df)):
        low, high, ts = df['low'].iloc[j], df['high'].iloc[j], df.index[j]
        if sig['direction'] == "SHORT":
            if low <= sig['tp']: return {"outcome": "WIN", "exit_ts": ts, "exit_price": sig['tp']}
            if high >= sig['sl']: return {"outcome": "LOSS", "exit_ts": ts, "exit_price": sig['sl']}
        else: # LONG
            if high >= sig['tp']: return {"outcome": "WIN", "exit_ts": ts, "exit_price": sig['tp']}
            if low <= sig['sl']: return {"outcome": "LOSS", "exit_ts": ts, "exit_price": sig['sl']}
    return {"outcome": "OPEN", "exit_ts": df.index[-1], "exit_price": df['close'].iloc[-1]}

def backtest_worker(start_idx: int, end_idx: int, df: pd.DataFrame, pois_df: pd.DataFrame, min_rr: float) -> List[Dict[str, Any]]:
    """Worker function to process a specific chunk of the data."""
    chunk_signals = []
    for i in range(start_idx, end_idx):
        current_ts = df.index[i]

        df_slice = df.iloc[:i+1]
        pois_slice = pois_df[pois_df['timestamp'] <= current_ts]
        
        controller = StrategyController(df_slice, pois_slice)
        res = controller.run(min_rr=min_rr)

        if res["status"] == "TRADE":
            res["start_ts"] = current_ts
            res.update(simulate_exit(df, i, res))
            chunk_signals.append(res)
            
    return chunk_signals

def run_backtest(base_path: Path, interval: str, min_rr: float) -> None:
    vector_file = base_path / f"{interval}.vector.parquet"
    pois_file = base_path / f"{interval}.pois.parquet"

    if not vector_file.exists() or not pois_file.exists():
        print(f"Error: Required files not found in {base_path}!")
        return

    # Load data once in main process
    df = pd.read_parquet(vector_file)
    df.index = pd.to_datetime(df['timestamp'], utc=True)
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    pois_df = pd.read_parquet(pois_file)
    pois_df['timestamp'] = pd.to_datetime(pois_df['timestamp'], utc=True)
    
    total_candles = len(df)
    start_point = 50
    
    # Determine number of processes (CPU cores)
    num_cores = multiprocessing.cpu_count()
    chunk_size = (total_candles - start_point) // num_cores
    
    print(f"--- Parallel Backtesting {base_path.parent.name} | Mode: {base_path.name} ---")
    print(f"[*] Using {num_cores} CPU cores for {total_candles} candles...")

    # Chunks prep
    tasks = []
    for n in range(num_cores):
        s = start_point + n * chunk_size
        e = s + chunk_size if n < num_cores - 1 else total_candles
        tasks.append((s, e, df, pois_df, min_rr))

    # Execute in parallel
    with multiprocessing.Pool(processes=num_cores) as pool:
        results = pool.starmap(backtest_worker, tasks)

    # Flatten the list of signals from all workers
    all_raw_signals = [sig for chunk in results for sig in chunk]
    
    # --- FILTERING ---
    all_raw_signals.sort(key=lambda x: x['start_ts'])
    
    final_signals = []
    active_trade_until = None
    
    for sig in all_raw_signals:
        if active_trade_until is None or sig['start_ts'] > active_trade_until:
            final_signals.append(sig)
            active_trade_until = sig['exit_ts']
            print(f"📍 {sig['type']} {sig['direction']} на {sig['start_ts'].strftime('%d-%m %H:%M')}")

    print_report(final_signals)

def print_report(results: List[Dict[str,Any]]) -> None:
    if not results:
        print("\nNo trades found for this period.")
        return

    print("\n" + "="*115)
    header = f"{'TYPE':<10} | {'DIRECTION':<7} | {'RESULT':<8} | {'ENTRANCE':<10} | {'EXIT':<10} | {'IN':<15} | {'OUT'}"
    print(header)
    print("-" * 115)
    
    wins = 0
    for r in results:
        if r['outcome'] == "WIN": wins += 1
        start_str = r['start_ts'].strftime('%d-%m %H:%M')
        exit_str = r['exit_ts'].strftime('%d-%m %H:%M')
        
        print(f"{r['type']:<10} | {r['direction']:<7} | {r['outcome']:<8} | "
              f"{r['entry']:<10.2f} | {r['exit_price']:<10.2f} | "
              f"{start_str:<15} | {exit_str}")
    
    wr = (wins / len(results)) * 100
    print("="*115)
    print(f"Total: {len(results)} | Wins: {wins} | Losses: {len(results)-wins} | WIN RATE: {wr:.2f}%")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    parser = argparse.ArgumentParser(description="Parallel Backtester for crypto MM strategy")
    parser.add_argument('symbol', type=str, help="Token name")
    parser.add_argument('mode', type=str, help="Subfolder")
    parser.add_argument("--interval", type=str, default="15m")
    parser.add_argument("--rr", type=float, default=1.5)

    args = parser.parse_args()
    base_data_path = Path("data") / args.symbol / args.mode
    
    if not base_data_path.exists():
        print(f"Error: Directory {base_data_path} not found!")
    else:
        run_backtest(base_data_path, args.interval, args.rr)
    
    print("\nPress Enter to exit...")
    input()