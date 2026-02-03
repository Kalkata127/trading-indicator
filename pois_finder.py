import pandas as pd
import numpy as np
import argparse
import os

class POIFinder:
    def __init__(self, threshold_pct=0.0005):
        self.threshold_pct = threshold_pct

    def process(self, input_file):
        df = pd.read_parquet(input_file)
        if not isinstance(df.index, pd.DatetimeIndex):
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df.index = df['timestamp']

        pois = []
        # Taking only climax vectors
        climax_candles = df[df['va'] == 1].copy()
        
        print(f"Working on: {len(climax_candles)} potential zones...")

        for ts, row in climax_candles.iterrows():
            is_bull = row['close'] > row['open']
            top = np.float64(row['high'])
            bottom = np.float64(row['low'])
            poi_type = 'GREEN' if is_bull else 'RED'
            
            is_covered = False
            covered_ts = None
            
            # Check in future (after curr candle)
            future_data = df[df.index > ts]
            
            for f_ts, f_row in future_data.iterrows():
                if is_bull:
                    if f_row['low'] <= bottom * (1 + self.threshold_pct):
                        is_covered = True
                        covered_ts = f_ts
                        break
                else:
                    if f_row['high'] >= top * (1 - self.threshold_pct):
                        is_covered = True
                        covered_ts = f_ts
                        break
            
            pois.append({
                'poi_id': f"{ts.timestamp()}_{poi_type}",
                'timestamp': ts,
                'zone_top': top,
                'zone_bottom': bottom,
                'type': poi_type,
                'isCovered': is_covered,
                'covered_timestamp': covered_ts
            })

        poi_df = pd.DataFrame(pois)
        output_file = input_file.replace('.vector.parquet', '.pois.parquet')
        poi_df.to_parquet(output_file, index=False)
        print(f"Saved {len(poi_df)} zones in: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate POI zones from vector candles.")
    parser.add_argument('input_file', type=str, help="Path to .vector.parquet file")
    parser.add_argument('--threshold', type=float, default=0.0005, help="Mitigation threshold percentage")
    args = parser.parse_args()

    finder = POIFinder(threshold_pct=args.threshold)
    finder.process(args.input_file)

if __name__ == "__main__":
    main()