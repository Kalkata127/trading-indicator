import sys
import pandas as pd
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from strategy_controller import StrategyController
from DataManager import DataManager

class TradingCLI:
    def __init__(self, base_dir: str = "data"):
        self.base_dir: Path = Path(base_dir)
        self.manager: DataManager = DataManager(base_dir)

    def list_items(self, symbol: Optional[str] = None) -> None:
        if not self.base_dir.exists():
            print("[-] No data directory found yet.")
            return

        if not symbol:
            tokens: List[Path] = [d for d in self.base_dir.iterdir() if d.is_dir()]
            print("\n📂 Available Tokens:")
            for t in tokens:
                print(f" - {t.name}")
        else:
            token_path = self.base_dir / symbol
            if not token_path.exists():
                print(f"❌ Error: Token {symbol} not found.")
                return
            periods: List[Path] = [d for d in token_path.iterdir() if d.is_dir()]
            print(f"\n📂 Available periods for {symbol}:")
            for p in periods:
                p_type = "[L]" if p.name == "live" else "[B]"
                print(f" {p_type} {p.name}")
        print("")

    def delete(self, symbol: str, period: Optional[str] = None) -> None:
        target_path: Path = self.base_dir / symbol
        if period:
            target_path = target_path / period

        if not target_path.exists():
            print(f"❌ Error: Path {target_path} does not exist.")
            return

        confirm: str = input(f"⚠️ Are you sure you want to delete {target_path}? (y/n): ")
        if confirm.lower() == 'y':
            shutil.rmtree(target_path)
            print(f"✅ Successfully deleted {target_path}")
        else:
            print("🚫 Deletion cancelled.")

    def run_sub_script(self, script_name: str, args: List[str]) -> None:
        try:
            subprocess.run(["python", script_name] + args, check=True)
        except subprocess.CalledProcessError:
            print(f"❌ Error executing {script_name}")
        except FileNotFoundError:
            print(f"❌ Error: {script_name} not found in current directory.")

def execute_command(cli: TradingCLI, cmd_input: str) -> bool:
    parts = cmd_input.split()
    if not parts:
        return True
    
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in ["exit", "quit", "e", "q"]:
        print("👋 Exiting Trading System. Goodbye!")
        return False

    try:
        if cmd == "list":
            symbol = args[0] if len(args) > 0 else None
            cli.list_items(symbol)
        
        elif cmd == "update":
            if not args: print("❌ Usage: update <symbol>"); return True
            cli.manager.update_live_data(args[0])
        
        elif cmd == "fetch":
            if len(args) < 3: print("❌ Usage: fetch <symbol> <start> <end>"); return True
            cli.manager.fetch_backtest_data(args[0], args[1], args[2])
        
        elif cmd == "plot":
            if len(args) < 2: print("❌ Usage: plot <symbol> <mode> [--flags]"); return True
            cli.run_sub_script("plot_Candles.py", args)
        
        elif cmd == "test":
            if len(args) < 2: print("❌ Usage: test <symbol> <mode> [--flags]"); return True
            cli.run_sub_script("backtest.py", args)

        # --- NEW COMMAND: SIGNAL (Live Only) ---
        elif cmd == "signal":
            if not args:
                print("❌ Usage: signal <symbol>")
                return True
            
            symbol = args[0].upper()
            mode = "live" # Forced to live mode only
            
            print(f"[*] Syncing live data for {symbol}...")
            # Automatically fetches last 7 days if folder is empty or updates if exists
            cli.manager.update_live_data(symbol)
            
            target_dir = cli.base_dir / symbol / mode
            vector_file = target_dir / "15m.vector.parquet"
            pois_file = target_dir / "15m.pois.parquet"
            
            if not vector_file.exists() or not pois_file.exists():
                print(f"❌ Error: Processed data not found in {target_dir}. Ensure recalculation in DataManager is working.")
                return True

            # Load data for analysis
            df = pd.read_parquet(vector_file)
            if 'timestamp' in df.columns:
                df.index = pd.to_datetime(df['timestamp'], utc=True)
            df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
            
            pois_df = pd.read_parquet(pois_file)
            if 'timestamp' in pois_df.columns:
                pois_df['timestamp'] = pd.to_datetime(pois_df['timestamp'], utc=True)

            print(f"[*] Analyzing latest candle for {symbol}...")
            controller = StrategyController(df, pois_df)
            result = controller.run(min_rr=1.5)

            # Visual feedback
            if result["status"] == "TRADE":
                print(f"\n🚀 [SIGNAL] {result['type']} {result['direction']} identified!")
                print(f"📍 Entry: {result['entry']:.2f} | TP: {result['tp']:.2f} | SL: {result['sl']:.2f} | RR: {result['rr']:.2f}")
            elif result["status"] == "CANDIDATE":
                print(f"\n👀 [CANDIDATE] Vector found, but strategy conditions (Trend/RR) not fully met.")
            else:
                print(f"\n😴 No trade signal for {symbol} at the moment.")
        # ---------------------------------------
        
        elif cmd == "delete":
            if not args: print("❌ Usage: delete <symbol> [period]"); return True
            period = args[1] if len(args) > 1 else None
            cli.delete(args[0], period)
        
        elif cmd == "help":
            print("\n📜 Commands:")
            print(" list [symbol]                  - List tokens or subfolders")
            print(" update <symbol>                - Refresh live data (last 7 days auto-fetch)")
            print(" signal <symbol>                - Check for real-time trade signals (Live mode)")
            print(" fetch <symbol> <start> <end>   - Download backtest data (max 1 month)")
            print(" plot <symbol> <mode> [flags]   - Open chart (flags: --vector, --pois, --ema, --sr)")
            print(" test <symbol> <mode> [--rr X]  - Run strategy backtest")
            print(" delete <symbol> [period]       - Remove data with confirmation")
            print(" exit                           - Close terminal")
        
        else:
            print(f"❓ Unknown command: {cmd}. Type 'help' for options.")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    
    return True

def main():
    cli = TradingCLI()

    if len(sys.argv) > 1:
        cmd_line = " ".join(sys.argv[1:])
        execute_command(cli, cmd_line)
    else:
        print("\n🚀 Welcome to the Trading Analysis System")
        print("Type 'help' for commands or 'exit' to quit.")
        
        while True:
            try:
                user_input = input("TradingBot > ").strip()
                if not execute_command(cli, user_input):
                    break
            except KeyboardInterrupt:
                print("\n👋 Use 'exit' to close the terminal.")
                continue

if __name__ == "__main__":
    main()