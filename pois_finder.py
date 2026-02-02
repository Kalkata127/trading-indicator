import pandas as pd
from collections import deque

class POIFinder:
    def __init__(self, min_dist=15):
        self.min_dist = min_dist
        self.active_pois = []

    def find_pois(self, df):        
        if 'va' not in df.columns:
            print("[Err] Column 'va' missing. Use first make_vector_candles.py.")
            return None

        sig_indices = df[df['va'] == 1].index
        
        if sig_indices.empty:
            return None

        temp_pois = []
        # Find last vectors from groups
        for i in range(len(sig_indices)):
            current_idx = sig_indices[i]
            is_last = True
            
            if i + 1 < len(sig_indices):
                pos_curr = df.index.get_loc(current_idx)
                pos_next = df.index.get_loc(sig_indices[i+1])
                # If the next Climax is right after the current, that means the current isn't last in group
                if pos_next == pos_curr + 1:
                    is_last = False
            
            if is_last:
                row = df.loc[current_idx]
                temp_pois.append({
                    "timestamp": current_idx,
                    "high": row['high'],
                    "low": row['low'],
                    "type": "RED" if row['close'] < row['open'] else "GREEN",
                    "mitigated": False
                })

        # Mitigation(Price coverage) logic
        final_pois = []
        for poi in temp_pois:
            poi_start_time = poi['timestamp']
            
            # Get data after POI appear, to check if price returned there
            post_poi_data = df[df.index > poi_start_time]
            
            if post_poi_data.empty:
                # If this is the newest candle, its not covered yet
                final_pois.append(poi)
                continue

            if poi['type'] == "RED":
                is_hit = post_poi_data['high'].max() >= poi['low']
            else:
                is_hit = post_poi_data['low'].min() <= poi['high']
            
            if not is_hit:
                final_pois.append(poi)

        if not final_pois:
            return None

        self.active_pois = final_pois
        return self.active_pois