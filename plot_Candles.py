import argparse
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from indicators import ema


# -------------------------------------------------
# POI HELPERS (SUPPORT / RESISTANCE)
# -------------------------------------------------
def load_pois(poi_paths):
    if not poi_paths:
        return None

    dfs = []
    for p in poi_paths:
        try:
            dfs.append(pd.read_parquet(p))
        except Exception as e:
            print(f"[WARN] Failed to load POI file {p}: {e}")

    if not dfs:
        return None

    return pd.concat(dfs, ignore_index=True)


def draw_sr_levels(ax, df, poi_df):
    if poi_df is None or poi_df.empty:
        return

    last_price = df["close"].iloc[-1]

    for _, poi in poi_df.iterrows():
        price = float(poi["price"])
        level_type = poi.get("type", "")
        timeframe = poi.get("timeframe", "1h")
        touches = int(poi.get("touches", 1))

        # Color by support / resistance
        if level_type == "support":
            color = "#2ecc71"  # green
        else:
            color = "#e74c3c"  # red

        # Line thickness by timeframe + touches
        base_width = 1.2 if timeframe == "1h" else 2.0
        width = base_width + min(touches - 1, 3) * 0.4

        # Alpha by timeframe
        alpha = 0.5 if timeframe == "1h" else 0.75

        ax.axhline(
            y=price,
            color=color,
            linewidth=width,
            alpha=alpha,
            linestyle="-",
        )


# -------------------------------------------------
# NORMAL CANDLE PLOT
# -------------------------------------------------
def plot_candles(parquet_path, title=None, volume=True, plot_ema=False, poi_paths=None):
    df = pd.read_parquet(parquet_path)

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df["timestamp"], utc=True)

    df = df[["open", "high", "low", "close", "volume"]]

    add_plots = []

    if plot_ema:
        ema_50 = ema(df["close"], 50)
        ema_200 = ema(df["close"], 200)

        add_plots += [
            mpf.make_addplot(ema_50, color="blue", width=1),
            mpf.make_addplot(ema_200, color="red", width=1),
        ]

    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mpf.make_marketcolors(
            up="#26a69a",
            down="#ef5350",
            wick="white",
            edge="inherit",
        ),
    )

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        volume=volume,
        addplot=add_plots,
        title=title or parquet_path,
        ylabel="Price",
        ylabel_lower="Volume",
        tight_layout=True,
        returnfig=True,
    )

    ax = axes[0]

    poi_df = load_pois(poi_paths)
    draw_sr_levels(ax, df, poi_df)

    plt.show()


# -------------------------------------------------
# VECTOR CANDLE PLOT
# -------------------------------------------------
def plot_vector_candles(parquet_path, title=None, volume=True, plot_ema=False, poi_paths=None):
    df = pd.read_parquet(parquet_path)

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df["timestamp"], utc=True)

    if "isVector" not in df.columns:
        raise ValueError("File missing 'isVector' column.")

    df = df[["open", "high", "low", "close", "volume", "isVector"]]

    marker_y = df["high"] * 1.001
    vector_y = marker_y.where(df["isVector"] == 1)

    add_plots = [
        mpf.make_addplot(
            vector_y,
            type="scatter",
            marker="v",
            markersize=80,
            color="yellow",
        )
    ]

    if plot_ema:
        ema_50 = ema(df["close"], 50)
        ema_200 = ema(df["close"], 200)

        add_plots += [
            mpf.make_addplot(ema_50, color="blue", width=1),
            mpf.make_addplot(ema_200, color="red", width=1),
        ]

    style = mpf.make_mpf_style(base_mpf_style="nightclouds")

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        volume=volume,
        addplot=add_plots,
        title=title or parquet_path,
        ylabel="Price",
        ylabel_lower="Volume",
        tight_layout=True,
        returnfig=True,
    )

    ax = axes[0]

    poi_df = load_pois(poi_paths)
    draw_sr_levels(ax, df, poi_df)

    plt.show()


# -------------------------------------------------
# CLI
# -------------------------------------------------
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("parquet_path", type=str, help="Path to candles parquet file.")
    parser.add_argument("--title", type=str, help="Chart title.")
    parser.add_argument("--volume", action="store_true", help="Show volume.")
    parser.add_argument("--vector", action="store_true", help="Show vector candles.")
    parser.add_argument("--ema", action="store_true", help="Plot EMAs.")
    parser.add_argument(
        "--poi",
        nargs="*",
        help="Paths to SR parquet files (e.g. 1h.sr.parquet 2h.sr.parquet)",
    )

    args = parser.parse_args()

    if args.vector:
        plot_vector_candles(
            args.parquet_path,
            args.title,
            args.volume,
            args.ema,
            args.poi,
        )
    else:
        plot_candles(
            args.parquet_path,
            args.title,
            args.volume,
            args.ema,
            args.poi,
        )


if __name__ == "__main__":
    main()
