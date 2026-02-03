import argparse
import pandas as pd
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from indicators import ema
from pois_finder import POIFinder
import os

def add_emas(df,add_plots):
    ema_50 = ema(df["close"], 50)
    ema_200 = ema(df["close"], 200)
    add_plots += [
        mpf.make_addplot(ema_50, color="blue", width=1),
        mpf.make_addplot(ema_200, color="red", width=1),
    ]

def add_vector_candles(df, add_plots):
    if 'va' not in df.columns:
        return
    
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

    if climax_bull_m.any():
        add_plots.append(create_marker_series(climax_bull_m, 'lime', 100))
    if climax_bear_m.any():
        add_plots.append(create_marker_series(climax_bear_m, 'red', 100))
    if rising_bull_m.any():
        add_plots.append(create_marker_series(rising_bull_m, 'blue', 60))
    if rising_bear_m.any():
        add_plots.append(create_marker_series(rising_bear_m, 'fuchsia', 60))

def add_sr(sr_file_path, df, mpf_params):
    if not os.path.exists(sr_file_path):
        return

    sr_df = pd.read_parquet(sr_file_path)
    if sr_df.empty:
        return

    # Convert timestamp to object
    sr_df["timestamp"] = pd.to_datetime(sr_df["timestamp"], utc=True)
    last_timestamp = df.index[-1]
    
    lines = []
    colors = []
    
    for i in range(len(sr_df)):
        start_time = sr_df["timestamp"].iloc[i]
        price = sr_df["price"].iloc[i]
        sr_type = sr_df["type"].iloc[i].lower()
        
        if start_time > last_timestamp:
            continue
            
        # Add line to the end of plot
        lines.append([(start_time, price), (last_timestamp, price)])
        
        color = "#00ff00" if sr_type == "support" else "#ff0000"
        colors.append(color)

    if lines:
        mpf_params['alines'] = dict(
            alines=lines,
            colors=colors,
            linewidths=1.2,
            alpha=0.7
        )

def draw_poi_rectangles(ax, df, poi_df):
    if poi_df is None or poi_df.empty:
        return

    last_ts_num = mdates.date2num(df.index[-1])
    
    for _, poi in poi_df.iterrows():
        x_start = mdates.date2num(poi['timestamp'])
        
        # Right border
        if poi['isCovered'] and pd.notna(poi['covered_timestamp']):
            x_end = mdates.date2num(poi['covered_timestamp'])
        else:
            x_end = last_ts_num
            
        y_bottom = poi['zone_bottom']
        height = poi['zone_top'] - poi['zone_bottom']
        color = 'green' if poi['type'] == 'GREEN' else 'red'
        
        rect = Rectangle(
            (x_start, y_bottom),
            width=x_end - x_start,
            height=height,
            facecolor=color,
            alpha=0.15 if poi['isCovered'] else 0.4,
            edgecolor=color if not poi['isCovered'] else 'none',
            linewidth=1,
            zorder=0
        )
        ax.add_patch(rect)

def choose_style(vector,mpf_module):
    if vector:
        return mpf_module.make_mpf_style(base_mpf_style="nightclouds")
    
    return mpf_module.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mpf_module.make_marketcolors(
            up="#26a69a",
            down="#ef5350",
            wick="white",
            edge="inherit",
        )
    )

def files_ok(file_path, sr):
    if not os.path.exists(file_path):
        print(f"Error: Candles file not found! {file_path}")
        return 0
    
    if sr and not os.path.exists(sr):
        print(f"Error: SR File not found! {sr}")
    return 1

def plot_candles(
    file_path: str, *, 
    vector: bool = False, 
    volume: bool = False, 
    title: str | None = None, 
    ema: bool = False, 
    sr: str | None = None,
    pois_path: str | None = None
) -> None:
    
    if not files_ok(file_path, sr):
        return
        
    # Load and prep data
    df = pd.read_parquet(file_path)
    df.set_index(pd.to_datetime(df["timestamp"], utc=True), inplace=True)

    needed_cols = ["open", "high", "low", "close", "volume"]
    if "va" in df.columns:
        needed_cols.append("va")
    df = df[needed_cols].copy()

    add_plots = []
    if ema:
        add_emas(df, add_plots)

    if vector:
        add_vector_candles(df, add_plots)

    style = choose_style(vector, mpf)
    
    mpf_arguments = dict(
        type="candle",
        style=style,
        volume=volume,
        addplot=add_plots,
        title=(title or os.path.basename(file_path)),
        ylabel="Price",
        tight_layout=True,
        returnfig=True,      
        show_nontrading=True 
    )

    if sr:
        add_sr(sr, df, mpf_arguments)

    # Initial drawing
    fig, axlist = mpf.plot(df, **mpf_arguments)

    if vector and pois_path:
        if os.path.exists(pois_path):
            poi_df = pd.read_parquet(pois_path)
            # Ensure right data format
            poi_df['timestamp'] = pd.to_datetime(poi_df['timestamp'], utc=True)
            if 'covered_timestamp' in poi_df.columns:
                poi_df['covered_timestamp'] = pd.to_datetime(poi_df['covered_timestamp'], utc=True)
            
            draw_poi_rectangles(axlist[0], df, poi_df)
        else:
            print(f"Warning: POI file not found at {pois_path}")

    plt.show()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True, help="Path to candles file.")      
    parser.add_argument("--title", type=str, help="Chart title.")
    parser.add_argument("--volume", action="store_true", help="Show volume.")
    parser.add_argument("--vector", action="store_true", help="Enable vector analysis.")
    parser.add_argument("--ema", action="store_true", help="Plot EMA50 and EMA200.")
    parser.add_argument("--sr", type=str, help="Path to SR parquet file.")   
    parser.add_argument("--pois", type=str, help="Path to .pois.parquet file.") # НОВ АРГУМЕНТ

    args = parser.parse_args()

    plot_candles(
        file_path=args.file, 
        vector=args.vector, 
        volume=args.volume, 
        title=args.title, 
        ema=args.ema, 
        sr=args.sr,
        pois_path=args.pois
    )

if __name__ == "__main__":
    main()