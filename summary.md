# Alpha-Mining Backtesting Framework — Context Refresh

This document summarizes the **entire codebase, design intent, and research alignment** for the alpha-mining backtesting framework. It is intended to bring a new ChatGPT session (or collaborator) fully up to speed.

---

## 1. Research Context (Why this exists)

This codebase implements the **infrastructure** needed to reproduce and extend the paper:

> *LLM-enhanced Formulaic Alpha Generation*

Key ideas from the paper:

* **Alpha factors** are formulaic expressions mapping historical market data to predictive signals.
* **Formulaic alphas** are preferred over black-box models for interpretability.
* **Information Coefficient (IC)** is used as the primary metric for signal quality.
* Large Language Models (LLMs) can generate candidate alpha expressions, but:

  * They must follow a strict syntax
  * Invalid expressions must be rejected
  * Alpha quality is evaluated independently of portfolio assumptions

This repo focuses on:

✅ Data ingestion
✅ Alpha operator execution
✅ Expression parsing
✅ IC / Rank IC evaluation
✅ (Optional) simple PnL interpretation

It **does NOT yet implement**:

* Reinforcement learning
* Alpha mutation loops
* LLM prompting logic

---

## 2. High-level Architecture

```
LLM (future)
   ↓
Formula String  ──▶  Parser  ──▶  Operator Engine  ──▶  Alpha Series
                                                   ↓
                                              IC Backtester
                                                   ↓
                                          Signal Quality Metrics
```

The architecture mirrors **WorldQuant-style alpha mining pipelines**.

---

## 3. Data Model (Critical)

### Input data format (long / panel format)

All data is stored and processed as:

| date | ticker | open | high | low | close | volume | adj_close |
| ---- | ------ | ---- | ---- | --- | ----- | ------ | --------- |

This enables:

* **Time-series ops** → `groupby(ticker)`
* **Cross-sectional ops** → `groupby(date)`

Before alpha evaluation, data is indexed as:

```python
df.set_index(["date", "ticker"]).sort_index()
```

---

## 4. File-by-File Breakdown

### `data_ingestion.py`

**Purpose**: Fetch and store OHLCV data from Yahoo Finance.

Key points:

* Uses `yfinance`
* Saves data locally to `data/raw/yfinance/ohlcv.csv`
* Returns a long-format DataFrame
* Intended to be replaced later with CSI300 constituent feeds

---

### `operators.py`

**Purpose**: Implements all Appendix-A operators from the paper.

Operator categories:

#### Cross-sectional Unary (CS–U)

* `xAbs(x)`
* `xLog(x)`

#### Cross-sectional Binary (CS–B)

* `Add(x, y)`
* `Sub(x, y)`
* `Mul(x, y)`
* `Div(x, y)`
* `Greater(x, y)`
* `Less(x, y)`

#### Time-series Unary (TS–U)

* `Ref(x, t)`
* `Mean(x, t)`
* `Med(x, t)`
* `Sum(x, t)`
* `Std(x, t)`
* `Var(x, t)`
* `Max(x, t)`
* `Min(x, t)`
* `Mad(x, t)`
* `Delta(x, t)`
* `WMA(x, t)`
* `EMA(x, t)`

#### Time-series Binary (TS–B)

* `Cov(x, y, t)`
* `Corr(x, y, t)`

All operators:

* Accept `pd.Series` indexed by `(date, ticker)`
* Return `pd.Series`
* Are composable and parser-friendly

---

### `parser.py`

**Purpose**: Safely parse and evaluate LLM-style alpha expressions.

Key design decisions:

* Uses Python `ast` (no `eval`)
* Only allows:

  * Function calls
  * Variable names
  * Numeric constants
* Explicitly blocks:

  * Infix math (`+`, `-`, etc.)
  * Attribute access
  * Imports or lambdas

Example supported expressions:

```
Var(close, 20)
Sub(Delta(xLog(close), 5), Mean(close, 20))
Corr(close, volume, 10)
```

The parser maps expression tokens directly to functions in `operators.py`.

---

### `backtester.py`

**Purpose**: Evaluate alpha quality using IC and Rank IC.

#### Forward return definition

```
20-day forward return = Ref(close, -20) / close - 1
```

#### Metrics implemented

* **IC (Information Coefficient)**

  * Daily cross-sectional Pearson correlation between alpha and future returns

* **Rank IC**

  * Same as IC, but using ranked values

* **ICIR**

  * Mean(IC) / Std(IC)

#### IC Interpretation helper

IC strength is classified as:

| IC Mean   | Interpretation |
| --------- | -------------- |
| < 0.01    | Noise          |
| 0.01–0.02 | Weak           |
| 0.02–0.03 | Moderate       |
| 0.03–0.05 | Strong         |
| > 0.05    | Very Strong    |

#### Optional: Simple PnL backtest

* Daily long-short portfolio
* Long top quantile, short bottom quantile
* Dollar neutral
* No transaction costs

This is **educational**, not the primary research metric.

---

### `run_example.py`

**Purpose**: End-to-end demo.

Pipeline:

1. Fetch OHLCV data
2. Build panel (`date`, `ticker` index)
3. Parse an alpha expression
4. Compute IC / Rank IC
5. (Optionally) compute PnL

This file represents how an **LLM-generated expression would flow through the system**.

---

## 5. Conceptual Clarifications (Very Important)

### IC vs PnL

* **IC measures signal quality**, not money
* **PnL depends on portfolio construction choices**
* Alpha-mining research optimizes IC first

Mental model:

```
Alpha → Ranking → Portfolio → PnL
        ↑
        IC measures this
```

This is why the paper focuses on IC / ICIR.

---

## 6. What Is Complete vs Missing

### Implemented

* Data ingestion
* Operator engine
* Expression parsing
* IC / Rank IC evaluation
* Simple long-short PnL

### Not implemented (future work)

* Alpha set containers
* Alpha ensemble weighting
* Reinforcement learning optimization
* LLM prompting / mutation loops
* Transaction costs & turnover constraints

---

## 7. Intended Next Extensions

Logical next steps (in order):

1. Alpha set + ensemble weighting
2. RL-based alpha selection
3. LLM-triggered alpha mutation
4. Multi-round interaction loop (as in the paper)

---

## 8. Key Design Philosophy

* **Research correctness over trading realism**
* **Strict syntax to support LLM generation**
* **Separation of concerns** (data, operators, parsing, evaluation)
* **Reproducibility and interpretability first**

This codebase is a **research scaffold**, not a production trading system.

---

## 9. One-line Summary

> This repository implements the full execution and evaluation backbone for formulaic alpha mining, enabling safe LLM-generated expressions to be parsed, executed on panel data, and evaluated using IC-based metrics consistent with academic quant research.
