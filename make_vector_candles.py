import os
import pandas as pd
import argparse


def calculate_vector_candles(input_file, lookback=10, threshold_volume_mult=2):
    df = pd.read_parquet(input_file)

    if isinstance(df.index, pd.DatetimeIndex):
        # index already has timestamps → also expose as column for consistency
        df['timestamp'] = df.index

    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df.index = df['timestamp']

    elif 'open_time' in df.columns:
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
        df.index = df['timestamp']

    else:
        raise ValueError("No timestamp index, timestamp column, or open_time column found in input.")
    
    # Ensure we keep all original columns
    if 'isVector' not in df.columns:
        df['isVector'] = 0

    # Calculate for each candle starting from lookback
    for i in range(lookback, len(df)):
        recent = df.iloc[i-lookback:i]
        av_volume = recent['volume'].mean()

        # current candle
        candle = df.iloc[i]
        candle_range = candle['high'] - candle['low']
        value2 = candle['volume'] * candle_range

        # highest value2 in lookback
        highest_value2 = (recent['volume'] * (recent['high'] - recent['low'])).max()

        # determine if vector candle
        if candle['volume'] >= av_volume * threshold_volume_mult or value2 >= highest_value2:
            df.at[df.index[i], 'isVector'] = 1

    print(f"Total vector candles detected: {df['isVector'].sum()}")

    output_dir = os.path.dirname(input_file)  # Get the directory from input_file path
    output_file = os.path.join(output_dir, os.path.basename(input_file).replace('.parquet', '.vector.parquet'))

    # Save to output parquet in the same directory as input file
    df.to_parquet(output_file, index=False)
    print(f"Output saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Detect vector candles from raw OHLC data")
    parser.add_argument('input_file', type=str, help='Path to input raw parquet file')
    parser.add_argument('--lookback', type=int, default=10, help='Lookback candles for average/highest calculation')
    parser.add_argument('--threshold_volume_mult', type=float, default=2.0, help='Volume multiplier for vector candle')
    args = parser.parse_args()

    calculate_vector_candles(args.input_file, args.lookback, args.threshold_volume_mult)
    

if __name__ == '__main__':
    main()
