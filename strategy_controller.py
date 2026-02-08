import pandas as pd
from typing import Dict, Any

class StrategyController:
    def __init__(self, df: pd.DataFrame, pois_df: pd.DataFrame, threshold_pct: float = 0.0002) -> None:
        self.df = df
        self.raw_pois = pois_df
        self.threshold_pct = threshold_pct

    def get_dynamic_active_pois(self) -> pd.DataFrame:
        active = []
        for _, poi in self.raw_pois.iterrows():
            after_poi = self.df[self.df.index > poi['timestamp']]
            if after_poi.empty:
                active.append(poi)
                continue
            is_covered = False
            if poi['type'] == 'GREEN':
                if (after_poi['low'] <= poi['zone_bottom'] * (1 + self.threshold_pct)).any(): 
                    is_covered = True
            else:
                if (after_poi['high'] >= poi['zone_top'] * (1 - self.threshold_pct)).any(): 
                    is_covered = True
            if not is_covered: 
                active.append(poi)
        return pd.DataFrame(active)

    def run(self, min_rr: float = 1.5) -> Dict[str, Any]:
        if len(self.df) < 2: 
            return {"status": "SKIP"}
        
        # id=1: Prev candle, 2: Current candle
        prev = self.df.iloc[-2]  
        curr = self.df.iloc[-1]  
        
        active_pois = self.get_dynamic_active_pois()
        if active_pois.empty:
            return {"status": "CANDIDATE", "msg": "No open POI zones."}

        ema50 = curr['ema50']
        current_price = curr['close']
        is_prev_bull = prev['close'] > prev['open']
        is_curr_bull = curr['close'] > curr['open']

        # --- REVERSAL ---
        # Looking for reversal only if both candles are vector ones (va>0)
        if prev.get('va', 0) > 0 and curr.get('va', 0) > 0:

            # id 2 must be 30% bigger than id 1
            is_reversal_vol = curr['volume'] >= (prev['volume'] * 1.3)
            
            # 1. Bearish Reversal (SHORT): Green (id1) -> (bigger) Red (id2)
            if is_prev_bull and not is_curr_bull and is_reversal_vol:
                # Must be above ema
                if current_price > ema50:
                    target = active_pois[active_pois['type'] == 'GREEN'].sort_values('timestamp', ascending=False).head(1)
                    if not target.empty:
                        entry = current_price
                        tp = target.iloc[0]['zone_bottom'] # Tp: Active green zone below
                        sl = prev['close']  # SL: Green candle close (id=1)
                        
                        risk = abs(sl - entry)
                        reward = abs(entry - tp)
                        rr = reward / risk if risk > 0 else 0
                        if rr >= min_rr:
                            return {
                                "status": "TRADE", 
                                "type": "REVERSAL", 
                                "direction": "SHORT", 
                                "entry": entry, 
                                "tp": tp, 
                                "sl": sl, 
                                "rr": rr,
                                "start_ts": curr.name
                            }

            # 2. Bullish Reversal (LONG): Red vector (id1) -> (Bigger) Green vector (id2)
            if not is_prev_bull and is_curr_bull and is_reversal_vol:
                # Must be under Ema
                if current_price < ema50:
                    target = active_pois[active_pois['type'] == 'RED'].sort_values('timestamp', ascending=False).head(1)
                    if not target.empty:
                        entry = current_price 
                        tp = target.iloc[0]['zone_bottom'] # TP: Active red zone above
                        sl = curr['open']  # SL: Green candle open (id=2)
                        
                        risk = abs(entry - sl)
                        reward = abs(tp - entry)
                        rr = reward / risk if risk > 0 else 0
                        if rr >= min_rr:
                            return {
                                "status": "TRADE", 
                                "type": "REVERSAL", 
                                "direction": "LONG", 
                                "entry": entry, 
                                "tp": tp, 
                                "sl": sl, 
                                "rr": rr,
                                "start_ts": curr.name
                            }

        # --- TREND FOLLOW ---
        # Only if the previous candle is vector one (va>0)
        if prev.get('va', 0) > 0:
            # TREND SHORT (Bearish vector -> Continuation)
            if not is_prev_bull:
                target = active_pois[active_pois['type'] == 'GREEN'].sort_values('timestamp', ascending=False).head(1)
                if not target.empty and current_price < ema50 and current_price < prev['close']:
                    entry, tp = current_price, target.iloc[0]['zone_bottom']
                    sl = self.df.iloc[-15:]['high'].max() # SR above local structure
                    rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0
                    if rr >= min_rr:
                        return {"status": "TRADE", "type": "TREND", "direction": "SHORT", "entry": entry, "tp": tp, "sl": sl, "rr": rr, "start_ts": curr.name}

            # TREND LONG (Bullish vector -> Continuation)
            elif is_prev_bull:
                target = active_pois[active_pois['type'] == 'RED'].sort_values('timestamp', ascending=False).head(1)
                if not target.empty and current_price > ema50 and current_price > prev['close']:
                    entry, tp = current_price, target.iloc[0]['zone_bottom']
                    sl = self.df.iloc[-15:]['low'].min() # SR under local structure
                    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
                    if rr >= min_rr:
                        return {"status": "TRADE", "type": "TREND", "direction": "LONG", "entry": entry, "tp": tp, "sl": sl, "rr": rr, "start_ts": curr.name}

        return {"status": "SKIP"}