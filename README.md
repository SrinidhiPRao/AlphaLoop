# AlphaLoop

AlphaLoop searches for quantitative trading alphas on the NIFTY 50. It takes seed alpha expressions, improves each one through an iterative mutation loop, and ranks the results by how well they predict 20-day forward returns.

## How it works

**Seeds.** Every episode of the loop starts from one seed expression. Seeds come from two interchangeable sources: Gemini, which writes new expressions from a prompt, or the 101 Formulaic Alphas published by WorldQuant. In our comparison, Gemini seeds beat randomly generated ones and came close to the WorldQuant 101 in performance.

**Optimisation loop.** An episode mutates the current expression 100 times by default. A mutation does one of four things: swaps an operator for another of the same arity, swaps a price or volume variable, shifts a window length by 5 (kept between 1 and 50), or wraps a variable in a time-series operator. The reward is the mean daily IC of the expression. The loop always accepts an improvement. It accepts a worse expression with probability exp(ΔIC / T), where the temperature T decays linearly from 0.02 to 0.001, so early iterations explore and late ones settle. Expressions that fail to parse or evaluate are discarded.

**Evaluation.** The parser turns each expression into a signal over open, high, low, close, and volume. Each day the signal is z-scored across stocks. IC is the daily correlation between that signal and the 20-day forward return, and Rank IC is the same correlation on ranks. The absolute mean IC maps to a strength label: Noise, Weak, Moderate, Strong, or Very Strong.

**Backtest.** The signal-weighted backtester converts each day's signal into dollar-neutral weights, long the positive scores and short the negative ones, in proportion to signal strength. It rebalances daily and assumes no transaction costs. It reports Sharpe ratio, maximum drawdown, and a NAV curve rebased to 100, which the UI plots against the NIFTY 50 index.

**Research engine.** Every 5 minutes the engine fetches fresh prices, runs one episode, and merges the 5 best new expressions with the stored leaderboard. It re-scores every candidate on current data, keeps the top 10 by mean IC, and writes the best alpha's portfolio and equity curve to `alpha.db`.

**Web UI.** A FastAPI server reads `alpha.db` and serves a dashboard with the leaderboard, the NAV curve against the benchmark, a signal heatmap, and per-stock long/short positions.

`research_engine.py` and `server.py` run independently and share data only through `alpha.db`.

## Tech stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Backend | FastAPI, served with Uvicorn |
| Storage | SQLite |
| Price data | yfinance |
| Seed generation | Gemini |
| Seed alphas | WorldQuant 101 Formulaic Alphas |
| Data handling | pandas |
| Configuration | python-dotenv |

## Configuration

Put the Gemini API key in a `.env` file as `GEMINI_API_KEY`. The ticker universe lives in `data.py`, and the data start date is set in `research_engine.py`.
