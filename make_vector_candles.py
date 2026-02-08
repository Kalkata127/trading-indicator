import os
import pandas as pd
import argparse
from pathlib import Path

def calculate_vector_candles(input_file: Path, lookback: int = 10) -> None:
    df = pd.read_parquet(input_file)
    
    if 'ignore' in df.columns:
        df = df.drop(columns=['ignore'])

    # Ensure timestamp and make it index
    if 'timestamp' not in df.columns:
        if 'open_time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
        else:
            # if index, output as column
            df = df.reset_index()
            if 'index' in df.columns:
                df = df.rename(columns={'index': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.set_index('timestamp')
    df = df.sort_index()

    # Calculate average val for 10 periods
    df['av'] = df['volume'].rolling(window=lookback, min_periods=1).mean()

    # Calculate climax value (Value2)
    df['value2'] = df['volume'] * (df['high'] - df['low'])

    # Calculate highest Value2 for 10 periods
    df['hivalue2'] = df['value2'].rolling(window=lookback, min_periods=1).max()

    df['va'] = 0
    
    # Rising (va = 2): Volume >= 150% of Average
    df.loc[df['volume'] >= df['av'] * 1.5, 'va'] = 2
    
    # Climax (va = 1): Priority condition
    climax_mask = (df['volume'] >= df['av'] * 2.0) | (df['value2'] >= df['hivalue2'])
    df.loc[climax_mask, 'va'] = 1

    # Cleanup helper colunns and keep 'timestamp'
    # reset_index(), to return timestamp as col before the 
    output_df = df.drop(columns=['av', 'value2', 'hivalue2']).reset_index()
    
    print(f"Detected: {len(df[df['va']==1])} Climax and {len(df[df['va']==2])} Rising candles.")

    output_dir = os.path.dirname(input_file)
    output_file = os.path.join(output_dir, os.path.basename(input_file).replace('.parquet', '.vector.parquet'))

    output_df.to_parquet(output_file, index=False)
    print(f"Output saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="New Vector Candle Detection (va 0,1,2)")
    parser.add_argument('input_file', type=str, help='Path to input parquet file')
    parser.add_argument('--lookback', type=int, default=10)
    args = parser.parse_args()

    calculate_vector_candles(args.input_file, args.lookback)

if __name__ == '__main__':
    main()