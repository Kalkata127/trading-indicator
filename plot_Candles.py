import argparse
import pandas as pd
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from indicators import ema
from pathlib import Path
from typing import Optional, List, Dict, Any

def choose_style(vector_enabled: bool, mpf_module: Any) -> Dict[str, Any]:
    if vector_enabled:
        return mpf_module.make_mpf_style(base_mpf_style="nightclouds")
    
    return mpf_module.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mpf_module.make_marketcolors(
            up="#26a69a",   # Teal
            down="#ef5350", # Red
            wick="white",
            edge="inherit",
        )
    )

def load_data(file_path: Path) -> Optional[pd.DataFrame]:
    if not file_path.exists():
        return None
    
    df: pd.DataFrame = pd.read_parquet(file_path)
    if df.empty:
        return None
        
    # Standardize index handling
    if 'timestamp' in df.columns:
        df.index = pd.to_datetime(df['timestamp'], utc=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
        
    df.sort_index(inplace=True)
    return df

def get_indicators(df: pd.DataFrame, args: argparse.Namespace) -> List[Dict[str, Any]]:
    add_plots: List[Dict[str, Any]] = []
    
    if args.ema:
        e50: pd.Series = ema(df["close"], 50)
        e200: pd.Series = ema(df["close"], 200)
        add_plots += [
            mpf.make_addplot(e50, color="blue", width=1),
            mpf.make_addplot(e200, color="red", width=1),
        ]
        
    if args.vector and 'va' in df.columns:
        def create_marker(mask: pd.Series, color: str, size: int) -> Dict[str, Any]:
            series: pd.Series = pd.Series(np.nan, index=df.index)
            series.loc[mask] = df.loc[mask, 'high'] * 1.002
            return mpf.make_addplot(series, type='scatter', marker='v', color=color, markersize=size)

        climax_bull: pd.Series = (df['va'] == 1) & (df['close'] > df['open'])
        climax_bear: pd.Series = (df['va'] == 1) & (df['close'] < df['open'])
        rising_bull: pd.Series = (df['va'] == 2) & (df['close'] > df['open'])
        rising_bear: pd.Series = (df['va'] == 2) & (df['close'] < df['open'])

        if climax_bull.any(): add_plots.append(create_marker(climax_bull, 'lime', 100))
        if climax_bear.any(): add_plots.append(create_marker(climax_bear, 'red', 100))
        if rising_bull.any(): add_plots.append(create_marker(rising_bull, 'blue', 60))
        if rising_bear.any(): add_plots.append(create_marker(rising_bear, 'fuchsia', 60))
        
    return add_plots

def apply_sr_levels(sr_file: Path, df: pd.DataFrame, mpf_params: Dict[str, Any]) -> None:
    if not sr_file.exists():
        print(f"Warning: SR file not found: {sr_file.name}")
        return

    sr_df: pd.DataFrame = pd.read_parquet(sr_file)
    sr_df["timestamp"] = pd.to_datetime(sr_df["timestamp"], utc=True)
    last_ts: pd.Timestamp = df.index[-1]
    
    lines: List[List[tuple]] = []
    colors: List[str] = []
    for _, row in sr_df.iterrows():
        if row["timestamp"] > last_ts: continue
        lines.append([(row["timestamp"], row["price"]), (last_ts, row["price"])])
        colors.append("#00ff00" if row["type"].lower() == "support" else "#ff0000")
    
    if lines:
        mpf_params['alines'] = dict(alines=lines, colors=colors, linewidths=1.2, alpha=0.7)

def apply_pois(ax: plt.Axes, df: pd.DataFrame, pois_file: Path) -> None:
    if not pois_file.exists():
        print(f"Warning: POI file not found: {pois_file.name}")
        return

    poi_df: pd.DataFrame = pd.read_parquet(pois_file)
    poi_df['timestamp'] = pd.to_datetime(poi_df['timestamp'], utc=True)
    last_ts_num: float = mdates.date2num(df.index[-1])

    for _, poi in poi_df.iterrows():
        x_start: float = mdates.date2num(poi['timestamp'])
        # Handle coverage timestamp
        x_end: float = mdates.date2num(pd.to_datetime(poi['covered_timestamp'], utc=True)) if poi.get('isCovered') and pd.notna(poi.get('covered_timestamp')) else last_ts_num
        y_bot: float = poi['zone_bottom']
        height: float = poi['zone_top'] - poi['zone_bottom']
        color: str = 'green' if poi['type'] == 'GREEN' else 'red'
        
        rect = Rectangle((x_start, y_bot), width=x_end - x_start, height=height,
                         facecolor=color, alpha=0.2, edgecolor='none', zorder=0)
        ax.add_patch(rect)

def main() -> None:
    parser = argparse.ArgumentParser(description="Finalized modular plotter for Crypto assets.")
    parser.add_argument('symbol', type=str, help="Trading pair name (e.g., BTCUSDC)")
    parser.add_argument('mode', type=str, help="Folder mode (e.g., live or backtest_period_name)")
    parser.add_argument("--interval", type=str, default="15m", help="Candle timeframe")
    parser.add_argument("--volume", action="store_true", help="Plot volume bars")
    parser.add_argument("--vector", action="store_true", help="Enable vector markers")
    parser.add_argument("--ema", action="store_true", help="Plot EMA lines")
    parser.add_argument("--sr", action="store_true", help="Draw S&R levels")
    parser.add_argument("--pois", action="store_true", help="Draw POI zones")

    args: argparse.Namespace = parser.parse_args()

    # Dynamic path construction
    base_dir: Path = Path("data") / args.symbol / args.mode
    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        return

    # Choose source file: prioritize vector if requested
    target_path: Path = base_dir / f"{args.interval}.parquet"
    if args.vector:
        v_path: Path = base_dir / f"{args.interval}.vector.parquet"
        if v_path.exists(): target_path = v_path

    df: pd.DataFrame = load_data(target_path)
    if df is None:
        print(f"Error: File {target_path.name} is missing or empty.")
        return

    add_plots: List[Dict[str, Any]] = get_indicators(df, args)
    mpf_params: Dict[str, Any] = dict(
        type="candle",
        style=choose_style(args.vector or args.ema, mpf),
        volume=args.volume,
        title=f"{args.symbol} | {args.mode} | {args.interval}",
        ylabel="Price",
        tight_layout=True,
        returnfig=True,
        show_nontrading=True,
        warn_too_much_data=2000
    )

    if add_plots:
        mpf_params['addplot'] = add_plots

    if args.sr:
        apply_sr_levels(base_dir / "2h.sr.parquet", df, mpf_params)

    fig, axlist = mpf.plot(df, **mpf_params)

    if args.pois:
        apply_pois(axlist[0], df, base_dir / f"{args.interval}.pois.parquet")

    plt.show()

if __name__ == "__main__":
    main()