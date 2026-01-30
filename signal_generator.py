import pandas as pd
import numpy as np
from indicators import ema

class MMSignalStrategy:
    def __init__(self, wick_threshold=0.25):
        self.wick_threshold = wick_threshold 

    def calculate_indicators(self, df):
        df = df.copy()
        df['ema50'] = ema(df['close'], 50)
        df['ema200'] = ema(df['close'], 200)
        
        # Calculating filters
        df['body_size'] = (df['close'] - df['open']).abs()
        df['total_range'] = df['high'] - df['low']
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        
        return df

    def check_signal(self, df):
        """Анализира последните две свещи за сигнал."""
        if len(df) < 2:
            return {"action": "WAIT", "strength": 0, "reason": "Insufficient data"}

        # Last two closed candles (T-1 and T)
        t_minus_1 = df.iloc[-2]
        t = df.iloc[-1]

        # Double Vector
        is_bullish_sequence = (t_minus_1['isVector'] == 1 and t['isVector'] == 1 and 
                               t_minus_1['close'] > t_minus_1['open'] and t['close'] > t['open'])
        
        is_bearish_sequence = (t_minus_1['isVector'] == 1 and t['isVector'] == 1 and 
                               t_minus_1['close'] < t_minus_1['open'] and t['close'] < t['open'])

        if not (is_bullish_sequence or is_bearish_sequence):
            return {"action": "NO_TRADE", "strength": 0, "reason": "No double vector pattern"}

        # Wick Filter
        # Does the second candle have wick at the opposite direction
        if is_bullish_sequence:
            wick_ratio = t['upper_wick'] / (t['total_range'] + 1e-9)
            if wick_ratio > self.wick_threshold:
                return {"action": "NO_TRADE", "strength": 0, "reason": "Bullish vector has large upper wick"}
        
        if is_bearish_sequence:
            wick_ratio = t['lower_wick'] / (t['total_range'] + 1e-9)
            if wick_ratio > self.wick_threshold:
                return {"action": "NO_TRADE", "strength": 0, "reason": "Bearish vector has large lower wick"}

        strength = 3
        action = "BUY" if is_bullish_sequence else "SELL"
        
        if (is_bullish_sequence and t['close'] > t['ema50']) or \
           (is_bearish_sequence and t['close'] < t['ema50']):
            strength += 1
            
        if (is_bullish_sequence and t['close'] > t['ema200']) or \
           (is_bearish_sequence and t['close'] < t['ema200']):
            strength += 2

        return {
            "action": action,
            "strength": strength,
            "price": t['close'],
            "timestamp": t.name,
            "reason": f"Double Vector confirmed with strength {strength}"
        }

def main():
    file_path = "data/BTCUSDC/15m_4D_23-01-2026_21-30-00___27-01-2026_21-15-00.candles.parquet"
    try:
        df = pd.read_parquet(file_path)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df['timestamp'], utc=True)
            
        strategy = MMSignalStrategy()
        df_with_inds = strategy.calculate_indicators(df)
        signal = strategy.check_signal(df_with_inds)
        
        print(f"--- SIGNAL REPORT [{pd.Timestamp.now()}] ---")
        print(f"Action: {signal['action']}")
        print(f"Strength: {signal['strength']}/6")
        print(f"Reason: {signal['reason']}")
        if signal['action'] != "NO_TRADE":
            print(f"Entry Price: {signal['price']}")
            
    except Exception as e:
        print(f"Error processing signal: {e}")

if __name__ == "__main__":
    main()