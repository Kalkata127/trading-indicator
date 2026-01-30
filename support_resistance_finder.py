import pandas as pd
import pathlib
import argparse
from indicators import ema
from typing import List, Tuple, Optional

def is_confirmed_momentum(
    window: pd.DataFrame, 
    vol_ema: pd.Series, 
    trend: str = 'up'
) -> Tuple[bool, Optional[float]]:
    """
    Checks 2 following candles with big volume
    Returns (confirmed, price).
    """
    for j in range(len(window) - 1):
        c1, c2 = window.iloc[j], window.iloc[j+1]
        v_ema1, v_ema2 = vol_ema.iloc[j], vol_ema.iloc[j+1]
        
        if trend == 'up':
            if c1['close'] > c1['open'] and c2['close'] > c2['open'] and c1['volume'] > v_ema1 and c2['volume'] > v_ema2:
                return True, float(c2['high'])
        else:
            if c1['close'] < c1['open'] and c2['close'] < c2['open'] and c1['volume'] > v_ema1 and c2['volume'] > v_ema2:
                return True, float(c2['low'])
                
    return False, None

class SRFinder:
    def __init__(self, threshold: float = 0.005):
        self._threshold = threshold

    def process_file(self, input_path: str, output_dir: str) -> None:
        path = pathlib.Path(input_path)
        if not path.exists():
            print(f"Error: File {input_path} does not exist.")
            return

        df = pd.read_parquet(input_path)
        
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={df.index.name: 'timestamp', 'index': 'timestamp'})
        
        # If missing we create it
        if 'timestamp' not in df.columns:
            df['timestamp'] = df.index

        #Right format
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        levels_data = self.identify_sr_levels(df)
        
        # Making result DataFrame
        res_df = pd.DataFrame(levels_data, columns=['type', 'price', 'timestamp'])
        
        out_path = pathlib.Path(output_dir) / f"{path.stem}.sr.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        res_df.to_parquet(out_path)
        print(f"Successfully saved {len(res_df)} levels to {out_path}")

    def identify_sr_levels(self, df: pd.DataFrame, k: int = 2, vol_period: int = 20) -> List[dict]:
        vol_ema_series = ema(df['volume'], vol_period)
        found_levels = []

        for i in range(k, len(df) - k):
            current_low = df['low'].iloc[i]
            current_high = df['high'].iloc[i]
            current_time = df['timestamp'].iloc[i]
            
            # Support Identification
            if current_low == df['low'].iloc[i-k:i+k+1].min():
                prev_window = df.iloc[max(0, i-5):i]
                prev_vol_ema = vol_ema_series.iloc[max(0, i-5):i]
                
                confirmed, conf_price = is_confirmed_momentum(prev_window, prev_vol_ema, trend='down')
                if confirmed:
                    price = (current_low + conf_price) / 2
                    found_levels.append({'type': 'support', 'price': price, 'timestamp': current_time})

            # Resistance Identification
            elif current_high == df['high'].iloc[i-k:i+k+1].max():
                prev_window = df.iloc[max(0, i-5):i]
                prev_vol_ema = vol_ema_series.iloc[max(0, i-5):i]
                
                confirmed, conf_price = is_confirmed_momentum(prev_window, prev_vol_ema, trend='up')
                if confirmed:
                    price = (current_high + conf_price) / 2
                    found_levels.append({'type': 'resistance', 'price': price, 'timestamp': current_time})

        return self.merge_levels(found_levels)

    def merge_levels(self, levels: List[dict]) -> List[dict]:
        if not levels:
            return []
        
        # Sort by price for easier merging
        levels.sort(key=lambda x: x['price'])
        merged = []
        
        curr = levels[0]
        for i in range(1, len(levels)):
            nxt = levels[i]
            
            if nxt['type'] == curr['type'] and (nxt['price'] - curr['price']) / curr['price'] < self._threshold:
                curr['price'] = (curr['price'] + nxt['price']) / 2
            else:
                merged.append(curr)
                curr = nxt
        
        merged.append(curr)
        return merged

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Identify Support and Resistance levels from OHLCV data.")
    parser.add_argument("--file", help="Path to the .parquet file")
    parser.add_argument("--out", default="data/", help="Output directory")
    parser.add_argument("--threshold", type=float, default=0.005, help="Merging threshold (default 0.5%)")
    args = parser.parse_args()

    detector = SRFinder(threshold=args.threshold)
    detector.process_file(args.file, args.out)