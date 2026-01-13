# Alpha-Mining Codebase — API & Data Reference

This document is a **technical API reference** for the alpha-mining backtesting codebase.

It enumerates **all modules, classes, functions, arguments, return types, and data schemas**. It is intended to allow ChatGPT (or a developer) to reason about the code **without seeing the source files**.

---

## 1. Global Data Conventions

### 1.1 Core DataFrame Schema (Raw Data)

All market data is stored in **long / panel format**:

```
date        : datetime64[ns]
ticker      : str
open        : float
high        : float
low         : float
close       : float
adj_close   : float
volume      : float
```

### 1.2 Indexed Panel Format (Critical)

Before alpha evaluation, data MUST be indexed as:

```python
(df
 .set_index(["date", "ticker"])
 .sort_index()
)
```

This yields:

```
MultiIndex:
  level 0 → date
  level 1 → ticker
```

All operators, parser logic, and backtesting logic **assume this index structure**.

---

## 2. `data_ingestion.py`

### Purpose

Fetch OHLCV data from Yahoo Finance and store it locally for reproducible backtesting.

---

### Function: `fetch_ohlcv`

```python
fetch_ohlcv(
    tickers: list[str],
    start: str = "2010-01-01",
    end: str | None = None,
    interval: str = "1d",
    save: bool = True
) -> pd.DataFrame
```

#### Description

- Downloads OHLCV data using `yfinance`
- Converts it to long-format panel data
- Optionally saves to `data/raw/yfinance/ohlcv.csv`

#### Returns

A `pd.DataFrame` with columns:

```
date | ticker | open | high | low | close | adj_close | volume
```

---

## 3. `operators.py`

### Purpose

Implements **all formulaic alpha operators** described in Appendix A of the paper.

All operators:

- Accept `pd.Series`
- Assume `(date, ticker)` MultiIndex
- Return `pd.Series`

---

### 3.1 Cross-Sectional Unary (CS–U)

```python
xAbs(x: pd.Series) -> pd.Series
xLog(x: pd.Series) -> pd.Series
```

| Function | Description                 |
| -------- | --------------------------- |
| `xAbs`   | Absolute value              |
| `xLog`   | Natural logarithm (0 → NaN) |

---

### 3.2 Cross-Sectional Binary (CS–B)

```python
Add(x, y)
Sub(x, y)
Mul(x, y)
Div(x, y)
Greater(x, y)
Less(x, y)
```

| Function  | Description           |
| --------- | --------------------- |
| `Add`     | x + y                 |
| `Sub`     | x − y                 |
| `Mul`     | x × y                 |
| `Div`     | x / y (0 → NaN)       |
| `Greater` | elementwise max(x, y) |
| `Less`    | elementwise min(x, y) |

---

### 3.3 Time-Series Unary (TS–U)

All TS operators operate **per ticker** using `groupby(level="ticker")`.

```python
Ref(x, t)
Mean(x, t)
Med(x, t)
Sum(x, t)
Std(x, t)
Var(x, t)
Max(x, t)
Min(x, t)
Mad(x, t)
Delta(x, t)
WMA(x, t)
EMA(x, t)
```

| Function | Definition                 |
| -------- | -------------------------- |
| `Ref`    | x shifted by t days        |
| `Mean`   | Rolling mean               |
| `Med`    | Rolling median             |
| `Sum`    | Rolling sum                |
| `Std`    | Rolling std                |
| `Var`    | Rolling variance           |
| `Max`    | Rolling max                |
| `Min`    | Rolling min                |
| `Mad`    | Mean absolute deviation    |
| `Delta`  | x − Ref(x, t)              |
| `WMA`    | Weighted moving average    |
| `EMA`    | Exponential moving average |

---

### 3.4 Time-Series Binary (TS–B)

```python
Cov(x, y, t)
Corr(x, y, t)
```

| Function | Description                 |
| -------- | --------------------------- |
| `Cov`    | Rolling covariance          |
| `Corr`   | Rolling Pearson correlation |

---

## 4. `parser.py`

### Purpose

Safely parse and evaluate LLM-generated alpha expressions.

---

### Class: `AlphaExpressionParser`

```python
AlphaExpressionParser(
    variables: dict[str, pd.Series]
)
```

#### Constructor Arguments

| Name        | Type | Description                                             |
| ----------- | ---- | ------------------------------------------------------- |
| `variables` | dict | Maps variable names (`close`, `volume`, etc.) to Series |

---

### Method: `parse`

```python
parse(expr: str) -> pd.Series
```

#### Description

- Parses expression using Python AST
- Evaluates recursively
- Maps function names to `operators.py`

---

### Allowed Syntax

✔ Function calls
✔ Variable names
✔ Numeric constants
✔ Nested expressions

❌ Infix math (`+`, `-`)
❌ Attribute access
❌ Imports
❌ Lambdas

---

### Example Expressions

```
Var(close, 20)
Sub(Delta(xLog(close), 5), Mean(close, 20))
Corr(close, volume, 10)
```

---

## 5. `backtester.py`

### Purpose

Evaluate alpha signal quality using IC-based metrics.

---

### Class: `ICBacktester`

```python
ICBacktester(df: pd.DataFrame)
```

#### Required Columns in `df`

```
date | ticker | close
```

---

### Internal Forward Return Definition

```python
fwd_ret_20 = Ref(close, -20) / close - 1
```

---

### Method: `compute_ic`

```python
compute_ic(alpha: pd.Series) -> pd.Series
```

- Computes **daily cross-sectional Pearson correlation**
- Returns a time series indexed by date

---

### Method: `compute_rank_ic`

```python
compute_rank_ic(alpha: pd.Series) -> pd.Series
```

- Same as `compute_ic`
- Uses ranks instead of raw values

---

### Method: `interpret_ic`

```python
interpret_ic(ic: pd.Series) -> dict
```

Returns:

```
{
  "IC Mean": float,
  "IC Std": float,
  "ICIR": float,
  "Signal Strength": str
}
```

---

### Method: `long_short_pnl` (Optional)

```python
long_short_pnl(
    alpha: pd.Series,
    quantile: float = 0.2
) -> pd.Series
```

- Long top quantile
- Short bottom quantile
- Dollar neutral
- No transaction costs

Returns daily portfolio returns.

---

## 6. Execution Flow Summary

```text
Raw OHLCV Data
     ↓
Panel Data (MultiIndex)
     ↓
LLM Formula String
     ↓
AlphaExpressionParser
     ↓
Operator Engine
     ↓
Alpha Series
     ↓
ICBacktester
     ↓
IC / Rank IC / ICIR
```

---

## 7. Strict Assumptions (Do Not Violate)

- All Series must share the same `(date, ticker)` index
- No infix operators in expressions
- Time-series window `t` is an integer literal
- Missing values are expected and handled via NaNs

---

## 8. One-Sentence Mental Model

> This codebase is a deterministic execution engine that converts formulaic alpha expressions into cross-sectional ranking signals and evaluates their predictive power using IC-based metrics, independent of portfolio assumptions.
