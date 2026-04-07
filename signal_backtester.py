import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter


class SignalWeightedBacktester:
    """
    Signal-weighted portfolio backtester.

    Each day, the alpha signal is normalized into dollar-neutral portfolio
    weights. The strategy is long stocks with positive scores and short
    stocks with negative scores, with weight proportional to signal strength.

    Portfolio is rebalanced daily. No transaction costs assumed.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df["date"] = pd.to_datetime(self.df["date"])
        self.df.sort_values(["ticker", "date"], inplace=True)

        # 1-day forward return for daily rebalancing
        self.df["fwd_ret_1"] = (
            self.df.groupby("ticker")["close"].shift(-1) / self.df["close"] - 1
        )
        self.df.set_index(["date", "ticker"], inplace=True)

    def neutralize(self, alpha: pd.Series) -> pd.Series:
        """Cross-sectional z-score neutralization."""

        def _zscore(x):
            mu = x.mean()
            sigma = x.std()
            if sigma == 0 or np.isnan(sigma):
                return x - mu
            return (x - mu) / sigma

        return alpha.groupby(level="date").transform(_zscore)

    def _compute_weights(self, alpha_neutralized: pd.Series) -> pd.Series:
        """
        Normalize neutralized scores into dollar-neutral weights.
        weight_i = score_i / sum(|score_i|) per day.
        Gross exposure = 1 by construction.
        """

        def _normalize(x):
            denom = x.abs().sum()
            if denom == 0:
                return x * 0
            return x / denom

        return alpha_neutralized.groupby(level="date").transform(_normalize)

    def run(self, alpha: pd.Series) -> dict:
        """
        Run the signal-weighted backtest.

        Parameters
        ----------
        alpha   : pd.Series with MultiIndex (date, ticker)
        plot    : whether to display the equity curve

        Returns
        -------
        dict with total_return, sharpe, max_drawdown, nav (pd.Series)
        """
        alpha_neutralized = self.neutralize(alpha)
        weights = self._compute_weights(alpha_neutralized)
        # weights = self._compute_weights(alpha)

        data = pd.concat([weights, self.df["fwd_ret_1"]], axis=1)
        data.columns = ["weight", "ret"]
        data = data.dropna()

        # Daily portfolio return = sum of (weight_i * ret_i) across stocks
        daily_returns = data.groupby(level="date").apply(
            lambda x: (x["weight"] * x["ret"]).sum()
        )

        # NAV curve starting at 1.0
        nav = (1 + daily_returns).cumprod()
        nav.iloc[0] = 1 + daily_returns.iloc[0]  # ensure first point is set

        # --- Metrics ---
        total_return = nav.iloc[-1] - 1
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

        # Max drawdown
        rolling_max = nav.cummax()
        drawdown = (nav - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        metrics = {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "nav": nav,
            "daily_returns": daily_returns,
        }
        return metrics
