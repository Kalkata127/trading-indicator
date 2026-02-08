import unittest
import pandas as pd
from datetime import datetime, timedelta, timezone
from backtest import simulate_exit

class TestTradingLogic(unittest.TestCase):

    def create_mock_data(self, num_candles: int = 100) -> pd.DataFrame:
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        
        # Правим цената да расте леко, за да имаме бичи тренд за EMA
        prices = [100.0 + (i * 0.1) for i in range(num_candles)]
        
        data = {
            'timestamp': [base_time + timedelta(minutes=15*i) for i in range(num_candles)],
            'open': prices,
            'high': [p + 0.5 for p in prices],
            'low': [p - 0.5 for p in prices],
            'close': [p + 0.2 for p in prices],
            'volume': [1000.0] * num_candles,
            'va': [0] * num_candles
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        # EMA50 под цената за LONG тренд
        df['ema50'] = df['close'] - 5.0 
        return df

    def test_simulate_exit_win(self) -> None:
        df = self.create_mock_data(20)
        sig = {
            'direction': 'LONG',
            'entry': 100.0,
            'tp': 105.0,
            'sl': 95.0
        }
        # На 5-тата свещ цената „излита“ до TP
        df.iloc[5, df.columns.get_loc('high')] = 106.0

        result = simulate_exit(df, 0, sig)
        
        self.assertEqual(result['outcome'], 'WIN')
        self.assertEqual(result['exit_price'], 105.0)
        print("Exit Simulation (WIN): PASSED")

if __name__ == '__main__':
    unittest.main()