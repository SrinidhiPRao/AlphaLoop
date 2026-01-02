import pandas as pd

from data_ingestion import fetch_ohlcv
from backtester import ICBacktester
from parser import AlphaExpressionParser

# -------------------------------
# Step 1: Fetch data
# -------------------------------
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

# -------------------------------
# Step 2: Prepare panel
# -------------------------------
df_panel = df.set_index(["date", "ticker"]).sort_index()

variables = {
    "open": df_panel["open"],
    "high": df_panel["high"],
    "low": df_panel["low"],
    "close": df_panel["close"],
    "volume": df_panel["volume"],
}

# -------------------------------
# Step 3: Parse LLM-style formula
# -------------------------------
expr = "Sub(Delta(xLog(close), 5), Mean(close, 20))"

parser = AlphaExpressionParser(variables)
alpha = parser.parse(expr)

# -------------------------------
# Step 4: Backtest
# -------------------------------
bt = ICBacktester(df)

ic = bt.compute_ic(alpha)
rank_ic = bt.compute_rank_ic(alpha)

print("Expression:", expr)
print("IC Summary:", bt.summary(ic))
print("Rank IC Summary:", bt.summary(rank_ic))
