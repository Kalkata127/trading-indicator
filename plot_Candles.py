import argparse
import pandas as pd
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from indicators import ema
import os
from pathlib import Path

def add_emas(df, add_plots):
    ema_50 = ema(df["close"], 50)
    ema_200 = ema(df["close"], 200)
    add_plots += [
        mpf.make_addplot(ema_50, color="blue", width=1),
        mpf.make_addplot(ema_200, color="red", width=1),
    ]

def add_vector_candles(df, add_plots):
    if 'va' not in df.columns: return

    # Create series of Nan with the same length and index as df
    def create_marker_series(mask, color, size):
        # Marker will be, where the condition is right
        series = pd.Series(np.nan, index=df.index)
        series.loc[mask] = df.loc[mask, 'high'] * 1.002
        return mpf.make_addplot(series, type='scatter', marker='v', color=color, markersize=size)

    climax_bull_m = (df['va'] == 1) & (df['close'] > df['open'])
    climax_bear_m = (df['va'] == 1) & (df['close'] < df['open'])
    rising_bull_m = (df['va'] == 2) & (df['close'] > df['open'])
    rising_bear_m = (df['va'] == 2) & (df['close'] < df['open'])

    if climax_bull_m.any(): add_plots.append(create_marker_series(climax_bull_m, 'lime', 100))
    if climax_bear_m.any(): add_plots.append(create_marker_series(climax_bear_m, 'red', 100))
    if rising_bull_m.any(): add_plots.append(create_marker_series(rising_bull_m, 'blue', 60))
    if rising_bear_m.any(): add_plots.append(create_marker_series(rising_bear_m, 'fuchsia', 60))

def add_sr(sr_df, df, mpf_params):
    last_timestamp = df.index[-1]
    lines, colors = [], []
    for i in range(len(sr_df)):
        start_time = sr_df["timestamp"].iloc[i]
        price = sr_df["price"].iloc[i]
        sr_type = sr_df["type"].iloc[i].lower()
        if start_time > last_timestamp: continue
        lines.append([(start_time, price), (last_timestamp, price)])
        colors.append("#00ff00" if sr_type == "support" else "#ff0000")
    if lines:
        mpf_params['alines'] = dict(alines=lines, colors=colors, linewidths=1.2, alpha=0.7)

def draw_poi_rectangles(ax, df, poi_df):
    last_ts_num = mdates.date2num(df.index[-1])
    for _, poi in poi_df.iterrows():
        x_start = mdates.date2num(poi['timestamp'])
        x_end = mdates.date2num(poi['covered_timestamp']) if poi['isCovered'] and pd.notna(poi['covered_timestamp']) else last_ts_num
        y_bottom, height = poi['zone_bottom'], poi['zone_top'] - poi['zone_bottom']
        color = 'green' if poi['type'] == 'GREEN' else 'red'
        rect = Rectangle((x_start, y_bottom), width=x_end - x_start, height=height,
                         facecolor=color, alpha=0.15 if poi['isCovered'] else 0.4,
                         edgecolor=color if not poi['isCovered'] else 'none', linewidth=1, zorder=0)
        ax.add_patch(rect)

def main():
    parser = argparse.ArgumentParser(description="Smart plotter for crypto data.")
    parser.add_argument('symbol', type=str, help="Token name (ex. ETHUSDC)")
    parser.add_argument('mode', type=str, help="Subfolder (live or specific backtest)")
    parser.add_argument("--interval", type=str, default="15m", help="Timeframe (15m default)")
    parser.add_argument("--volume", action="store_true", help="Show volume")
    parser.add_argument("--vector", action="store_true", help="Vector candles")
    parser.add_argument("--ema", action="store_true", help="Show EMA50/200")
    parser.add_argument("--sr", action="store_true", help="Show S&R levels")
    parser.add_argument("--pois", action="store_true", help="Show POI zones")

    args = parser.parse_args()

    # Making path to directory
    base_path = Path("data") / args.symbol / args.mode
    if not base_path.exists():
        print(f"Error: Directory {base_path} doesn't exist!")
        return

    # Try to load main file
    candles_file = base_path / f"{args.interval}.parquet"
    if args.vector:
        # Check for vector file, if --vector passed
        v_file = base_path / f"{args.interval}.vector.parquet"
        if v_file.exists():
            candles_file = v_file
        else:
            print(f"Warning: Vector candles file {v_file.name} not found. Using normal mode instead!")

    if not candles_file.exists():
        print(f"Error: Main file {candles_file} not found!")
        return

    # Loading data
    df = pd.read_parquet(candles_file)
    df.set_index(pd.to_datetime(df["timestamp"], utc=True), inplace=True)

    add_plots = []
    if args.ema:
        add_emas(df, add_plots)
    if args.vector and 'va' in df.columns:
        add_vector_candles(df, add_plots)

    mpf_params = dict(
        type="candle", style="nightclouds", volume=args.volume,
        addplot=add_plots, title=f"{args.symbol} {args.mode} ({args.interval})",
        ylabel="Price", tight_layout=True, returnfig=True, show_nontrading=True
    )
    # S&R (2h.sr.parquet)
    if args.sr:
        sr_file = base_path / "2h.sr.parquet"
        if sr_file.exists():
            sr_df = pd.read_parquet(sr_file)
            sr_df["timestamp"] = pd.to_datetime(sr_df["timestamp"], utc=True)
            add_sr(sr_df, df, mpf_params)
        else:
            print(f"Warning: SR file {sr_file.name} not found!")

    fig, axlist = mpf.plot(df, **mpf_params)

    # POIs
    if args.pois:
        pois_file = base_path / f"{args.interval}.pois.parquet"
        if pois_file.exists():
            poi_df = pd.read_parquet(pois_file)
            poi_df['timestamp'] = pd.to_datetime(poi_df['timestamp'], utc=True)
            if 'covered_timestamp' in poi_df.columns:
                poi_df['covered_timestamp'] = pd.to_datetime(poi_df['covered_timestamp'], utc=True)
            draw_poi_rectangles(axlist[0], df, poi_df)
        else:
            print(f"Waring: POI file {pois_file.name} not found.")

    plt.show()

if __name__ == "__main__":
    main()