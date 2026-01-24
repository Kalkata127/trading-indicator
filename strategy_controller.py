import pandas as pd
from indicators import compute_ema


class StrategyController:
    def __init__(self, df: pd.DataFrame, sr_df: pd.DataFrame | None = None):
        self.df = df.copy()
        self.sr_df = sr_df

        if not isinstance(self.df.index, pd.DatetimeIndex):
            self.df.index = pd.to_datetime(self.df["timestamp"], utc=True)

    # ------------------------------
    def load_indicators(self):
        self.df["ema_50"] = compute_ema(self.df, 50)
        self.df["ema_200"] = compute_ema(self.df, 200)

    # ------------------------------
    def run(
        self,
        lookback=6,
        use_last_closed=True,
        min_strength=5,
        min_rr=1.5,
        tp_level=1,          # 1 = nearest, 2 = second nearest, etc.
        sl_level=1,
        sl_buffer_pct=0.001, # 0.1% buffer
        min_stop_pct=0.002   # at least 0.2% stop distance
    ):
        """
        Returns dict:
          status: TRADE/NO_TRADE
          plus fields for trade OR reason/debug for NO_TRADE
        """

        # Require EMA50 to be available at evaluation candle
        eval_idx = -2 if use_last_closed else -1
        if pd.isna(self.df.iloc[eval_idx].get("ema_50", None)):
            return self._no_trade(
                "EMA50_NOT_READY",
                debug={"available_rows": len(self.df)}
            )


        # Choose the evaluation end candle:
        # - last closed candle (recommended live/testing)
        # - or last candle in df
        end_idx = -2 if use_last_closed else -1
        end_row = self.df.iloc[end_idx]
        end_ts = end_row.name

        # Require EMA50 at least
        if pd.isna(end_row.get("ema_50", None)):
            return self._no_trade("EMA_NOT_READY", debug={"end_ts": str(end_ts)})

        # Search for the most recent vector candle in the lookback window ending at end_idx
        window = self.df.iloc[end_idx - (lookback - 1) : end_idx + 1]
        vector_row = None
        for _, r in window[::-1].iterrows():
            if r.get("isVector", 0) == 1:
                vector_row = r
                break

        debug = {
            "eval_end_ts": str(end_ts),
            "eval_end_close": float(end_row["close"]),
            "lookback": lookback,
            "use_last_closed": use_last_closed,
        }

        if vector_row is None:
            return self._no_trade("NO_VECTOR_IN_LOOKBACK", debug=debug)

        signal = self._build_signal(vector_row)
        debug["vector_ts"] = str(vector_row.name)
        debug["vector_close"] = float(vector_row["close"])
        debug["vector_open"] = float(vector_row["open"])
        debug["vector_isVector"] = int(vector_row.get("isVector", 0))
        debug["vector_strength_score"] = int(signal["strength"])
        debug["vector_direction"] = signal["direction"]
        debug["ema50_at_vector"] = float(vector_row["ema_50"])
        debug["ema200_at_vector"] = float(vector_row["ema_200"])

        if signal["strength"] < min_strength:
            return self._no_trade("STRENGTH_TOO_LOW", debug=debug)

        trade = self._build_trade_from_signal(
            signal,
            min_rr=min_rr,
            tp_level=tp_level,
            sl_level=sl_level,
            sl_buffer_pct=sl_buffer_pct,
            min_stop_pct=min_stop_pct,
            debug=debug
        )

        if trade is None:
            return self._no_trade("NO_VALID_TRADE_AFTER_TP_SL", debug=debug)

        return trade

    # ------------------------------
    def _build_signal(self, row):
        close = float(row["close"])
        open_ = float(row["open"])
        ema50 = float(row["ema_50"])
        ema200 = float(row["ema_200"])

        is_bull = close > open_
        direction = "BUY" if is_bull else "SELL"

        # Strength 1–10 (simple + interpretable)
        strength = 3  # vector base

        # EMA50 alignment
        if (is_bull and close > ema50) or ((not is_bull) and close < ema50):
            strength += 2

        # EMA200 alignment (stronger)
        if (is_bull and close > ema200) or ((not is_bull) and close < ema200):
            strength += 2

        return {
            "timestamp": row.name,
            "direction": direction,
            "price": close,
            "strength": min(strength, 10),
        }

    # ------------------------------
    def _build_trade_from_signal(
        self,
        signal,
        min_rr,
        tp_level,
        sl_level,
        sl_buffer_pct,
        min_stop_pct,
        debug
    ):
        entry = float(signal["price"])
        direction = signal["direction"]
        strength = int(signal["strength"])
        ts = signal["timestamp"]

        tp = None
        sl = None

        # Use SR levels if available
        if self.sr_df is not None and not self.sr_df.empty:
            sr = self.sr_df.copy()
            # Expect schema: price, type(support/resistance), timeframe, touches
            sr["price"] = sr["price"].astype(float)

            above = sr[sr["price"] > entry].sort_values("price")
            below = sr[sr["price"] < entry].sort_values("price", ascending=False)

            # pick nth level (1=nearest)
            def pick_level(df_levels, n):
                if df_levels.empty:
                    return None
                idx = min(n - 1, len(df_levels) - 1)
                return float(df_levels.iloc[idx]["price"])

            if direction == "BUY":
                tp = pick_level(above[above["type"] == "resistance"], tp_level) or pick_level(above, tp_level)
                sl = pick_level(below[below["type"] == "support"], sl_level) or pick_level(below, sl_level)
            else:
                tp = pick_level(below[below["type"] == "support"], tp_level) or pick_level(below, tp_level)
                sl = pick_level(above[above["type"] == "resistance"], sl_level) or pick_level(above, sl_level)

        # Fallback TP/SL if missing
        if sl is None:
            sl = entry * (1 - 0.005) if direction == "BUY" else entry * (1 + 0.005)
        if tp is None:
            tp = entry * (1 + 0.01) if direction == "BUY" else entry * (1 - 0.01)

        # Apply SL buffer (push SL slightly further away)
        if direction == "BUY":
            sl = sl * (1 - sl_buffer_pct)
        else:
            sl = sl * (1 + sl_buffer_pct)

        # Enforce minimum stop distance (avoid micro-wick stops)
        min_stop_dist = entry * min_stop_pct
        if abs(entry - sl) < min_stop_dist:
            sl = entry - min_stop_dist if direction == "BUY" else entry + min_stop_dist

        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk <= 0:
            return None

        rr = reward / risk

        debug["entry"] = entry
        debug["tp"] = tp
        debug["sl"] = sl
        debug["rr"] = round(rr, 2)
        debug["tp_level_used"] = tp_level
        debug["sl_level_used"] = sl_level
        debug["sl_buffer_pct"] = sl_buffer_pct
        debug["min_stop_pct"] = min_stop_pct

        if rr < min_rr:
            # soft penalty instead of reject? for now: reject (you can change this later)
            return None

        return {
            "status": "TRADE",
            "timestamp": ts,
            "direction": direction,
            "entry": round(entry, 2),
            "stop_loss": round(sl, 2),
            "take_profit": round(tp, 2),
            "strength": strength,
            "rr": round(rr, 2),
            "debug": debug,
        }

    # ------------------------------
    def _no_trade(self, reason, debug):
        last = self.df.iloc[-1]
        return {
            "status": "NO_TRADE",
            "timestamp": last.name,
            "price": float(last["close"]),
            "reason": reason,
            "debug": debug,
        }
