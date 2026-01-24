import pandas as pd

def compute_ema(df, period=50, price_col="close"):
    """
    Returns a pd.Series with EMA values of length `period` on `price_col`.
    """
    return df[price_col].ewm(span=period, adjust=False).mean()

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def add_ema(df: pd.DataFrame, length: int, column_name: str = None) -> pd.DataFrame:
    """
    Adds an EMA column to the DataFrame.

    Parameters:
        df (pd.DataFrame): must contain 'close'
        length (int): EMA period
        column_name (str): optional override for column name
                          default becomes "ema_<length>"

    Returns:
        pd.DataFrame: df with new EMA column added
    """
    if column_name is None:
        column_name = f"ema_{length}"

    df[column_name] = ema(df["close"], length)
    return df
