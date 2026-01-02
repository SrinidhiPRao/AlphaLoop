import numpy as np
import pandas as pd

class ICBacktester:
    def __init__(self, df):
        """
        df must contain:
        date | ticker | close
        """
        self.df = df.copy()
        self.df["date"] = pd.to_datetime(self.df["date"])
        self.df.sort_values(["ticker", "date"], inplace=True)

        self.df["fwd_ret_20"] = (
            self.df.groupby("ticker")["close"]
                   .shift(-20) / self.df["close"] - 1
        )

        self.df.set_index(["date", "ticker"], inplace=True)

    def compute_ic(self, alpha: pd.Series):
        data = pd.concat(
            [alpha, self.df["fwd_ret_20"]],
            axis=1,
            keys=["alpha", "ret"]
        ).dropna()

        daily_ic = (
            data.groupby(level="date")
                .apply(lambda x: x["alpha"].corr(x["ret"]))
        )

        return daily_ic

    def compute_rank_ic(self, alpha: pd.Series):
        data = pd.concat(
            [alpha, self.df["fwd_ret_20"]],
            axis=1,
            keys=["alpha", "ret"]
        ).dropna()

        daily_rank_ic = (
            data.groupby(level="date")
                .apply(
                    lambda x: x["alpha"].rank().corr(x["ret"].rank())
                )
        )

        return daily_rank_ic

    def summary(self, ic_series):
        return {
            "IC Mean": ic_series.mean(),
            "IC Std": ic_series.std(),
            "ICIR": ic_series.mean() / ic_series.std()
        }
