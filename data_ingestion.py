import yfinance as yf
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw/yfinance")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_ohlcv(tickers, start="2010-01-01", end=None, interval="1d", save=True):
    """
    Fetch OHLCV data from yfinance and return a long-format DataFrame.
    """

    df = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        interval=interval,
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )

    records = []

    for ticker in tickers:
        tdf = df[ticker].copy()
        tdf.reset_index(inplace=True)
        tdf["ticker"] = ticker

        tdf.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
                "Date": "date",
            },
            inplace=True,
        )

        records.append(tdf)

    full_df = pd.concat(records, ignore_index=True)

    # Ensure correct dtypes
    full_df["date"] = pd.to_datetime(full_df["date"])
    full_df.sort_values(["ticker", "date"], inplace=True)

    if save:
        path = DATA_DIR / "ohlcv.csv"
        full_df.to_csv(path, index=False)
        print(f"Saved data to {path}")

    return full_df
