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

    def run(self, alpha: pd.Series, plot: bool = True) -> dict:
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

        if plot:
            self._plot_equity_curve(nav, daily_returns, metrics)

        return metrics

    def _plot_equity_curve(
        self, nav: pd.Series, daily_returns: pd.Series, metrics: dict
    ):
        fig, (ax1, ax2) = plt.subplots(
            2,
            1,
            figsize=(12, 7),
            gridspec_kw={"height_ratios": [3, 1]},
            facecolor="#0d1117",
        )
        fig.patch.set_facecolor("#0d1117")

        # --- NAV curve ---
        ax1.set_facecolor("#0d1117")
        ax1.plot(nav.index, nav.values, color="#00d4aa", linewidth=1.5, zorder=3)
        ax1.fill_between(
            nav.index,
            1,
            nav.values,
            where=(nav.values >= 1),
            color="#00d4aa",
            alpha=0.08,
        )
        ax1.fill_between(
            nav.index,
            1,
            nav.values,
            where=(nav.values < 1),
            color="#ff4d6d",
            alpha=0.12,
        )
        ax1.axhline(1.0, color="#444c56", linewidth=0.8, linestyle="--")

        # Annotate total return
        final_nav = nav.iloc[-1]
        color = "#00d4aa" if final_nav >= 1 else "#ff4d6d"
        ax1.annotate(
            f"{(final_nav - 1) * 100:+.1f}%",
            xy=(nav.index[-1], final_nav),
            xytext=(-60, 10),
            textcoords="offset points",
            fontsize=11,
            color=color,
            fontweight="bold",
        )

        ax1.set_ylabel("Portfolio NAV", color="#8b949e", fontsize=10)
        ax1.tick_params(colors="#8b949e", labelsize=9)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        for spine in ax1.spines.values():
            spine.set_edgecolor("#30363d")
        ax1.grid(axis="y", color="#21262d", linewidth=0.6)

        # Stats box
        stats_text = (
            f"Sharpe  {metrics['sharpe']:+.2f}    "
            f"MaxDD  {metrics['max_drawdown'] * 100:.1f}%    "
            f"Return  {metrics['total_return'] * 100:+.1f}%"
        )
        ax1.set_title(
            "Signal-Weighted Portfolio  ·  " + stats_text,
            color="#e6edf3",
            fontsize=11,
            pad=12,
            loc="left",
            fontfamily="monospace",
        )

        # --- Daily returns bar chart ---
        ax2.set_facecolor("#0d1117")
        colors = ["#00d4aa" if r >= 0 else "#ff4d6d" for r in daily_returns.values]
        ax2.bar(
            daily_returns.index,
            daily_returns.values,
            color=colors,
            width=1.0,
            alpha=0.7,
        )
        ax2.axhline(0, color="#444c56", linewidth=0.6)
        ax2.set_ylabel("Daily Ret", color="#8b949e", fontsize=9)
        ax2.tick_params(colors="#8b949e", labelsize=8)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        for spine in ax2.spines.values():
            spine.set_edgecolor("#30363d")
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y*100:.1f}%"))
        ax2.grid(axis="y", color="#21262d", linewidth=0.6)

        plt.tight_layout(h_pad=0.5)
        plt.show()

    def print_metrics(self, metrics: dict):
        print("\n=== Signal-Weighted Backtest Results ===")
        print(f"  Total Return  : {metrics['total_return'] * 100:+.2f}%")
        print(f"  Sharpe Ratio  : {metrics['sharpe']:.3f}")
        print(f"  Max Drawdown  : {metrics['max_drawdown'] * 100:.2f}%")
        print("========================================\n")
