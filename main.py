import pandas as pd
from dotenv import load_dotenv
from stocks import NSE_TICKERS
from data_ingestion import fetch_ohlcv
from backtester import ICBacktester
from signal_backtester import SignalWeightedBacktester
from rl_optimizer import run_rl_loop
from parser import AlphaExpressionParser

load_dotenv()

# Step 1: Fetch data
df = fetch_ohlcv(tickers=NSE_TICKERS, start="2023-01-01", save=True)

# Step 2: Prepare panel
df_panel = df.set_index(["date", "ticker"]).sort_index()
variables = {
    "open": df_panel["open"],
    "high": df_panel["high"],
    "low": df_panel["low"],
    "close": df_panel["close"],
    "volume": df_panel["volume"],
}

# Step 3: Run RL loop (IC is the reward signal internally)
bt = ICBacktester(df)
results = run_rl_loop(
    variables=variables,
    backtester=bt,
    n_episodes=5,
    n_iterations_per_episode=100,
    use_annealing=True,
    top_k=10,
)


# Step 4: Evaluate top result with IC metrics
print("\n=== Detailed evaluation of best alpha ===")
best_expr, best_ic = results.leaderboard[0]
print(f"Expression : {best_expr}")
print(f"IC Mean    : {best_ic:.4f}")

parser = AlphaExpressionParser(variables)
alpha = parser.parse(best_expr)

ic = bt.compute_ic(alpha)
rank_ic = bt.compute_rank_ic(alpha)
print("IC Interpretation:     ", bt.interpret_ic(ic))
print("Rank IC Interpretation:", bt.interpret_ic(rank_ic))

# Step 5: Signal-weighted portfolio backtest on the best alpha
print("\n=== Signal-Weighted Portfolio Backtest ===")
sw_bt = SignalWeightedBacktester(df)
metrics = sw_bt.run(alpha, plot=True)
sw_bt.print_metrics(metrics)
