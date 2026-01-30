import pandas as pd
from collections import deque

class POIFinder:
    def __init__(self, volume_std_threshold=2.0, min_dist=15):
        self.volume_std_threshold = volume_std_threshold
        self.min_dist = min_dist
        self.poi_stack = deque()  # LIFO queue

    def update_pois(self, df):
        """
        Scans DF for new big candles and cleans 'consumed' ones
        """
        # Calculate step for 'big' vector candle
        # TODO: other method
        avg_vol = df['volume'].mean()
        std_vol = df['volume'].std()
        threshold = avg_vol + (self.volume_std_threshold * std_vol)

        significant_vectors = df[
            (df['isVector'] == 1) & 
            (df['volume'] > threshold)
        ]

        self.poi_stack.clear()
        
        for idx, row in significant_vectors.iterrows():
            # TODO: Логика за групиране на последователни вектори в една POI зона
            
            poi = {
                "timestamp": idx,
                "price_high": row['high'],
                "price_low": row['low'],
                "type": "RED" if row['close'] < row['open'] else "GREEN",
                "volume": row['volume']
            }
            self.poi_stack.append(poi)

    def get_active_target(self, current_time):
        for poi in reversed(self.poi_stack):
            # Distance check (in candles or time)
            dist = (current_time - poi['timestamp']).total_seconds() / 60 / 15 # 15min candels
            
            if dist >= self.min_dist:
                return poi
        return None

    def is_covered(self, poi, current_price):
        if current_price <= poi['price_high'] and current_price >= poi['price_low']:
            return True
        return False