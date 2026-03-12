import pandas as pd
from dotenv import load_dotenv

from data_ingestion import fetch_ohlcv
from backtester import ICBacktester
from parser import AlphaExpressionParser
from generate_alpha import generate_alpha_expression

load_dotenv()

# Step 1: Fetch data
NSE_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "ITC.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
]

df = fetch_ohlcv(tickers=NSE_TICKERS, start="2022-01-01", save=True)

# Step 2: Prepare panel
df_panel = df.set_index(["date", "ticker"]).sort_index()

variables = {
    "open": df_panel["open"],
    "high": df_panel["high"],
    "low": df_panel["low"],
    "close": df_panel["close"],
    "volume": df_panel["volume"],
}

for _ in range(3):
    # Step 3: Parse LLM-style formula
    expr = generate_alpha_expression()
    print("Generated alpha:", expr)

    parser = AlphaExpressionParser(variables)
    alpha = parser.parse(expr)

    # Step 4: Backtest
    bt = ICBacktester(df)

    ic = bt.compute_ic(alpha)
    rank_ic = bt.compute_rank_ic(alpha)

    print("IC Interpretation:", bt.interpret_ic(ic))
    print("Rank IC Interpretation:", bt.interpret_ic(rank_ic))

    pnl = bt.long_short_pnl(alpha)
    print("Avg Long-Short Return:", pnl.mean())
    print("Sharpe (annualized):", pnl.mean() / pnl.std() * (252**0.5))

    with open("results.csv", "a+") as f:
        f.write(f"expr, {ic}, {rank_ic}")
    """How to interpret IC:
    IC Mean	Interpretation
    ~0.00	Noise
    0.01	Weak but usable
    0.02-0.03	Solid alpha
    0.05+	Very strong
    0.10	Extremely rare
    """
