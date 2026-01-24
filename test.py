import pandas as pd
from strategy_controller import StrategyController


def load_chart(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df["timestamp"], utc=True)
    return df


def run_test_points(df: pd.DataFrame, sr_df: pd.DataFrame, timestamps: list):
    trades = []
    no_trades = 0

    print("\n=== STRATEGY TEST RESULTS ===\n")

    for ts in timestamps:
        ts = pd.to_datetime(ts, utc=True)
        df_cut = df[df.index <= ts]

        controller = StrategyController(df_cut, sr_df=sr_df)
        controller.load_indicators()

        decision = controller.run(
            lookback=6,
            use_last_closed=True,
            min_strength=5,
            min_rr=1.5,
            tp_level=2,         # <-- try second level for TP (less tight)
            sl_level=1,
            sl_buffer_pct=0.001,
            min_stop_pct=0.002
        )

        if decision["status"] == "NO_TRADE":
            no_trades += 1
            print(f"{ts} -> NO_TRADE | reason={decision['reason']} | debug={decision.get('debug', {})}")
            continue

        trades.append(decision)
        print(
            f"{ts} -> TRADE {decision['direction']} | "
            f"entry={decision['entry']} SL={decision['stop_loss']} TP={decision['take_profit']} "
            f"RR={decision['rr']} strength={decision['strength']}\n"
            f"    debug: {decision['debug']}"
        )

    print("\n=== SUMMARY ===")
    print(f"Checkpoints: {len(timestamps)}")
    print(f"Trades: {len(trades)}")
    print(f"No trade: {no_trades}")

    if trades:
        rrs = [t["rr"] for t in trades]
        strengths = [t["strength"] for t in trades]
        print(f"Avg RR: {round(sum(rrs)/len(rrs), 2)} | Min RR: {min(rrs)} | Max RR: {max(rrs)}")
        print("Strength counts:", {s: strengths.count(s) for s in sorted(set(strengths))})


def main():
    candles_file = "data/BTCUSDT/15m_4D_08-12-2025_15-30-00___12-12-2025_15-15-00.candles.parquet"
    sr_2h_file = "data/BTCUSDT/pois/2h.sr.parquet"

    df = load_chart(candles_file)
    sr_df = pd.read_parquet(sr_2h_file)

    test_points = [
        "2025-12-09 15:30:00",
        "2025-12-09 15:45:00",
        "2025-12-09 20:15:00",
        "2025-12-10 06:45:00",
        "2025-12-10 19:00:00",
        "2025-12-12 15:15:00",
    ]

    run_test_points(df, sr_df, test_points)


if __name__ == "__main__":
    main()
