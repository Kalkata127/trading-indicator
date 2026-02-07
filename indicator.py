import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from strategy_controller import StrategyController
from indicators import ema

def check_current_market_state(symbol, mode, interval="15m", min_rr=1.5):
    # 1. Setup paths
    base_path = Path("data") / symbol / mode
    vector_file = base_path / f"{interval}.vector.parquet"
    pois_file = base_path / f"{interval}.pois.parquet"

    # 2. Check if required files exist
    if not vector_file.exists():
        print(f"❌ Error: Vector file not found at {vector_file}")
        return
    if not pois_file.exists():
        print(f"❌ Error: POI file not found at {pois_file}")
        return

    # 3. Load and prepare data
    df = pd.read_parquet(vector_file)
    df.index = pd.to_datetime(df['timestamp'], utc=True)
    
    # StrategyController expects 'ema50' column to exist
    df['ema50'] = ema(df['close'], 50)
    
    pois_df = pd.read_parquet(pois_file)
    pois_df['timestamp'] = pd.to_datetime(pois_df['timestamp'], utc=True)

    controller = StrategyController(df, pois_df)
    decision = controller.run(min_rr=min_rr)

    print("\n" + "║" + "═"*60 + "║")
    print(f"║ 🔍 INDICATOR ANALYSIS: {symbol:<35} ║")
    print(f"║ 📂 Mode: {mode:<45} ║")
    print(f"║ ⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<38} ║")
    print(f"║ 📊 Last Candle: {df.index[-1].strftime('%H:%M'):<41} ║")
    print("╟" + "─"*60 + "╢")

    if decision["status"] == "TRADE":
        print(f"║ ✅ SIGNAL DETECTED: {decision['type']} {decision['direction']:<28} ║")
        print(f"║ 💰 Entry Price: {decision['entry']:<41.2f} ║")
        print(f"║ 🎯 Take Profit: {decision['tp']:<42.2f} ║")
        print(f"║ 🛡️ Stop Loss:   {decision['sl']:<42.2f} ║")
        print(f"║ ⚖️ Risk/Reward: {decision['rr']:<42.2f} ║")
    elif decision["status"] == "CANDIDATE":
        msg = decision.get('msg', 'Criteria almost met')
        print(f"║ 👀 STATUS: CANDIDATE ({msg[:35]}) ║")
    else:
        print(f"║ ❌ STATUS: No valid signal for entry.                      ║")
    
    print("╚" + "═"*60 + "╝\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Signal Indicator")
    parser.add_argument('symbol', type=str, help="Trading symbol (e.g., BTCUSDC)")
    parser.add_argument('mode', type=str, help="Data folder (e.g., live or backtest_name)")
    parser.add_argument("--interval", type=str, default="15m", help="Candle timeframe")
    parser.add_argument("--rr", type=float, default=1.5, help="Minimum Risk/Reward ratio")

    args = parser.parse_args()
    check_current_market_state(args.symbol, args.mode, args.interval, args.rr)