import pandas as pd
import argparse
import os
from pathlib import Path
from strategy_controller import StrategyController

def simulate_exit(df, start_idx, sig):
    """Checking future candles for hitting TP/SL."""
    for j in range(start_idx + 1, len(df)):
        low, high, ts = df['low'].iloc[j], df['high'].iloc[j], df.index[j]
        if sig['direction'] == "SHORT":
            if low <= sig['tp']: return {"outcome": "WIN", "exit_ts": ts, "exit_price": sig['tp']}
            if high >= sig['sl']: return {"outcome": "LOSS", "exit_ts": ts, "exit_price": sig['sl']}
        else: # LONG
            if high >= sig['tp']: return {"outcome": "WIN", "exit_ts": ts, "exit_price": sig['tp']}
            if low <= sig['sl']: return {"outcome": "LOSS", "exit_ts": ts, "exit_price": sig['sl']}
    return {"outcome": "OPEN", "exit_ts": df.index[-1], "exit_price": df['close'].iloc[-1]}

def run_backtest(base_path, interval, min_rr):
    # Construct path to files in the folder
    vector_file = base_path / f"{interval}.vector.parquet"
    pois_file = base_path / f"{interval}.pois.parquet"

    if not vector_file.exists():
        print(f"Error: Vector candle file {vector_file.name} not found in {base_path}!")
        return
    if not pois_file.exists():
        print(f"Error: POI file {pois_file.name} not found in {base_path}!")
        return

    # Load data
    df = pd.read_parquet(vector_file)
    df.index = pd.to_datetime(df['timestamp'], utc=True)
    # Calculate Ema
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    pois_df = pd.read_parquet(pois_file)
    pois_df['timestamp'] = pd.to_datetime(pois_df['timestamp'], utc=True)
    
    found_signals, active_trade_until = [], None

    print(f"--- Backtesting {base_path.parent.name} | Mode: {base_path.name} ---")
    
    # Analysis start from 50th candle (for the EMA)
    for i in range(50, len(df)):
        current_ts = df.index[i]
        
        # Skip if we are in trade
        if active_trade_until and current_ts <= active_trade_until:
            continue

        df_slice = df.iloc[:i+1]
        pois_slice = pois_df[pois_df['timestamp'] <= current_ts]
        
        # Inicializing controller with current data slice
        controller = StrategyController(df_slice, pois_slice)
        res = controller.run(min_rr=min_rr)

        if res["status"] == "TRADE":
            # Simulating exit in future
            res.update(simulate_exit(df, i, res))
            found_signals.append(res)
            active_trade_until = res['exit_ts']
            print(f"📍 {res['type']} {res['direction']} на {current_ts.strftime('%d-%m %H:%M')}")

    print_report(found_signals)

def print_report(results):
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
    parser = argparse.ArgumentParser(description="Backtester for crypto MM stategy")

    parser.add_argument('symbol', type=str, help="Token name (ex. BTCUSDC)")
    parser.add_argument('mode', type=str, help="Subfolder (live or backtest)")
    parser.add_argument("--interval", type=str, default="15m", help="Interval (default 15m)")
    parser.add_argument("--rr", type=float, default=1.5, help="Minimal Risk/Reward")

    args = parser.parse_args()

    # Making path to folder
    base_data_path = Path("data") / args.symbol / args.mode
    
    if not base_data_path.exists():
        print(f"Error: Directory {base_data_path} not found!")
    else:
        run_backtest(base_data_path, args.interval, args.rr)
    input()