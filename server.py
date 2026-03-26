"""
server.py  —  FastAPI server. Reads from alpha.db written by research_engine.py.

Run with:  uvicorn server:app --reload
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

app = FastAPI()
DB_PATH = Path("alpha.db")


# ── DB helper ─────────────────────────────────────────────────────────────────


def get_con():
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503, detail="Database not ready. Run research_engine.py first."
        )
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def meta(con, key, default=None):
    row = con.execute("SELECT value FROM run_meta WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


# ── API ───────────────────────────────────────────────────────────────────────


@app.get("/api/portfolio")
def get_portfolio(horizon: str = "1M"):
    col = {
        "1W": "expected_return_1w",
        "1M": "expected_return_1m",
        "3M": "expected_return_3m",
    }.get(horizon, "expected_return_1m")

    con = get_con()
    rows = con.execute(
        f"""
        SELECT ticker, signal, weight, {col} AS expected_return, direction, updated_at
        FROM portfolio
        ORDER BY ABS(signal) DESC
    """
    ).fetchall()
    con.close()

    if not rows:
        raise HTTPException(status_code=503, detail="Portfolio not yet computed.")

    return {
        "portfolio": [dict(r) for r in rows],
        "horizon": horizon,
        "updated_at": rows[0]["updated_at"],
        "n_alphas": 10,
    }


@app.get("/api/heatmap")
def get_heatmap():
    con = get_con()
    rows = con.execute(
        "SELECT ticker, signal FROM portfolio ORDER BY ticker"
    ).fetchall()
    con.close()

    if not rows:
        raise HTTPException(status_code=503, detail="No signal data yet.")

    return {"stocks": [dict(r) for r in rows]}


@app.get("/api/performance")
def get_performance():
    con = get_con()

    curve = con.execute(
        "SELECT date, nav, benchmark FROM equity_curve ORDER BY date"
    ).fetchall()

    lb = con.execute(
        "SELECT ic_mean, sharpe, max_drawdown, total_return FROM leaderboard WHERE rank = 1"
    ).fetchone()

    con.close()

    if not curve:
        raise HTTPException(status_code=503, detail="Equity curve not yet computed.")

    dates = [r["date"] for r in curve]
    nav = [r["nav"] for r in curve]
    bench = [r["benchmark"] for r in curve]

    metrics = {
        "total_return": round(lb["total_return"], 2) if lb else 0,
        "sharpe": round(lb["sharpe"], 3) if lb else 0,
        "max_drawdown": round(lb["max_drawdown"], 2) if lb else 0,
        "ic_mean": round(lb["ic_mean"], 4) if lb else 0,
    }

    return {
        "dates": dates,
        "nav": nav,
        "benchmark": bench,
        "metrics": metrics,
    }


@app.get("/api/leaderboard")
def get_leaderboard():
    con = get_con()
    rows = con.execute("SELECT * FROM leaderboard ORDER BY rank").fetchall()
    last_run = meta(con, "last_run")
    con.close()

    if not rows:
        raise HTTPException(status_code=503, detail="Leaderboard not yet populated.")

    return {
        "leaderboard": [dict(r) for r in rows],
        "updated_at": last_run or datetime.utcnow().isoformat(),
    }


@app.get("/api/stock/{ticker}")
def get_stock(ticker: str, horizon: str = "1M"):
    """
    Returns the signal value and expected return for a single ticker.
    OHLCV charting data comes from the portfolio table (signal only).
    For a richer chart, wire this to your raw CSV or a separate DB table.
    """
    col = {
        "1W": "expected_return_1w",
        "1M": "expected_return_1m",
        "3M": "expected_return_3m",
    }.get(horizon, "expected_return_1m")

    con = get_con()
    row = con.execute(
        f"""
        SELECT ticker, signal, weight, {col} AS expected_return, direction, updated_at
        FROM portfolio WHERE ticker = ?
    """,
        (ticker,),
    ).fetchone()
    con.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"{ticker} not in portfolio.")

    return dict(row) | {"horizon": horizon}


# ── Static files ──────────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")
