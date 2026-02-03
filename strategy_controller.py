import pandas as pd
import numpy as np

class StrategyController:
    def __init__(self, df):
        self.df = df
        self.poi_stack = []
        self.sr_levels = None

    def load_indicators(self):
        if 'va' not in self.df.columns or 'ema50' not in self.df.columns:
            pass

        temp_stack = []
        for i in range(len(self.df)):
            row = self.df.iloc[i]
            ts = self.df.index[i]

            if row['va'] == 1:
                new_poi = {
                    "timestamp": ts,
                    "high": row['high'],
                    "low": row['low'],
                    "type": "BULL" if row['close'] > row['open'] else "BEAR",
                    "active": True
                }
                
                if temp_stack and (ts - temp_stack[-1]['timestamp']).total_seconds() <= 900:
                    temp_stack[-1] = new_poi
                else:
                    temp_stack.append(new_poi)

            for poi in temp_stack:
                if not poi['active']: continue
                
                if poi['type'] == "BULL" and row['low'] <= poi['high']:
                    poi['active'] = False
                elif poi['type'] == "BEAR" and row['high'] >= poi['low']:
                    poi['active'] = False

        self.poi_stack = temp_stack

    def find_nearest_resistance(self, current_time, direction="SHORT"):

        lookback = self.df.tail(20)
        lookback = 35
        if direction == "SHORT":
            return lookback['high'].max()
        else:
            return lookback['low'].min()

    def run(self, min_dist=15, min_rr=1.5, **kwargs):

        if len(self.df) < 2:
            return {"status": "NO_TRADE", "reason": "Insufficient data"}

        last_candle = self.df.iloc[-1]
        current_time = self.df.index[-1]

        target_poi = next((p for p in self.poi_stack if p['active'] and p['type'] == "BULL"), None)

        if not target_poi:
            return {"status": "NO_TRADE", "reason": "No active POI magnet found"}

        dist_candles = (current_time - target_poi['timestamp']).total_seconds() / 900
        if dist_candles < min_dist:
            return {"status": "NO_TRADE", "reason": f"Too close to POI ({int(dist_candles)} candles)"}

        is_reversal = (last_candle['va'] == 1 and 
                       last_candle['close'] < last_candle['open'] and 
                       last_candle['close'] < last_candle['ema50'])


        if is_reversal:
            entry_price = last_candle['close']

            tp_price = target_poi['zone_top'] 
            
            sl_price = self.find_nearest_resistance(current_time, "SHORT")
            
            if sl_price <= entry_price:
                sl_price = entry_price * 1.005 

            risk = sl_price - entry_price
            reward = entry_price - tp_price
            rr = round(reward / risk, 2) if risk > 0 else 0

            if rr < min_rr:
                return {"status": "NO_TRADE", "reason": f"RR too low ({rr})"}

            return {
                "status": "TRADE",
                "direction": "SHORT",
                "entry": round(entry_price, 2),
                "take_profit": round(tp_price, 2),
                "stop_loss": round(sl_price, 2),
                "rr": rr,
                "strength": 6,
                "reason": f"Reversal targeting POI from {target_poi['timestamp'].strftime('%Y-%m-%d %H:%M')}"
            }

        return {"status": "NO_TRADE", "reason": "No reversal signal under EMA"}
    