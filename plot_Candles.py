import argparse
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from indicators import ema


def plot_candles(parquet_path, title=None, volume=True, plot_ema=False):
    df = pd.read_parquet(parquet_path)

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df["timestamp"], utc=True)

    df = df[["open", "high", "low", "close", "volume"]].copy()

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

    mpf.plot(
        df,
        type="candle",
        style=style,
        volume=volume,
        addplot=add_plots,
        title=(title or parquet_path),
        ylabel="Price",
        ylabel_lower="Volume",
        tight_layout=True,
    )
    plt.show()


def plot_vector_candles(parquet_path, title=None, volume=True, plot_ema=False):
    df = pd.read_parquet(parquet_path)

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df["timestamp"], utc=True)

    if "isVector" not in df.columns:
        raise ValueError("File missing 'isVector' column.")

    df = df[["open", "high", "low", "close", "volume", "isVector"]].copy()

    # Vector markers (triangle above candle)
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

    mpf.plot(
        df,
        type="candle",
        style=style,
        volume=volume,
        addplot=add_plots,
        title=(title or parquet_path),
        ylabel="Price",
        ylabel_lower="Volume",
        tight_layout=True,
    )
    plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("parquet_path", type=str, help="Path to candles parquet file.")
    parser.add_argument("--title", type=str, help="Chart title.")
    parser.add_argument("--volume", action="store_true", help="Show volume.")
    parser.add_argument("--vector", action="store_true", help="Show vector candle markers.")
    parser.add_argument("--ema", action="store_true", help="Plot EMA50 and EMA200.")
    args = parser.parse_args()

    if args.vector:
        plot_vector_candles(args.parquet_path, args.title, args.volume, args.ema)
    else:
        plot_candles(args.parquet_path, args.title, args.volume, args.ema)


if __name__ == "__main__":
    main()
