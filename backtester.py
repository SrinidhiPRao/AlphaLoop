import numpy as np
import pandas as pd


class ICBacktester:
    def __init__(self, df):
        self.df = df.copy()
        self.df["date"] = pd.to_datetime(self.df["date"])
        self.df.sort_values(["ticker", "date"], inplace=True)

        self.df["fwd_ret_20"] = (
            self.df.groupby("ticker")["close"].shift(-20) / self.df["close"] - 1
        )

        self.df.set_index(["date", "ticker"], inplace=True)

    # -------------------------
    # IC Metrics
    # -------------------------
    def compute_ic(self, alpha):
        data = pd.concat([alpha, self.df["fwd_ret_20"]], axis=1)
        data.columns = ["alpha", "ret"]
        data = data.dropna()

        return data.groupby(level="date").apply(lambda x: x["alpha"].corr(x["ret"]))

    def compute_rank_ic(self, alpha):
        data = pd.concat([alpha, self.df["fwd_ret_20"]], axis=1)
        data.columns = ["alpha", "ret"]
        data = data.dropna()

        return data.groupby(level="date").apply(
            lambda x: x["alpha"].rank().corr(x["ret"].rank())
        )

    def interpret_ic(self, ic_series):
        mean = ic_series.mean()
        std = ic_series.std()
        icir = mean / std

        strength = (
            "Very Strong"
            if abs(mean) > 0.05
            else (
                "Strong"
                if abs(mean) > 0.03
                else (
                    "Moderate"
                    if abs(mean) > 0.02
                    else "Weak" if abs(mean) > 0.01 else "Noise"
                )
            )
        )

        return {
            "IC Mean": mean,
            "IC Std": std,
            "ICIR": icir,
            "Signal Strength": strength,
        }

    # -------------------------
    # Simple Long-Short Backtest
    # -------------------------
    def long_short_pnl(self, alpha, quantile=0.2):
        """
        Long top quantile, short bottom quantile
        """

        data = pd.concat([alpha, self.df["fwd_ret_20"]], axis=1)
        data.columns = ["alpha", "ret"]
        data = data.dropna()

        def daily_pnl(x):
            q = x["alpha"].quantile(quantile)
            q_inv = x["alpha"].quantile(1 - quantile)

            long = x[x["alpha"] >= q_inv]["ret"].mean()
            short = x[x["alpha"] <= q]["ret"].mean()

            return long - short

        daily_returns = data.groupby(level="date").apply(daily_pnl)

        return daily_returns
