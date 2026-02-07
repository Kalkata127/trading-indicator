import pandas as pd
import argparse
import os
from strategy_controller import StrategyController

def simulate_exit(df, start_idx, sig):
    """Checks future candles for hitting TP or SL"""
    for j in range(start_idx + 1, len(df)):
        low, high, ts = df['low'].iloc[j], df['high'].iloc[j], df.index[j]
        if sig['direction'] == "SHORT":
            if low <= sig['tp']: return {"outcome": "WIN", "exit_ts": ts, "exit_price": sig['tp']}
            if high >= sig['sl']: return {"outcome": "LOSS", "exit_ts": ts, "exit_price": sig['sl']}
        else:
            if high >= sig['tp']: return {"outcome": "WIN", "exit_ts": ts, "exit_price": sig['tp']}
            if low <= sig['sl']: return {"outcome": "LOSS", "exit_ts": ts, "exit_price": sig['sl']}
    return {"outcome": "OPEN", "exit_ts": df.index[-1], "exit_price": df['close'].iloc[-1]}

def run_backtest(vector_file, pois_file, min_rr):
    df = pd.read_parquet(vector_file)
    df.index = pd.to_datetime(df['timestamp'], utc=True)
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    pois_df = pd.read_parquet(pois_file)
    pois_df['timestamp'] = pd.to_datetime(pois_df['timestamp'], utc=True)
    
    found_signals, active_trade_until = [], None

    print("--- Market analysis: ---")
    for i in range(50, len(df)):
        current_ts = df.index[i]
        if active_trade_until and current_ts <= active_trade_until: continue

        df_slice = df.iloc[:i+1]
        pois_slice = pois_df[pois_df['timestamp'] <= current_ts]
        
        controller = StrategyController(df_slice, pois_slice)
        res = controller.run(min_rr=min_rr)

        if res["status"] == "TRADE":
            res.update(simulate_exit(df, i, res))
            found_signals.append(res)
            active_trade_until = res['exit_ts']
            print(f"📍 {res['type']} {res['direction']} on {current_ts.strftime('%d-%m %H:%M')}")

    print_report(found_signals)

def print_report(results):
    if not results: return print("\nNo trades found.")
    print("\n" + "="*115)
    print(f"{'TYPE':<10} | {'DIRECTION':<7} | {'RESULT':<8} | {'ENTRY':<10} | {'EXIT':<10} | {'IN':<15} | {'OUT'}")
    print("-" * 115)
    wins = 0
    for r in results:
        if r['outcome'] == "WIN": wins += 1
        print(f"{r['type']:<10} | {r['direction']:<7} | {r['outcome']:<8} | {r['entry']:<10.2f} | "
              f"{r['exit_price']:<10.2f} | {r['start_ts'].strftime('%d-%m %H:%M'):<15} | {r['exit_ts'].strftime('%d-%m %H:%M')}")
    print("="*115)
    print(f"Total: {len(results)} | WIN RATE: {(wins/len(results))*100:.2f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vector", type=str, required=True)
    parser.add_argument("--pois", type=str, required=True)
    parser.add_argument("--rr", type=float, default=1.5)
    args = parser.parse_args()
    run_backtest(args.vector, args.pois, args.rr)