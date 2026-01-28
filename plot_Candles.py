import argparse
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from indicators import ema
import os

def add_emas(df,add_plots):
    ema_50 = ema(df["close"], 50)
    ema_200 = ema(df["close"], 200)
    add_plots += [
        mpf.make_addplot(ema_50, color="blue", width=1),
        mpf.make_addplot(ema_200, color="red", width=1),
    ]

def add_vector_candles(df,add_plots):
    marker_y = df["high"] * 1.001
    vector_y = marker_y.where(df["isVector"] == 1)
    if vector_y.count() > 0:
        add_plots.append(mpf.make_addplot(vector_y, type = "scatter", marker = "v", markersize = 80, color = "yellow"))

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

def plot_candles(
    file_path: str,*,vector: bool = False,volume: bool = False, title: str | None = None, ema: bool = False, 
    sr: str | None = None) -> None:

    if not os.path.exists(file_path):
        print("Error: Candles file not found!")
        return
    if sr and not os.path.exists(sr):
        print(f"Error: SR File not found!")

    df = pd.read_parquet(file_path)
    df.set_index(pd.to_datetime(df["timestamp"], utc=True), inplace=True) #save for mplfinance

    if vector and "isVector" in df.columns:
        df = df[["open", "high", "low", "close", "volume", "isVector"]].copy()
    else:
        df = df[["open", "high", "low", "close", "volume"]].copy()

    add_plots = []
    if ema:
        add_emas(df,add_plots)

    if vector:
        add_vector_candles(df, add_plots)
    

    style = choose_style(vector, mpf)

    mpf_arguments = dict(
        type="candle",
        style=style,
        volume=volume,
        addplot=add_plots,
        title=(title or file_path),
        ylabel="Price",
        ylabel_lower="Volume",
        tight_layout=True,
    )

    if sr:
        add_sr(sr, df, mpf_arguments)

    mpf.plot(df, **mpf_arguments) #unpacking dictionary
    plt.show()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True, help="Path to candles file.")      
    parser.add_argument("--title", type=str, help="Chart title.")
    parser.add_argument("--volume", action="store_true", help="Show volume.")
    parser.add_argument("--vector", action="store_true", help="Show vector candle markers.")
    parser.add_argument("--ema", action="store_true", help="Plot EMA50 and EMA200.")
    parser.add_argument("--sr", type=str, help="Path to SR parquet file")   

    import sys
    print(f"--- DEBUG: sys.argv е: {sys.argv} ---")
    args = parser.parse_args()

    plot_candles(
            file_path=args.file, 
            vector=args.vector, 
            volume=args.volume, 
            title=args.title, 
            ema=args.ema, 
            sr=args.sr
        ) #pass as keyword args

if __name__ == "__main__":
    main()