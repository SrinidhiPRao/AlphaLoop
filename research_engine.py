"""
research_engine.py

Runs continuously: fetches data, runs RL loop, and writes results to SQLite.
The FastAPI server reads from the same DB — fully decoupled.

Run with:  python research_engine.py
"""

import time
import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from data import NSE_TICKERS, alphas
from data_ingestion import fetch_ohlcv
from backtester import ICBacktester
from signal_backtester import SignalWeightedBacktester
from rl_optimizer import run_rl_loop
from parser import AlphaExpressionParser

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

DB_PATH = Path("alpha.db")


# ── DB setup ──────────────────────────────────────────────────────────────────


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
    CREATE TABLE IF NOT EXISTS leaderboard (
        rank         INTEGER,
        formula      TEXT PRIMARY KEY,
        ic_mean      REAL,
        sharpe       REAL,
        max_drawdown REAL,
        total_return REAL,
        found_at     TEXT
    );
    CREATE TABLE IF NOT EXISTS portfolio (
        ticker              TEXT PRIMARY KEY,
        signal              REAL,
        weight              REAL,
        expected_return_1w  REAL,
        expected_return_1m  REAL,
        expected_return_3m  REAL,
        direction           TEXT,
        updated_at          TEXT
    );
    CREATE TABLE IF NOT EXISTS equity_curve (
        date      TEXT PRIMARY KEY,
        nav       REAL,
        benchmark REAL
    );
    CREATE TABLE IF NOT EXISTS run_meta (
        key   TEXT PRIMARY KEY,
        value TEXT
    );
    """
    )
    con.commit()
    con.close()
    log.info("DB initialised at %s", DB_PATH)


# ── Helpers ───────────────────────────────────────────────────────────────────


def load_leaderboard_exprs(con):
    """Return formula strings currently stored in the DB."""
    rows = con.execute("SELECT formula FROM leaderboard ORDER BY rank").fetchall()
    return [r[0] for r in rows]


def evaluate_all(candidates, variables, df):
    """
    Re-evaluate every candidate with fresh market data.
    Returns list of (expr, ic_mean, sharpe, max_drawdown, total_return)
    sorted by ic_mean descending. Failures are skipped with a warning.
    """
    bt = ICBacktester(df)
    sw_bt = SignalWeightedBacktester(df)
    parser = AlphaExpressionParser(variables)
    scored = []

    for expr in candidates:
        try:
            alpha = parser.parse(expr)
            ic_mean = float(bt.interpret_ic(bt.compute_ic(alpha))["IC Mean"])
            metrics = sw_bt.run(alpha, plot=False)
            sharpe = float(metrics.get("sharpe", 0))
            max_dd = float(metrics.get("max_drawdown", 0))
            total_ret = float(metrics.get("total_return", 0))
            scored.append((expr, ic_mean, sharpe, max_dd, total_ret))
            log.info("  eval %-55s  IC=%.4f  Sharpe=%.3f", expr[:55], ic_mean, sharpe)
        except Exception as e:
            log.warning("  eval failed for %s: %s", expr[:55], e)

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ── Writers ───────────────────────────────────────────────────────────────────


def write_leaderboard(con, scored_top10):
    """scored_top10: list of (expr, ic_mean, sharpe, max_dd, total_ret)"""
    con.execute("DELETE FROM leaderboard")
    for rank, (expr, ic_mean, sharpe, max_dd, total_ret) in enumerate(
        scored_top10, start=1
    ):
        con.execute(
            """
            INSERT OR REPLACE INTO leaderboard
                (rank, formula, ic_mean, sharpe, max_drawdown, total_return, found_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                rank,
                expr,
                ic_mean,
                sharpe,
                max_dd,
                total_ret,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    con.commit()
    log.info("Leaderboard written — %d formulas", len(scored_top10))


def write_portfolio(con, best_expr, variables, df):
    parser = AlphaExpressionParser(variables)
    alpha = parser.parse(best_expr)

    latest_date = alpha.index.get_level_values("date").max()
    latest = alpha.xs(latest_date, level="date")

    gross = latest.abs().sum()
    if gross == 0:
        log.warning("Zero gross exposure — skipping portfolio write")
        return

    weights = latest / gross
    now = datetime.now(timezone.utc).isoformat()
    con.execute("DELETE FROM portfolio")

    for ticker, signal in latest.items():
        sig = float(signal)
        w = float(weights[ticker])
        base = sig * 0.018  # ~1.8% per sigma over 20 days
        con.execute(
            """
            INSERT OR REPLACE INTO portfolio
                (ticker, signal, weight,
                 expected_return_1w, expected_return_1m, expected_return_3m,
                 direction, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ticker,
                sig,
                round(abs(w) * 100, 4),
                round(base * (5 / 20) * 100, 4),
                round(base * 100, 4),
                round(base * (60 / 20) * 100, 4),
                "long" if sig >= 0 else "short",
                now,
            ),
        )

    con.commit()
    log.info("Portfolio written — %d positions at %s", len(latest), latest_date)


def write_equity_curve(con, best_expr, variables, df):
    sw_bt = SignalWeightedBacktester(df)
    parser = AlphaExpressionParser(variables)
    alpha = parser.parse(best_expr)
    metrics = sw_bt.run(alpha, plot=False)

    nav_series = metrics.get("nav")
    if nav_series is None:
        log.warning("No nav series returned — skipping equity curve write")
        return
    nav_series = (nav_series / nav_series.iloc[0]) * 100

    # Fetch Nifty 50 benchmark aligned to nav date range
    start_date = nav_series.index.min().strftime("%Y-%m-%d")
    bench_series = None
    try:
        nifty_df = fetch_ohlcv(["^NSEI"], start=start_date, save=False)
        nifty_df["date"] = pd.to_datetime(nifty_df["date"]).dt.tz_localize(None)
        nifty_close = nifty_df.set_index("date")["close"].sort_index()

        # Align to nav index, forward-fill any missing dates (holidays)
        nav_index = (
            nav_series.index.tz_localize(None)
            if hasattr(nav_series.index, "tz") and nav_series.index.tz
            else nav_series.index
        )
        nifty_aligned = nifty_close.reindex(nav_index, method="ffill")

        # Normalize to 100 at first available point
        first_valid = nifty_aligned.first_valid_index()
        if first_valid is not None:
            bench_series = (nifty_aligned / nifty_aligned[first_valid]) * 100
            log.info("Benchmark fetched — %d rows", bench_series.notna().sum())
    except Exception as e:
        log.warning("Benchmark fetch failed: %s — chart will show alpha only", e)

    dates = nav_series.index.astype(str).tolist()
    navs = nav_series.tolist()
    bench = bench_series.tolist() if bench_series is not None else [None] * len(navs)

    con.execute("DELETE FROM equity_curve")
    con.executemany(
        "INSERT OR REPLACE INTO equity_curve (date, nav, benchmark) VALUES (?, ?, ?)",
        zip(dates, navs, bench),
    )
    con.commit()
    log.info("Equity curve written — %d rows", len(dates))


def write_meta(con, key, value):
    con.execute(
        "INSERT OR REPLACE INTO run_meta (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    con.commit()


# ── Core iteration ────────────────────────────────────────────────────────────


def run_once(df, df_panel, variables):
    con = sqlite3.connect(DB_PATH)
    bt = ICBacktester(df)

    # load existing leaderboard formulas from DB
    existing_exprs = load_leaderboard_exprs(con)
    log.info("Existing leaderboard: %d formulas", len(existing_exprs))

    # run RL to generate 5 fresh candidates
    log.info("Running RL loop for new candidates …")
    results = run_rl_loop(
        variables=variables,
        backtester=bt,
        n_episodes=1,
        n_iterations_per_episode=100,
        use_annealing=True,
        top_k=5,
    )
    new_exprs = [expr for expr, _ in results.leaderboard]
    log.info("RL produced %d new candidates", len(new_exprs))

    # merge
    all_candidates = list(dict.fromkeys(existing_exprs + new_exprs))
    log.info("Re-evaluating all %d candidates with current data …", len(all_candidates))

    # re-evaluate
    scored = evaluate_all(all_candidates, variables, df)

    # find top 10
    top10 = scored[:10]
    best_expr = top10[0][0]
    best_ic = top10[0][1]
    log.info("Best IC: %.4f  expr: %s", best_ic, best_expr)

    # write to db
    write_leaderboard(con, top10)
    write_portfolio(con, best_expr, variables, df)
    write_equity_curve(con, best_expr, variables, df)
    write_meta(con, "last_run", datetime.now(timezone.utc).isoformat())
    write_meta(con, "best_ic", best_ic)
    write_meta(con, "n_alphas", len(top10))

    con.close()
    log.info("Run complete.")


def main():
    init_db()

    log.info("Fetching OHLCV data …")
    df = fetch_ohlcv(tickers=NSE_TICKERS, start="2026-01-01", save=True)

    df_panel = df.set_index(["date", "ticker"]).sort_index()
    variables = {
        "open": df_panel["open"],
        "high": df_panel["high"],
        "low": df_panel["low"],
        "close": df_panel["close"],
        "volume": df_panel["volume"],
    }

    while True:
        try:
            run_once(df, df_panel, variables)
        except Exception as e:
            log.error("Run failed: %s", e, exc_info=True)
        log.info("Sleeping 5 minutes …")
        time.sleep(300)


if __name__ == "__main__":
    main()
