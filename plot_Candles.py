import argparse
import pandas as pd
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from indicators import ema
from pathlib import Path

def choose_style(vector_enabled, mpf_module):
    if vector_enabled:
        return mpf_module.make_mpf_style(base_mpf_style="nightclouds")
    
    # Default
    return mpf_module.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mpf_module.make_marketcolors(
            up="#26a69a",
            down="#ef5350",
            wick="white",
            edge="inherit",
        )
    )

def load_and_prepare_data(file_path):
    if not file_path.exists():
        return None
    
    df = pd.read_parquet(file_path)
    if df.empty:
        return None
        
    # Convert to DatetimeIndex (handles 'timestamp' as column or index)
    if 'timestamp' in df.columns:
        df.index = pd.to_datetime(df['timestamp'], utc=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
        
    df.sort_index(inplace=True)
    return df

def get_indicators(df, args):
    add_plots = []
    
    if args.ema:
        e50 = ema(df["close"], 50)
        e200 = ema(df["close"], 200)
        add_plots += [
            mpf.make_addplot(e50, color="blue", width=1),
            mpf.make_addplot(e200, color="red", width=1),
        ]
        
    if args.vector and 'va' in df.columns:
        def create_marker(mask, color, size):
            series = pd.Series(np.nan, index=df.index)
            series.loc[mask] = df.loc[mask, 'high'] * 1.002
            return mpf.make_addplot(series, type='scatter', marker='v', color=color, markersize=size)

        # Different vector cadnles filter
        climax_bull = (df['va'] == 1) & (df['close'] > df['open'])
        climax_bear = (df['va'] == 1) & (df['close'] < df['open'])
        rising_bull = (df['va'] == 2) & (df['close'] > df['open'])
        rising_bear = (df['va'] == 2) & (df['close'] < df['open'])

        if climax_bull.any(): add_plots.append(create_marker(climax_bull, 'lime', 100))
        if climax_bear.any(): add_plots.append(create_marker(climax_bear, 'red', 100))
        if rising_bull.any(): add_plots.append(create_marker(rising_bull, 'blue', 60))
        if rising_bear.any(): add_plots.append(create_marker(rising_bear, 'fuchsia', 60))
        
    return add_plots

def setup_sr_lines(sr_file, df, mpf_params):
    if not sr_file.exists():
        print(f"S&R file not found: {sr_file.name}")
        return

    sr_df = pd.read_parquet(sr_file)
    sr_df["timestamp"] = pd.to_datetime(sr_df["timestamp"], utc=True)
    last_ts = df.index[-1]
    
    lines, colors = [], []
    for _, row in sr_df.iterrows():
        if row["timestamp"] > last_ts: continue
        lines.append([(row["timestamp"], row["price"]), (last_ts, row["price"])])
        colors.append("#00ff00" if row["type"].lower() == "support" else "#ff0000")
    
    if lines:
        mpf_params['alines'] = dict(alines=lines, colors=colors, linewidths=1.2, alpha=0.7)

def overlay_pois(ax, df, pois_file):
    if not pois_file.exists():
        print(f"POI file not found: {pois_file.name}")
        return

    poi_df = pd.read_parquet(pois_file)
    poi_df['timestamp'] = pd.to_datetime(poi_df['timestamp'], utc=True)
    last_ts_num = mdates.date2num(df.index[-1])

    for _, poi in poi_df.iterrows():
        x_start = mdates.date2num(poi['timestamp'])
        x_end = mdates.date2num(pd.to_datetime(poi['covered_timestamp'], utc=True)) if poi.get('isCovered') and pd.notna(poi.get('covered_timestamp')) else last_ts_num
        y_bot, height = poi['zone_bottom'], poi['zone_top'] - poi['zone_bottom']
        color = 'green' if poi['type'] == 'GREEN' else 'red'
        
        rect = Rectangle((x_start, y_bot), width=x_end - x_start, height=height,
                         facecolor=color, alpha=0.2, edgecolor='none', zorder=0)
        ax.add_patch(rect)

def main():
    parser = argparse.ArgumentParser(description="Modular Crypto Plotter")
    parser.add_argument('symbol', type=str, help="Token name")
    parser.add_argument('mode', type=str, help="live or backtest name")
    parser.add_argument("--interval", type=str, default="15m")
    parser.add_argument("--volume", action="store_true")
    parser.add_argument("--vector", action="store_true")
    parser.add_argument("--ema", action="store_true")
    parser.add_argument("--sr", action="store_true")
    parser.add_argument("--pois", action="store_true")

    args = parser.parse_args()

    # Path to folder
    base_dir = Path("data") / args.symbol / args.mode
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return

    # Choosing main file
    target_path = base_dir / f"{args.interval}.parquet"
    if args.vector:
        v_path = base_dir / f"{args.interval}.vector.parquet"
        if v_path.exists(): target_path = v_path

    # Load and check for empty file
    df = load_and_prepare_data(target_path)
    if df is None:
        print(f"File {target_path.name} is missing or empty.")
        return

    # Params prep
    add_plots = get_indicators(df, args)
    
    mpf_params = dict(
        type="candle",
        style=choose_style(args.vector or args.ema, mpf),
        volume=args.volume,
        title=f"{args.symbol} {args.mode} ({args.interval})",
        ylabel="Price",
        tight_layout=True,
        returnfig=True,
        show_nontrading=True
    )

    if add_plots:
        mpf_params['addplot'] = add_plots

    # setup for SR
    if args.sr:
        setup_sr_lines(base_dir / "2h.sr.parquet", df, mpf_params)

    fig, axlist = mpf.plot(df, **mpf_params)

    if args.pois:
        overlay_pois(axlist[0], df, base_dir / f"{args.interval}.pois.parquet")

    plt.show()

if __name__ == "__main__":
    main()